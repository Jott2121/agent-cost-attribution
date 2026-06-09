"""Estimated dollar cost for token counts, by model.

CAVEAT (important, surfaced in output): workflow telemetry reports a SINGLE token count per agent with
NO input/output split. Dollar figures are therefore ESTIMATES — we price the token count at a per-model
blended rate using a configurable input-share assumption (default 0.85: agentic/tool-heavy runs are
input-dominated). Prices are public list prices and change over time; update PRICES as needed.
"""

# $ per 1,000,000 tokens, as (input, output). Public list prices — update as they change.
PRICES = {
    "opus":   (15.0, 75.0),
    "sonnet": (3.0, 15.0),
    "haiku":  (1.0, 5.0),
}
_UNKNOWN = PRICES["opus"]          # unknown model → priced as opus (conservative / high end)
DEFAULT_INPUT_SHARE = 0.85


def _tier(model):
    m = (model or "").lower()
    for tier in ("opus", "sonnet", "haiku"):
        if tier in m:
            return tier
    return None


def blended_rate(model, *, input_share=DEFAULT_INPUT_SHARE):
    """Blended $ per single token for `model`, given the input-share assumption."""
    inp, outp = PRICES.get(_tier(model), _UNKNOWN)
    per_mtok = input_share * inp + (1.0 - input_share) * outp
    return per_mtok / 1_000_000.0


def estimate_cost(tokens, model, *, input_share=DEFAULT_INPUT_SHARE):
    """Estimated USD to process `tokens` on `model`. An ESTIMATE — see module caveat."""
    return (tokens or 0) * blended_rate(model, input_share=input_share)


def cost_by_stage(run, *, input_share=DEFAULT_INPUT_SHARE):
    """{stage: estimated USD}, summed PER AGENT (so per-agent model routing is reflected)."""
    from agent_cost_attribution.ledger import agents
    out = {}
    for a in agents(run):
        out[a.stage] = out.get(a.stage, 0.0) + estimate_cost(a.tokens, a.model, input_share=input_share)
    return out


def total_cost(run, *, input_share=DEFAULT_INPUT_SHARE):
    """Estimated USD for the whole run."""
    return sum(cost_by_stage(run, input_share=input_share).values())
