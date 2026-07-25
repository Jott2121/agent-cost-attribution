"""Guard the distribution metadata that only PyPI validates.

PyPI rejects an unknown classifier, and any direct-URL dependency, with a 400 at
upload time. `twine check` catches neither -- it only validates that the long
description renders. So both defects pass every local gate and surface on the one
step that cannot be retried, since a version number is never reusable. These tests
are that missing gate.
"""
import tomllib
from pathlib import Path

from trove_classifiers import classifiers as VALID_CLASSIFIERS

DISTRIBUTION = "agent-cost-attribution"


def _pyproject():
    """Locate this project's pyproject.toml by walking up from the test file.

    Deliberately fails rather than skips when it cannot be found: a metadata guard
    that silently no-ops is worse than no guard, because it reports green.
    """
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "pyproject.toml"
        if candidate.is_file():
            data = tomllib.loads(candidate.read_text(encoding="utf-8"))
            if data.get("project", {}).get("name") == DISTRIBUTION:
                return data
    raise AssertionError(
        f"no pyproject.toml for {DISTRIBUTION} above {Path(__file__).resolve()}"
    )


def test_classifiers_are_real_trove_classifiers():
    declared = _pyproject()["project"].get("classifiers", [])
    assert declared, "classifiers disappeared from pyproject.toml"
    unknown = [c for c in declared if c not in VALID_CLASSIFIERS]
    assert not unknown, f"not real trove classifiers: {unknown}"


def test_no_direct_url_dependencies_anywhere():
    """Extras count too -- optional dependencies land in Requires-Dist just the same."""
    project = _pyproject()["project"]
    deps = list(project.get("dependencies", []))
    for extra, extra_deps in project.get("optional-dependencies", {}).items():
        deps += list(extra_deps)
    direct = [d for d in deps if "@" in d or d.startswith(("git+", "http"))]
    assert not direct, f"direct-URL dependencies cannot be published to PyPI: {direct}"


def test_declared_python_floor_matches_the_classifiers():
    """A `Programming Language :: Python :: X.Y` claim below requires-python is a lie
    pip will happily honour: the install succeeds and the code fails at import.
    """
    project = _pyproject()["project"]
    floor = project["requires-python"].lstrip(">=").strip()
    floor_key = tuple(int(p) for p in floor.split("."))
    claimed = [
        c.rsplit(" :: ", 1)[1]
        for c in project.get("classifiers", [])
        if c.startswith("Programming Language :: Python :: ") and c[-1].isdigit()
    ]
    versions = [tuple(int(p) for p in c.split(".")) for c in claimed if "." in c]
    below = [".".join(str(p) for p in v) for v in versions if v < floor_key]
    assert not below, f"classifiers claim Python {below} but requires-python is >={floor}"
