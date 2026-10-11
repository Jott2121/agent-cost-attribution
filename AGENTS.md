# AGENTS.md — agent-cost-attribution

> Portable agent instructions. Read by Cursor (local and cloud agents), Claude Code, Codex, and Grok Bot cloud-agent runs.
> Keep this file under ~150 lines. Procedures live in `.cursor/skills/`. Scoped rules live in `.cursor/rules/*.mdc`. Review rules live in `.cursor/BUGBOT.md`.
> There is no CLAUDE.md. This file is the source of truth.

## What this repo is

A stdlib-only meter (`agent_cost_attribution`) and a playbook for cutting token burn in agentic coding without giving up capability. Point the meter at Claude Code workflow telemetry (`wf_*.json`) and it prints a per-stage token waterfall, an estimated dollar cost, and a silent-degradation check. Dollars are list-price estimates at an 85% input blend: the telemetry has no input/output split.

The headline receipt is a **67% cost cut (~$0.60 → ~$0.20)** from routing four mechanical extractors to a cheap model while the synthesizer stayed on the strong model, with the same four facts extracted. `python scripts/check_receipts.py` re-derives those dollars and the 67% from the stage token totals in `examples/routing-savings.md` using `pricing.estimate_cost`. The token counts and the "identical facts" claim come from live runs of `examples/routing-demo.js`. Those `wf_*.json` files are not in the repo, so that half cannot be re-derived offline. The script prints that gap. Do not change the published number.

- **Status:** active · **License:** MIT · **Package:** `agent-cost-attribution` on PyPI (v0.1.1)
- **Entry points:** `agent_cost_attribution/`, `tests/`, `examples/`, `scripts/check_receipts.py`
- **Part of:** the governed-agent stack (rag-guard · graph-guard · agent-gate · crucible · oracle-gate · agent-cost-attribution · bow · fleet-mode · sabot)

## Commands (run these; don't guess)

```bash
python -m pip install -e ".[dev]"
# lint / typecheck: n/a — this repo has no ruff or mypy config
python -m pytest -q --cov=agent_cost_attribution --cov-report=term-missing --cov-fail-under=90
python -m agent_cost_attribution examples/sample-run.json
python scripts/check_receipts.py
```

A task is not done until pytest passes at the coverage floor of 90 and `scripts/check_receipts.py` exits 0. Paste both outputs in the PR. The README's "currently 96% covered" is a point-in-time reading, not a second threshold. Do not lower `--cov-fail-under`.

## Non-negotiables

1. **No employer data. Ever.** Personal work on personal equipment. Never add, paste, paraphrase, or anonymize anything from Lockheed Martin systems, documents, tickets, chats, or datasets. No employer names in fixtures, no internal acronyms, no realistic HR records. Synthetic data only. If a prompt looks like it came from work, stop and ask. The author bio in the README does not name an employer, so CI scans it.
2. **Receipts over hype.** Every number in the README, docs, PR descriptions, or posts must be reproducible from a committed command, or explicitly marked UNVERIFIED the way the headline token counts are. Link the command and the artifact. No "blazing fast", "SOTA", or "production-grade" without a measurement.
3. **Honest benchmarks.** Report nulls and regressions at the same prominence as wins. State n, model, date, and that dollars are estimates. Never delete an inconvenient run; mark it superseded with a reason.
4. **Fail closed.** Gates and guards deny on error, timeout, missing input, or unparseable output. The meter's parser is fail-soft on a corrupt file (`{}`); the invariant is fail-closed (no agent rows means `invariant_ok=False`). Never weaken a guard to make a test pass. Never catch-and-ignore exceptions on a decision path.
5. **Tests and CI are the definition of done.** New behavior ships with a test that fails without it. Bug fixes ship with a regression test. Do not lower coverage floors. Do not mark tests `skip` or `xfail` to get green.
6. **Model never grades its own output.** Prefer mechanical verdicts (tests, the token invariant, `scripts/check_receipts.py`). Where a judge model is needed, use a different model lineage from the author and record both.
7. **Irreversible = human-gated.** No force-push, no history rewrite, no publishing to PyPI, no tagging releases, no posting. Open a PR; a human merges.

## Code style

- Python >=3.9. CI runs 3.9 through 3.13. Stay on syntax that floor supports. Stdlib-only at runtime; every new runtime dependency needs a one-line justification in the PR.
- Type hints on public functions. Small pure functions. No global mutable state.
- Raise specific exceptions. No bare `except` on a decision path.
- Secrets only via env vars. Never print secret values.
- Don't commit build output: `__pycache__/`, `*.pyc`, `.coverage`, `.venv/`, `.cursor/hook-logs/`.

## How to work in this repo

- Start non-trivial work in Plan mode; save the plan to `.cursor/plans/` and link it in the PR.
- Default to one agent. Fan out only for read-heavy, independent work. Writes stay single-threaded per file.
- Keep PRs small (under ~400 changed lines) with one intent. Title: `type(scope): summary`.
- PR body must include: **What / Why / How verified (commands + output) / Numbers changed (before → after, with command) / Risks / Not done**.
- When you learn something durable, propose an edit to this file or a skill in the same PR.

## Directory map

```
README.md                  headline and the 67% receipt link
PLAYBOOK.md                practices with savings, axis, risk, and effort
ROUTING.md                 case study: retrofitting model routing onto a live fleet
agent_cost_attribution/    meter: ledger, pricing, health, cli, routing.py
tests/                     pytest; the sum==total invariant is golden-tested
examples/sample-run.json   synthetic telemetry for the quickstart (not a measured run)
examples/routing-demo.js   live workflow that produced the 67% runs (needs an agent runtime)
examples/routing-savings.md  published before/after meter output
examples/self-correction-deep-research.md  narrative receipt; no committed telemetry
scripts/check_receipts.py  offline recompute of the headline dollars and the README sample quote
.github/workflows/         CI (pytest 3.9–3.13, coverage comment), CodeQL, publish
.cursor/                   rules, hooks, Bugbot, MCP, verify-receipts skill
```

## Known traps

- **The shell guard blocks `git pull --rebase`.** The hook matcher includes both `git pull` and `rebase`, so a rebasing pull reaches `.cursor/hooks/guard-shell.sh` and is denied, including forms with flags between `git` and the subcommand (`git -C dir rebase`, `git -c key rebase`). A plain `git pull` is allowed. A missing, blank, or non-string `command` is denied; invalid JSON exits non-zero (fail closed). Force-push is denied even when the flag is not adjacent to `push` (`git push origin --force`, `git push -f`), and so is a hard reset (`git reset HEAD --hard`). The guard also denies `git tag`, `twine upload`, `uv publish`, `gh release`, and pipe-to-shell. A non-force `git push`, and `curl`/`wget`, ask instead of running. Do not loosen the guard to finish a task.
- `~$` figures are estimates. Do not treat them as an invoice, and do not "correct" a published estimate because a newer list price would change it. Update `PRICES` only in a PR that shows before → after.
- `examples/sample-run.json` is synthetic and labeled as such. Don't cite it as a research result.
- `routing.savings_estimate()` is a planning estimate. Never publish it as a measurement.
- `examples/self-correction-deep-research.md` and the dollar projections in `PLAYBOOK.md` are not backed by committed `wf_*.json`. Leave them, or mark them UNVERIFIED. Don't invent telemetry.
