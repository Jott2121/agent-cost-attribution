# Plan: remove the employer name from current files, keep the guard fail-closed

Goal: no plain-text employer name in any tracked file, with the employer-data guard still catching it.
Owner-approved. History rewrite is out of scope by the owner's choice.

1. Inventory: case-insensitive employer-name grep over tracked files (full name, short name, and abbreviations as whole words), kept out of tracked files and PR text; judge each two-letter abbreviation hit by hand. Scan docs, examples, and saved answers for indirect pointers (programs, products, sites, internal acronyms, role titles).
2. Replace each mention with generic "employer" wording in AGENTS.md, `.cursor/rules/00-core-principles.mdc`, `.cursor/BUGBOT.md`, `.cursor/hooks/format-and-scan.sh`, `.github/workflows/ci.yml`.
3. Guard: `.github/blocked-terms.sha256` holds SHA-256 digests of lowercased terms. `scripts/scan_employer_terms.py` hashes every word, adjacent two-word phrase (spaced and joined) in every tracked file. Optional `EMPLOYER_MARKERS` regex from an Actions secret. Exit 2 (fail closed) on missing/empty/malformed digest file, bad regex, unreadable file, or git failure. Skips only the digest file and build junk.
4. CI `no-employer-data`: run the scanner self-test and the whole-tree scan; keep the export-control grep and build-junk check.
5. Tests in `tests/test_employer_scan.py` plant synthetic terms in temp dirs only. Verify: pytest at the 90 floor, `check_receipts.py`, scanner exit 0 on the tree.
