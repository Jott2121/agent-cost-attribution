#!/usr/bin/env python3
"""Fail if any tracked file contains a blocked employer term.

The blocked terms are not stored in the repo. `.github/blocked-terms.sha256`
holds SHA-256 digests of the lowercased terms. This script lowercases every
tracked file, splits it into alphanumeric words, and hashes each word, each
adjacent two-word phrase joined by one space, and the same pair with no
separator. Any digest in the hash file is a hit.

Extra terms can come from the EMPLOYER_MARKERS environment variable, a regex
alternation (e.g. an Actions secret of the same name), matched
case-insensitively per line. Hits print file and line only, never the term.

Exit codes: 0 clean, 1 blocked term found, 2 scan could not run (missing,
empty, or malformed hash file; invalid EMPLOYER_MARKERS; unreadable file;
git failure). Anything other than 0 must be treated as a failure.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Iterator, List, Optional, Pattern, Sequence, Set, Tuple

ROOT = Path(__file__).resolve().parents[1]
HASH_FILE = Path(".github") / "blocked-terms.sha256"
JUNK_DIRS = {".git", "node_modules", "__pycache__", ".venv", "build", "dist", ".pytest_cache"}
JUNK_SUFFIXES = (".pyc", ".egg-info")
WORD_RE = re.compile(r"[a-z0-9]+")
DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")


class ScanError(Exception):
    """The scan could not run; callers must fail closed."""


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_digests(path: Path) -> Set[str]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise ScanError(f"cannot read hash file {path}: {exc}") from exc
    digests: Set[str] = set()
    for n, raw in enumerate(lines, 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if not DIGEST_RE.match(line):
            raise ScanError(f"{path}:{n}: not a lowercase SHA-256 hex digest")
        digests.add(line)
    if not digests:
        raise ScanError(f"hash file {path} has no digests")
    return digests


def load_markers(value: Optional[str]) -> Optional[Pattern[str]]:
    if value is None or not value.strip():
        return None
    try:
        return re.compile(value.strip(), re.IGNORECASE)
    except re.error as exc:
        raise ScanError(f"EMPLOYER_MARKERS is not a valid regex: {exc}") from exc


def is_excluded(rel: str, hash_rel: str) -> bool:
    if rel == hash_rel:
        return True
    parts = rel.split("/")
    if any(p in JUNK_DIRS or p.endswith(JUNK_SUFFIXES) for p in parts):
        return True
    return False


def tracked_files(root: Path) -> List[str]:
    try:
        out = subprocess.run(
            ["git", "-C", str(root), "ls-files", "-z"],
            check=True,
            capture_output=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ScanError(f"git ls-files failed: {exc}") from exc
    files = [p for p in out.decode("utf-8", "surrogateescape").split("\0") if p]
    if not files:
        raise ScanError("git ls-files returned no files")
    return files


def candidates(text: str) -> Iterator[Tuple[int, str]]:
    """Yield (offset, candidate) for each word, spaced pair, and joined pair."""
    prev: Optional[Tuple[int, str]] = None
    for m in WORD_RE.finditer(text):
        word = m.group(0)
        yield m.start(), word
        if prev is not None:
            yield prev[0], f"{prev[1]} {word}"
            yield prev[0], prev[1] + word
        prev = (m.start(), word)


def scan_text(text: str, digests: Set[str], markers: Optional[Pattern[str]]) -> List[Tuple[int, str]]:
    """Return sorted (line, reason) hits for one file's text."""
    hits: Set[Tuple[int, str]] = set()
    lowered = text.lower()
    for offset, cand in candidates(lowered):
        digest = sha256_hex(cand)
        if digest in digests:
            hits.add((lowered.count("\n", 0, offset) + 1, f"blocked term (sha256 {digest[:12]})"))
    if markers is not None:
        for n, line in enumerate(text.splitlines(), 1):
            if markers.search(line):
                hits.add((n, "EMPLOYER_MARKERS match"))
    return sorted(hits)


def scan(
    root: Path,
    files: Optional[Sequence[str]],
    hash_file: Path,
    markers_value: Optional[str],
) -> List[str]:
    digests = load_digests(hash_file)
    markers = load_markers(markers_value)
    try:
        hash_rel = hash_file.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        hash_rel = ""
    rels: List[str] = []
    for f in files if files is not None else tracked_files(root):
        p = Path(f)
        abs_p = p if p.is_absolute() else root / p
        try:
            rels.append(abs_p.resolve().relative_to(root.resolve()).as_posix())
        except ValueError:
            rels.append(abs_p.resolve().as_posix())
    findings: List[str] = []
    for rel in rels:
        if is_excluded(rel, hash_rel):
            continue
        path = Path(rel) if Path(rel).is_absolute() else root / rel
        try:
            text = path.read_bytes().decode("utf-8", "replace")
        except OSError as exc:
            raise ScanError(f"cannot read {rel}: {exc}") from exc
        for line, reason in scan_text(text, digests, markers):
            findings.append(f"{rel}:{line}: {reason}")
    return findings


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", type=Path, default=ROOT, help="repo root (default: this repo)")
    ap.add_argument("--hash-file", type=Path, help="digest file (default: <root>/.github/blocked-terms.sha256)")
    ap.add_argument("--files", nargs="+", help="scan these files instead of `git ls-files`")
    args = ap.parse_args(argv)
    root: Path = args.root
    hash_file: Path = args.hash_file or root / HASH_FILE
    try:
        findings = scan(root, args.files, hash_file, os.environ.get("EMPLOYER_MARKERS"))
    except ScanError as exc:
        print(f"employer scan failed closed: {exc}", file=sys.stderr)
        return 2
    if findings:
        for f in findings:
            print(f)
        print(f"employer scan: {len(findings)} hit(s)", file=sys.stderr)
        return 1
    print("employer scan: clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
