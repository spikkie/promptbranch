from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

SCHEMA_ID = "promptbranch.orchestration.event_intake"
SCHEMA_VERSION = "1.0"
ROOT = Path(__file__).resolve().parent
DEFAULT_EXAMPLES_DIR = ROOT / "docs" / "design" / "orchestration" / "examples" / "events"
SCHEMA_PATH = ROOT / "docs" / "design" / "orchestration" / "schemas" / "event_intake.schema.json"
VERSION_PATTERN = re.compile(r"^v[0-9]+\.[0-9]+\.[0-9]+(?:\.[0-9]+)*$")
EVENT_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")

REQUIRED_AUTHORITY = {
    "proposal_only": True,
    "runtime_state_mutation_allowed": False,
    "source_mutation_allowed": False,
    "artifact_adoption_allowed": False,
    "deployment_allowed": False,
    "model_may_execute": False,
    "promptbranch_must_validate": True,
}
ALLOWED_EVENT_TYPES = {"slice_proposal", "validation_proposal", "release_proposal"}
ALLOWED_SLICE_TYPES = {"normal", "repair"}
ALLOWED_ACTION_KINDS = {
    "define_schema",
    "validate_event",
    "record_proposal_fixture",
    "plan_next_slice",
    "release_candidate_request",
}


def display_path(path: Path, *, root: Path | None = None) -> str:
    base = (root or ROOT).resolve()
    try:
        resolved = path.resolve()
    except OSError:
        return str(path)
    try:
        return str(resolved.relative_to(base))
    except ValueError:
        return str(resolved)


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        value = json.load(fh)
    if not isinstance(value, dict):
        raise ValueError(f"{display_path(path)} must contain a JSON object")
    return value


def repo_relative_path(value: Any, *, root: Path = ROOT) -> Path | None:
    if not isinstance(value, str) or not value.strip():
        return None
    candidate = Path(value)
    if candidate.is_absolute() or ".." in candidate.parts:
        return None
    resolved = (root / candidate).resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError:
        return None
    return resolved


def _require_string(value: dict[str, Any], key: str, source: str, errors: list[str]) -> str:
    text = str(value.get(key) or "").strip()
    if not text:
        errors.append(f"{source}: {key} is required")
    return text


def _validate_authority(value: dict[str, Any], source: str, errors: list[str]) -> None:
    authority = value.get("authority") or {}
    if not isinstance(authority, dict):
        errors.append(f"{source}: authority must be an object")
        authority = {}
    for key, expected in REQUIRED_AUTHORITY.items():
        if authority.get(key) is not expected:
            errors.append(f"{source}: authority.{key} must be {expected!r}")


def _validate_release(value: dict[str, Any], source: str, errors: list[str]) -> None:
    release = value.get("release") or {}
    if not isinstance(release, dict):
        errors.append(f"{source}: release must be an object")
        return
    baseline = _require_string(release, "baseline_version", f"{source}: release", errors)
    target = _require_string(release, "target_version", f"{source}: release", errors)
    slice_type = _require_string(release, "slice_type", f"{source}: release", errors)
    if baseline and not VERSION_PATTERN.match(baseline):
        errors.append(f"{source}: release.baseline_version must be canonical v-prefixed version text")
    if target and not VERSION_PATTERN.match(target):
        errors.append(f"{source}: release.target_version must be canonical v-prefixed version text")
    if baseline and target and baseline == target:
        errors.append(f"{source}: release.target_version must differ from baseline_version")
    if slice_type and slice_type not in ALLOWED_SLICE_TYPES:
        errors.append(f"{source}: release.slice_type must be one of {sorted(ALLOWED_SLICE_TYPES)}")


def _validate_repo(value: dict[str, Any], source: str, errors: list[str]) -> None:
    repo = value.get("repo") or {}
    if not isinstance(repo, dict):
        errors.append(f"{source}: repo must be an object")
        return
    repo_id = _require_string(repo, "id", f"{source}: repo", errors)
    if repo_id and not EVENT_ID_PATTERN.match(repo_id):
        errors.append(f"{source}: repo.id contains unsupported characters")
    path_value = repo.get("path")
    if path_value is not None and repo_relative_path(path_value) is None:
        errors.append(f"{source}: repo.path must be repo-relative and must not contain '..'")


