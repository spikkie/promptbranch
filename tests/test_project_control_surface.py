from __future__ import annotations

from pathlib import Path
import json
import subprocess
import sys

from promptbranch_project_control import build_project_next_slice_payload, validate_project_control_surface

ROOT = Path(__file__).resolve().parents[1]
PROJECT_DOCS = ROOT / "docs" / "project"

REQUIRED_FILES = [
    "README.md",
    "mvp.md",
    "definition-of-done.md",
    "plan.md",
    "status.md",
    "release-status.md",
    "decisions.md",
    "migration.md",
    "validation-matrix.md",
    "plan-state.json",
    "architecture.md",
    "slice-horizon.md",
]


def read_doc(name: str) -> str:
    return (PROJECT_DOCS / name).read_text(encoding="utf-8")




def test_project_control_surface_accepts_deep_repair_version() -> None:
    from promptbranch_project_control import VERSION_RE

    assert VERSION_RE.match("v0.1.103.10.52")
    assert VERSION_RE.match("v0.1.104")
    assert VERSION_RE.match("v0.1.104.13.9")

def test_project_control_surface_required_files_exist() -> None:
    missing = [name for name in REQUIRED_FILES if not (PROJECT_DOCS / name).is_file()]
    assert missing == []


def test_definition_of_done_has_evidence_table() -> None:
    text = read_doc("definition-of-done.md")
    assert "| ID | DoD item | Status | Evidence | Last release |" in text
    assert "DOD-001" in text
    assert "DOD-008" in text
    assert "open" in text
    assert "done" in text


def test_release_status_has_allowed_table_and_current_baseline() -> None:
    text = read_doc("release-status.md")
    assert "| Version | Type | Slice | ZIP status | Validation | DoD movement | Accepted checksum |" in text
    assert "v0.1.102" in text
    assert "accepted/current" in text
    assert "chatgpt_claudecode_workflow-2_v0.1.102.zip" in text
    assert "v0.1.103.10.52" in text
    assert "standard browser profile default" in text
    assert "candidate" in text


def test_migration_has_mapping_table_and_preserves_old_docs() -> None:
    text = read_doc("migration.md")
    assert "| Existing file | Current role | Migrated to | Migration status | Notes |" in text
    assert "docs/mvp-definition-of-done.md" in text
    assert "docs/design/orchestration/docs/current_status.md" in text
    assert "not deleted" in text or "preserved" in text


def test_status_has_next_safe_action_and_accepted_baseline() -> None:
    text = read_doc("status.md")
    assert "## Next safe action" in text
    assert "accepted/current baseline with adoption evidence:" in text
    assert "chatgpt_claudecode_workflow-2_v0.1.102.zip" in text
    assert "chatgpt_claudecode_workflow-2_v0.1.103.10.52.zip" in text
    assert "standard browser profile default" in text


def test_validation_matrix_declares_required_release_groups() -> None:
    text = read_doc("validation-matrix.md")
    assert "| Group | Required | Purpose | Representative command |" in text
    for group in [
        "project_control_surface",
        "version_surface",
        "artifact_json_contracts",
        "repo_project_registry",
        "browser_scheduler_source_lifecycle",
        "release_lifecycle_plan",
        "compileall",
        "zip_hygiene",
    ]:
        assert group in text
    assert "missing_required_groups" in text



def test_k8s_game_plan_reconciled_before_implementation() -> None:
    status = read_doc("status.md")
    plan = read_doc("plan.md")
    decisions = read_doc("decisions.md")
    migration = read_doc("migration.md")
    orchestration_status = (ROOT / "docs" / "design" / "orchestration" / "docs" / "current_status.md").read_text(encoding="utf-8")
    k8s_contract = (ROOT / "docs" / "design" / "orchestration" / "docs" / "k8s_game_mvp_contract.md").read_text(encoding="utf-8")

    combined = "\n".join([status, plan, decisions, migration, orchestration_status, k8s_contract])
    assert "v0.1.86 — K8s-game orchestration plan reconciliation" in plan
    assert "chatgpt_claudecode_workflow-2_v0.1.85.zip" in combined
    assert "no game implementation" in combined
    assert "no Kubernetes apply" in combined
    assert "dry-run/deploy evidence gate" in combined
    assert "current reconciliation release:    v0.1.86" in orchestration_status
    assert "v0.1.87 candidate direction" in orchestration_status


