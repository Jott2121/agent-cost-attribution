---
name: verify-receipts
description: Use before opening or updating a PR, or when README/docs numbers change. Re-runs this repo's tests and receipt checks, cross-checks the headline 67% cost cut, and writes a receipts block for the PR body.
---
# Verify receipts (agent-cost-attribution)

1. Read AGENTS.md "Commands". From a clean checkout run:

```bash
python -m pip install -e ".[dev]"
python -m pytest -q --cov=agent_cost_attribution --cov-report=term-missing --cov-fail-under=90
python -m agent_cost_attribution examples/sample-run.json
python scripts/check_receipts.py
```

There is no ruff or mypy config. Do not invent a lint gate. Capture exit codes, the last ~20 lines of pytest, and the full `check_receipts.py` output.

2. Headline number (do not change it): **67% cost cut, ~$0.60 → ~$0.20**, with the same four facts extracted.

   - **Re-derived offline.** `scripts/check_receipts.py` prices the stage token totals printed in `examples/routing-savings.md` with `agent_cost_attribution.pricing.estimate_cost` (Opus for the baseline; Haiku for the routed extractors; Opus for the synthesizer; 85% input blend). The rounded totals are ~$0.60 and ~$0.20, and `(0.60 − 0.20) / 0.60` rounds to 67%. The same script checks that the README sample-run fence matches `python -m agent_cost_attribution examples/sample-run.json` byte for byte (trailing whitespace aside).
   - **Not re-derivable offline.** The token counts (74,991 and 67,684) and the "identical facts extracted" claim come from two live runs of `examples/routing-demo.js` (`{route:false}`, then `{route:true}`). Telemetry ids `wf_5ba026c3-250` and `wf_8e2be971-29e` are not committed, and the demo script needs an agent runtime. When `check_receipts.py` prints UNVERIFIED for that half, leave the published number alone and copy the UNVERIFIED note into the PR. Do not backfill synthetic telemetry to make the live half look reproduced.

3. `git diff origin/main -- README.md examples/ PLAYBOOK.md ROUTING.md` — list every number that changed. For each, name the command that produces it and re-run it. If you can't reproduce it, mark it UNVERIFIED and stop; do not open the PR as ready.

4. Run `python scripts/scan_employer_terms.py` (must exit 0; 1 is a hit, 2 means it could not scan) and grep the diff for secret and export-control patterns (see `.cursor/rules/40-security-and-data.mdc`). Any new hit is a stop. This repo's author bio does not name an employer, and CI scans the README on purpose.

5. Confirm no thresholds were lowered (`--cov-fail-under=90` stays 90) and no tests were skipped, xfailed, or removed.

6. Output a Markdown block:

   - Commands run + pass/fail
   - Numbers: before → after → command → reproduced? (Y/N). For the headline, Y means the dollar and percent arithmetic, N means the live token counts and the facts claim, with the reason in step 2.
   - Not verified / known gaps

7. Paste that block into the PR's "How verified" section. Never claim a check passed that you didn't run.
