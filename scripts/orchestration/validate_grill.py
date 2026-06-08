#!/usr/bin/env python3
"""Read-only validator for Promptbranch orchestration grill envelopes.

The grill surface is proposal data only. This validator intentionally performs
local deterministic checks and does not call ChatGPT, Ollama, browser sessions,
Kubernetes, source-sync, or artifact-adoption paths.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
ORCH = ROOT / "docs" / "design" / "orchestration"
GRILL_SCHEMA_ID = "promptbranch.orchestration.grill"
STATE_MACHINE_PATH = ORCH / "state_machines" / "k8s_game_mvp.state_machine.json"
ALLOWED_STAGES = {
    "G0_intent",
    "G1_mvp",
    "G2_architecture",
    "G3_slice",
    "G4_implementation",
    "G5_release_deployment",
    "G6_maintenance",
}
STAGE_TRANSITION_RECOMMENDATIONS = {
    "G0_intent": ("draft", "intake_accepted"),
    "G1_mvp": ("intake_accepted", "grill_me_accepted"),
    "G2_architecture": ("grill_me_accepted", "architecture_accepted"),
    "G3_slice": ("architecture_accepted", "slice_plan_accepted"),
    "G4_implementation": ("slice_plan_accepted", "implementation_candidate"),
    "G5_release_deployment": ("implementation_candidate", "artifact_verified"),
    "G6_maintenance": ("deployment_smoke_passed", "maintenance_ready"),
}
ALLOWED_PROVIDERS = {"chatgpt", "manual_fixture"}
REJECTED_PROVIDERS = {"ollama", "local_llm", "unknown"}


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        value = json.load(fh)
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def load_state_machine(path: Path = STATE_MACHINE_PATH) -> dict[str, Any]:
    value = read_json(path)
    transitions = value.get("transitions")
    if not isinstance(transitions, list):
        raise ValueError(f"{path} must contain a transitions list")
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
) -> list[str]:
    errors: list[str] = []
    if state_machine is None:
        try:
            state_machine = load_state_machine()
        except Exception as exc:  # noqa: BLE001 - validator should report deterministic setup errors.
            errors.append(f"{source}: failed to load state machine: {exc}")
            state_machine = {}
    transition_pairs = state_machine_transition_pairs(state_machine)

    if value.get("schema") != GRILL_SCHEMA_ID:
        errors.append(f"{source}: schema must be {GRILL_SCHEMA_ID}")
    if value.get("schema_version") != "1.0":
        errors.append(f"{source}: schema_version must be 1.0")

    stage = value.get("stage")
    if stage not in ALLOWED_STAGES:
        errors.append(f"{source}: stage must be one of {sorted(ALLOWED_STAGES)}")

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
    if provider_kind in REJECTED_PROVIDERS or provider_kind not in ALLOWED_PROVIDERS:
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
        expected_transition = STAGE_TRANSITION_RECOMMENDATIONS.get(str(stage))
        if expected_transition and (from_state, to_state) != expected_transition:
            errors.append(
                f"{source}: stage {stage} must recommend transition "
                f"{expected_transition[0]!r}->{expected_transition[1]!r}, got {from_state!r}->{to_state!r}"
            )

    return errors


def example_paths() -> list[Path]:
    return sorted((ORCH / "examples" / "grills").glob("*.example.json"))


def validate_paths(paths: list[Path]) -> list[str]:
    errors: list[str] = []
    try:
        state_machine = load_state_machine()
    except Exception as exc:  # noqa: BLE001 - CLI validator should report deterministic setup errors.
        return [f"{STATE_MACHINE_PATH.relative_to(ROOT)}: failed to read state machine: {exc}"]
    for path in paths:
        try:
            value = read_json(path)
        except Exception as exc:  # noqa: BLE001 - CLI validator should report all readable errors.
            errors.append(f"{path}: failed to read JSON: {exc}")
            continue
        errors.extend(validate_grill_envelope(value, source=str(path.relative_to(ROOT)), state_machine=state_machine))
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate read-only orchestration grill envelopes.")
    parser.add_argument("paths", nargs="*", help="Optional grill JSON files. Defaults to committed examples.")
    args = parser.parse_args(argv)

    paths = [Path(p) for p in args.paths] if args.paths else example_paths()
    errors = validate_paths(paths)
    if errors:
        print(json.dumps({"ok": False, "status": "grill_invalid", "errors": errors}, indent=2))
        return 1
    print(
        json.dumps(
            {
                "ok": True,
                "status": "grill_examples_valid",
                "validated_count": len(paths),
                "state_machine": str(STATE_MACHINE_PATH.relative_to(ROOT)),
                "transition_policy": STAGE_TRANSITION_RECOMMENDATIONS,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
