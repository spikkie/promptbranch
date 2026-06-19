from __future__ import annotations

import promptbranch_version


def test_version_tag_does_not_double_prefix_current_release() -> None:
    assert promptbranch_version.PACKAGE_VERSION == "0.1.78.2.11"
    assert promptbranch_version.VERSION_TAG == "v0.1.78.2.11"
    assert promptbranch_version.VERSION_TAG != "vv0.1.78.2.11"


def test_version_tag_normalizes_prefixed_inputs_without_double_v() -> None:
    assert promptbranch_version.version_tag("0.1.75") == "v0.1.75"
    assert promptbranch_version.version_tag("v0.1.75") == "v0.1.75"
    assert promptbranch_version.version_tag("vv0.1.75") == "v0.1.75"
    assert promptbranch_version.normalize_version("vv0.1.75") == "0.1.75"