def _validate_proposed_action(value: dict[str, Any], source: str, errors: list[str]) -> None:
    action = value.get("proposed_action") or {}
    if not isinstance(action, dict):
        errors.append(f"{source}: proposed_action must be an object")
        return
    kind = _require_string(action, "kind", f"{source}: proposed_action", errors)
    if kind and kind not in ALLOWED_ACTION_KINDS:
        errors.append(f"{source}: proposed_action.kind must be one of {sorted(ALLOWED_ACTION_KINDS)}")
    _require_string(action, "summary", f"{source}: proposed_action", errors)
    writes = action.get("writes") or []
    if not isinstance(writes, list):
        errors.append(f"{source}: proposed_action.writes must be a list")
        return
    for index, item in enumerate(writes):
        if not isinstance(item, str) or not item.strip():
            errors.append(f"{source}: proposed_action.writes[{index}] must be a non-empty string")
            continue
        if repo_relative_path(item) is None:
            errors.append(f"{source}: proposed_action.writes[{index}] must be repo-relative and must not contain '..'")


def _validate_evidence(value: dict[str, Any], source: str, errors: list[str]) -> None:
    evidence = value.get("evidence") or {}
    if not isinstance(evidence, dict):
        errors.append(f"{source}: evidence must be an object")
        return
    status = str(evidence.get("validation_status") or "").strip()
    if status != "proposal_validated_read_only":
        errors.append(f"{source}: evidence.validation_status must be proposal_validated_read_only")
    validated_by = evidence.get("validated_by") or []
    if not isinstance(validated_by, list) or not validated_by:
        errors.append(f"{source}: evidence.validated_by must be a non-empty list")
    elif "scripts/orchestration/validate_event_intake.py" not in validated_by and "pb orchestration validate-event" not in validated_by:
        errors.append(
            f"{source}: evidence.validated_by must include scripts/orchestration/validate_event_intake.py "
            "or pb orchestration validate-event"
        )
    notes = evidence.get("notes") or []
    if not isinstance(notes, list) or not notes:
        errors.append(f"{source}: evidence.notes must be a non-empty list")


def validate_event_intake(value: dict[str, Any], *, source: str = "<memory>") -> list[str]:
    errors: list[str] = []
    if value.get("schema") != SCHEMA_ID:
        errors.append(f"{source}: schema must be {SCHEMA_ID}")
    if value.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"{source}: schema_version must be {SCHEMA_VERSION}")
    event_id = _require_string(value, "event_id", source, errors)
    if event_id and not EVENT_ID_PATTERN.match(event_id):
        errors.append(f"{source}: event_id contains unsupported characters")
    event_type = _require_string(value, "event_type", source, errors)
    if event_type and event_type not in ALLOWED_EVENT_TYPES:
        errors.append(f"{source}: event_type must be one of {sorted(ALLOWED_EVENT_TYPES)}")

    _validate_repo(value, source, errors)
    _validate_release(value, source, errors)
    _validate_authority(value, source, errors)
    _validate_proposed_action(value, source, errors)
    _validate_evidence(value, source, errors)
    return errors


def example_paths(root: Path = ROOT) -> list[Path]:
    examples_dir = root / "docs" / "design" / "orchestration" / "examples" / "events"
    return sorted(examples_dir.glob("*.example.json"))



ORCHESTRATION_RELATIVE_DIR = Path("docs") / "design" / "orchestration"
ACCEPTED_EVENT_SCHEMA_ID = "promptbranch.orchestration.accepted_event"
ACCEPTED_EVENT_SCHEMA_VERSION = "1.0"
GRILL_SCHEMA_ID = "promptbranch.orchestration.grill"
ACCEPTED_EVENT_STATE_MACHINE_RELATIVE_PATH = ORCHESTRATION_RELATIVE_DIR / "state_machines" / "k8s_game_mvp.state_machine.json"
ACCEPTED_EVENT_EXAMPLES_RELATIVE_DIR = ORCHESTRATION_RELATIVE_DIR / "examples" / "accepted_events"
VERSION_PATTERN = re.compile(r"^v[0-9]+\.[0-9]+\.[0-9]+(?:\.[0-9]+)*$")
ARTIFACT_REF_PATTERN = re.compile(r"^chatgpt_claudecode_workflow-2_v[0-9]+\.[0-9]+\.[0-9]+(?:\.[0-9]+)*\.zip$")
ACCEPTED_EVENT_EXPECTED_CONSTRAINTS = {
    "fixture_only": True,
    "runtime_state_mutation_allowed": False,
    "source_mutation_allowed": False,
    "artifact_adoption_allowed": False,
    "deployment_allowed": False,
    "model_may_execute": False,
    "promptbranch_must_validate": True,
}
GRILL_ALLOWED_STAGES = {
    "G0_intent",
    "G1_mvp",
    "G2_architecture",
    "G3_slice",
    "G4_implementation",
    "G5_release_deployment",
    "G6_maintenance",
}
GRILL_STAGE_TRANSITION_RECOMMENDATIONS = {
    "G0_intent": ("draft", "intake_accepted"),
    "G1_mvp": ("intake_accepted", "grill_me_accepted"),
    "G2_architecture": ("grill_me_accepted", "architecture_accepted"),
    "G3_slice": ("architecture_accepted", "slice_plan_accepted"),
    "G4_implementation": ("slice_plan_accepted", "implementation_candidate"),
    "G5_release_deployment": ("implementation_candidate", "artifact_verified"),
    "G6_maintenance": ("deployment_smoke_passed", "maintenance_ready"),
}
GRILL_ALLOWED_PROVIDERS = {"chatgpt", "manual_fixture"}
GRILL_REJECTED_PROVIDERS = {"ollama", "local_llm", "unknown"}


