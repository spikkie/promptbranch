from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

from promptbranch_project_authority import (
    AUTHORITY_GRAPH_REL,
    build_project_authority_show_payload,
    validate_project_authority_graph,
)

ROOT = Path(__file__).resolve().parents[1]


def _copy_authority_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    for rel in (
        "PROJECT_SETTINGS.md",
        "AGENTS.md",
        ".promptbranch-repo.json",
        ".promptbranch-ai.json",
        ".promptbranch/ai-registry.json",
        "VERSION",
        "pyproject.toml",
        "promptbranch_version.py",
        ".promptbranch-release.yml",
        "docs/project/plan-state.json",
        "docs/project/status.md",
        "docs/project/plan.md",
        "docs/project/release-status.md",
        "docs/project/promptbranch-behavioral-surface-v0.1.109.1.json",
        "docs/project/behavioral-surface.md",
        "promptbranch_protocol/schemas/application.architecture.schema.json",
        "promptbranch_protocol/schemas/application.registry.schema.json",
        str(AUTHORITY_GRAPH_REL),
    ):
        source = ROOT / rel
        target = repo / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    return repo


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_authority_graph_show_lists_declared_domains() -> None:
    payload = build_project_authority_show_payload(ROOT)
    assert payload["ok"] is True
    assert payload["status"] == "authority_graph_loaded"
    assert payload["domain_count"] == 12
    assert payload["remote_mutation_allowed"] is False
    assert payload["mutation_performed"] is False


def test_authority_graph_validate_passes_static_repo() -> None:
    payload = validate_project_authority_graph(ROOT)
    assert payload["ok"] is True, payload["errors"]
    assert payload["status"] == "authority_consistent"
    assert payload["mutation_performed"] is False
    assert payload["writes_attempted"] == 0
    assert {item["domain"]: item["status"] for item in payload["runtime_domains"]} == {"artifact.adopted_identity": "deferred_runtime"}
    assert payload["external_domains"][0]["status"] == "not_observed_read_only"


def test_authority_graph_duplicate_domain_fails_closed(tmp_path: Path) -> None:
    repo = _copy_authority_repo(tmp_path)
    graph_path = repo / AUTHORITY_GRAPH_REL
    graph = json.loads(graph_path.read_text(encoding="utf-8"))
    graph["domains"].append(dict(graph["domains"][0]))
    graph_path.write_text(json.dumps(graph), encoding="utf-8")

    payload = validate_project_authority_graph(repo)
    assert payload["ok"] is False
    assert payload["status"] == "authority_ambiguous"
    assert any("duplicate authority domain" in error for error in payload["errors"])


def test_authority_graph_missing_authority_fails_closed(tmp_path: Path) -> None:
    repo = _copy_authority_repo(tmp_path)
    (repo / "PROJECT_SETTINGS.md").unlink()

    payload = validate_project_authority_graph(repo)
    assert payload["ok"] is False
    assert payload["status"] == "authority_missing"
    assert any("PROJECT_SETTINGS.md" in error for error in payload["errors"])


def test_version_projection_drift_is_detected(tmp_path: Path) -> None:
    repo = _copy_authority_repo(tmp_path)
    pyproject = repo / "pyproject.toml"
    pyproject.write_text(pyproject.read_text().replace('version = "0.1.114.2"', 'version = "9.9.9"'), encoding="utf-8")

    payload = validate_project_authority_graph(repo)
    assert payload["ok"] is False
    assert payload["status"] == "projection_drift"
    assert any("pyproject.toml" in error for error in payload["errors"])


def test_plan_state_markdown_projection_drift_is_detected(tmp_path: Path) -> None:
    repo = _copy_authority_repo(tmp_path)
    status = repo / "docs/project/status.md"
    status.write_text(status.read_text().replace("chatgpt_claudecode_workflow-2_v0.1.113.zip", "drifted.zip"), encoding="utf-8")

    payload = validate_project_authority_graph(repo)
    assert payload["ok"] is False
    assert payload["status"] == "projection_drift"
    assert any("docs/project/status.md" in error for error in payload["errors"])


