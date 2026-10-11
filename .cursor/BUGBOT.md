# .cursor/BUGBOT.md — review rules for agent-cost-attribution
# (Bugbot does NOT read .cursor/rules/*.mdc; it reads this file.)

Flag as **blocking**:
1. Any guard, gate, validator, or refusal path that now fails OPEN (returns allow/True/answer on exception, timeout, empty, or malformed input). The meter's corrupt-file path may return `{}`; the invariant and the shell guard may not.
2. Lowered thresholds: `--cov-fail-under` (floor is 90), mutation score floors, MIN_SCORE-style constants, retry/timeout bounds removed.
3. Tests that were deleted, skipped, xfailed, or had assertions weakened without a stated reason in the PR body.
4. README or docs numbers that changed without a reproducing command or artifact in the PR. The headline 67% (~$0.60 → ~$0.20) is recomputed by `python scripts/check_receipts.py` from stage tokens in `examples/routing-savings.md`. Changing that number, or replacing the UNVERIFIED live-run half with invented telemetry, is blocking.
5. Any content that looks like employer or corporate data: employer names or their abbreviations, program/product/site names, internal acronyms, CUI/ITAR markings, real-looking employee records, internal URLs. This repo is personal work only. The existing author bio does not name an employer; new employer references are blocking. So is removing digests from `.github/blocked-terms.sha256`, adding scan exclusions to `scripts/scan_employer_terms.py`, or committing a blocked term in plain text.
6. Secrets, tokens, `.env` files, or absolute personal paths committed.
7. Unpinned GitHub Actions (must be full SHA) or widened workflow `permissions:`.
8. Live network or model calls added to the default test path.

Flag as **non-blocking**:
- New runtime dependency without justification.
- Non-deterministic code in eval paths (unseeded RNG, unordered iteration in hashes/output).
- Exceptions swallowed in non-decision code.

Do not comment on formatting nits or naming bikesheds. This repo does not run ruff in CI.
