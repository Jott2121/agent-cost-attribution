"""Per-stage token attribution for multi-agent workflow runs.

Reusable + stdlib-only: reads platform workflow telemetry (wf_*.json) and decomposes totalTokens
across stages (phases). No dependency on any workflow's internals, so it works for ANY workflow run,
not just deep-research.

Verified schema: a run JSON has top-level `totalTokens` and `workflowProgress`, a list whose entries
are either type=="workflow_phase" (headers, no tokens) or type=="workflow_agent" (per-agent records
with `phaseTitle`, `state`, `tokens`, `model`). Invariant: agent tokens sum EXACTLY to totalTokens.

Fail-soft: a missing/corrupt run degrades to {}, never crashes a caller.
"""
import json
from dataclasses import dataclass
from pathlib import Path

_AGENT = "workflow_agent"


def _as_int(value):
    """Coerce to int, fail-soft to 0 (a corrupt token/count field must never crash a parse)."""
    try:
        return int(value or 0)
    except (ValueError, TypeError):
        return 0


@dataclass(frozen=True)
class AgentRecord:
    agent_id: str
    label: str
    stage: str
    model: str
    state: str
    tokens: int
    tool_calls: int


def load_run(path):
    """Load a run JSON; fail-soft to {} on missing/corrupt/non-object."""
    try:
        data = json.loads(Path(path).read_text())
    except (OSError, ValueError, TypeError):
        return {}
    return data if isinstance(data, dict) else {}


def agents(run):
    """Per-agent records (type==workflow_agent). Phase-header rows are skipped."""
    out = []
    for e in (run.get("workflowProgress") or []):
        if not isinstance(e, dict) or e.get("type") != _AGENT:
            continue
        out.append(AgentRecord(
            agent_id=e.get("agentId", ""),
            label=e.get("label", ""),
            stage=e.get("phaseTitle", "?"),
            model=e.get("model", ""),
            state=e.get("state", "?"),
            tokens=_as_int(e.get("tokens")),
            tool_calls=_as_int(e.get("toolCalls")),
        ))
    return out


def total_tokens(run):
    """The run's reported total token count, fail-soft to 0."""
    return _as_int(run.get("totalTokens"))


def decompose(run):
    """{stage: summed tokens}, preserving first-seen (phase) order."""
    out = {}
    for a in agents(run):
        out[a.stage] = out.get(a.stage, 0) + a.tokens
    return out


def verify_invariant(run):
    """True iff per-agent tokens sum to the run's totalTokens — the parser's correctness check.

    A run with no agent rows returns False (no data is not a satisfied invariant)."""
    ags = agents(run)
    if not ags:
        return False
    return sum(a.tokens for a in ags) == total_tokens(run)


def summary(run):
    """Per-stage decomposition with pct/count/state-mix, plus the invariant flag."""
    tot = total_tokens(run)
    stages = {}
    for a in agents(run):
        s = stages.setdefault(a.stage, {"tokens": 0, "count": 0, "states": {}})
        s["tokens"] += a.tokens
        s["count"] += 1
        s["states"][a.state] = s["states"].get(a.state, 0) + 1
    for s in stages.values():
        s["pct"] = round(100 * s["tokens"] / tot, 1) if tot else 0.0
    return {
        "run_id": run.get("runId", ""),
        "workflow": run.get("workflowName", ""),
        "status": run.get("status", ""),
        "total_tokens": tot,
        "invariant_ok": verify_invariant(run),
        "stages": stages,
    }
