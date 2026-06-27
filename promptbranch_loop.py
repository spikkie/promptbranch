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

LOOP_ACTION_WALKTHROUGH_SCHEMA = "promptbranch.loop.action_walkthrough"
LOOP_ACTION_WALKTHROUGH_SCHEMA_VERSION = "1.0"
LOOP_READ_ONLY_EXECUTION_SCHEMA = "promptbranch.loop.read_only_execution"
LOOP_READ_ONLY_EXECUTION_SCHEMA_VERSION = "1.0"
LOOP_READ_ONLY_EVIDENCE_REPORT_SCHEMA = "promptbranch.loop.read_only_evidence_report"
LOOP_READ_ONLY_EVIDENCE_REPORT_SCHEMA_VERSION = "1.0"

STATE_ACTION_BLUEPRINTS: dict[str, tuple[str, str]] = {
    "INTAKE": (
        "load target definition and create loop context",
        "target JSON parsed and target_id/goal are available",
    ),
    "REQUIREMENTS_CHECK": (
        "verify bounded requirements before any action is considered",
        "allowed_paths and validation_commands are present or human input is required",
    ),
    "PLAN": (
        "derive the bounded step plan from the validated target",
        "plan is explicit, ordered, and still side-effect free",
    ),
    "ACT_STUB": (
        "describe the action that would be taken in a future execution slice",
        "no command, file mutation, Project Source mutation, or deployment is performed",
    ),
    "TEST_STUB": (
        "list validation commands that would be used in a future execution slice",
        "commands are listed but not executed",
    ),
    "VERIFY_STUB": (
        "describe how validation evidence would be checked",
        "verification remains synthetic and side-effect free",
    ),
    "DIAGNOSE_STUB": (
        "describe how a failed validation would be diagnosed",
        "no corrective action is executed automatically",
    ),
    "CORRECT_STUB": (
        "describe the correction phase without mutating files",
        "correction remains proposal-only",
    ),
    "DEPLOY_GATE_STUB": (
        "evaluate whether deployment is allowed for this target",
        "deployment is not performed in MVP-1 dry-run walkthroughs",
    ),
    "DEPLOY_STUB": (
        "describe deployment that would happen only after an explicit future gate",
        "no Kubernetes, Docker, or Helm mutation is performed",
    ),
    "POST_DEPLOY_VERIFY_STUB": (
        "describe post-deployment verification for a future execution slice",
        "no cluster or external system is inspected or mutated",
    ),
    "SOLVED": (
        "stop the loop because the dry-run plan reaches its terminal success state",
        "final state is recorded without artifact adoption",
    ),
    "REQUIREMENTS_MISSING": (
        "stop and ask the operator for missing requirements",
        "missing requirement is explicit and no action is performed",
    ),
    "BLOCKED": (
        "stop because target parsing or validation blocked planning",
        "error is reported without side effects",
    ),
}

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



def _state_action_blueprint(state: str) -> tuple[str, str]:
    return STATE_ACTION_BLUEPRINTS.get(
        state,
        (
            "describe planned state transition without executing it",
            "state transition remains side-effect free",
        ),
    )