def discover_repo_root(start: Path | None = None) -> Path:
    """Find the repo root that owns docs/design/orchestration.

    Promptbranch can run from an installed pipx module while the operator's
    current working directory is the repository.  Validators must therefore not
    assume package-install layout contains repo docs or scripts.  Prefer the
    working tree when it exposes the orchestration docs; fall back to the module
    directory for source-tree execution.
    """
    candidates: list[Path] = []
    for seed in [start, Path.cwd(), ROOT]:
        if seed is None:
            continue
        try:
            resolved = seed.resolve()
        except OSError:
            resolved = seed
        if resolved.is_file():
            resolved = resolved.parent
        candidates.extend([resolved, *resolved.parents])
    seen: set[Path] = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        if (candidate / ORCHESTRATION_RELATIVE_DIR).is_dir():
            return candidate
    return ROOT


def orchestration_root(root: Path | None = None) -> Path:
    return discover_repo_root(root) / ORCHESTRATION_RELATIVE_DIR


def display_path_for_root(path: Path, *, root: Path | None = None) -> str:
    base = discover_repo_root(root).resolve()
    try:
        resolved = path.resolve()
    except OSError:
        return str(path)
    try:
        return str(resolved.relative_to(base))
    except ValueError:
        return str(resolved)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def repo_relative_path_for_root(value: Any, *, root: Path | None = None) -> Path | None:
    if not isinstance(value, str) or not value.strip():
        return None
    candidate = Path(value)
    if candidate.is_absolute() or ".." in candidate.parts:
        return None
    repo_root = discover_repo_root(root)
    resolved = (repo_root / candidate).resolve()
    try:
        resolved.relative_to(repo_root.resolve())
    except ValueError:
        return None
    return resolved


def accepted_event_state_machine_path(root: Path | None = None) -> Path:
    return discover_repo_root(root) / ACCEPTED_EVENT_STATE_MACHINE_RELATIVE_PATH


def accepted_event_example_paths(root: Path | None = None) -> list[Path]:
    repo_root = discover_repo_root(root)
    return sorted((repo_root / ACCEPTED_EVENT_EXAMPLES_RELATIVE_DIR).glob("*.example.json"))


def load_accepted_event_state_machine(root: Path | None = None) -> dict[str, Any]:
    path = accepted_event_state_machine_path(root)
    value = read_json(path)
    transitions = value.get("transitions")
    if not isinstance(transitions, list):
        raise ValueError(f"{display_path_for_root(path, root=root)} must contain a transitions list")
    return value


def state_machine_transition_pairs(machine: dict[str, Any]) -> set[tuple[str, str]]:
    pairs: set[tuple[str, str]] = set()
    for transition in machine.get("transitions", []):
        if isinstance(transition, dict):
            from_state = str(transition.get("from") or "").strip()
            to_state = str(transition.get("to") or "").strip()
            if from_state and to_state:
                pairs.add((from_state, to_state))
    return pairs


