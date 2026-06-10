"""Route every model call to the cheapest sufficient model — the enforcement half of A1.

The meter (this repo) tells you WHERE tokens go per stage; this module is the policy layer
that makes the fix stick: a single role table maps each workload to a model + effort, so
"right-size the model per task" (PLAYBOOK A1) is one table instead of N scattered call
sites. The case study that produced this pattern is in ROUTING.md.

Design rules (each one earned by a real failure, see ROUTING.md):
- One table, no hardcoded models at call sites — an unpinned call silently inherits your
  most expensive default.
- Unknown role -> KeyError (fail closed): a typo'd role must surface, not silently route.
- Overrides file -> fail SOFT: a corrupt tuning file must degrade to defaults, never
  silence a production routine.
- Per-message escalation is IMPERATIVE-ONLY and tag-overridable: a missed escalation is
  recoverable (the user types the tag); a false escalation silently burns budget.

Dependency-free, ~120 lines. Pair with `pricing.savings_estimate`-style numbers via
`savings_estimate()` below — but treat those as planning estimates; the meter measures.
"""
import json
import re
from pathlib import Path


class Router:
    """Role -> {"model", "effort"} resolution with optional fail-soft file overrides.

    `roles` is your table, e.g. {"chat": {"model": "...", "effort": "medium"}, ...}.
    `overrides_path` (JSON: {role: {model?, effort?}}) lets you re-route live without a
    deploy; partial overrides merge over defaults, garbage is ignored per-key.
    """

    def __init__(self, roles, overrides_path=None):
        self.roles = dict(roles)
        # Coerce str -> Path: fail-soft is for CORRUPT files, not for hiding a caller's
        # type mistake (a str path silently disabling live tuning is the worst outcome).
        self.overrides_path = (Path(overrides_path) if isinstance(overrides_path, str)
                               else overrides_path)

    def _overrides(self):
        if self.overrides_path is None:
            return {}
        try:
            loaded = json.loads(self.overrides_path.read_text())
        except (OSError, ValueError, TypeError):
            return {}
        return loaded if isinstance(loaded, dict) else {}

    def resolve(self, role):
        """{"model", "effort"} for `role`. Unknown role raises KeyError (fail closed)."""
        cfg = dict(self.roles[role])
        ov = self._overrides().get(role)
        if isinstance(ov, dict):
            m = ov.get("model")
            if isinstance(m, str) and m.strip():
                cfg["model"] = m.strip()
            if "effort" in ov:
                e = ov["effort"]
                cfg["effort"] = e.strip() if isinstance(e, str) and e.strip() else None
        return cfg

    def model_for(self, role):
        return self.resolve(role)["model"]

    def effort_for(self, role):
        return self.resolve(role)["effort"]


class MessageRouter:
    """Per-message routing for a chat-style agent: explicit !tag > escalation regex >
    cheap default. The tag is stripped from the text before the model sees it.

    `tags` maps tag names to {"model", "effort"} (typed as `!name` anywhere in a message).
    `deep_pattern` is YOUR escalation regex — keep it imperative-only (see module
    docstring for why false escalations are the failure mode, not missed ones).
    """

    def __init__(self, router, *, tags, deep_pattern,
                 default_role="chat", deep_role="chat_deep"):
        self.router = router
        self.tags = {k.lower(): dict(v) for k, v in tags.items()}
        if self.tags:
            names = "|".join(re.escape(k) for k in sorted(self.tags))
            self._tag_re = re.compile(rf"(?:(?<=\s)|^)!({names})\b", re.I)
        else:
            self._tag_re = re.compile(r"(?!x)x")     # never matches: no tags configured
        self._deep_re = re.compile(deep_pattern, re.I)
        self.default_role = default_role
        self.deep_role = deep_role

    def route(self, text):
        """Returns ({"model", "effort"}, cleaned_text)."""
        text = text if isinstance(text, str) else ""
        m = self._tag_re.search(text)
        if m:
            cleaned = self._tag_re.sub("", text, count=1)
            cleaned = re.sub(r"[ \t]{2,}", " ", cleaned).strip()
            return dict(self.tags[m.group(1).lower()]), cleaned
        if self._deep_re.search(text):
            return self.router.resolve(self.deep_role), text
        return self.router.resolve(self.default_role), text


def savings_estimate(traffic, roles, *, baseline_model, input_share=None):
    """PLANNING estimate of routed vs uniform-baseline spend. NOT a measurement.

    `traffic` maps role -> token volume (get real volumes from the meter's per-stage
    waterfall). Returns {"baseline_usd", "routed_usd", "saved_usd", "saved_pct"}, priced
    with this repo's `pricing` blended rates (same caveats: list prices, input-share
    assumption). Publish measured deltas from the meter, not this — this is for deciding
    whether the routing work is worth doing.
    """
    from agent_cost_attribution import pricing
    share = pricing.DEFAULT_INPUT_SHARE if input_share is None else input_share
    router = Router(roles)
    baseline = routed = 0.0
    for role, tokens in traffic.items():
        baseline += pricing.estimate_cost(tokens, baseline_model, input_share=share)
        routed += pricing.estimate_cost(tokens, router.model_for(role), input_share=share)
    saved = baseline - routed
    return {"baseline_usd": baseline, "routed_usd": routed, "saved_usd": saved,
            "saved_pct": (100.0 * saved / baseline) if baseline else 0.0}
