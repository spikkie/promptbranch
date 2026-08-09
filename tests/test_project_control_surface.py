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
    "canonical-release-state-machine.md",
    "project-authority-graph-v0.1.109.json",
    "promptbranch-behavioral-surface-v0.1.109.1.json",
    "behavioral-surface.md",
]


def read_doc(name: str) -> str:
    return (PROJECT_DOCS / name).read_text(encoding="utf-8")




def test_project_control_surface_accepts_deep_repair_version() -> None:
    from promptbranch_project_control import VERSION_RE

    assert VERSION_RE.match("v0.1.103.10.106")
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
    assert "v0.1.104.5" in text
    assert "accepted/current" in text
    assert "chatgpt_claudecode_workflow-2_v0.1.124.zip" in text
    assert "chatgpt_claudecode_workflow-2_v0.1.125.3.4.2.zip" in text
    assert "v0.1.104" in text
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
    assert "accepted/current artifact:" in text
    assert "chatgpt_claudecode_workflow-2_v0.1.124.zip" in text
    assert "chatgpt_claudecode_workflow-2_v0.1.125.3.4.2.zip" in text
    assert "standard browser profile default" in text


def test_validation_matrix_declares_required_release_groups() -> None:
    text = read_doc("validation-matrix.md")
    assert "| Group | Required | Purpose | Representative command |" in text
    for group in [
        "project_control_surface",
        "project_authority_behavioral_surface",
        "application_architecture_structural",
        "application_architecture_registry",
        "application_architecture_executable",
        "version_surface",
        "artifact_json_contracts",
        "repo_project_registry",
        "browser_scheduler_source_lifecycle",
        "release_lifecycle_plan",
        "release_state_machine",
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
    assert data["accepted_current_version"] == "v0.1.125.3.4.2"
    assert data["accepted_current_artifact"] == "chatgpt_claudecode_workflow-2_v0.1.125.3.4.2.zip"
    assert data["active_candidate_version"] == "v0.1.126.1.1.1.1.3"
    assert data["active_candidate_artifact"] == "chatgpt_claudecode_workflow-2_v0.1.126.1.1.1.1.3.zip"
    assert data["active_candidate_transport_artifact"] == "chatgpt_claudecode_workflow-2_v0.1.126.1.1.1.1.3.zip"
    assert data["next_normal_version"] == "v0.1.126"
    assert data["active_slice"] == "v0.1.126.1.1.1.1.3 — Release validation Python authority propagation repair"
    assert data["next_planned_version_after_acceptance"] == "v0.1.127"
    assert data["next_planned_slice_after_acceptance"] == "v0.1.127 — Portable Promptbranch tool-authoring skill and export bundle"
    assert data["repair_must_not_advance_scope"] is True
    assert data["release_mode"] == "repair"
    assert data["scope_advance_allowed"] is False
    assert "controlled problem-solving loop" in data["architecture_goal"]
    assert len(data["rolling_slice_horizon"]) == 12


def test_project_control_surface_validator_passes_current_repo() -> None:
    payload = validate_project_control_surface(ROOT)
    assert payload["ok"] is True, payload.get("errors")
    assert payload["accepted_current_version"] == "v0.1.125.3.4.2"
    assert payload["active_candidate_version"] == "v0.1.126.1.1.1.1.3"
    assert payload["next_normal_slice"] == "v0.1.126 — Persistent whole-release ETA estimator"
    assert "controlled problem-solving loop" in payload["architecture_goal"]
    assert len(payload["rolling_slice_horizon"]) == 12


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
    assert payload["active_candidate_artifact"] == "chatgpt_claudecode_workflow-2_v0.1.126.1.1.1.1.3.zip"


def test_project_control_surface_validator_rejects_drifted_status(tmp_path: Path) -> None:
    import shutil

    repo = tmp_path / "repo"
    shutil.copytree(ROOT / "docs", repo / "docs")
    shutil.copy2(ROOT / "PROJECT_SETTINGS.md", repo / "PROJECT_SETTINGS.md")
    shutil.copy2(ROOT / "AGENTS.md", repo / "AGENTS.md")
    shutil.copy2(ROOT / ".promptbranch-ai.json", repo / ".promptbranch-ai.json")
    (repo / ".promptbranch").mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / ".promptbranch" / "ai-registry.json", repo / ".promptbranch" / "ai-registry.json")
    (repo / "promptbranch_protocol" / "schemas").mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "promptbranch_protocol" / "schemas" / "application.architecture.schema.json", repo / "promptbranch_protocol" / "schemas" / "application.architecture.schema.json")
    shutil.copy2(ROOT / "promptbranch_protocol" / "schemas" / "application.registry.schema.json", repo / "promptbranch_protocol" / "schemas" / "application.registry.schema.json")
    (repo / "VERSION").write_text("v0.1.126\n", encoding="utf-8")
    status = repo / "docs" / "project" / "status.md"
    text = status.read_text(encoding="utf-8")
    status.write_text(text.replace("accepted_current_artifact: chatgpt_claudecode_workflow-2_v0.1.125.3.4.2.zip", "accepted_current_artifact: chatgpt_claudecode_workflow-2_v0.1.79.zip"), encoding="utf-8")

    payload = validate_project_control_surface(repo)
    assert payload["ok"] is False
    assert any("accepted_current_artifact" in error or "accepted_current_version" in error for error in payload["errors"])



