from __future__ import annotations

import stat
import zipfile
from pathlib import Path

from promptbranch_artifact_guardian import _minimal_yaml_load, guard_zip_artifact, load_artifact_guardian_policy


POLICY = """schema_version: 1

project:
  id: chatgpt_claudecode_workflow-2
  artifact_pattern: "chatgpt_claudecode_workflow-2_{version}.zip"
  version_file: "VERSION"

zip:
  forbid_wrapper_folder: true
  forbid_nested_zip: true
  preserve_executable_bits: true

required_entries:
  - ".gitignore"
  - "VERSION"
  - "README.md"
  - "run.sh"

forbidden_entries:
  - ".git/"
  - "__pycache__/"
  - "*.pyc"
  - ".pytest_cache/"
  - "debug_artifacts/"
  - "*.zip"
  - "*.log"
  - ".env"

executable_entries:
  - "run.sh"

version_checks:
  require_version_file_equals_cli_version: true
  require_artifact_name_contains_version: true
"""


def _write_policy(repo: Path) -> Path:
    policy = repo / ".artifact-guardian.yml"
    policy.write_text(POLICY, encoding="utf-8")
    return policy


def _zipinfo(name: str, *, executable: bool = False) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name)
    mode = 0o755 if executable else 0o644
    info.external_attr = (stat.S_IFREG | mode) << 16
    return info


def _make_zip(path: Path, entries: dict[str, str], *, executable: set[str] | None = None) -> Path:
    executable = executable or set()
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in entries.items():
            archive.writestr(_zipinfo(name, executable=name in executable), content)
    return path


def _valid_entries(version: str = "v0.1.78") -> dict[str, str]:
    return {
        ".gitignore": "*.pyc\n",
        "VERSION": f"{version}\n",
        "README.md": "# test\n",
        "run.sh": "#!/usr/bin/env bash\n",
    }


def _guard(tmp_path: Path, zip_path: Path, version: str = "v0.1.78") -> dict:
    return guard_zip_artifact(repo=tmp_path, zip_path=zip_path, version=version, policy_path=tmp_path / ".artifact-guardian.yml")


def _failure_classes(result: dict) -> set[str]:
    return {item.get("failure_class") for item in result.get("failures", [])}


def test_minimal_yaml_fallback_parses_policy_lists() -> None:
    payload = _minimal_yaml_load(POLICY)
    assert payload["required_entries"] == [".gitignore", "VERSION", "README.md", "run.sh"]
    assert payload["forbidden_entries"][0] == ".git/"
    assert payload["executable_entries"] == ["run.sh"]


def test_policy_loads_minimal_yaml(tmp_path: Path) -> None:
    policy = _write_policy(tmp_path)
    payload = load_artifact_guardian_policy(policy)
    assert payload["schema_version"] == 1
    assert payload["project"]["artifact_pattern"] == "chatgpt_claudecode_workflow-2_{version}.zip"


def test_valid_zip_passes_guard(tmp_path: Path) -> None:
    _write_policy(tmp_path)
    archive = _make_zip(tmp_path / "chatgpt_claudecode_workflow-2_v0.1.78.zip", _valid_entries(), executable={"run.sh"})
    result = _guard(tmp_path, archive)
    assert result["ok"] is True
    assert result["status"] == "guard_passed"
    assert result["release_ready"] is True
    assert result["checks"]["required_entries"] == "passed"
    assert result["failures"] == []


def test_zip_missing_gitignore_fails_before_candidate_handoff(tmp_path: Path) -> None:
    _write_policy(tmp_path)
    entries = _valid_entries()
    entries.pop(".gitignore")
    archive = _make_zip(tmp_path / "chatgpt_claudecode_workflow-2_v0.1.78.zip", entries, executable={"run.sh"})
    result = _guard(tmp_path, archive)
    assert result["ok"] is False
    assert result["release_ready"] is False
    assert "required_entry_missing" in _failure_classes(result)
    assert any(item.get("path") == ".gitignore" for item in result["failures"])


def test_zip_missing_version_fails_guard(tmp_path: Path) -> None:
    _write_policy(tmp_path)
    entries = _valid_entries()
    entries.pop("VERSION")
    archive = _make_zip(tmp_path / "chatgpt_claudecode_workflow-2_v0.1.78.zip", entries, executable={"run.sh"})
    result = _guard(tmp_path, archive)
    assert "required_entry_missing" in _failure_classes(result)
    assert "version_mismatch" in _failure_classes(result)