def test_loop_target_schema_and_dry_run_planner_control_surface() -> None:
    status = read_doc("status.md")
    plan = read_doc("plan.md")
    decisions = read_doc("decisions.md")
    migration = read_doc("migration.md")
    dod = read_doc("definition-of-done.md")
    loop_contract = (ROOT / "docs" / "design" / "orchestration" / "docs" / "loop_target_schema_contract.md").read_text(encoding="utf-8")

    combined = "\n".join([status, plan, decisions, migration, dod, loop_contract])
    assert "v0.1.87 — Loop target schema and dry-run planner" in combined
    assert "chatgpt_claudecode_workflow-2_v0.1.86.zip" in combined
    assert "promptbranch.loop.target" in combined
    assert "side-effect free" in combined or "side-effect-free" in combined
    assert "no Kubernetes" in combined or "kubernetes_mutation_performed=false" in combined
    assert "DOD-105" in combined


def test_plan_state_is_machine_readable_next_slice_authority() -> None:
    data = json.loads((PROJECT_DOCS / "plan-state.json").read_text(encoding="utf-8"))
    assert data["schema"] == "promptbranch.project.plan_state"
    assert data["schema_version"] == "1.0"
    assert data["accepted_current_version"] == "v0.1.102"
    assert data["accepted_current_artifact"] == "chatgpt_claudecode_workflow-2_v0.1.102.zip"
    assert data["active_candidate_version"] == "v0.1.103.10.52"
    assert data["active_candidate_artifact"] == "chatgpt_claudecode_workflow-2_v0.1.103.10.52.zip"
    assert data["next_normal_version"] == "v0.1.103.10.52"
    assert data["active_slice"] == "v0.1.103.10.52 — release-live project-ensure challenge fails fast and compose down remains operator-safe"
    assert data["next_planned_version_after_acceptance"] == "v0.1.104"
    assert data["next_planned_slice_after_acceptance"] == "Sandbox mutation verification and rollback evidence gate"
    assert data["repair_must_not_advance_scope"] is True
    assert data["release_mode"] == "repair"
    assert data["scope_advance_allowed"] is False
    assert data["architecture_goal"] == "controlled problem-solving loop"
    assert len(data["rolling_slice_horizon"]) == 5


def test_project_control_surface_validator_passes_current_repo() -> None:
    payload = validate_project_control_surface(ROOT)
    assert payload["ok"] is True, payload.get("errors")
    assert payload["accepted_current_version"] == "v0.1.102"
    assert payload["active_candidate_version"] == "v0.1.103.10.52"
    assert payload["next_normal_slice"] == "v0.1.103.10.52 — release-live project-ensure challenge fails fast and compose down remains operator-safe"
    assert payload["architecture_goal"] == "controlled problem-solving loop"
    assert len(payload["rolling_slice_horizon"]) == 5