def test_agents_must_not_pin_mutable_release_version(tmp_path: Path) -> None:
    repo = _copy_authority_repo(tmp_path)
    agents = repo / "AGENTS.md"
    agents.write_text(agents.read_text() + "\nCurrent version is v9.9.9.\n", encoding="utf-8")

    payload = validate_project_authority_graph(repo)
    assert payload["ok"] is False
    assert payload["status"] == "projection_drift"
    assert any("AGENTS.md must not pin" in error for error in payload["errors"])


def test_project_settings_must_not_duplicate_mutable_release_state(tmp_path: Path) -> None:
    repo = _copy_authority_repo(tmp_path)
    settings = repo / "PROJECT_SETTINGS.md"
    settings.write_text(settings.read_text() + "\nActive candidate: candidate.zip\n", encoding="utf-8")

    payload = validate_project_authority_graph(repo)
    assert payload["ok"] is False
    assert payload["status"] == "projection_drift"
    assert any("PROJECT_SETTINGS.md duplicates mutable release state" in error for error in payload["errors"])


def test_authority_validation_performs_zero_file_mutation(tmp_path: Path) -> None:
    repo = _copy_authority_repo(tmp_path)
    files = sorted(path for path in repo.rglob("*") if path.is_file())
    before = {path.relative_to(repo): _digest(path) for path in files}

    payload = validate_project_authority_graph(repo)

    after = {path.relative_to(repo): _digest(path) for path in files}
    assert payload["ok"] is True
    assert payload["mutation_performed"] is False
    assert payload["writes_attempted"] == 0
    assert after == before


def test_runtime_validation_fails_when_runtime_authorities_are_absent(tmp_path: Path) -> None:
    repo = _copy_authority_repo(tmp_path)
    payload = validate_project_authority_graph(repo, include_runtime=True)
    assert payload["ok"] is False
    assert payload["status"] == "authority_missing"
    assert any("runtime authority unavailable" in error for error in payload["errors"])


def test_project_authority_cli_show_and_validate_emit_json() -> None:
    for command, expected_status in (("show", "authority_graph_loaded"), ("validate", "authority_consistent")):
        result = subprocess.run(
            [sys.executable, "promptbranch_cli.py", "project", "authority", command, "--repo-path", str(ROOT), "--json"],
            cwd=ROOT,
            check=False,
            text=True,
            capture_output=True,
        )
        assert result.returncode == 0, result.stderr + result.stdout
        payload = json.loads(result.stdout)
        assert payload["ok"] is True
        assert payload["status"] == expected_status
        assert payload["mutation_performed"] is False


def test_tracked_project_binding_is_required_for_static_validation(tmp_path: Path) -> None:
    repo = _copy_authority_repo(tmp_path)
    (repo / ".promptbranch-repo.json").unlink()

    payload = validate_project_authority_graph(repo)

    assert payload["ok"] is False
    assert payload["status"] == "authority_missing"
    assert any("repository.project_identity" in error and ".promptbranch-repo.json" in error for error in payload["errors"])


def test_tracked_project_binding_must_match_graph_repo_id(tmp_path: Path) -> None:
    repo = _copy_authority_repo(tmp_path)
    path = repo / ".promptbranch-repo.json"
    binding = json.loads(path.read_text(encoding="utf-8"))
    binding["repo_id"] = "different-repo"
    binding["artifact_pattern"] = "different-repo_<version>.zip"
    path.write_text(json.dumps(binding), encoding="utf-8")

    payload = validate_project_authority_graph(repo)

    assert payload["ok"] is False
    assert payload["status"] == "projection_drift"
    assert any("does not match authority graph repo_id" in error for error in payload["errors"])
