"""Silent-degradation detector for multi-agent workflow runs.

The failure that broke the cost baseline (wf_3d01df61): a stage's agents can all ERROR — or run
anomalously cheap — while the run still reports a status and a plausible totalTokens, so a naive
per-stage decomposition silently mis-attributes cost (Fetch looked like 66% only because every
verifier crashed at ~1588 tok). This flags such stages so a cost number is never published on a
degraded run.
"""
import statistics

from agent_cost_attribution.ledger import agents


def detect_degradation(run, *, min_agents=5, cheap_ratio=0.25):
    """Findings (empty == healthy). Each: {stage, kind, severity, detail}.

    kind 'errors' : a stage has agents in state 'error'.
    kind 'cheap'  : a stage of >= min_agents whose mean tokens/agent is < cheap_ratio of the run-wide
                    baseline (median of per-stage mean costs) — the signature of a mass-degraded stage.
    """
    ags = agents(run)
    findings = []

    by_stage = {}
    for a in ags:
        by_stage.setdefault(a.stage, []).append(a)

    # Run-wide baseline: median of per-stage mean token costs (one data point per stage).
    # Using per-stage means rather than per-agent tokens prevents a degraded stage's own
    # cheap agents from dragging the median down and hiding itself.
    stage_means = [statistics.mean(r.tokens for r in rows)
                   for rows in by_stage.values() if rows]
    median = statistics.median(stage_means) if stage_means else 0

    for stage, rows in by_stage.items():
        errs = [r for r in rows if r.state == "error"]
        if errs:
            findings.append({"stage": stage, "kind": "errors", "severity": "high",
                             "detail": f"{len(errs)}/{len(rows)} agents in state 'error'"})
        if median and len(rows) >= min_agents:
            mean_tok = statistics.mean(r.tokens for r in rows)
            if mean_tok < cheap_ratio * median:
                findings.append({"stage": stage, "kind": "cheap", "severity": "high",
                                 "detail": f"mean {mean_tok:.0f} tok/agent over {len(rows)} agents "
                                           f"< {cheap_ratio:.0%} of run median {median:.0f}"})
    return findings


def is_healthy(run, **kw):
    return not detect_degradation(run, **kw)