def test_architecture_and_slice_horizon_are_documented() -> None:
    architecture = read_doc("architecture.md")
    horizon = read_doc("slice-horizon.md")
    assert "controlled problem-solving loop" in architecture
    assert "Fixed architecture invariants" in architecture
    assert "Repair releases must not advance scope" in architecture
    for version in ["v0.1.125.3.3", "v0.1.125.3.4.1", "v0.1.125.3.4.2", "v0.1.126", "v0.1.127", "v0.1.128", "v0.1.129", "v0.1.130", "v0.1.131", "v0.1.132", "v0.1.133", "v0.1.134"]:
        assert version in horizon
    assert "Repair horizon rule" in horizon


def test_project_next_slice_payload_is_derived_from_validated_control_surface() -> None:
    payload = build_project_next_slice_payload(ROOT)
    assert payload["ok"] is True, payload.get("errors")
    assert payload["baseline_artifact"] == "chatgpt_claudecode_workflow-2_v0.1.125.3.4.2.zip"
    assert payload["next_normal_version"] == "v0.1.126"
    assert payload["next_normal_slice"] == "v0.1.126 — Persistent whole-release ETA estimator"
    assert payload["next_slice_after_acceptance_version"] == "v0.1.127"
    assert payload["next_slice_after_acceptance"] == "v0.1.127 — Portable Promptbranch tool-authoring skill and export bundle"
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
    assert payload["next_normal_version"] == "v0.1.126"
    assert payload["next_slice_after_acceptance_version"] == "v0.1.127"


def test_project_control_surface_validator_rejects_short_horizon(tmp_path: Path) -> None:
    import shutil

    repo = tmp_path / "repo"
    shutil.copytree(ROOT / "docs", repo / "docs")
    shutil.copy2(ROOT / "PROJECT_SETTINGS.md", repo / "PROJECT_SETTINGS.md")
    shutil.copy2(ROOT / "AGENTS.md", repo / "AGENTS.md")
    (repo / "VERSION").write_text("v0.1.126\n", encoding="utf-8")
    state_file = repo / "docs" / "project" / "plan-state.json"
    data = json.loads(state_file.read_text(encoding="utf-8"))
    data["rolling_slice_horizon"] = data["rolling_slice_horizon"][:3]
    state_file.write_text(json.dumps(data), encoding="utf-8")

    payload = validate_project_control_surface(repo)
    assert payload["ok"] is False
    assert "plan-state rolling_slice_horizon must contain 4 to 12 slices" in payload["errors"]


def test_project_control_surface_validator_rejects_missing_active_horizon(tmp_path: Path) -> None:
    import shutil

    repo = tmp_path / "repo"
    shutil.copytree(ROOT / "docs", repo / "docs")
    shutil.copy2(ROOT / "PROJECT_SETTINGS.md", repo / "PROJECT_SETTINGS.md")
    shutil.copy2(ROOT / "AGENTS.md", repo / "AGENTS.md")
    (repo / "VERSION").write_text("v0.1.126\n", encoding="utf-8")
    state_file = repo / "docs" / "project" / "plan-state.json"
    data = json.loads(state_file.read_text(encoding="utf-8"))
    for item in data["rolling_slice_horizon"]:
        if item["status"] == "active":
            item["status"] = "planned"
    state_file.write_text(json.dumps(data), encoding="utf-8")

    payload = validate_project_control_surface(repo)
    assert payload["ok"] is False
    assert "rolling_slice_horizon must contain exactly one active slice" in payload["errors"]