def validate_grill_envelope(
    value: dict[str, Any],
    *,
    source: str = "<memory>",
    state_machine: dict[str, Any] | None = None,
    root: Path | None = None,
) -> list[str]:
    errors: list[str] = []
    if state_machine is None:
        try:
            state_machine = load_accepted_event_state_machine(root)
        except Exception as exc:  # noqa: BLE001 - validator should report deterministic setup errors.
            errors.append(f"{source}: failed to load state machine: {exc}")
            state_machine = {}
    transition_pairs = state_machine_transition_pairs(state_machine)

    if value.get("schema") != GRILL_SCHEMA_ID:
        errors.append(f"{source}: schema must be {GRILL_SCHEMA_ID}")
    if value.get("schema_version") != "1.0":
        errors.append(f"{source}: schema_version must be 1.0")

    stage = value.get("stage")
    if stage not in GRILL_ALLOWED_STAGES:
        errors.append(f"{source}: stage must be one of {sorted(GRILL_ALLOWED_STAGES)}")

    project = value.get("project") or {}
    if not isinstance(project, dict):
        errors.append(f"{source}: project must be an object")
        project = {}
    project_id = str(project.get("id") or "").strip()
    if not project_id:
        errors.append(f"{source}: project.id is required")
    elif state_machine.get("project_id") and project_id != state_machine.get("project_id"):
        errors.append(
            f"{source}: project.id {project_id!r} must match state machine project_id "
            f"{state_machine.get('project_id')!r}"
        )
    if not str(project.get("role") or "").strip():
        errors.append(f"{source}: project.role is required")

    provider = value.get("provider") or {}
    if not isinstance(provider, dict):
        errors.append(f"{source}: provider must be an object")
        provider = {}
    provider_kind = provider.get("kind")
    if provider_kind in GRILL_REJECTED_PROVIDERS or provider_kind not in GRILL_ALLOWED_PROVIDERS:
        errors.append(f"{source}: provider.kind rejected: {provider_kind!r}")
    if provider_kind == "manual_fixture" and provider.get("critical_path") is not False:
        errors.append(f"{source}: manual_fixture provider must not be critical_path")
    if provider_kind == "chatgpt" and provider.get("critical_path") is not True:
        errors.append(f"{source}: chatgpt provider must be critical_path=true")

    if value.get("proposal_status") != "proposal_only":
        errors.append(f"{source}: proposal_status must be proposal_only")

    constraints = value.get("constraints") or {}
    if not isinstance(constraints, dict):
        errors.append(f"{source}: constraints must be an object")
        constraints = {}
    expected_constraints = {
        "model_may_execute": False,
        "promptbranch_must_validate": True,
        "source_mutation_allowed": False,
        "artifact_adoption_allowed": False,
    }
    for key, expected in expected_constraints.items():
        if constraints.get(key) is not expected:
            errors.append(f"{source}: constraints.{key} must be {expected!r}")

    questions = value.get("questions") or []
    if not isinstance(questions, list) or not questions:
        errors.append(f"{source}: questions must be a non-empty list")
    else:
        seen_ids: set[str] = set()
        for index, question in enumerate(questions):
            if not isinstance(question, dict):
                errors.append(f"{source}: questions[{index}] must be an object")
                continue
            qid = str(question.get("id") or "").strip()
            if not qid:
                errors.append(f"{source}: questions[{index}].id is required")
            elif qid in seen_ids:
                errors.append(f"{source}: duplicate question id {qid}")
            seen_ids.add(qid)
            if not str(question.get("question") or "").strip():
                errors.append(f"{source}: questions[{index}].question is required")
            if not str(question.get("risk") or "").strip():
                errors.append(f"{source}: questions[{index}].risk is required")

    acceptance = value.get("acceptance") or {}
    if not isinstance(acceptance, dict):
        errors.append(f"{source}: acceptance must be an object")
        acceptance = {}
    if acceptance.get("decision") not in {"continue", "revise", "block"}:
        errors.append(f"{source}: acceptance.decision must be continue, revise, or block")
    if not isinstance(acceptance.get("blocking_findings", []), list):
        errors.append(f"{source}: acceptance.blocking_findings must be a list")

    recommendation = value.get("next_state_recommendation") or {}
    if not isinstance(recommendation, dict):
        errors.append(f"{source}: next_state_recommendation must be an object")
        recommendation = {}
    for key in ("from", "to", "reason"):
        if not str(recommendation.get(key) or "").strip():
            errors.append(f"{source}: next_state_recommendation.{key} is required")

    from_state = str(recommendation.get("from") or "").strip()
    to_state = str(recommendation.get("to") or "").strip()
    if from_state and to_state:
        if (from_state, to_state) not in transition_pairs:
            errors.append(
                f"{source}: next_state_recommendation {from_state!r}->{to_state!r} "
                "is not a k8s-game MVP state-machine transition"
            )
        expected_transition = GRILL_STAGE_TRANSITION_RECOMMENDATIONS.get(str(stage))
        if expected_transition and (from_state, to_state) != expected_transition:
            errors.append(
                f"{source}: stage {stage} must recommend transition "
                f"{expected_transition[0]!r}->{expected_transition[1]!r}, got {from_state!r}->{to_state!r}"
            )

    return errors


