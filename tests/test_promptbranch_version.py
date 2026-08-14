from __future__ import annotations

from pathlib import Path
import re
import tomllib

import promptbranch_version
from promptbranch_source_fingerprint import iter_release_source_files

ROOT = Path(__file__).resolve().parents[1]
REPAIR_VERSION_LITERAL_RE = re.compile(r"v?0\.1\.103\.10\.\d+")


def _version_from_version_file() -> str:
    raw = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    assert raw.startswith("v")
    assert not raw.startswith("vv")
    return raw[1:]


def _pyproject_dynamic_version_attr() -> str:
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project = data["project"]
    assert "version" not in project
    assert "version" in project["dynamic"]
    return data["tool"]["setuptools"]["dynamic"]["version"]["attr"]


def test_version_tag_does_not_double_prefix_current_release() -> None:
    expected = _version_from_version_file()

    assert _pyproject_dynamic_version_attr() == "promptbranch_version.PACKAGE_VERSION"
    assert promptbranch_version.PACKAGE_VERSION == expected
    assert promptbranch_version.VERSION_TAG == f"v{expected}"
    assert not promptbranch_version.VERSION_TAG.startswith("vv")


def test_version_tag_normalizes_prefixed_inputs_without_double_v() -> None:
    assert promptbranch_version.version_tag("0.1.75") == "v0.1.75"
    assert promptbranch_version.version_tag("v0.1.75") == "v0.1.75"
    assert promptbranch_version.version_tag("vv0.1.75") == "v0.1.75"
    assert promptbranch_version.normalize_version("vv0.1.75") == "0.1.75"


def test_pyproject_version_is_derived_from_version_authority() -> None:
    assert _pyproject_dynamic_version_attr() == "promptbranch_version.PACKAGE_VERSION"
    source = (ROOT / "promptbranch_version.py").read_text(encoding="utf-8")
    assert 'Path(__file__).resolve().with_name("VERSION")' in source
    assert 'PACKAGE_VERSION = _version_from_authority()' in source
    assert re.search(r'^\s*PACKAGE_VERSION\s*=\s*["\'][^"\']+["\']', source, re.MULTILINE) is None


def _current_release_version_offenders(root: Path) -> list[str]:
    current = (root / "VERSION").read_text(encoding="utf-8").strip()
    normalized = current.removeprefix("v")
    offenders: list[str] = []
    for path in iter_release_source_files(root):
        version_sensitive_name = (
            path.suffix in {".py", ".toml", ".sh", ".yml", ".yaml"}
            or path.name in {"Dockerfile", "Containerfile", "Makefile"}
            or path.name.startswith("Dockerfile.")
            or path.name.startswith("Containerfile.")
        )
        if path.name == "VERSION" or not version_sensitive_name:
            continue
        source = path.read_text(encoding="utf-8", errors="replace")
        if current in source or normalized in source:
            offenders.append(path.relative_to(root).as_posix())
    release_contract = root / ".promptbranch-release.json"
    if release_contract.is_file():
        source = release_contract.read_text(encoding="utf-8", errors="replace")
        if current in source or normalized in source:
            offenders.append(".promptbranch-release.json")
    return offenders


def test_current_release_version_is_not_hard_coded_in_executable_or_packaging_sources() -> None:
    assert _current_release_version_offenders(ROOT) == []


def test_current_release_version_scan_ignores_operator_runtime_history(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    (root / "VERSION").write_text("v9.8.7\n", encoding="utf-8")
    (root / ".promptbranch-release.json").write_text("{}\n", encoding="utf-8")
    historical = root / ".pb_profile" / "release_attempts_v2" / "old" / "runtime" / "extracted"
    historical.mkdir(parents=True)
    (historical / "legacy.py").write_text('PACKAGE_VERSION = "9.8.7"\n', encoding="utf-8")
    (root / "canonical.py").write_text("VALUE = 1\n", encoding="utf-8")

    assert _current_release_version_offenders(root) == []

    (root / "canonical.py").write_text('PACKAGE_VERSION = "9.8.7"\n', encoding="utf-8")
    assert _current_release_version_offenders(root) == ["canonical.py"]


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


def test_candidate_pytest_runner_is_exact_and_consistent() -> None:
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

    assert project_dependencies.get("pytest") == "9.0.2"
    assert requirements_dependencies.get("pytest") == "9.0.2"
    assert requirements_dependencies.get("pytest-asyncio") == "1.3.0"


def test_dockerfile_uses_version_authority_contract_not_source_regexes() -> None:
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert "python3 -m promptbranch_docker_build_contract" in dockerfile
    assert "version_py_match" not in dockerfile
    assert "pyproject_match" not in dockerfile
    assert r"PACKAGE_VERSION\s*=" not in dockerfile


def test_docker_build_contract_supports_python310_tomli_fallback() -> None:
    source = (ROOT / "promptbranch_docker_build_contract.py").read_text(encoding="utf-8")
    requirements = {
        line.strip().split("==", 1)[0].lower()
        for line in (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    assert "except ModuleNotFoundError" in source
    assert "import tomli as tomllib" in source
    assert "tomli" in requirements


def test_docker_build_contract_is_declared_installable() -> None:
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert "promptbranch_docker_build_contract" in data["tool"]["setuptools"]["py-modules"]
