#!/usr/bin/env python3
"""Recompute published receipts that can be checked offline.

The headline 67% (~$0.60 → ~$0.20) is a cost-axis claim. This script re-derives
the dollar figures and the percentage from the stage token totals printed in
examples/routing-savings.md, priced by agent_cost_attribution.pricing (the same
85% input blend the meter uses).

It does not re-run examples/routing-demo.js. That file is a live agent workflow,
and the wf_*.json telemetry is not in the repo, so the token counts and the
"identical facts" claim stay UNVERIFIED. A clean exit means the offline half
matches; it does not mean the live half was re-run.
"""
from __future__ import annotations

import difflib
import re
import subprocess
import sys
from pathlib import Path
from typing import NamedTuple, NoReturn

from agent_cost_attribution.pricing import estimate_cost

ROOT = Path(__file__).resolve().parents[1]
RECEIPT = ROOT / "examples" / "routing-savings.md"
README = ROOT / "README.md"

SECTION_RE = re.compile(
    r"\*\*(?P<heading>Baseline[^*]*|Routed[^*]*)\*\*\s*```\n(?P<body>.*?)```",
    re.S,
)
HEAD_RE = re.compile(
    r"^routing-demo\s+(?P<run>\S+)\s+status=\S+\s+total=(?P<tokens>[\d,]+) tok\s+"
    r"~\$?(?P<usd>[\d,.]+)\s+invariant_ok=(?P<inv>\w+)",
    re.M,
)
STAGE_RE = re.compile(
    r"^  (?P<stage>\S+)\s+(?P<tokens>[\d,]+)\s+(?P<pct>[\d.]+)%\s+"
    r"~\$\s*(?P<usd>[\d,.]+)\s+n=(?P<n>\d+)",
    re.M,
)

README_NEEDLES = (
    "67% (~$0.60 → ~$0.20)",
    "67% (~$0.60 to ~$0.20)",
)


class Head(NamedTuple):
    run: str
    tokens: int
    usd: str
    invariant: str


class Stage(NamedTuple):
    stage: str
    tokens: int
    pct: float
    usd: str
    n: int
    model: str


def fail(msg: str) -> NoReturn:
    print(f"FAIL: {msg}", file=sys.stderr)
    raise SystemExit(1)


def money(raw: str) -> str:
    return raw.replace(",", "")


def model_for(heading: str, stage: str) -> str:
    lowered = heading.lower()
    if lowered.startswith("baseline") and "opus" in lowered and "haiku" not in lowered:
        return "opus"
    if lowered.startswith("routed") and "haiku" in lowered and "opus" in lowered:
        if stage.lower().startswith("extract"):
            return "haiku"
        if stage.lower().startswith("synth"):
            return "opus"
        fail(f"no model rule for routed stage {stage!r} under {heading!r}")
    fail(f"cannot assign models from heading {heading!r}")


def parse_sections(text: str) -> list[tuple[str, Head, list[Stage]]]:
    found = list(SECTION_RE.finditer(text))
    if len(found) != 2:
        fail(f"expected 2 meter blocks in {RECEIPT.name}, found {len(found)}")
    parsed: list[tuple[str, Head, list[Stage]]] = []
    for match in found:
        heading = match.group("heading").strip()
        body = match.group("body")
        heads = list(HEAD_RE.finditer(body))
        if len(heads) != 1:
            fail(f"{heading}: expected 1 run header, found {len(heads)}")
        head_m = heads[0]
        head = Head(
            run=head_m.group("run"),
            tokens=int(head_m.group("tokens").replace(",", "")),
            usd=money(head_m.group("usd")),
            invariant=head_m.group("inv"),
        )
        stages: list[Stage] = []
        for stage_m in STAGE_RE.finditer(body):
            stage_name = stage_m.group("stage")
            stages.append(
                Stage(
                    stage=stage_name,
                    tokens=int(stage_m.group("tokens").replace(",", "")),
                    pct=float(stage_m.group("pct")),
                    usd=money(stage_m.group("usd")),
                    n=int(stage_m.group("n")),
                    model=model_for(heading, stage_name),
                )
            )
        if {s.stage for s in stages} != {"Extract", "Synthesize"}:
            fail(f"{heading}: expected Extract and Synthesize, found {[s.stage for s in stages]}")
        parsed.append((heading, head, stages))
    return parsed


def check_run(heading: str, head: Head, stages: list[Stage]) -> float:
    if head.invariant != "True":
        fail(f"{heading}: invariant_ok is {head.invariant}, expected True")
    if sum(s.tokens for s in stages) != head.tokens:
        fail(f"{heading}: stage tokens do not sum to {head.tokens}")
    total = 0.0
    for stage in stages:
        pct = round(100 * stage.tokens / head.tokens, 1)
        if pct != stage.pct:
            fail(f"{heading} {stage.stage}: pct {stage.pct} != recomputed {pct}")
        est = estimate_cost(stage.tokens, stage.model)
        shown = f"{est:.2f}"
        if shown != stage.usd:
            fail(
                f"{heading} {stage.stage}: pricing.estimate_cost({stage.tokens}, {stage.model!r}) "
                f"rounds to {shown}, receipt shows {stage.usd}"
            )
        total += est
        print(
            f"  {stage.stage:12} {stage.tokens:>7} tok  model={stage.model:5}  "
            f"exact=${est:.6f}  rounded=${shown}  published=${stage.usd}"
        )
    rounded_total = f"{total:.2f}"
    if rounded_total != head.usd:
        fail(f"{heading}: summed estimate rounds to {rounded_total}, receipt shows {head.usd}")
    print(f"  total exact=${total:.6f}  rounded=${rounded_total}  published=${head.usd}  run={head.run}")
    return total


