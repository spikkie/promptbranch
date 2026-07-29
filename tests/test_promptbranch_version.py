from __future__ import annotations

from pathlib import Path
import re
import tomllib

import promptbranch_version

ROOT = Path(__file__).resolve().parents[1]
REPAIR_VERSION_LITERAL_RE = re.compile(r"v?0\.1\.103\.10\.\d+")


def _version_from_version_file() -> str:
    raw = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    assert raw.startswith("v")
    assert not raw.startswith("vv")
    return raw[1:]


def _version_from_pyproject() -> str:
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    return data["project"]["version"]


def test_version_tag_does_not_double_prefix_current_release() -> None:
    expected = _version_from_version_file()

    assert _version_from_pyproject() == expected
    assert promptbranch_version.PACKAGE_VERSION == expected
    assert promptbranch_version.VERSION_TAG == f"v{expected}"
    assert not promptbranch_version.VERSION_TAG.startswith("vv")


def test_version_tag_normalizes_prefixed_inputs_without_double_v() -> None:
    assert promptbranch_version.version_tag("0.1.75") == "v0.1.75"
    assert promptbranch_version.version_tag("v0.1.75") == "v0.1.75"
    assert promptbranch_version.version_tag("vv0.1.75") == "v0.1.75"
    assert promptbranch_version.normalize_version("vv0.1.75") == "0.1.75"


def test_pyproject_version_matches_package_version() -> None:
    assert _version_from_pyproject() == promptbranch_version.PACKAGE_VERSION


def test_version_surface_tests_do_not_pin_stale_repair_candidate_literals() -> None:
    expected = _version_from_version_file()
    allowed = {expected, f"v{expected}"}
    text = Path(__file__).read_text(encoding="utf-8")
    literals = set(REPAIR_VERSION_LITERAL_RE.findall(text))
    stale_literals = sorted(literal for literal in literals if literal not in allowed)
    assert stale_literals == []


def test_fastapi_starlette_compatibility_pair_is_exact_and_consistent() -> None:
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project_dependencies = {
        item.split("==", 1)[0].strip().lower(): item.split("==", 1)[1].strip()
        for item in data["project"]["dependencies"]
        if "==" in item
    }
    requirements_dependencies = {
        item.split("==", 1)[0].strip().lower(): item.split("==", 1)[1].strip()
        for raw in (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines()
        if (item := raw.strip()) and not item.startswith("#") and "==" in item
    }

    expected = {"fastapi": "0.128.2", "starlette": "0.50.0"}
    assert {name: project_dependencies.get(name) for name in expected} == expected
    assert {name: requirements_dependencies.get(name) for name in expected} == expected
