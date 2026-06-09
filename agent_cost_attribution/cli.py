"""CLI: python -m agent_cost_attribution <run.json | run-dir> ...

Prints a per-stage token waterfall + a silent-degradation health report for each run. Workload-
agnostic: any wf_*.json (or a directory of them) works — this is the reusable surface.
"""
import sys
from pathlib import Path

from agent_cost_attribution.ledger import load_run, summary
from agent_cost_attribution.health import detect_degradation
from agent_cost_attribution.pricing import cost_by_stage, DEFAULT_INPUT_SHARE


def _iter_paths(args):
    for a in args:
        p = Path(a)
        if p.is_dir():
            yield from sorted(p.glob("wf_*.json"))
        else:
            yield p


def render(run, *, input_share=DEFAULT_INPUT_SHARE):
    s = summary(run)
    costs = cost_by_stage(run, input_share=input_share)
    total_usd = sum(costs.values())
    head = (f"{s['workflow'] or '?'}  {s['run_id']}  status={s['status']}  "
            f"total={s['total_tokens']:,} tok  ~${total_usd:,.2f}  invariant_ok={s['invariant_ok']}")
    lines = [head]
    for stage, st in sorted(s["stages"].items(), key=lambda kv: -kv[1]["tokens"]):
        bar = "#" * int(round(st["pct"] / 2))
        usd = costs.get(stage, 0.0)
        lines.append(f"  {stage:14s} {st['tokens']:>9,}  {st['pct']:5.1f}%  ~${usd:>7,.2f}  n={st['count']:<3d} {bar}")
    findings = detect_degradation(run)
    if findings:
        lines.append("  ! DEGRADED — cost numbers on this run are NOT publishable:")
        for f in findings:
            lines.append(f"      [{f['severity']}] {f['stage']}: {f['kind']} — {f['detail']}")
    lines.append(f"  ($ = estimate: list prices, {input_share:.0%}-input blend; telemetry has no I/O split)")
    return "\n".join(lines)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        print("usage: python -m agent_cost_attribution <run.json | run-dir> ...", file=sys.stderr)
        return 2
    paths = list(_iter_paths(argv))
    if not paths:
        print("no run files found", file=sys.stderr)
        return 1
    for p in paths:
        run = load_run(p)
        if not run:
            print(f"{p}: unreadable/empty", file=sys.stderr)
            continue
        print(render(run))
        print()
    return 0
