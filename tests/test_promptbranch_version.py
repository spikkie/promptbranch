from __future__ import annotations

import promptbranch_version


def test_version_tag_does_not_double_prefix_current_release() -> None:
    assert promptbranch_version.PACKAGE_VERSION == "0.1.103.10.47"
    assert promptbranch_version.VERSION_TAG == "v0.1.103.10.47"
    assert promptbranch_version.VERSION_TAG != "vv0.1.80"


def test_version_tag_normalizes_prefixed_inputs_without_double_v() -> None:
    assert promptbranch_version.version_tag("0.1.75") == "v0.1.75"
    assert promptbranch_version.version_tag("v0.1.75") == "v0.1.75"
    assert promptbranch_version.version_tag("vv0.1.75") == "v0.1.75"
    assert promptbranch_version.normalize_version("vv0.1.75") == "0.1.75"


def test_pyproject_version_matches_package_version() -> None:
    import re
    from pathlib import Path

    pyproject = Path(__file__).resolve().parents[1] / "pyproject.toml"
    text = pyproject.read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    assert match is not None
    assert match.group(1) == promptbranch_version.PACKAGE_VERSION