def test_project_control_surface_cli_emits_json() -> None:
    result = subprocess.run(
        [sys.executable, "promptbranch_cli.py", "project", "validate-control-surface", "--repo-path", str(ROOT), "--json"],
        cwd=ROOT,
        check=False,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stderr + result.stdout
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["status"] == "passed"
    assert payload["active_candidate_artifact"] == "chatgpt_claudecode_workflow-2_v0.1.103.10.52.zip"


def test_project_control_surface_validator_rejects_drifted_status(tmp_path: Path) -> None:
    import shutil

    repo = tmp_path / "repo"
    shutil.copytree(ROOT / "docs", repo / "docs")
    (repo / "VERSION").write_text("v0.1.103.1\n", encoding="utf-8")
    status = repo / "docs" / "project" / "status.md"
    text = status.read_text(encoding="utf-8")
    status.write_text(text.replace("chatgpt_claudecode_workflow-2_v0.1.102.zip", "chatgpt_claudecode_workflow-2_v0.1.79.zip", 1), encoding="utf-8")

    payload = validate_project_control_surface(repo)
    assert payload["ok"] is False
    assert any("accepted_current_artifact" in error or "accepted_current_version" in error for error in payload["errors"])



def test_architecture_and_slice_horizon_are_documented() -> None:
    architecture = read_doc("architecture.md")
    horizon = read_doc("slice-horizon.md")
    assert "controlled problem-solving loop" in architecture
    assert "Fixed architecture invariants" in architecture
    assert "Repair releases must not advance scope" in architecture
    for version in ["v0.1.103.10.52", "v0.1.104", "v0.1.105", "v0.1.106", "v0.1.107"]:
        assert version in horizon
    assert "Repair horizon rule" in horizon


def test_project_next_slice_payload_is_derived_from_validated_control_surface() -> None:
    payload = build_project_next_slice_payload(ROOT)
    assert payload["ok"] is True, payload.get("errors")
    assert payload["baseline_artifact"] == "chatgpt_claudecode_workflow-2_v0.1.102.zip"
    assert payload["next_normal_version"] == "v0.1.103.10.52"
    assert payload["next_normal_slice"] == "v0.1.103.10.52 — release-live project-ensure challenge fails fast and compose down remains operator-safe"
    assert payload["next_slice_after_acceptance_version"] == "v0.1.104"
    assert payload["next_slice_after_acceptance"] == "Sandbox mutation verification and rollback evidence gate"
    assert payload["architecture_invariants_checked"] is True
    assert payload["control_surface_validated"] is True


def test_project_next_slice_cli_emits_json() -> None:
    result = subprocess.run(
        [sys.executable, "promptbranch_cli.py", "project", "next-slice", "--repo-path", str(ROOT), "--json"],
        cwd=ROOT,
        check=False,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stderr + result.stdout
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["status"] == "next_slice_ready"
    assert payload["next_normal_version"] == "v0.1.103.10.52"
    assert payload["next_slice_after_acceptance_version"] == "v0.1.104"


def test_project_control_surface_validator_rejects_short_horizon(tmp_path: Path) -> None:
    import shutil

    repo = tmp_path / "repo"
    shutil.copytree(ROOT / "docs", repo / "docs")
    (repo / "VERSION").write_text("v0.1.103.1\n", encoding="utf-8")
    state_file = repo / "docs" / "project" / "plan-state.json"
    data = json.loads(state_file.read_text(encoding="utf-8"))
    data["rolling_slice_horizon"] = data["rolling_slice_horizon"][:3]
    state_file.write_text(json.dumps(data), encoding="utf-8")

    payload = validate_project_control_surface(repo)
    assert payload["ok"] is False
    assert "plan-state rolling_slice_horizon must contain 4 to 5 slices" in payload["errors"]


def test_project_control_surface_validator_rejects_missing_active_horizon(tmp_path: Path) -> None:
    import shutil

    repo = tmp_path / "repo"
    shutil.copytree(ROOT / "docs", repo / "docs")
    (repo / "VERSION").write_text("v0.1.103.1\n", encoding="utf-8")
    state_file = repo / "docs" / "project" / "plan-state.json"
    data = json.loads(state_file.read_text(encoding="utf-8"))
    for item in data["rolling_slice_horizon"]:
        if item["status"] == "active":
            item["status"] = "planned"
    state_file.write_text(json.dumps(data), encoding="utf-8")

    payload = validate_project_control_surface(repo)
    assert payload["ok"] is False
    assert "rolling_slice_horizon must contain exactly one active slice" in payload["errors"]

def test_project_control_surface_validator_rejects_repair_scope_advance(tmp_path: Path) -> None:
    import shutil

    repo = tmp_path / "repo"
    shutil.copytree(ROOT / "docs", repo / "docs")
    (repo / "VERSION").write_text("v0.1.103.1\n", encoding="utf-8")
    state_file = repo / "docs" / "project" / "plan-state.json"
    data = json.loads(state_file.read_text(encoding="utf-8"))
    data["release_mode"] = "repair"
    data["scope_advance_allowed"] = True
    state_file.write_text(json.dumps(data), encoding="utf-8")

    payload = validate_project_control_surface(repo)
    assert payload["ok"] is False
    assert "repair releases must set scope_advance_allowed=false" in payload["errors"]
