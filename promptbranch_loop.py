from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

LOOP_TARGET_SCHEMA = "promptbranch.loop.target"
LOOP_TARGET_SCHEMA_VERSION = "1.0"
LOOP_PLANNER_SCHEMA = "promptbranch.loop.plan"
LOOP_PLANNER_SCHEMA_VERSION = "1.0"

TERMINAL_STATES = {"SOLVED", "BLOCKED", "HUMAN_REQUIRED", "OUT_OF_SCOPE", "REQUIREMENTS_MISSING"}
CORE_STATES = [
    "INTAKE",
    "REQUIREMENTS_CHECK",
    "PLAN",
    "ACT_STUB",
    "TEST_STUB",
    "VERIFY_STUB",
    "DIAGNOSE_STUB",
    "CORRECT_STUB",
    "DEPLOY_GATE_STUB",
]
DEPLOY_STATES = ["DEPLOY_STUB", "POST_DEPLOY_VERIFY_STUB"]

FORBIDDEN_ACTION_DEFAULTS = [
    "project_delete",
    "project_source_mutation",
    "artifact_adoption",
    "kubernetes_apply",
    "docker_push",
    "helm_release",
    "destructive_filesystem_change",
]

@dataclass(frozen=True)
class LoopTarget:
    target_id: str
    goal: str
    allowed_paths: tuple[str, ...]
    forbidden_actions: tuple[str, ...]
    validation_commands: tuple[str, ...]
    human_required_when: tuple[str, ...]
    deployment_allowed: bool
    deployment_requested: bool
    max_iterations: int
    raw: dict[str, Any]


class LoopTargetError(ValueError):
    pass


