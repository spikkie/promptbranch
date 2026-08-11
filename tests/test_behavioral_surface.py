from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import zipfile

from promptbranch_artifacts import ArtifactRecord, ArtifactRegistry, sha256_file
from promptbranch_behavioral_surface import BEHAVIORAL_SURFACE_REL, build_behavioral_surface_show_payload, validate_behavioral_surface
from promptbranch_project import project_registry_dir, write_repo_identity
from promptbranch_project_authority import validate_project_authority_graph

ROOT = Path(__file__).resolve().parents[1]


def test_behavioral_surface_show_lists_all_five_kinds() -> None:
    payload = build_behavioral_surface_show_payload(ROOT)
    assert payload["ok"] is True
    assert payload["status"] == "behavioral_surface_loaded"
    assert set(payload["counts_by_kind"]) == {"instruction", "skill", "agent", "tool", "prompt"}
    assert payload["mutation_performed"] is False


def test_behavioral_surface_validate_is_consistent_and_read_only() -> None:
    payload = validate_behavioral_surface(ROOT)
    assert payload["ok"] is True, payload["errors"]
    assert payload["status"] == "behavioral_surface_consistent"
    assert payload["mutation_performed"] is False
    assert payload["writes_attempted"] == 0
    assert payload["counts_by_kind"]["tool"] == 12


def test_behavioral_surface_filter_by_kind() -> None:
    payload = build_behavioral_surface_show_payload(ROOT, kind="prompt")
    assert payload["ok"] is True
    assert payload["selected_count"] == payload["counts_by_kind"]["prompt"]
    assert all(entry["kind"] == "prompt" for entry in payload["entries"])


def test_behavioral_surface_duplicate_id_fails_closed(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    shutil.copytree(ROOT, repo, ignore=shutil.ignore_patterns(".git", ".pb_profile", "__pycache__"))
    path = repo / BEHAVIORAL_SURFACE_REL
    payload = json.loads(path.read_text())
    payload["entries"].append(dict(payload["entries"][0]))
    path.write_text(json.dumps(payload))
    result = validate_behavioral_surface(repo)
    assert result["ok"] is False
    assert any("duplicate behavioral surface id" in error for error in result["errors"])


def test_behavioral_surface_unknown_skill_tool_fails_closed(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    shutil.copytree(ROOT, repo, ignore=shutil.ignore_patterns(".git", ".pb_profile", "__pycache__"))
    path = repo / BEHAVIORAL_SURFACE_REL
    payload = json.loads(path.read_text())
    skill = next(entry for entry in payload["entries"] if entry["kind"] == "skill")
    skill["allowed_tools"].append("unknown.write.tool")
    path.write_text(json.dumps(payload))
    result = validate_behavioral_surface(repo)
    assert result["ok"] is False
    assert any("unknown allowed tool" in error for error in result["errors"])



def test_behavioral_surface_missing_tool_dispatcher_fails_closed(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    shutil.copytree(ROOT, repo, ignore=shutil.ignore_patterns(".git", ".pb_profile", "__pycache__"))
    path = repo / BEHAVIORAL_SURFACE_REL
    payload = json.loads(path.read_text())
    tool = next(entry for entry in payload["entries"] if entry["kind"] == "tool")
    tool.pop("dispatcher", None)
    path.write_text(json.dumps(payload))
    result = validate_behavioral_surface(repo)
    assert result["ok"] is False
    assert any("dispatcher is required" in error for error in result["errors"])

def test_runtime_authority_resolves_project_registry(tmp_path: Path, monkeypatch) -> None:
    repo = tmp_path / "repo"
    for rel in ("PROJECT_SETTINGS.md", "AGENTS.md", ".promptbranch-ai.json", ".promptbranch/ai-registry.json", "VERSION", "pyproject.toml", "promptbranch_version.py", ".promptbranch-release.yml", "docs/project/plan-state.json", "docs/project/status.md", "docs/project/plan.md", "docs/project/release-status.md", "docs/project/project-authority-graph-v0.1.109.json", "docs/project/promptbranch-behavioral-surface-v0.1.109.1.json", "docs/project/behavioral-surface.md"):
        source = ROOT / rel
        target = repo / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    monkeypatch.setenv("PROMPTBRANCH_PROJECT_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("PROMPTBRANCH_PROJECT_CONFIG_HOME", str(tmp_path / "config"))
    write_repo_identity(repo, project_id="project-x", project_home_url="https://chatgpt.com/g/g-p-project-x/project", repo_id="chatgpt_claudecode_workflow-2")
    registry = ArtifactRegistry(project_registry_dir("project-x"))
    registry.initialize()
    artifact = repo / "chatgpt_claudecode_workflow-2_v0.1.109.zip"
    with zipfile.ZipFile(artifact, "w", compression=zipfile.ZIP_STORED) as archive:
        archive.writestr("VERSION", "v0.1.109\n")
        archive.writestr("README.md", "runtime authority fixture\n")
    registry.add(ArtifactRecord(
        path=str(artifact),
        filename=artifact.name,
        kind="adopted_release",
        version="v0.1.109",
        repo_path=None,
        sha256=sha256_file(artifact),
        size_bytes=artifact.stat().st_size,
        file_count=1,
        created_at="2026-07-25T04:39:54Z",
        source_ref="chatgpt_claudecode_workflow-2_v0.1.109(3).zip",
        repo_id="chatgpt_claudecode_workflow-2",
    ))
    result = validate_project_authority_graph(repo, include_runtime=True)
    assert result["ok"] is True, result["errors"]
    assert result["status"] == "authority_consistent"
    adopted = next(item for item in result["runtime_domains"] if item["domain"] == "artifact.adopted_identity")
    assert adopted["status"] == "available"
    assert adopted["current"]["version"] == "v0.1.109"
