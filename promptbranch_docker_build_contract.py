from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10 Docker runtime
    import tomli as tomllib

from promptbranch_source_fingerprint import source_fingerprint
from promptbranch_version import PACKAGE_VERSION, normalize_version


DYNAMIC_VERSION_ATTR = "promptbranch_version.PACKAGE_VERSION"


def validate_docker_build_context(
    root: str | Path,
    *,
    expected_version: object = "unknown",
    expected_source_fingerprint: object = "unknown",
) -> dict[str, Any]:
    base = Path(root).expanduser().resolve()
    expected = normalize_version(expected_version)
    version_file = normalize_version((base / "VERSION").read_text(encoding="utf-8"))
    package_version = normalize_version(PACKAGE_VERSION)

    pyproject_data = tomllib.loads((base / "pyproject.toml").read_text(encoding="utf-8"))
    project = pyproject_data.get("project") if isinstance(pyproject_data.get("project"), dict) else {}
    dynamic = project.get("dynamic") if isinstance(project.get("dynamic"), list) else []
    setuptools = pyproject_data.get("tool", {}).get("setuptools", {})
    dynamic_cfg = setuptools.get("dynamic") if isinstance(setuptools, dict) else {}
    version_cfg = dynamic_cfg.get("version") if isinstance(dynamic_cfg, dict) else {}
    version_attr = str(version_cfg.get("attr") or "") if isinstance(version_cfg, dict) else ""

    actual_fingerprint = source_fingerprint(base)
    expected_fingerprint = str(expected_source_fingerprint or "").strip()

    checks = {
        "version_file_present": (base / "VERSION").is_file(),
        "version_file_valid": bool(version_file),
        "package_version_valid": bool(package_version),
        "version_file_matches_package": bool(version_file) and version_file == package_version,
        "pyproject_has_no_static_project_version": "version" not in project,
        "pyproject_declares_dynamic_version": "version" in dynamic,
        "pyproject_dynamic_version_attr_exact": version_attr == DYNAMIC_VERSION_ATTR,
        "expected_version_matches": expected in (None, "unknown") or (version_file == expected and package_version == expected),
        "expected_source_fingerprint_matches": expected_fingerprint in ("", "unknown")
        or actual_fingerprint == expected_fingerprint,
    }
    ok = all(checks.values())
    return {
        "ok": ok,
        "status": "docker_build_context_verified" if ok else "docker_build_context_mismatch",
        "root": str(base),
        "expected_version": expected,
        "version_file": version_file,
        "package_version": package_version,
        "pyproject_dynamic_version_attr": version_attr,
        "expected_source_fingerprint": expected_fingerprint,
        "actual_source_fingerprint": actual_fingerprint,
        "checks": checks,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify Docker build context against VERSION authority.")
    parser.add_argument("--root", default="/app")
    parser.add_argument("--expected-version", default="unknown")
    parser.add_argument("--expected-source-fingerprint", default="unknown")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    payload = validate_docker_build_context(
        args.root,
        expected_version=args.expected_version,
        expected_source_fingerprint=args.expected_source_fingerprint,
    )
    if args.json:
        print(json.dumps(payload, sort_keys=True))
    else:
        print(payload["status"])
    if not payload["ok"]:
        print(json.dumps(payload, sort_keys=True), file=sys.stderr)
    return 0 if payload["ok"] else 42


if __name__ == "__main__":
    raise SystemExit(main())