def _validate_accepted_event_baseline(value: dict[str, Any], source: str, errors: list[str]) -> None:
    baseline = value.get("baseline") or {}
    if not isinstance(baseline, dict):
        errors.append(f"{source}: baseline must be an object")
        baseline = {}
    required = ("artifact_ref", "artifact_version", "source_ref", "source_version", "role")
    for key in required:
        if not str(baseline.get(key) or "").strip():
            errors.append(f"{source}: baseline.{key} is required")
    artifact_ref = str(baseline.get("artifact_ref") or "").strip()
    source_ref = str(baseline.get("source_ref") or "").strip()
    artifact_version = str(baseline.get("artifact_version") or "").strip()
    source_version = str(baseline.get("source_version") or "").strip()
    if artifact_ref and not ARTIFACT_REF_PATTERN.match(artifact_ref):
        errors.append(f"{source}: baseline.artifact_ref must be a canonical chatgpt_claudecode_workflow-2 release ZIP")
    if source_ref and not ARTIFACT_REF_PATTERN.match(source_ref):
        errors.append(f"{source}: baseline.source_ref must be a canonical chatgpt_claudecode_workflow-2 source ZIP")
    if artifact_version and not VERSION_PATTERN.match(artifact_version):
        errors.append(f"{source}: baseline.artifact_version must be a canonical v-prefixed version")
    if source_version and not VERSION_PATTERN.match(source_version):
        errors.append(f"{source}: baseline.source_version must be a canonical v-prefixed version")
    if artifact_ref and artifact_version and artifact_version not in artifact_ref:
        errors.append(f"{source}: baseline.artifact_ref must contain baseline.artifact_version")
    if source_ref and source_version and source_version not in source_ref:
        errors.append(f"{source}: baseline.source_ref must contain baseline.source_version")
    if artifact_version and source_version and artifact_version != source_version:
        errors.append(f"{source}: baseline.artifact_version must match baseline.source_version")
    if str(baseline.get("role") or "").strip() != "accepted_current_source_baseline":
        errors.append(f"{source}: baseline.role must be accepted_current_source_baseline")


def validate_accepted_event(
    value: dict[str, Any],
    *,
    source: str = "<memory>",
    state_machine: dict[str, Any] | None = None,
    root: Path | None = None,
) -> list[str]:
    errors: list[str] = []
    repo_root = discover_repo_root(root)
    if state_machine is None:
        try:
            state_machine = load_accepted_event_state_machine(repo_root)
        except Exception as exc:  # noqa: BLE001 - validator should report deterministic setup errors.
            errors.append(f"{source}: failed to load state machine: {exc}")
            state_machine = {}

    if value.get("schema") != ACCEPTED_EVENT_SCHEMA_ID:
        errors.append(f"{source}: schema must be {ACCEPTED_EVENT_SCHEMA_ID}")
    if value.get("schema_version") != ACCEPTED_EVENT_SCHEMA_VERSION:
        errors.append(f"{source}: schema_version must be {ACCEPTED_EVENT_SCHEMA_VERSION}")
    if not str(value.get("event_id") or "").strip():
        errors.append(f"{source}: event_id is required")
    if value.get("decision") != "accepted":
        errors.append(f"{source}: decision must be accepted")

    project = value.get("project") or {}
    if not isinstance(project, dict):
        errors.append(f"{source}: project must be an object")
        project = {}
    project_id = str(project.get("id") or "").strip()
    if not project_id:
        errors.append(f"{source}: project.id is required")
    elif state_machine.get("project_id") and project_id != state_machine.get("project_id"):
        errors.append(
            f"{source}: project.id {project_id!r} must match state machine project_id "
            f"{state_machine.get('project_id')!r}"
        )
    if not str(project.get("role") or "").strip():
        errors.append(f"{source}: project.role is required")

    _validate_accepted_event_baseline(value, source, errors)

    constraints = value.get("constraints") or {}
    if not isinstance(constraints, dict):
        errors.append(f"{source}: constraints must be an object")
        constraints = {}
    for key, expected in ACCEPTED_EVENT_EXPECTED_CONSTRAINTS.items():
        if constraints.get(key) is not expected:
            errors.append(f"{source}: constraints.{key} must be {expected!r}")

    source_grill = value.get("source_grill") or {}
    if not isinstance(source_grill, dict):
        errors.append(f"{source}: source_grill must be an object")
        source_grill = {}
    grill_path = repo_relative_path_for_root(source_grill.get("path"), root=repo_root)
    grill_value: dict[str, Any] = {}
    if grill_path is None:
        errors.append(f"{source}: source_grill.path must be a repo-relative path")
    elif not grill_path.exists():
        errors.append(f"{source}: source_grill.path does not exist: {display_path_for_root(grill_path, root=repo_root)}")
    else:
        try:
            grill_value = read_json(grill_path)
        except Exception as exc:  # noqa: BLE001 - report file errors as validation errors.
            errors.append(f"{source}: failed to read source grill: {exc}")
            grill_value = {}
        expected_sha = str(source_grill.get("sha256") or "").strip()
        actual_sha = sha256_file(grill_path)
        if expected_sha != actual_sha:
            errors.append(
                f"{source}: source_grill.sha256 mismatch for {display_path_for_root(grill_path, root=repo_root)}: "
                f"expected {expected_sha!r}, actual {actual_sha!r}"
            )
        if grill_value:
            grill_errors = validate_grill_envelope(
                grill_value,
                source=display_path_for_root(grill_path, root=repo_root),
                state_machine=state_machine,
                root=repo_root,
            )
            if grill_errors:
                errors.extend(f"{source}: source_grill invalid: {err}" for err in grill_errors)

    grill_stage = str(grill_value.get("stage") or "").strip()
    source_stage = str(source_grill.get("stage") or "").strip()
    if not source_stage:
        errors.append(f"{source}: source_grill.stage is required")
    elif grill_stage and source_stage != grill_stage:
        errors.append(f"{source}: source_grill.stage {source_stage!r} must match source grill stage {grill_stage!r}")

    accepted_transition = value.get("accepted_transition") or {}
    if not isinstance(accepted_transition, dict):
        errors.append(f"{source}: accepted_transition must be an object")
        accepted_transition = {}
    from_state = str(accepted_transition.get("from") or "").strip()
    to_state = str(accepted_transition.get("to") or "").strip()
    if not from_state:
        errors.append(f"{source}: accepted_transition.from is required")
    if not to_state:
        errors.append(f"{source}: accepted_transition.to is required")
    if not str(accepted_transition.get("reason") or "").strip():
        errors.append(f"{source}: accepted_transition.reason is required")
    if from_state and to_state and (from_state, to_state) not in state_machine_transition_pairs(state_machine):
        errors.append(
            f"{source}: accepted transition {from_state!r}->{to_state!r} is not a k8s-game MVP "
            "state-machine transition"
        )

    recommendation = grill_value.get("next_state_recommendation") if isinstance(grill_value, dict) else None
    if isinstance(recommendation, dict) and from_state and to_state:
        rec_from = str(recommendation.get("from") or "").strip()
        rec_to = str(recommendation.get("to") or "").strip()
        if (from_state, to_state) != (rec_from, rec_to):
            errors.append(
                f"{source}: accepted_transition {from_state!r}->{to_state!r} must match source grill "
                f"recommendation {rec_from!r}->{rec_to!r}"
            )

    evidence = value.get("evidence") or {}
    if not isinstance(evidence, dict):
        errors.append(f"{source}: evidence must be an object")
        evidence = {}
    validated_by = evidence.get("validated_by") or []
    if not isinstance(validated_by, list) or not validated_by:
        errors.append(f"{source}: evidence.validated_by must be a non-empty list")
    if "scripts/orchestration/validate_grill.py" not in validated_by:
        errors.append(f"{source}: evidence.validated_by must include scripts/orchestration/validate_grill.py")
    if (
        "scripts/orchestration/validate_accepted_event.py" not in validated_by
        and "pb orchestration validate-accepted-event" not in validated_by
    ):
        errors.append(
            f"{source}: evidence.validated_by must include scripts/orchestration/validate_accepted_event.py "
            "or pb orchestration validate-accepted-event"
        )
    if evidence.get("validation_status") != "read_only_fixture_validated":
        errors.append(f"{source}: evidence.validation_status must be read_only_fixture_validated")
    notes = evidence.get("validation_notes") or []
    if not isinstance(notes, list) or not notes:
        errors.append(f"{source}: evidence.validation_notes must be a non-empty list")

    return errors