def test_version_mismatch_fails_guard(tmp_path: Path) -> None:
    _write_policy(tmp_path)
    archive = _make_zip(tmp_path / "chatgpt_claudecode_workflow-2_v0.1.78.zip", _valid_entries("v0.1.77.11"), executable={"run.sh"})
    result = _guard(tmp_path, archive)
    assert result["checks"]["version_file"] == "failed"
    assert "version_mismatch" in _failure_classes(result)


def test_wrapper_folder_fails_guard(tmp_path: Path) -> None:
    _write_policy(tmp_path)
    entries = {f"wrapper/{name}": content for name, content in _valid_entries().items()}
    archive = _make_zip(tmp_path / "chatgpt_claudecode_workflow-2_v0.1.78.zip", entries, executable={"wrapper/run.sh"})
    result = _guard(tmp_path, archive)
    assert "wrapper_folder_present" in _failure_classes(result)
    assert result["checks"]["wrapper_folder"] == "failed"


def test_nested_zip_fails_guard(tmp_path: Path) -> None:
    _write_policy(tmp_path)
    entries = _valid_entries() | {"old.zip": "not really a zip"}
    archive = _make_zip(tmp_path / "chatgpt_claudecode_workflow-2_v0.1.78.zip", entries, executable={"run.sh"})
    result = _guard(tmp_path, archive)
    assert "nested_zip_present" in _failure_classes(result)
    assert "forbidden_entry_present" in _failure_classes(result)


def test_forbidden_cache_file_fails_guard(tmp_path: Path) -> None:
    _write_policy(tmp_path)
    entries = _valid_entries() | {"pkg/__pycache__/mod.pyc": "cache"}
    archive = _make_zip(tmp_path / "chatgpt_claudecode_workflow-2_v0.1.78.zip", entries, executable={"run.sh"})
    result = _guard(tmp_path, archive)
    assert "forbidden_entry_present" in _failure_classes(result)
    assert result["checks"]["forbidden_entries"] == "failed"

def test_forbidden_debug_artifacts_fails_guard(tmp_path: Path) -> None:
    _write_policy(tmp_path)
    entries = _valid_entries() | {"debug_artifacts/project_source_trace.json": "{}"}
    archive = _make_zip(tmp_path / "chatgpt_claudecode_workflow-2_v0.1.78.zip", entries, executable={"run.sh"})
    result = _guard(tmp_path, archive)
    assert result["ok"] is False
    assert result["checks"]["forbidden_entries"] == "failed"
    assert "forbidden_entry_present" in _failure_classes(result)
    assert any(item.get("path") == "debug_artifacts/project_source_trace.json" for item in result["failures"])


def test_artifact_name_mismatch_fails_guard(tmp_path: Path) -> None:
    _write_policy(tmp_path)
    archive = _make_zip(tmp_path / "wrong_v0.1.78.zip", _valid_entries(), executable={"run.sh"})
    result = _guard(tmp_path, archive)
    assert "artifact_name_mismatch" in _failure_classes(result)
    assert result["checks"]["artifact_name"] == "failed"


def test_executable_bit_missing_fails_guard(tmp_path: Path) -> None:
    _write_policy(tmp_path)
    archive = _make_zip(tmp_path / "chatgpt_claudecode_workflow-2_v0.1.78.zip", _valid_entries(), executable=set())
    result = _guard(tmp_path, archive)
    assert "executable_bit_missing" in _failure_classes(result)
    assert result["checks"]["executable_bits"] == "failed"


def test_guard_output_contract_is_stable(tmp_path: Path) -> None:
    _write_policy(tmp_path)
    archive = _make_zip(tmp_path / "chatgpt_claudecode_workflow-2_v0.1.78.zip", _valid_entries(), executable={"run.sh"})
    result = _guard(tmp_path, archive)
    assert set(result) == {
        "ok",
        "action",
        "repo",
        "policy",
        "artifact",
        "artifact_filename",
        "version",
        "status",
        "checks",
        "failure_count",
        "failures",
        "entry_count",
        "healed",
        "release_ready",
    }
    assert result["action"] == "artifact_guard"
