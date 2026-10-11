#!/usr/bin/env bash
# afterFileEdit (notification-only): format the edited Python file and warn on employer-data / secret patterns.
# It can't block the edit; CI's no-employer-data job is the real gate.
# Employer terms are checked by scripts/scan_employer_terms.py against hashed terms; a scan error also warns.
set -uo pipefail
f="$(python3 -c 'import sys,json; print(json.load(sys.stdin).get("file_path",""))')"
[ -f "$f" ] || exit 0
case "$f" in *.py) command -v ruff >/dev/null && ruff format -q "$f" && ruff check -q --fix "$f" ;; esac
warn() {
  mkdir -p .cursor/hook-logs
  echo "$(date -u +%FT%TZ) WARN $1 in $f" >> .cursor/hook-logs/warnings.log
}
if ! python3 scripts/scan_employer_terms.py --files "$f" >/dev/null 2>&1; then
  warn "employer term (or employer scan failed closed)"
fi
if grep -EIiq '\bCUI\b|ITAR|EXPORT CONTROLLED|BEGIN (RSA|OPENSSH) PRIVATE KEY|xai-[A-Za-z0-9]{20,}' "$f"; then
  warn "export-control/secret pattern"
fi
exit 0