def _accepted_event_input_mode(paths: list[Path], *, default_count: int | None = None) -> str:
    if not paths:
        return "none"
    if default_count is not None and len(paths) == default_count:
        default_names = {path.name for path in accepted_event_example_paths()}
        path_names = {path.name for path in paths}
        if default_names and path_names == default_names:
            return "committed_default_examples"
    return "explicit_paths"


def _resolve_accepted_event_input_paths(
    paths: list[Path],
    *,
    root: Path,
) -> tuple[list[Path], list[str]]:
    resolved: list[Path] = []
    errors: list[str] = []
    repo_root = root.resolve()
    for original in paths:
        if ".." in original.parts:
            errors.append(f"{original}: accepted-event input path must not contain '..'")
            continue
        candidate = original if original.is_absolute() else repo_root / original
        try:
            resolved_candidate = candidate.resolve(strict=False)
        except OSError as exc:
            errors.append(f"{original}: failed to resolve accepted-event input path: {exc}")
            continue
        try:
            resolved_candidate.relative_to(repo_root)
        except ValueError:
            errors.append(f"{original}: accepted-event input path must resolve inside the repository root")
            continue
        resolved.append(resolved_candidate)
    return resolved, errors


def validate_accepted_event_paths(paths: list[Path], *, root: Path | None = None) -> dict[str, Any]:
    repo_root = discover_repo_root(root)
    raw_paths = list(paths)
    input_mode = _accepted_event_input_mode(raw_paths, default_count=len(accepted_event_example_paths(repo_root)))
    resolved_paths, path_errors = _resolve_accepted_event_input_paths(raw_paths, root=repo_root)
    if not raw_paths:
        return {
            "ok": False,
            "action": "orchestration_validate_accepted_event",
            "status": "accepted_event_invalid",
            "schema": ACCEPTED_EVENT_SCHEMA_ID,
            "schema_version": ACCEPTED_EVENT_SCHEMA_VERSION,
            "validated_count": 0,
            "validated_paths": [],
            "errors": ["no accepted-event examples were found; pass explicit paths or restore committed examples"],
            "input_mode": input_mode,
            "fixture_only": True,
            "accepted_state_written": False,
            "runtime_state_mutation_allowed": False,
            "source_mutation_allowed": False,
            "artifact_adoption_allowed": False,
            "deployment_allowed": False,
            "model_may_execute": False,
            "operator_action": "restore_accepted_event_examples_or_pass_explicit_paths",
        }
    errors: list[str] = list(path_errors)
    try:
        state_machine = load_accepted_event_state_machine(repo_root)
    except Exception as exc:  # noqa: BLE001 - collect deterministic setup error.
        errors.append(f"failed to load state machine: {exc}")
        state_machine = {}
    for path in resolved_paths:
        try:
            value = read_json(path)
        except Exception as exc:  # noqa: BLE001 - validator should report file errors.
            errors.append(f"{display_path_for_root(path, root=repo_root)}: failed to read JSON: {exc}")
            continue
        errors.extend(
            validate_accepted_event(
                value,
                source=display_path_for_root(path, root=repo_root),
                state_machine=state_machine,
                root=repo_root,
            )
        )
    validated = [] if errors else [display_path_for_root(path, root=repo_root) for path in resolved_paths]
    return {
        "ok": not errors,
        "action": "orchestration_validate_accepted_event",
        "status": "accepted_event_examples_valid" if not errors else "accepted_event_invalid",
        "schema": ACCEPTED_EVENT_SCHEMA_ID,
        "schema_version": ACCEPTED_EVENT_SCHEMA_VERSION,
        "validated_count": len(validated),
        "validated_paths": validated,
        "errors": errors,
        "state_machine": display_path_for_root(accepted_event_state_machine_path(repo_root), root=repo_root),
        "input_mode": input_mode,
        "fixture_only": True,
        "accepted_state_written": False,
        "runtime_state_mutation_allowed": False,
        "source_mutation_allowed": False,
        "artifact_adoption_allowed": False,
        "deployment_allowed": False,
        "model_may_execute": False,
        "operator_action": "accepted_event_may_be_reviewed; no state was mutated" if not errors else "fix_accepted_event_json_and_rerun_validator",
    }


