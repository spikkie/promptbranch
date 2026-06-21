#!/usr/bin/env python3
"""Read-only validator for Promptbranch orchestration accepted-event fixtures.

Accepted-event fixtures are data-only proof surfaces in this slice.  The
validator consumes a valid grill recommendation, checks it against the canonical
k8s-game MVP state machine, and verifies the committed accepted-event fixture
without mutating runtime state, project sources, artifacts, deployment state, or
Promptbranch registries.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2].resolve()
ORCH = ROOT / "docs" / "design" / "orchestration"
ACCEPTED_EVENT_SCHEMA_ID = "promptbranch.orchestration.accepted_event"
ACCEPTED_EVENT_SCHEMA_VERSION = "1.0"
STATE_MACHINE_PATH = ORCH / "state_machines" / "k8s_game_mvp.state_machine.json"
GRILL_VALIDATOR_PATH = ROOT / "scripts" / "orchestration" / "validate_grill.py"
VERSION_PATTERN = re.compile(r"^v[0-9]+\.[0-9]+\.[0-9]+(?:\.[0-9]+)*$")
ARTIFACT_REF_PATTERN = re.compile(r"^chatgpt_claudecode_workflow-2_v[0-9]+\.[0-9]+\.[0-9]+(?:\.[0-9]+)*\.zip$")
EXPECTED_CONSTRAINTS = {
    "fixture_only": True,
    "runtime_state_mutation_allowed": False,
    "source_mutation_allowed": False,
    "artifact_adoption_allowed": False,
    "deployment_allowed": False,
    "model_may_execute": False,
    "promptbranch_must_validate": True,
}


def display_path(path: Path) -> str:
    """Return a stable source label for repo-local and external CLI paths."""
    try:
        resolved = path.resolve()
    except OSError:
        return str(path)
    try:
        return str(resolved.relative_to(ROOT))
    except ValueError:
        return str(resolved)


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        value = json.load(fh)
    if not isinstance(value, dict):
        raise ValueError(f"{display_path(path)} must contain a JSON object")
    return value


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def repo_relative_path(value: Any) -> Path | None:
    if not isinstance(value, str) or not value.strip():
        return None
    candidate = Path(value)
    if candidate.is_absolute() or ".." in candidate.parts:
        return None
    resolved = (ROOT / candidate).resolve()
    try:
        resolved.relative_to(ROOT)
    except ValueError:
        return None
    return resolved


def _validate_baseline(value: dict[str, Any], source: str, errors: list[str]) -> None:
    baseline = value.get("baseline") or {}
    if not isinstance(baseline, dict):
        errors.append(f"{source}: baseline must be an object")
        return
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


def load_grill_validator():
    spec = importlib.util.spec_from_file_location("validate_grill", GRILL_VALIDATOR_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load {GRILL_VALIDATOR_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_state_machine() -> dict[str, Any]:
    value = read_json(STATE_MACHINE_PATH)
    transitions = value.get("transitions")
    if not isinstance(transitions, list):
        raise ValueError(f"{display_path(STATE_MACHINE_PATH)} must contain a transitions list")
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


def validate_accepted_event(
    value: dict[str, Any],
    *,
    source: str = "<memory>",
    state_machine: dict[str, Any] | None = None,
    grill_validator: Any | None = None,
) -> list[str]:
    errors: list[str] = []
    if state_machine is None:
        try:
            state_machine = load_state_machine()
        except Exception as exc:  # noqa: BLE001 - validator should report deterministic setup errors.
            errors.append(f"{source}: failed to load state machine: {exc}")
            state_machine = {}
    if grill_validator is None:
        try:
            grill_validator = load_grill_validator()
        except Exception as exc:  # noqa: BLE001 - validator should report deterministic setup errors.
            errors.append(f"{source}: failed to load grill validator: {exc}")
            grill_validator = None

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

    _validate_baseline(value, source, errors)

    constraints = value.get("constraints") or {}
    if not isinstance(constraints, dict):
        errors.append(f"{source}: constraints must be an object")
        constraints = {}
    for key, expected in EXPECTED_CONSTRAINTS.items():
        if constraints.get(key) is not expected:
            errors.append(f"{source}: constraints.{key} must be {expected!r}")

    source_grill = value.get("source_grill") or {}
    if not isinstance(source_grill, dict):
        errors.append(f"{source}: source_grill must be an object")
        source_grill = {}
    grill_path = repo_relative_path(source_grill.get("path"))
    grill_value: dict[str, Any] = {}
    if grill_path is None:
        errors.append(f"{source}: source_grill.path must be a repo-relative path")
    elif not grill_path.exists():
        errors.append(f"{source}: source_grill.path does not exist: {display_path(grill_path)}")
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
                f"{source}: source_grill.sha256 mismatch for {display_path(grill_path)}: "
                f"expected {expected_sha!r}, actual {actual_sha!r}"
            )
        if grill_validator is not None and grill_value:
            grill_errors = grill_validator.validate_grill_envelope(
                grill_value,
                source=display_path(grill_path),
                state_machine=state_machine,
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
    if "scripts/orchestration/validate_accepted_event.py" not in validated_by:
        errors.append(f"{source}: evidence.validated_by must include scripts/orchestration/validate_accepted_event.py")
    if evidence.get("validation_status") != "read_only_fixture_validated":
        errors.append(f"{source}: evidence.validation_status must be read_only_fixture_validated")
    notes = evidence.get("validation_notes") or []
    if not isinstance(notes, list) or not notes:
        errors.append(f"{source}: evidence.validation_notes must be a non-empty list")

    return errors


def example_paths() -> list[Path]:
    return sorted((ORCH / "examples" / "accepted_events").glob("*.example.json"))


def validate_paths(paths: list[Path]) -> list[str]:
    errors: list[str] = []
    try:
        state_machine = load_state_machine()
    except Exception as exc:  # noqa: BLE001 - collect deterministic setup error.
        return [f"failed to load state machine: {exc}"]
    try:
        grill_validator = load_grill_validator()
    except Exception as exc:  # noqa: BLE001 - collect deterministic setup error.
        return [f"failed to load grill validator: {exc}"]

    for path in paths:
        try:
            value = read_json(path)
        except Exception as exc:  # noqa: BLE001 - validator should report file errors.
            errors.append(f"{display_path(path)}: failed to read JSON: {exc}")
            continue
        errors.extend(
            validate_accepted_event(
                value,
                source=display_path(path),
                state_machine=state_machine,
                grill_validator=grill_validator,
            )
        )
    return errors


def validate_paths_payload(paths: list[Path]) -> dict[str, Any]:
    resolved_paths = list(paths)
    if not resolved_paths:
        return {
            "ok": False,
            "action": "orchestration_validate_accepted_event",
            "status": "accepted_event_invalid",
            "schema": ACCEPTED_EVENT_SCHEMA_ID,
            "schema_version": ACCEPTED_EVENT_SCHEMA_VERSION,
            "validated_count": 0,
            "validated_paths": [],
            "errors": ["no accepted-event examples were found; pass explicit paths or restore committed examples"],
            "fixture_only": True,
            "accepted_state_written": False,
            "runtime_state_mutation_allowed": False,
            "source_mutation_allowed": False,
            "artifact_adoption_allowed": False,
            "deployment_allowed": False,
            "model_may_execute": False,
            "operator_action": "restore_accepted_event_examples_or_pass_explicit_paths",
        }
    errors = validate_paths(resolved_paths)
    validated = [] if errors else [display_path(path) for path in resolved_paths]
    return {
        "ok": not errors,
        "action": "orchestration_validate_accepted_event",
        "status": "accepted_event_examples_valid" if not errors else "accepted_event_invalid",
        "schema": ACCEPTED_EVENT_SCHEMA_ID,
        "schema_version": ACCEPTED_EVENT_SCHEMA_VERSION,
        "validated_count": len(validated),
        "validated_paths": validated,
        "errors": errors,
        "state_machine": display_path(STATE_MACHINE_PATH),
        "fixture_only": True,
        "accepted_state_written": False,
        "runtime_state_mutation_allowed": False,
        "source_mutation_allowed": False,
        "artifact_adoption_allowed": False,
        "deployment_allowed": False,
        "model_may_execute": False,
        "operator_action": "accepted_event_may_be_reviewed; no state was mutated" if not errors else "fix_accepted_event_json_and_rerun_validator",
    }


def render_text(payload: dict[str, Any]) -> str:
    if payload.get("ok"):
        return (
            f"{payload['status']}: validated_count={payload['validated_count']} "
            "fixture_only=true accepted_state_written=false"
        )
    lines = [f"{payload['status']}: {len(payload.get('errors') or [])} error(s)"]
    lines.extend(f"- {error}" for error in payload.get("errors") or [])
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate read-only orchestration accepted-event fixtures.")
    parser.add_argument("paths", nargs="*", help="Optional accepted-event JSON files. Defaults to committed examples.")
    parser.add_argument("--json", action="store_true", help="Emit structured validation result as JSON.")
    args = parser.parse_args(argv)

    paths = [Path(p) for p in args.paths] if args.paths else example_paths()
    payload = validate_paths_payload(paths)
    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print(render_text(payload))
    return 0 if payload.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