def check_table(text: str, baseline: Head, routed: Head, base_stages: list[Stage], routed_stages: list[Stage]) -> None:
    row = "| **Run cost** | ~$0.60 | ~$0.20 | **−$0.40 / −67%** |"
    if row not in text:
        fail("result table run-cost row drifted from ~$0.60 / ~$0.20 / −67%")
    if baseline.usd != "0.60" or routed.usd != "0.20":
        fail(f"headline dollars are ${baseline.usd} → ${routed.usd}, expected $0.60 → $0.20")
    cut = round((float(baseline.usd) - float(routed.usd)) / float(baseline.usd) * 100)
    if cut != 67:
        fail(f"rounded-dollar cut is {cut}%, expected 67%")
    token_pct = (baseline.tokens - routed.tokens) / baseline.tokens * 100
    if f"{token_pct:.1f}" != "9.7":
        fail(f"token delta is {token_pct:.1f}%, receipt table expects 9.7%")
    if "−9.7%" not in text:
        fail("token delta row −9.7% missing from the receipt table")

    def stage_usd(stages: list[Stage], name: str) -> str:
        for stage in stages:
            if stage.stage == name:
                return stage.usd
        fail(f"missing stage {name}")

    extract_base = float(stage_usd(base_stages, "Extract"))
    extract_routed = float(stage_usd(routed_stages, "Extract"))
    extract_cut = round((extract_base - extract_routed) / extract_base * 100)
    ratio = round(extract_base / extract_routed, 1)
    extract_row = (
        f"| Extract stage | ~${stage_usd(base_stages, 'Extract')} | "
        f"~${stage_usd(routed_stages, 'Extract')} | **−{extract_cut}% (~{ratio}× cheaper)** |"
    )
    if extract_row not in text:
        fail(f"extract-stage table row drifted (expected {extract_row})")
    synth_row = "| Synthesize stage | ~$0.11 | ~$0.11 | unchanged (kept on Opus) ✓ |"
    if synth_row not in text:
        fail("synthesize-stage table row drifted")
    if "67%" not in text.splitlines()[0]:
        fail("receipt title no longer states 67%")


def plain_fences(text: str) -> list[str]:
    """Bodies of fences opened by a line that is exactly ``` (not ```bash).

    Closers are always a line that is exactly ```, including the closer of a
    ```bash fence. Those closers must not be treated as the next opener.
    """
    lines = text.splitlines()
    bodies: list[str] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        if line.startswith("```"):
            plain = line == "```"
            index += 1
            body: list[str] = []
            while index < len(lines) and lines[index] != "```":
                body.append(lines[index])
                index += 1
            if plain:
                bodies.append("\n".join(body))
        index += 1
    return bodies


def check_readme(readme: str) -> None:
    for needle in README_NEEDLES:
        if needle not in readme:
            fail(f"README missing published headline phrase: {needle}")
    quoted = next((b for b in plain_fences(readme) if b.startswith("sample-research")), None)
    if quoted is None:
        fail("README has no sample-research meter fence")
    proc = subprocess.run(
        [sys.executable, "-m", "agent_cost_attribution", "examples/sample-run.json"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        fail(f"sample meter exited {proc.returncode}: {proc.stderr.strip()}")
    actual = proc.stdout.strip("\n")
    if actual != quoted:
        diff = "".join(
            difflib.unified_diff(
                quoted.splitlines(keepends=True),
                actual.splitlines(keepends=True),
                fromfile="README.md fence",
                tofile="python -m agent_cost_attribution examples/sample-run.json",
            )
        )
        fail("README sample-run quote does not match the meter:\n" + diff)
    print("  README sample-run fence matches python -m agent_cost_attribution examples/sample-run.json")


def main() -> int:
    receipt = RECEIPT.read_text(encoding="utf-8")
    readme = README.read_text(encoding="utf-8")
    sections = parse_sections(receipt)
    print("Headline dollars recomputed from examples/routing-savings.md via pricing.estimate_cost:")
    exact: list[float] = []
    for heading, head, stages in sections:
        print(f"- {heading}")
        exact.append(check_run(heading, head, stages))
    baseline_h, routed_h = sections[0][1], sections[1][1]
    check_table(receipt, baseline_h, routed_h, sections[0][2], sections[1][2])
    exact_cut = (exact[0] - exact[1]) / exact[0] * 100
    if round(exact_cut) != 67:
        fail(f"exact-estimate cut rounds to {round(exact_cut)}%, expected 67% ({exact_cut:.2f}%)")
    print(f"  rounded dollars (0.60−0.20)/0.60 = 67%")
    print(f"  exact estimates ${exact[0]:.6f} → ${exact[1]:.6f} = {exact_cut:.2f}% (rounds to 67%)")
    print("Sample quickstart:")
    check_readme(readme)
    print()
    print("UNVERIFIED (known gap, not a failure):")
    print(
        "  Token counts "
        f"({baseline_h.tokens:,} on {baseline_h.run}, {routed_h.tokens:,} on {routed_h.run}) "
        "and the claim that both runs extracted the same four facts come from live runs of "
        "examples/routing-demo.js ({route:false} then {route:true}). Those wf_*.json files are "
        "not committed, and the demo needs an agent runtime, so this half cannot be re-derived offline."
    )
    print(
        "  examples/self-correction-deep-research.md and the dollar projections in PLAYBOOK.md "
        "are narrative; they have no committed telemetry either."
    )
    print(
        "  Per-agent counts inside each stage (n=4 extractors, n=1 synthesizer) are part of that "
        "live receipt. Stage totals are enough to re-price the dollars because cost is linear and "
        "every agent in a stage is on one model."
    )
    print()
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