def _accepted_event_preview(path: Path, value: dict[str, Any], *, root: Path) -> dict[str, Any]:
    baseline = value.get("baseline") if isinstance(value.get("baseline"), dict) else {}
    source_grill = value.get("source_grill") if isinstance(value.get("source_grill"), dict) else {}
    transition = value.get("accepted_transition") if isinstance(value.get("accepted_transition"), dict) else {}
    project = value.get("project") if isinstance(value.get("project"), dict) else {}
    return {
        "path": display_path_for_root(path, root=root),
        "event_id": value.get("event_id"),
        "project_id": project.get("id"),
        "source_grill_stage": source_grill.get("stage"),
        "source_grill_path": source_grill.get("path"),
        "accepted_transition": {
            "from": transition.get("from"),
            "to": transition.get("to"),
        },
        "decision": value.get("decision"),
        "baseline": {
            "artifact_ref": baseline.get("artifact_ref"),
            "artifact_version": baseline.get("artifact_version"),
            "source_ref": baseline.get("source_ref"),
            "source_version": baseline.get("source_version"),
        },
    }


def dry_run_accept_event_paths(paths: list[Path], *, root: Path | None = None) -> dict[str, Any]:
    repo_root = discover_repo_root(root)
    raw_paths = list(paths)
    resolved_paths, path_errors = _resolve_accepted_event_input_paths(raw_paths, root=repo_root)
    validation_payload = validate_accepted_event_paths(raw_paths, root=repo_root)
    base_payload: dict[str, Any] = {
        "action": "orchestration_accept_event_dry_run",
        "schema": ACCEPTED_EVENT_SCHEMA_ID,
        "schema_version": ACCEPTED_EVENT_SCHEMA_VERSION,
        "dry_run": True,
        "accepted_state_written": False,
        "runtime_state_mutation_allowed": False,
        "source_mutation_allowed": False,
        "artifact_adoption_allowed": False,
        "deployment_allowed": False,
        "model_may_execute": False,
    }
    if not validation_payload.get("ok"):
        return {
            **base_payload,
            "ok": False,
            "status": "accepted_event_dry_run_rejected",
            "would_accept": False,
            "validated_count": 0,
            "validated_paths": [],
            "accepted_event_preview": [],
            "input_mode": validation_payload.get("input_mode", "none"),
            "missing_evidence": [],
            "rejection_reasons": list(validation_payload.get("errors") or []),
            "validation": validation_payload,
            "operator_action": "fix_accepted_event_json_and_rerun_dry_run",
        }
    previews: list[dict[str, Any]] = []
    missing_evidence: list[str] = []
    for path in resolved_paths:
        try:
            value = read_json(path)
        except Exception as exc:  # noqa: BLE001 - should not happen after validation; keep deterministic payload.
            missing_evidence.append(f"{display_path_for_root(path, root=repo_root)}: failed to reread JSON for preview: {exc}")
            continue
        previews.append(_accepted_event_preview(path, value, root=repo_root))
    ok = not missing_evidence and bool(previews)
    return {
        **base_payload,
        "ok": ok,
        "status": "accepted_event_dry_run_ready" if ok else "accepted_event_dry_run_rejected",
        "would_accept": ok,
        "validated_count": validation_payload.get("validated_count", 0),
        "validated_paths": list(validation_payload.get("validated_paths") or []),
        "accepted_event_preview": previews,
        "input_mode": validation_payload.get("input_mode", "none"),
        "missing_evidence": missing_evidence,
        "rejection_reasons": [] if ok else missing_evidence,
        "validation": validation_payload,
        "operator_action": (
            "accepted_event_may_be_reviewed_for_future_write; no state was mutated"
            if ok
            else "fix_accepted_event_json_and_rerun_dry_run"
        ),
    }


