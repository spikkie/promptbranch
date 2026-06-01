#!/usr/bin/env python3
"""Read-only fixture validator for JSON Orchestration State MVP examples.

This is intentionally not a full orchestration engine. It validates the first
v0.1.0 data surfaces remain internally consistent and safe-by-default.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ORCH = ROOT / "orchestration"

EXPECTED_SCHEMAS = {
    "context": "promptbranch.orchestration.context",
    "decision": "promptbranch.orchestration.decision",
    "evidence": "promptbranch.orchestration.evidence",
}


def read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as fh:
        value = json.load(fh)
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def validate() -> list[str]:
    errors: list[str] = []

    context = read_json(ORCH / "examples" / "k8s_game_context.example.json")
    decision = read_json(ORCH / "examples" / "k8s_game_decision.example.json")
    evidence = read_json(ORCH / "examples" / "k8s_game_evidence.example.json")
    machine = read_json(ORCH / "state_machines" / "k8s_game_mvp.state_machine.json")

    if context.get("schema") != EXPECTED_SCHEMAS["context"]:
        errors.append("context example has unexpected schema")
    if decision.get("schema") != EXPECTED_SCHEMAS["decision"]:
        errors.append("decision example has unexpected schema")
    if evidence.get("schema") != EXPECTED_SCHEMAS["evidence"]:
        errors.append("evidence example has unexpected schema")

    constraints = context.get("constraints") or {}
    if constraints.get("model_may_execute") is not False:
        errors.append("context must declare model_may_execute=false")
    if constraints.get("promptbranch_validates") is not True:
        errors.append("context must declare promptbranch_validates=true")

    authority = decision.get("execution_authority") or {}
    if authority.get("model_may_execute") is not False:
        errors.append("decision must declare model_may_execute=false")
    if authority.get("promptbranch_must_validate") is not True:
        errors.append("decision must declare promptbranch_must_validate=true")

    checks = evidence.get("checks") or []
    if not checks:
        errors.append("evidence must include at least one check")

    states = machine.get("states") or []
    if len(states) != len(set(states)):
        errors.append("state machine contains duplicate states")
    if machine.get("initial_state") not in states:
        errors.append("state machine initial_state must be in states")

    for transition in machine.get("transitions") or []:
        if transition.get("from") not in states:
            errors.append(f"transition has unknown from-state: {transition.get('from')}")
        if transition.get("to") not in states:
            errors.append(f"transition has unknown to-state: {transition.get('to')}")

    forbidden = set(machine.get("forbidden_capabilities") or [])
    required_forbidden = {
        "model_executes_tools",
        "model_adopts_artifacts",
        "model_deploys",
        "model_mutates_source",
    }
    missing = sorted(required_forbidden - forbidden)
    if missing:
        errors.append(f"state machine missing forbidden capabilities: {missing}")

    return errors


def main() -> int:
    errors = validate()
    if errors:
        print(json.dumps({"ok": False, "errors": errors}, indent=2))
        return 1
    print(json.dumps({"ok": True, "status": "orchestration_examples_valid"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