def test_project_control_surface_validator_rejects_stale_active_candidate_version(tmp_path: Path) -> None:
    import shutil

    repo = tmp_path / "repo"
    shutil.copytree(ROOT / "docs", repo / "docs")
    (repo / "VERSION").write_text("v0.1.103.10.98\n", encoding="utf-8")
    state_file = repo / "docs" / "project" / "plan-state.json"
    data = json.loads(state_file.read_text(encoding="utf-8"))
    data["active_candidate_version"] = "v0.1.103.10.72"
    data["active_candidate_artifact"] = "chatgpt_claudecode_workflow-2_v0.1.103.10.72.zip"
    data["next_normal_version"] = "v0.1.103.10.72"
    data["next_normal_artifact"] = "chatgpt_claudecode_workflow-2_v0.1.103.10.72.zip"
    state_file.write_text(json.dumps(data), encoding="utf-8")

    payload = validate_project_control_surface(repo)
    assert payload["ok"] is False
    assert "VERSION 'v0.1.103.10.98' must match plan-state active_candidate_version 'v0.1.103.10.72'" in payload["errors"]

def test_project_control_surface_validator_rejects_repair_scope_advance(tmp_path: Path) -> None:
    import shutil

    repo = tmp_path / "repo"
    shutil.copytree(ROOT / "docs", repo / "docs")
    shutil.copy2(ROOT / "PROJECT_SETTINGS.md", repo / "PROJECT_SETTINGS.md")
    shutil.copy2(ROOT / "AGENTS.md", repo / "AGENTS.md")
    (repo / "VERSION").write_text("v0.1.126\n", encoding="utf-8")
    state_file = repo / "docs" / "project" / "plan-state.json"
    data = json.loads(state_file.read_text(encoding="utf-8"))
    data["release_mode"] = "repair"
    data["scope_advance_allowed"] = True
    state_file.write_text(json.dumps(data), encoding="utf-8")

    payload = validate_project_control_surface(repo)
    assert payload["ok"] is False
    assert "repair releases must set scope_advance_allowed=false" in payload["errors"]


def test_v0_1_106_promotion_decision_record_is_go_with_design_only_authority() -> None:
    record_path = PROJECT_DOCS / "correction-promotion-decision-v0.1.106.json"
    assert record_path.is_file()
    payload = json.loads(record_path.read_text(encoding="utf-8"))

    assert payload["schema"] == "promptbranch.loop.sandbox_correction_promotion_decision"
    assert payload["schema_version"] == "1.0"
    assert payload["decision_version"] == "v0.1.106"
    assert payload["readiness_contract_version"] == "v0.1.105.1"
    assert payload["status"] == "promotion_go_recorded"
    assert payload["decision"] == "go"
    assert payload["decision_scope"] == "controlled_execution_envelope_design_only"
    assert payload["source_readiness"]["observed_run_count"] == 3
    assert payload["source_readiness"]["unique_workspace_count"] == 3
    assert payload["source_readiness"]["unique_fingerprint_count"] == 1
    assert payload["source_readiness"]["determinism_fingerprint_sha256"] == "470e04f73c008bcd49827102f94f84e447f6f8618db69ae3272159f637959756"
    assert payload["mandatory_evidence"]["passed_check_count"] == 32
    assert payload["mandatory_evidence"]["failed_check_count"] == 0
    assert payload["triggered_stop_conditions"] == []
    assert payload["authority"]["v0_1_107_execution_envelope_design_authorized"] is True
    assert payload["authority"]["correction_execution_authority_granted"] is False
    assert payload["authority"]["disposable_repository_mutation_authority_granted"] is False
    assert payload["authority"]["real_repository_mutation_authority_granted"] is False
    assert payload["authority"]["deployment_authority_granted"] is False
    assert payload["authority"]["project_source_mutation_authority_granted"] is False
    assert payload["authority"]["artifact_adoption_authority_granted"] is False
    assert payload["authority"]["chatgpt_project_deletion_authority_granted"] is False
    assert payload["next_slice"]["version"] == "v0.1.107"
    assert payload["next_slice"]["scope"] == "design_only_no_correction_execution"