def _as_non_empty_string(value: Any, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise LoopTargetError(f"{field} must be a non-empty string")
    return value.strip()


def _as_string_list(value: Any, *, field: str, default: list[str] | None = None) -> tuple[str, ...]:
    if value is None:
        value = [] if default is None else default
    if not isinstance(value, list):
        raise LoopTargetError(f"{field} must be a list of strings")
    result: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            raise LoopTargetError(f"{field}[{index}] must be a non-empty string")
        result.append(item.strip())
    return tuple(result)


def _validation_commands(raw: dict[str, Any]) -> tuple[str, ...]:
    validation = raw.get("validation")
    if validation is None:
        return tuple()
    if isinstance(validation, list):
        return _as_string_list(validation, field="validation")
    if not isinstance(validation, dict):
        raise LoopTargetError("validation must be an object or list of strings")
    return _as_string_list(validation.get("commands"), field="validation.commands")


def _deployment_flags(raw: dict[str, Any]) -> tuple[bool, bool]:
    deployment = raw.get("deployment") or {}
    if not isinstance(deployment, dict):
        raise LoopTargetError("deployment must be an object")
    allowed = bool(deployment.get("allowed", False))
    requested = bool(deployment.get("requested", False))
    return allowed, requested


def parse_loop_target(payload: dict[str, Any]) -> LoopTarget:
    if not isinstance(payload, dict):
        raise LoopTargetError("target payload must be a JSON object")
    schema = payload.get("schema", LOOP_TARGET_SCHEMA)
    if schema != LOOP_TARGET_SCHEMA:
        raise LoopTargetError(f"schema must be {LOOP_TARGET_SCHEMA}")
    schema_version = payload.get("schema_version", LOOP_TARGET_SCHEMA_VERSION)
    if str(schema_version) != LOOP_TARGET_SCHEMA_VERSION:
        raise LoopTargetError(f"schema_version must be {LOOP_TARGET_SCHEMA_VERSION}")
    max_iterations = payload.get("max_iterations", 1)
    if not isinstance(max_iterations, int) or isinstance(max_iterations, bool) or max_iterations < 1:
        raise LoopTargetError("max_iterations must be an integer >= 1")
    deployment_allowed, deployment_requested = _deployment_flags(payload)
    forbidden = list(_as_string_list(payload.get("forbidden_actions"), field="forbidden_actions", default=FORBIDDEN_ACTION_DEFAULTS))
    for item in FORBIDDEN_ACTION_DEFAULTS:
        if item not in forbidden:
            forbidden.append(item)
    return LoopTarget(
        target_id=_as_non_empty_string(payload.get("target_id"), field="target_id"),
        goal=_as_non_empty_string(payload.get("goal"), field="goal"),
        allowed_paths=_as_string_list(payload.get("allowed_paths"), field="allowed_paths"),
        forbidden_actions=tuple(forbidden),
        validation_commands=_validation_commands(payload),
        human_required_when=_as_string_list(payload.get("human_required_when"), field="human_required_when"),
        deployment_allowed=deployment_allowed,
        deployment_requested=deployment_requested,
        max_iterations=max_iterations,
        raw=dict(payload),
    )


def load_loop_target(path: str | Path) -> tuple[LoopTarget | None, dict[str, Any] | None, str | None]:
    target_path = Path(path).expanduser().resolve()
    try:
        payload = json.loads(target_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return None, None, f"target_load_failed: {exc}"
    try:
        target = parse_loop_target(payload)
    except LoopTargetError as exc:
        return None, payload if isinstance(payload, dict) else None, str(exc)
    return target, payload, None


def validate_loop_target_file(path: str | Path) -> dict[str, Any]:
    target_path = Path(path).expanduser().resolve()
    target, payload, error = load_loop_target(target_path)
    if error or target is None:
        return {
            "ok": False,
            "action": "loop_validate",
            "status": "invalid_target",
            "target_path": str(target_path),
            "error": error,
            "side_effects_performed": False,
            "mutation_allowed": False,
            "deployment_allowed": False,
            "artifact_adoption_allowed": False,
            "project_source_mutation_allowed": False,
        }
    return {
        "ok": True,
        "action": "loop_validate",
        "status": "target_valid",
        "target_path": str(target_path),
        "schema": LOOP_TARGET_SCHEMA,
        "schema_version": LOOP_TARGET_SCHEMA_VERSION,
        "target_id": target.target_id,
        "goal": target.goal,
        "allowed_paths": list(target.allowed_paths),
        "forbidden_actions": list(target.forbidden_actions),
        "validation_commands": list(target.validation_commands),
        "human_required_when": list(target.human_required_when),
        "max_iterations": target.max_iterations,
        "deployment": {
            "allowed": target.deployment_allowed,
            "requested": target.deployment_requested,
        },
        "side_effects_performed": False,
        "mutation_allowed": False,
        "deployment_allowed": False,
        "artifact_adoption_allowed": False,
        "project_source_mutation_allowed": False,
    }


def _event(loop_id: str, target: LoopTarget, index: int, state: str, *, decision: str, next_state: str | None, status: str = "planned") -> dict[str, Any]:
    return {
        "loop_id": loop_id,
        "target_id": target.target_id,
        "event_index": index,
        "iteration": 1,
        "state": state,
        "status": status,
        "decision": decision,
        "next_state": next_state,
        "side_effects_performed": False,
        "mutation_allowed": False,
        "deployment_allowed": False,
        "artifact_adoption_allowed": False,
        "project_source_mutation_allowed": False,
    }


def build_loop_plan(target: LoopTarget, *, execute_stubbed: bool = False) -> dict[str, Any]:
    loop_id = f"loop-{target.target_id}"
    events: list[dict[str, Any]] = []
    index = 0
    transitions: list[tuple[str, str, str | None, str]] = [
        ("INTAKE", "target_loaded", "REQUIREMENTS_CHECK", "planned"),
    ]
    if not target.allowed_paths:
        transitions.append(("REQUIREMENTS_CHECK", "allowed_paths_missing", "REQUIREMENTS_MISSING", "blocked"))
        transitions.append(("REQUIREMENTS_MISSING", "ask_human_for_allowed_paths", None, "terminal"))
        final_state = "REQUIREMENTS_MISSING"
    elif not target.validation_commands:
        transitions.append(("REQUIREMENTS_CHECK", "validation_commands_missing", "REQUIREMENTS_MISSING", "blocked"))
        transitions.append(("REQUIREMENTS_MISSING", "ask_human_for_validation_commands", None, "terminal"))
        final_state = "REQUIREMENTS_MISSING"
    else:
        transitions.extend([
            ("REQUIREMENTS_CHECK", "requirements_complete", "PLAN", "planned"),
            ("PLAN", "dry_run_plan_created", "ACT_STUB", "planned"),
            ("ACT_STUB", "no_action_performed", "TEST_STUB", "stubbed"),
            ("TEST_STUB", "validation_commands_listed_not_executed", "VERIFY_STUB", "stubbed"),
            ("VERIFY_STUB", "verification_stub_passed", "DIAGNOSE_STUB", "stubbed"),
            ("DIAGNOSE_STUB", "no_issue_detected_by_stub", "CORRECT_STUB", "stubbed"),
            ("CORRECT_STUB", "no_correction_performed", "DEPLOY_GATE_STUB", "stubbed"),
        ])
        if target.deployment_requested and target.deployment_allowed:
            transitions.extend([
                ("DEPLOY_GATE_STUB", "deployment_allowed_but_not_executed_in_dry_run", "DEPLOY_STUB", "stubbed"),
                ("DEPLOY_STUB", "no_deployment_performed", "POST_DEPLOY_VERIFY_STUB", "stubbed"),
                ("POST_DEPLOY_VERIFY_STUB", "post_deploy_verification_not_executed", "SOLVED", "stubbed"),
                ("SOLVED", "stop", None, "terminal"),
            ])
        else:
            reason = "deployment_blocked_by_default" if target.deployment_requested else "deployment_not_requested"
            transitions.extend([
                ("DEPLOY_GATE_STUB", reason, "SOLVED", "stubbed"),
                ("SOLVED", "stop", None, "terminal"),
            ])
        final_state = "SOLVED"
    for state, decision, next_state, status in transitions:
        events.append(_event(loop_id, target, index, state, decision=decision, next_state=next_state, status=status))
        index += 1
    return {
        "ok": final_state == "SOLVED",
        "schema": LOOP_PLANNER_SCHEMA,
        "schema_version": LOOP_PLANNER_SCHEMA_VERSION,
        "action": "loop_run" if execute_stubbed else "loop_plan",
        "status": "planned" if final_state == "SOLVED" else "requirements_missing",
        "mode": "stubbed_control_flow_only",
        "target_id": target.target_id,
        "loop_id": loop_id,
        "goal": target.goal,
        "final_state": final_state,
        "max_iterations": target.max_iterations,
        "event_count": len(events),
        "planned_states": [event["state"] for event in events],
        "events": events,
        "allowed_paths": list(target.allowed_paths),
        "forbidden_actions": list(target.forbidden_actions),
        "validation_commands": list(target.validation_commands),
        "deployment": {
            "requested": target.deployment_requested,
            "allowed_by_target": target.deployment_allowed,
            "executed": False,
        },
        "safety": {
            "side_effects_performed": False,
            "mutation_allowed": False,
            "commands_executed": False,
            "deployment_performed": False,
            "kubernetes_mutation_performed": False,
            "project_source_mutation_performed": False,
            "artifact_adoption_performed": False,
            "chatgpt_project_deletion_performed": False,
        },
        "side_effects_performed": False,
        "operator_instruction": "This is a dry-run planner/stubbed loop. It does not execute actions, tests, corrections, deployment, Project Source mutation, or artifact adoption.",
    }


def plan_loop_target_file(path: str | Path, *, execute_stubbed: bool = False) -> dict[str, Any]:
    target_path = Path(path).expanduser().resolve()
    target, payload, error = load_loop_target(target_path)
    if error or target is None:
        return {
            "ok": False,
            "schema": LOOP_PLANNER_SCHEMA,
            "schema_version": LOOP_PLANNER_SCHEMA_VERSION,
            "action": "loop_run" if execute_stubbed else "loop_plan",
            "status": "invalid_target",
            "target_path": str(target_path),
            "error": error,
            "final_state": "BLOCKED",
            "side_effects_performed": False,
            "safety": {
                "side_effects_performed": False,
                "commands_executed": False,
                "deployment_performed": False,
                "kubernetes_mutation_performed": False,
                "project_source_mutation_performed": False,
                "artifact_adoption_performed": False,
                "chatgpt_project_deletion_performed": False,
            },
        }
    plan = build_loop_plan(target, execute_stubbed=execute_stubbed)
    plan["target_path"] = str(target_path)
    return plan


def build_loop_state_only_payload(plan: dict[str, Any]) -> dict[str, Any]:
    states = [event.get("state") for event in plan.get("events") or [] if event.get("state")]
    return {
        "ok": bool(plan.get("ok")),
        "schema": LOOP_PLANNER_SCHEMA,
        "schema_version": LOOP_PLANNER_SCHEMA_VERSION,
        "action": "loop_run",
        "status": plan.get("status"),
        "mode": "state_only",
        "target_id": plan.get("target_id"),
        "target_path": plan.get("target_path"),
        "loop_id": plan.get("loop_id"),
        "final_state": plan.get("final_state"),
        "state_count": len(states),
        "states": states,
        "dry_run": True,
        "side_effects_performed": False,
        "safety": {
            "side_effects_performed": False,
            "mutation_allowed": False,
            "commands_executed": False,
            "deployment_performed": False,
            "kubernetes_mutation_performed": False,
            "project_source_mutation_performed": False,
            "artifact_adoption_performed": False,
            "chatgpt_project_deletion_performed": False,
        },
        "operator_instruction": "State-only dry-run walkthrough. It prints planned loop states only and performs no actions, tests, corrections, deployment, Project Source mutation, or artifact adoption.",
    }


def render_loop_state_only_text(payload: dict[str, Any]) -> str:
    states = payload.get("states") or []
    if states:
        return "\n".join(str(state) for state in states) + "\n"
    if payload.get("error"):
        return f"ERROR\n"
    return ""


def render_loop_plan_text(plan: dict[str, Any]) -> str:
    lines = [
        f"status={plan.get('status')}",
        f"action={plan.get('action')}",
        f"target_id={plan.get('target_id') or 'none'}",
        f"loop_id={plan.get('loop_id') or 'none'}",
        f"mode={plan.get('mode') or 'none'}",
    ]
    if plan.get("error"):
        lines.append(f"error={plan.get('error')}")
    for event in plan.get("events") or []:
        lines.append(
            "state={state} status={status} decision={decision} next_state={next_state} side_effects_performed={side_effects}".format(
                state=event.get("state"),
                status=event.get("status"),
                decision=event.get("decision"),
                next_state=event.get("next_state") or "none",
                side_effects=str(bool(event.get("side_effects_performed"))).lower(),
            )
        )
    lines.append(f"final_state={plan.get('final_state') or 'none'}")
    lines.append(f"side_effects_performed={str(bool(plan.get('side_effects_performed'))).lower()}")
    return "\n".join(lines) + "\n"


def render_loop_validation_text(payload: dict[str, Any]) -> str:
    lines = [
        f"status={payload.get('status')}",
        f"target_id={payload.get('target_id') or 'none'}",
        f"schema={payload.get('schema') or LOOP_TARGET_SCHEMA}",
        f"schema_version={payload.get('schema_version') or LOOP_TARGET_SCHEMA_VERSION}",
    ]
    if payload.get("error"):
        lines.append(f"error={payload.get('error')}")
    lines.append(f"side_effects_performed={str(bool(payload.get('side_effects_performed'))).lower()}")
    return "\n".join(lines) + "\n"
