from __future__ import annotations

import json
import zipfile
from pathlib import Path

from promptbranch_release_scheduler import build_release_lifecycle_scheduler_plan


def _write_candidate_zip(path: Path, version: str = "v0.1.50") -> None:
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("VERSION", version + "\n")
        zf.writestr("README.md", "candidate\n")


def test_release_lifecycle_scheduler_plan_locks_repo_artifact_and_workspace(tmp_path: Path) -> None:
    artifact = tmp_path / "chatgpt_claudecode_workflow-2_v0.1.50.zip"
    _write_candidate_zip(artifact)

    payload = build_release_lifecycle_scheduler_plan(
        artifact_path=artifact,
        artifact_version="v0.1.50",
        target_version="v0.1.51",
        repo_path=tmp_path,
        workspace_url="https://chatgpt.com/g/g-p-demo/project",
        account_id="default",
        service_id="default",
    )

    assert payload["ok"] is True
    assert payload["status"] == "planned"
    assert payload["planning_only"] is True
    assert payload["mutation_executed"] is False
    assert payload["project_source_mutated"] is False
    assert payload["queue_policy"]["per_repo_lifecycle_serialized"] is True
    assert payload["queue_policy"]["per_workspace_source_upload_serialized"] is True
    assert payload["queue_policy"]["source_upload_uses_source_queue_plan"] is True
    resources = {item["resource"] for item in payload["resource_plan"]["resources"]}
    assert f"git_repo:{tmp_path.resolve()}:exclusive" in resources
    assert "sources:g-p-demo:exclusive" in resources
    assert payload["source_upload_queue_plan"]["scheduler_operation"] == "src_add"
    assert payload["source_upload_queue_plan"]["workspace"]["workspace_id"] == "g-p-demo"
    assert payload["verification_plan"]["project_source_upload_without_source_queue_allowed"] is False


def test_release_lifecycle_scheduler_plan_requires_workspace_for_source_upload(tmp_path: Path) -> None:
    artifact = tmp_path / "candidate.zip"
    _write_candidate_zip(artifact)

    payload = build_release_lifecycle_scheduler_plan(
        artifact_path=artifact,
        artifact_version="v0.1.50",
        repo_path=tmp_path,
        state_snapshot={},
    )

    assert payload["ok"] is False
    assert payload["status"] == "missing_context"
    assert "workspace_url" in payload["missing_context"]
    assert payload["source_upload_queue_plan"]["ok"] is False


def test_release_scheduler_module_is_declared_for_setuptools_install() -> None:
    import tomllib

    data = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    modules = data["tool"]["setuptools"]["py-modules"]

    assert "promptbranch_release_scheduler" in modules
