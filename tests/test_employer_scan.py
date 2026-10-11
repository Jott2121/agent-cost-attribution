"""scripts/scan_employer_terms.py: hash-based employer-term guard.

Planted terms are synthetic and written to temp dirs only; the real blocked
terms never appear in the repo, only their digests.
"""
from __future__ import annotations

import hashlib
import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "scan_employer_terms.py"
_spec = importlib.util.spec_from_file_location("scan_employer_terms", SCRIPT)
assert _spec is not None and _spec.loader is not None
scanner = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(scanner)

PLANTED = "zorblaxcorp"


def _digest(term: str) -> str:
    return hashlib.sha256(term.encode("utf-8")).hexdigest()


def _repo(tmp_path: Path, files: dict, digests: list) -> Path:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / ".github").mkdir()
    (tmp_path / ".github" / "blocked-terms.sha256").write_text(
        "# test digests\n" + "".join(d + "\n" for d in digests), encoding="utf-8"
    )
    for rel, body in files.items():
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body, encoding="utf-8")
    subprocess.run(["git", "-C", str(tmp_path), "add", "-A"], check=True)
    return tmp_path


def _run(root: Path, *extra: str, env_markers=None, monkeypatch=None):
    if monkeypatch is not None:
        if env_markers is None:
            monkeypatch.delenv("EMPLOYER_MARKERS", raising=False)
        else:
            monkeypatch.setenv("EMPLOYER_MARKERS", env_markers)
    return scanner.main(["--root", str(root), *extra])


@pytest.fixture(autouse=True)
def _no_secret(monkeypatch):
    monkeypatch.delenv("EMPLOYER_MARKERS", raising=False)


def test_planted_word_is_caught_without_printing_it(tmp_path, capsys):
    root = _repo(
        tmp_path,
        {"README.md": "clean intro\n", "data/notes.txt": "line one\nAuthor works at ZorblaxCorp.\n"},
        [_digest(PLANTED)],
    )
    assert _run(root) == 1
    out = capsys.readouterr().out
    assert "data/notes.txt:2: blocked term" in out
    assert "README.md" not in out
    assert PLANTED not in out.lower()


@pytest.mark.parametrize(
    "body",
    ["Acme Widgets", "acme-widgets", "ACME\nwidgets", "acmewidgets.example"],
)
def test_two_word_phrase_is_caught_across_separators(tmp_path, body):
    root = _repo(tmp_path, {"f.md": body + "\n"}, [_digest("acme widgets"), _digest("acmewidgets")])
    assert _run(root) == 1


def test_phrase_parts_alone_are_not_hits(tmp_path):
    root = _repo(tmp_path, {"f.md": "acme rockets; blue widgets\n"}, [_digest("acme widgets")])
    assert _run(root) == 0


def test_clean_tree_passes(tmp_path, capsys):
    root = _repo(tmp_path, {"README.md": "nothing to see\n", "a/b.py": "x = 1\n"}, [_digest(PLANTED)])
    assert _run(root) == 0
    assert "clean" in capsys.readouterr().out


def test_this_repo_is_clean_with_committed_digests_and_no_secret():
    assert scanner.main([]) == 0


def test_committed_hash_file_is_nonempty_and_well_formed():
    assert len(scanner.load_digests(ROOT / ".github" / "blocked-terms.sha256")) >= 1


def test_hash_file_is_excluded_but_other_tracked_dirs_are_scanned(tmp_path):
    root = _repo(
        tmp_path,
        {".cursor/rules/x.mdc": "ok\n", "AGENTS.md": "ok\n", ".github/workflows/ci.yml": "ok\n"},
        [_digest(PLANTED)],
    )
    assert _run(root) == 0
    (root / ".github" / "workflows" / "ci.yml").write_text(f"# {PLANTED}\n", encoding="utf-8")
    assert _run(root) == 1


def test_junk_dirs_are_skipped(tmp_path):
    root = _repo(tmp_path, {"node_modules/pkg/x.js": PLANTED, "ok.md": "fine\n"}, [_digest(PLANTED)])
    assert _run(root) == 0


@pytest.mark.parametrize("hash_body", [None, "", "# only a comment\n\n", "not-a-digest\n", _digest("x").upper() + "\n"])
def test_missing_empty_or_malformed_hash_file_fails_closed(tmp_path, capsys, hash_body):
    root = _repo(tmp_path, {"ok.md": "fine\n"}, [_digest(PLANTED)])
    hash_file = root / ".github" / "blocked-terms.sha256"
    if hash_body is None:
        hash_file.unlink()
    else:
        hash_file.write_text(hash_body, encoding="utf-8")
    assert _run(root) == 2
    assert "failed closed" in capsys.readouterr().err


def test_not_a_git_repo_fails_closed(tmp_path):
    (tmp_path / ".github").mkdir()
    (tmp_path / ".github" / "blocked-terms.sha256").write_text(_digest(PLANTED) + "\n", encoding="utf-8")
    assert _run(tmp_path) == 2


def test_employer_markers_env_adds_terms(tmp_path, monkeypatch, capsys):
    root = _repo(tmp_path, {"f.md": "contact Globex Industries\n"}, [_digest(PLANTED)])
    assert _run(root, env_markers="initech|globex", monkeypatch=monkeypatch) == 1
    out = capsys.readouterr().out
    assert "f.md:1: EMPLOYER_MARKERS match" in out
    assert "globex" not in out.lower()
    assert _run(root, env_markers="   ", monkeypatch=monkeypatch) == 0


def test_invalid_employer_markers_fails_closed(tmp_path, monkeypatch):
    root = _repo(tmp_path, {"f.md": "fine\n"}, [_digest(PLANTED)])
    assert _run(root, env_markers="(unclosed", monkeypatch=monkeypatch) == 2


def test_files_mode_for_the_edit_hook(tmp_path):
    root = _repo(tmp_path, {"hit.md": PLANTED + "\n", "ok.md": "fine\n"}, [_digest(PLANTED)])
    assert _run(root, "--files", str(root / "ok.md")) == 0
    assert _run(root, "--files", str(root / "hit.md")) == 1
    assert _run(root, "--files", str(root / ".github" / "blocked-terms.sha256")) == 0
    assert _run(root, "--files", str(root / "missing.md")) == 2


def test_cli_exit_code_end_to_end(tmp_path):
    root = _repo(tmp_path, {"hit.md": PLANTED + "\n"}, [_digest(PLANTED)])
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(root)],
        capture_output=True,
        text=True,
        env={k: v for k, v in os.environ.items() if k != "EMPLOYER_MARKERS"},
    )
    assert proc.returncode == 1, proc.stderr
    assert "hit.md:1: blocked term" in proc.stdout