def _event(loop_id: str, target: LoopTarget, index: int, state: str, *, decision: str, next_state: str | None, status: str = "planned") -> dict[str, Any]:
    planned_action, validation_gate = _state_action_blueprint(state)
    return {
        "loop_id": loop_id,
        "target_id": target.target_id,
        "event_index": index,
        "iteration": 1,
        "state": state,
        "status": status,
        "decision": decision,
        "planned_action": planned_action,
        "validation_gate": validation_gate,
        "execution_status": "not_executed_dry_run",
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



def build_loop_action_walkthrough_payload(plan: dict[str, Any]) -> dict[str, Any]:
    actions: list[dict[str, Any]] = []
    for event in plan.get("events") or []:
        state = event.get("state")
        if not state:
            continue
        planned_action = event.get("planned_action")
        validation_gate = event.get("validation_gate")
        if not planned_action or not validation_gate:
            planned_action, validation_gate = _state_action_blueprint(str(state))
        actions.append({
            "index": event.get("event_index"),
            "state": state,
            "status": event.get("status"),
            "decision": event.get("decision"),
            "planned_action": planned_action,
            "validation_gate": validation_gate,
            "execution_status": "not_executed_dry_run",
            "next_state": event.get("next_state"),
            "side_effects_performed": False,
            "mutation_allowed": False,
            "deployment_allowed": False,
            "artifact_adoption_allowed": False,
            "project_source_mutation_allowed": False,
        })
    return {
        "ok": bool(plan.get("ok")),
        "schema": LOOP_ACTION_WALKTHROUGH_SCHEMA,
        "schema_version": LOOP_ACTION_WALKTHROUGH_SCHEMA_VERSION,
        "action": "loop_run",
        "status": plan.get("status"),
        "mode": "planned_actions",
        "target_id": plan.get("target_id"),
        "target_path": plan.get("target_path"),
        "loop_id": plan.get("loop_id"),
        "final_state": plan.get("final_state"),
        "action_count": len(actions),
        "states": [item["state"] for item in actions],
        "actions": actions,
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
        "operator_instruction": "Planned-action dry-run walkthrough. It explains what each state would do next, but performs no commands, tests, corrections, deployment, Project Source mutation, or artifact adoption.",
    }


def _path_has_glob(pattern: str) -> bool:
    return any(token in pattern for token in ("*", "?", "["))


def _classify_allowed_path(pattern: str, *, repo_root: Path) -> dict[str, Any]:
    path = Path(pattern)
    parts = path.parts
    is_absolute = path.is_absolute()
    has_parent_traversal = ".." in parts
    has_home_prefix = pattern.startswith("~")
    safe = not is_absolute and not has_parent_traversal and not has_home_prefix
    matches: list[str] = []
    match_error: str | None = None
    if safe:
        try:
            if _path_has_glob(pattern):
                matches = [str(item.relative_to(repo_root)) for item in repo_root.glob(pattern)][:20]
            else:
                candidate = repo_root / pattern
                if candidate.exists():
                    matches = [str(candidate.relative_to(repo_root))]
        except Exception as exc:  # pragma: no cover - defensive for invalid glob patterns
            match_error = str(exc)
            safe = False
    return {
        "path": pattern,
        "safe": safe,
        "repo_relative": safe,
        "absolute": is_absolute,
        "parent_traversal": has_parent_traversal,
        "home_prefix": has_home_prefix,
        "glob": _path_has_glob(pattern),
        "match_count": len(matches),
        "matches_sample": matches,
        "match_error": match_error,
        "status": "safe" if safe else "unsafe_path_scope",
        "read_only": True,
        "mutation_performed": False,
    }


def build_loop_read_only_execution_payload(
    plan: dict[str, Any],
    *,
    repo_root: str | Path | None = None,
) -> dict[str, Any]:
    root = Path.cwd().resolve() if repo_root is None else Path(repo_root).expanduser().resolve()
    allowed_paths = [str(item) for item in plan.get("allowed_paths") or []]
    validation_commands = [str(item) for item in plan.get("validation_commands") or []]
    path_checks = [_classify_allowed_path(pattern, repo_root=root) for pattern in allowed_paths]
    unsafe_paths = [item for item in path_checks if not item.get("safe")]
    command_checks = [
        {
            "command": command,
            "declared": True,
            "read_only_inspection_performed": True,
            "execution_status": "not_executed_read_only",
            "side_effects_performed": False,
        }
        for command in validation_commands
    ]
    executed_state = "REQUIREMENTS_CHECK"
    payload = {
        "ok": bool(plan.get("ok")) and not unsafe_paths,
        "schema": LOOP_READ_ONLY_EXECUTION_SCHEMA,
        "schema_version": LOOP_READ_ONLY_EXECUTION_SCHEMA_VERSION,
        "action": "loop_run",
        "status": "read_only_checks_passed" if not unsafe_paths else "unsafe_path_scope",
        "mode": "read_only_execution",
        "execution_mode": "local_read_only_preflight",
        "target_id": plan.get("target_id"),
        "target_path": plan.get("target_path"),
        "loop_id": plan.get("loop_id"),
        "final_state": plan.get("final_state"),
        "executed_state": executed_state,
        "states": list(plan.get("planned_states") or []),
        "checks": {
            "allowed_paths": path_checks,
            "validation_commands": command_checks,
            "forbidden_actions": list(plan.get("forbidden_actions") or []),
        },
        "summary": {
            "allowed_path_count": len(path_checks),
            "unsafe_path_count": len(unsafe_paths),
            "validation_command_count": len(command_checks),
            "commands_executed": 0,
            "matched_path_count": sum(int(item.get("match_count") or 0) for item in path_checks),
        },
        "read_operations_performed": True,
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
        "operator_instruction": "Read-only execution preflight. It inspects declared path scopes and validation command declarations but executes no commands, mutates no files, performs no deployment, mutates no Project Sources, and adopts no artifacts.",
    }
    payload["evidence_report"] = build_loop_read_only_evidence_report(payload)
    return payload


def build_loop_read_only_evidence_report(payload: dict[str, Any]) -> dict[str, Any]:
    checks = payload.get("checks") if isinstance(payload.get("checks"), dict) else {}
    allowed_paths = list(checks.get("allowed_paths") or [])
    validation_commands = list(checks.get("validation_commands") or [])
    unsafe_paths = [item for item in allowed_paths if not item.get("safe")]
    safe_paths = [item for item in allowed_paths if item.get("safe")]
    skipped_commands = [item for item in validation_commands if item.get("execution_status") == "not_executed_read_only"]
    safety = payload.get("safety") if isinstance(payload.get("safety"), dict) else {}
    execution_clean = (
        bool(payload.get("ok"))
        and not unsafe_paths
        and int((payload.get("summary") or {}).get("commands_executed") or 0) == 0
        and not bool(payload.get("side_effects_performed"))
        and not bool(safety.get("deployment_performed"))
        and not bool(safety.get("kubernetes_mutation_performed"))
        and not bool(safety.get("project_source_mutation_performed"))
        and not bool(safety.get("artifact_adoption_performed"))
    )
    return {
        "ok": execution_clean,
        "schema": LOOP_READ_ONLY_EVIDENCE_REPORT_SCHEMA,
        "schema_version": LOOP_READ_ONLY_EVIDENCE_REPORT_SCHEMA_VERSION,
        "action": "loop_evidence_report",
        "status": "evidence_clean" if execution_clean else "evidence_blocked",
        "source_schema": payload.get("schema"),
        "source_status": payload.get("status"),
        "target_id": payload.get("target_id"),
        "target_path": payload.get("target_path"),
        "loop_id": payload.get("loop_id"),
        "execution_mode": payload.get("execution_mode"),
        "executed_state": payload.get("executed_state"),
        "final_state": payload.get("final_state"),
        "evidence_summary": {
            "allowed_path_count": len(allowed_paths),
            "safe_path_count": len(safe_paths),
            "unsafe_path_count": len(unsafe_paths),
            "matched_path_count": sum(int(item.get("match_count") or 0) for item in allowed_paths),
            "validation_command_count": len(validation_commands),
            "declared_command_count": len(validation_commands),
            "skipped_command_count": len(skipped_commands),
            "commands_executed": int((payload.get("summary") or {}).get("commands_executed") or 0),
        },
        "path_evidence": [
            {
                "path": item.get("path"),
                "status": item.get("status"),
                "safe": bool(item.get("safe")),
                "repo_relative": bool(item.get("repo_relative")),
                "glob": bool(item.get("glob")),
                "match_count": int(item.get("match_count") or 0),
                "read_only": bool(item.get("read_only")),
                "mutation_performed": bool(item.get("mutation_performed")),
            }
            for item in allowed_paths
        ],
        "command_evidence": [
            {
                "command": item.get("command"),
                "declared": bool(item.get("declared")),
                "execution_status": item.get("execution_status"),
                "executed": False,
                "side_effects_performed": bool(item.get("side_effects_performed")),
            }
            for item in validation_commands
        ],
        "blocked_reasons": ["unsafe_path_scope"] if unsafe_paths else [],
        "safety_assertions": {
            "commands_executed": False,
            "files_mutated": False,
            "deployment_performed": False,
            "kubernetes_mutation_performed": False,
            "project_source_mutation_performed": False,
            "artifact_adoption_performed": False,
            "chatgpt_project_deletion_performed": False,
        },
        "operator_instruction": "Evidence report only. It summarizes read-only preflight evidence and does not execute commands, mutate files, deploy, mutate Project Sources, adopt artifacts, or delete ChatGPT Projects.",
    }


def render_loop_read_only_evidence_report_text(payload: dict[str, Any]) -> str:
    lines = [
        f"status={payload.get('status')}",
        f"schema={payload.get('schema')}",
        f"target_id={payload.get('target_id') or 'none'}",
        f"execution_mode={payload.get('execution_mode') or 'none'}",
        f"executed_state={payload.get('executed_state') or 'none'}",
        f"final_state={payload.get('final_state') or 'none'}",
    ]
    summary = payload.get("evidence_summary") if isinstance(payload.get("evidence_summary"), dict) else {}
    lines.extend([
        f"safe_path_count={summary.get('safe_path_count', 0)}",
        f"unsafe_path_count={summary.get('unsafe_path_count', 0)}",
        f"declared_command_count={summary.get('declared_command_count', 0)}",
        f"skipped_command_count={summary.get('skipped_command_count', 0)}",
        f"commands_executed={summary.get('commands_executed', 0)}",
    ])
    for item in payload.get("path_evidence") or []:
        lines.append(
            "path_evidence={path} status={status} safe={safe} match_count={match_count} mutation_performed=false".format(
                path=item.get("path"),
                status=item.get("status"),
                safe=str(bool(item.get("safe"))).lower(),
                match_count=item.get("match_count", 0),
            )
        )
    for item in payload.get("command_evidence") or []:
        lines.append(
            "command_evidence={command} execution_status={status} executed=false".format(
                command=item.get("command"),
                status=item.get("execution_status"),
            )
        )
    lines.append("side_effects_performed=false")
    return "\n".join(lines) + "\n"


def render_loop_action_walkthrough_text(payload: dict[str, Any]) -> str:
    lines: list[str] = []
    for item in payload.get("actions") or []:
        state = item.get("state") or "UNKNOWN"
        planned_action = item.get("planned_action") or "none"
        validation_gate = item.get("validation_gate") or "none"
        next_state = item.get("next_state") or "none"
        lines.append(f"{state} | action={planned_action} | gate={validation_gate} | next={next_state}")
    if lines:
        return "\n".join(lines) + "\n"
    if payload.get("error"):
        return "ERROR\n"
    return ""


def render_loop_read_only_execution_text(payload: dict[str, Any]) -> str:
    lines = [
        f"status={payload.get('status')}",
        f"mode={payload.get('mode')}",
        f"target_id={payload.get('target_id') or 'none'}",
        f"executed_state={payload.get('executed_state') or 'none'}",
        "execution_mode=local_read_only_preflight",
    ]
    for item in (payload.get("checks") or {}).get("allowed_paths") or []:
        lines.append(
            "allowed_path={path} safe={safe} glob={glob} match_count={match_count} mutation_performed=false".format(
                path=item.get("path"),
                safe=str(bool(item.get("safe"))).lower(),
                glob=str(bool(item.get("glob"))).lower(),
                match_count=item.get("match_count", 0),
            )
        )
    for item in (payload.get("checks") or {}).get("validation_commands") or []:
        lines.append(
            "validation_command={command} execution_status=not_executed_read_only".format(
                command=item.get("command")
            )
        )
    lines.append("commands_executed=0")
    lines.append("side_effects_performed=false")
    return "\n".join(lines) + "\n"

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