def render_accept_event_dry_run_text(payload: dict[str, Any]) -> str:
    if payload.get("ok"):
        return (
            f"{payload['status']}: would_accept={str(payload.get('would_accept')).lower()} "
            f"validated_count={payload.get('validated_count')} accepted_state_written=false"
        )
    lines = [f"{payload.get('status')}: {len(payload.get('rejection_reasons') or [])} rejection(s)"]
    lines.extend(f"- {reason}" for reason in payload.get("rejection_reasons") or [])
    return "\n".join(lines)


def render_accepted_event_validation_text(payload: dict[str, Any]) -> str:
    if payload.get("ok"):
        return (
            f"{payload['status']}: validated_count={payload['validated_count']} "
            "fixture_only=true accepted_state_written=false"
        )
    lines = [f"{payload['status']}: {len(payload.get('errors') or [])} error(s)"]
    lines.extend(f"- {error}" for error in payload.get("errors") or [])
    return "\n".join(lines)


def validate_paths(paths: list[Path], *, root: Path = ROOT) -> dict[str, Any]:
    errors: list[str] = []
    validated: list[str] = []
    for path in paths:
        try:
            value = read_json(path)
        except Exception as exc:  # noqa: BLE001 - CLI validator should collect deterministic file errors.
            errors.append(f"{display_path(path, root=root)}: failed to read JSON: {exc}")
            continue
        source = display_path(path, root=root)
        event_errors = validate_event_intake(value, source=source)
        if event_errors:
            errors.extend(event_errors)
        else:
            validated.append(source)
    return {
        "ok": not errors,
        "action": "orchestration_validate_event",
        "status": "event_intake_valid" if not errors else "event_intake_invalid",
        "schema": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "validated_count": len(validated),
        "validated_paths": validated,
        "errors": errors,
        "proposal_only": True,
        "runtime_state_mutation_allowed": False,
        "source_mutation_allowed": False,
        "artifact_adoption_allowed": False,
        "deployment_allowed": False,
        "accepted_state_written": False,
        "operator_action": "fix_event_json_and_rerun_validator" if errors else "proposal_may_be_reviewed; no state was mutated",
    }


def render_text(payload: dict[str, Any]) -> str:
    if payload.get("ok"):
        return (
            f"{payload['status']}: validated_count={payload['validated_count']} "
            "proposal_only=true accepted_state_written=false"
        )
    lines = [f"{payload['status']}: {len(payload.get('errors') or [])} error(s)"]
    lines.extend(f"- {error}" for error in payload.get("errors") or [])
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate proposal-only Promptbranch orchestration event-intake JSON.")
    parser.add_argument("paths", nargs="*", help="Event-intake JSON files. Defaults to committed examples.")
    parser.add_argument("--json", action="store_true", help="Emit structured validation result as JSON.")
    args = parser.parse_args(argv)

    paths = [Path(p) for p in args.paths] if args.paths else example_paths()
    payload = validate_paths(paths)
    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print(render_text(payload))
    return 0 if payload.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