def test_v0_1_107_controlled_execution_envelope_record_is_design_only() -> None:
    record_path = PROJECT_DOCS / "controlled-correction-execution-envelope-v0.1.107.json"
    assert record_path.is_file()
    payload = json.loads(record_path.read_text(encoding="utf-8"))

    assert payload["schema"] == "promptbranch.loop.controlled_correction_execution_envelope_design"
    assert payload["design_version"] == "v0.1.107"
    assert payload["status"] == "execution_envelope_design_ready"
    assert payload["determinism"]["canonical_design_sha256"] == "742089d5904ab2db9fb16a44f1eb7390c3c1acbb3d12edf8a892e13c43b0c057"
    assert payload["execution_envelope"]["allowed_target"]["kind"] == "future_disposable_repository_copy"
    assert payload["execution_envelope"]["allowed_files"]["maximum_mutable_file_count"] == 1
    assert payload["execution_envelope"]["allowed_operation"]["maximum_occurrences"] == 1
    assert payload["execution_envelope"]["rollback"]["required"] is True
    assert payload["authority"]["future_envelope_validation_authority_granted"] is True
    assert payload["authority"]["correction_execution_authority_granted"] is False
    assert payload["authority"]["disposable_repository_mutation_authority_granted"] is False
    assert payload["authority"]["real_repository_mutation_authority_granted"] is False
    assert payload["safety"]["commands_executed"] == 0
    assert payload["safety"]["files_mutated"] is False
    assert payload["safety"]["workspace_created"] is False
    assert payload["next_slice"]["version"] == "v0.1.108"


def test_v0_1_108_controlled_execution_envelope_validation_record_is_validation_only() -> None:
    record_path = PROJECT_DOCS / "controlled-correction-execution-envelope-validation-v0.1.108.json"
    assert record_path.is_file()
    payload = json.loads(record_path.read_text(encoding="utf-8"))

    assert payload["schema"] == "promptbranch.loop.controlled_correction_execution_envelope_validation"
    assert payload["validation_version"] == "v0.1.108"
    assert payload["status"] == "execution_envelope_validation_passed"
    assert payload["passed_validation_check_count"] == 36
    assert payload["failed_validation_check_count"] == 0
    assert payload["determinism"]["recorded_design_sha256"] == "742089d5904ab2db9fb16a44f1eb7390c3c1acbb3d12edf8a892e13c43b0c057"
    assert payload["determinism"]["fingerprints_match"] is True
    assert payload["authority"]["v0_1_109_project_authority_graph_definition_authorized"] is True
    assert payload["authority"]["correction_execution_authority_granted"] is False
    assert payload["authority"]["disposable_repository_mutation_authority_granted"] is False
    assert payload["authority"]["real_repository_mutation_authority_granted"] is False
    assert payload["safety"]["commands_executed"] == 0
    assert payload["safety"]["files_mutated"] is False
    assert payload["safety"]["workspace_created"] is False
    assert payload["next_slice"]["version"] == "v0.1.109"
    assert payload["next_slice"]["slice"] == "PROJECT_SETTINGS.md, AGENTS.md and project authority-graph definition"


def test_v0_1_108_1_project_source_reliability_record_is_repair_only() -> None:
    record_path = PROJECT_DOCS / "project-source-staged-overwrite-removal-proof-reliability-v0.1.108.1.json"
    assert record_path.is_file()
    payload = json.loads(record_path.read_text(encoding="utf-8"))

    assert payload["schema"] == "promptbranch.project_source.file_reliability_repair"
    assert payload["repair_version"] == "v0.1.108.1"
    assert payload["repair_of_version"] == "v0.1.108"
    assert payload["staged_overwrite"]["maximum_retry_count"] == 1
    assert payload["staged_overwrite"]["old_source_delete_before_replacement_identity"] is False
    assert payload["removal_proof"]["required_stable_observations"] == 2
    assert payload["removal_proof"]["only_success_status"] == "verified_absent"
    assert payload["focused_live_profile"]["adoption_grade"] is False
    assert payload["authority"]["scope_advance_allowed"] is False
    assert payload["authority"]["v0_1_109_implementation_started"] is False
    assert payload["next_planned_slice_after_acceptance"]["version"] == "v0.1.109"


def test_tracked_project_binding_migration_document_exists() -> None:
    path = ROOT / "docs" / "migrations" / "tracked-project-binding-v0.1.109.1.1.md"
    text = path.read_text(encoding="utf-8")
    assert "pb project join --repo-root . --json" in text
    assert "git restore .promptbranch-repo.json" in text
    assert "runtime evidence" in text.lower()
