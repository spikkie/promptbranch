from __future__ import annotations

import fnmatch
import hashlib
import json
import shutil
import shlex
import subprocess
import tempfile
import time
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
LOOP_READ_ONLY_EVIDENCE_GATE_SCHEMA = "promptbranch.loop.read_only_evidence_gate"
LOOP_READ_ONLY_EVIDENCE_GATE_SCHEMA_VERSION = "1.0"
LOOP_READ_ONLY_COMMAND_EXECUTION_SCHEMA = "promptbranch.loop.read_only_command_execution"
LOOP_READ_ONLY_COMMAND_EXECUTION_SCHEMA_VERSION = "1.0"
LOOP_READ_ONLY_COMMAND_DIAGNOSIS_SCHEMA = "promptbranch.loop.read_only_command_diagnosis"
LOOP_READ_ONLY_COMMAND_DIAGNOSIS_SCHEMA_VERSION = "1.0"
LOOP_READ_ONLY_CORRECTION_PLAN_SCHEMA = "promptbranch.loop.read_only_correction_plan"
LOOP_READ_ONLY_CORRECTION_PLAN_SCHEMA_VERSION = "1.0"
LOOP_SANDBOX_FILE_MUTATION_SCHEMA = "promptbranch.loop.sandbox_file_mutation"
LOOP_SANDBOX_FILE_MUTATION_SCHEMA_VERSION = "1.0"
LOOP_SANDBOX_MUTATION_VERIFICATION_SCHEMA = "promptbranch.loop.sandbox_mutation_verification"
LOOP_SANDBOX_MUTATION_VERIFICATION_SCHEMA_VERSION = "1.0"

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
        "sandbox_mutation": target.raw.get("sandbox_mutation") if isinstance(target.raw.get("sandbox_mutation"), dict) else None,
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
    checks = plan.get("checks") if isinstance(plan.get("checks"), dict) else {}
    if checks:
        allowed_paths = [str(item.get("path")) for item in checks.get("allowed_paths") or [] if isinstance(item, dict) and item.get("path")]
        validation_commands = [str(item.get("command")) for item in checks.get("validation_commands") or [] if isinstance(item, dict) and item.get("command")]
    else:
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



def _path_matches_allowed_patterns(rel_path: str, patterns: list[str]) -> bool:
    normalized = rel_path.replace("\\", "/").strip("/")
    for pattern in patterns:
        candidate = str(pattern).replace("\\", "/").strip("/")
        if not candidate:
            continue
        if candidate == normalized:
            return True
        if candidate.endswith("/**"):
            prefix = candidate[:-3].rstrip("/")
            if normalized == prefix or normalized.startswith(prefix + "/"):
                return True
        if _path_has_glob(candidate) and fnmatch.fnmatch(normalized, candidate):
            return True
    return False


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _safe_stat_snapshot(path: Path, *, repo_root: Path) -> dict[str, Any]:
    try:
        rel = str(path.resolve().relative_to(repo_root))
        stat = path.stat()
        return {
            "path": rel,
            "exists": True,
            "is_file": path.is_file(),
            "size": stat.st_size,
            "sha256": _sha256_file(path) if path.is_file() else None,
        }
    except Exception as exc:  # pragma: no cover - defensive evidence path
        return {"path": str(path), "exists": False, "error": str(exc)}


def _classify_read_only_validation_command(command: str, *, repo_root: Path, allowed_paths: list[str]) -> dict[str, Any]:
    try:
        argv = shlex.split(command)
    except ValueError as exc:
        return {
            "command": command,
            "allowed": False,
            "status": "blocked_command_parse_error",
            "reason": str(exc),
            "argv": [],
        }
    if len(argv) != 4 or argv[:3] != ["python3", "-m", "json.tool"]:
        return {
            "command": command,
            "allowed": False,
            "status": "blocked_not_allowlisted",
            "reason": "v0.1.100 allows only: python3 -m json.tool <repo-relative-json-file>",
            "argv": argv,
        }
    target_arg = argv[3]
    target_path = Path(target_arg)
    if target_path.is_absolute() or ".." in target_path.parts or target_arg.startswith("~") or _path_has_glob(target_arg):
        return {
            "command": command,
            "allowed": False,
            "status": "blocked_unsafe_path_argument",
            "reason": "command target must be a literal repo-relative path without parent traversal, home prefix, or glob",
            "argv": argv,
            "path_argument": target_arg,
        }
    resolved = (repo_root / target_arg).resolve()
    try:
        rel_path = str(resolved.relative_to(repo_root))
    except ValueError:
        return {
            "command": command,
            "allowed": False,
            "status": "blocked_path_outside_repo",
            "reason": "command target resolved outside repo root",
            "argv": argv,
            "path_argument": target_arg,
        }
    if resolved.suffix.lower() != ".json":
        return {
            "command": command,
            "allowed": False,
            "status": "blocked_non_json_target",
            "reason": "python3 -m json.tool target must be a .json file",
            "argv": argv,
            "path_argument": rel_path,
        }
    if not resolved.is_file():
        return {
            "command": command,
            "allowed": False,
            "status": "blocked_missing_target",
            "reason": "command target file does not exist",
            "argv": argv,
            "path_argument": rel_path,
        }
    if not _path_matches_allowed_patterns(rel_path, allowed_paths):
        return {
            "command": command,
            "allowed": False,
            "status": "blocked_outside_allowed_paths",
            "reason": "command target is not covered by target.allowed_paths",
            "argv": argv,
            "path_argument": rel_path,
        }
    return {
        "command": command,
        "allowed": True,
        "status": "allowlisted_read_only_json_tool",
        "reason": "exact read-only JSON syntax validation command is allowlisted",
        "argv": argv,
        "path_argument": rel_path,
        "target_path": str(resolved),
    }


def build_loop_read_only_command_execution_payload(
    plan: dict[str, Any],
    gate: dict[str, Any],
    *,
    repo_root: str | Path | None = None,
    timeout_seconds: float = 15.0,
) -> dict[str, Any]:
    """Execute the first tightly allowlisted read-only validation command.

    v0.1.100 intentionally supports exactly one low-risk command class:
    ``python3 -m json.tool <repo-relative-json-file>``.  The command is run
    only after the existing read-only evidence gate has passed.  It captures
    command evidence and proves the command input file was not modified.
    """
    root = Path.cwd().resolve() if repo_root is None else Path(repo_root).expanduser().resolve()
    checks = plan.get("checks") if isinstance(plan.get("checks"), dict) else {}
    if checks:
        allowed_paths = [str(item.get("path")) for item in checks.get("allowed_paths") or [] if isinstance(item, dict) and item.get("path")]
        validation_commands = [str(item.get("command")) for item in checks.get("validation_commands") or [] if isinstance(item, dict) and item.get("command")]
    else:
        allowed_paths = [str(item) for item in plan.get("allowed_paths") or []]
        validation_commands = [str(item) for item in plan.get("validation_commands") or []]
    gate_passed = bool(gate.get("ok")) and gate.get("status") == "gate_passed"
    command_evidence: list[dict[str, Any]] = []
    blocked_reasons: list[str] = []
    commands_executed = 0
    mutation_detected = False

    if not gate_passed:
        blocked_reasons.append("evidence_gate_not_passed")
    for command in validation_commands:
        classification = _classify_read_only_validation_command(command, repo_root=root, allowed_paths=allowed_paths)
        evidence: dict[str, Any] = {
            "command": command,
            "declared": True,
            "allowlisted": bool(classification.get("allowed")),
            "classification_status": classification.get("status"),
            "classification_reason": classification.get("reason"),
            "argv": classification.get("argv") or [],
            "execution_status": "blocked_before_execution",
            "executed": False,
            "exit_code": None,
            "duration_seconds": 0.0,
            "stdout": "",
            "stderr": "",
            "side_effects_performed": False,
            "mutation_detected": False,
        }
        if classification.get("path_argument"):
            evidence["path_argument"] = classification.get("path_argument")
        if not gate_passed:
            evidence["blocked_reason"] = "evidence_gate_not_passed"
            command_evidence.append(evidence)
            continue
        if not classification.get("allowed"):
            evidence["blocked_reason"] = classification.get("status")
            blocked_reasons.append(str(classification.get("status") or "blocked_not_allowlisted"))
            command_evidence.append(evidence)
            continue
        target_path = Path(str(classification["target_path"]))
        before = _safe_stat_snapshot(target_path, repo_root=root)
        start = time.monotonic()
        try:
            result = subprocess.run(
                list(classification.get("argv") or []),
                cwd=root,
                text=True,
                capture_output=True,
                timeout=timeout_seconds,
                check=False,
            )
            duration = time.monotonic() - start
            after = _safe_stat_snapshot(target_path, repo_root=root)
            changed = before != after
            mutation_detected = mutation_detected or changed
            commands_executed += 1
            evidence.update({
                "execution_status": "executed_read_only_validation_passed" if result.returncode == 0 and not changed else "executed_read_only_validation_failed",
                "executed": True,
                "exit_code": result.returncode,
                "duration_seconds": round(duration, 6),
                "stdout": result.stdout[:4000],
                "stderr": result.stderr[:4000],
                "before": before,
                "after": after,
                "mutation_detected": changed,
                "side_effects_performed": changed,
            })
            if result.returncode != 0:
                blocked_reasons.append("read_only_validation_command_failed")
            if changed:
                blocked_reasons.append("read_only_validation_mutation_detected")
        except subprocess.TimeoutExpired as exc:
            duration = time.monotonic() - start
            commands_executed += 1
            evidence.update({
                "execution_status": "executed_read_only_validation_timeout",
                "executed": True,
                "exit_code": None,
                "duration_seconds": round(duration, 6),
                "stdout": (exc.stdout or "")[:4000] if isinstance(exc.stdout, str) else "",
                "stderr": (exc.stderr or "")[:4000] if isinstance(exc.stderr, str) else "",
                "before": before,
                "after": _safe_stat_snapshot(target_path, repo_root=root),
            })
            blocked_reasons.append("read_only_validation_timeout")
        command_evidence.append(evidence)

    executed_failures = [item for item in command_evidence if item.get("executed") and item.get("execution_status") != "executed_read_only_validation_passed"]
    blocked_commands = [item for item in command_evidence if not item.get("executed")]
    ok = gate_passed and commands_executed == 1 and not blocked_commands and not executed_failures and not mutation_detected
    return {
        "ok": ok,
        "schema": LOOP_READ_ONLY_COMMAND_EXECUTION_SCHEMA,
        "schema_version": LOOP_READ_ONLY_COMMAND_EXECUTION_SCHEMA_VERSION,
        "action": "loop_read_only_command_execution",
        "status": "read_only_validation_executed" if ok else "read_only_validation_blocked",
        "mode": "read_only_command_execution",
        "execution_mode": "local_allowlisted_read_only_validation",
        "target_id": plan.get("target_id"),
        "target_path": plan.get("target_path"),
        "loop_id": plan.get("loop_id"),
        "executed_state": "TEST_STUB",
        "final_state": plan.get("final_state"),
        "source_gate_status": gate.get("status"),
        "summary": {
            "declared_command_count": len(validation_commands),
            "allowlisted_command_count": sum(1 for item in command_evidence if item.get("allowlisted")),
            "blocked_command_count": len(blocked_commands),
            "commands_executed": commands_executed,
            "passed_command_count": sum(1 for item in command_evidence if item.get("execution_status") == "executed_read_only_validation_passed"),
            "failed_command_count": len(executed_failures),
            "mutation_detected": mutation_detected,
        },
        "command_evidence": command_evidence,
        "blocked_reasons": sorted(set(blocked_reasons)),
        "dry_run": False,
        "side_effects_performed": mutation_detected,
        "safety": {
            "side_effects_performed": mutation_detected,
            "mutation_allowed": False,
            "commands_executed": commands_executed,
            "deployment_performed": False,
            "kubernetes_mutation_performed": False,
            "project_source_mutation_performed": False,
            "artifact_adoption_performed": False,
            "chatgpt_project_deletion_performed": False,
        },
        "operator_instruction": "First controlled read-only validation command execution. Only one exact allowlisted JSON syntax command may run; file mutation, deployment, Kubernetes mutation, Project Source mutation, artifact adoption, and ChatGPT Project deletion remain forbidden.",
    }



def _diagnose_single_read_only_command(evidence: dict[str, Any]) -> dict[str, Any]:
    """Classify one read-only command evidence record without proposing fixes.

    v0.1.101 is diagnostic only.  It turns the v0.1.100 command evidence
    into a stable passed/blocked/failed classification while preserving the
    no-correction/no-mutation boundary.
    """
    command = str(evidence.get("command") or "")
    status = str(evidence.get("execution_status") or "")
    executed = bool(evidence.get("executed"))
    mutation_detected = bool(evidence.get("mutation_detected"))
    exit_code = evidence.get("exit_code")
    if not executed:
        result_classification = "blocked"
        reason = str(evidence.get("blocked_reason") or evidence.get("classification_status") or "blocked_before_execution")
        operator_action = "review_blocked_read_only_command_evidence"
    elif mutation_detected:
        result_classification = "failed"
        reason = "read_only_validation_mutation_detected"
        operator_action = "stop_for_operator_review"
    elif status == "executed_read_only_validation_timeout":
        result_classification = "failed"
        reason = "read_only_validation_timeout"
        operator_action = "stop_for_operator_review"
    elif exit_code not in (0, "0"):
        result_classification = "failed"
        reason = "read_only_validation_command_failed"
        operator_action = "review_command_stdout_stderr"
    elif status == "executed_read_only_validation_passed":
        result_classification = "passed"
        reason = "read_only_validation_passed"
        operator_action = "continue_to_next_planned_slice_after_acceptance"
    else:
        result_classification = "blocked"
        reason = status or "unknown_read_only_result_status"
        operator_action = "review_unclassified_read_only_command_evidence"
    return {
        "command": command,
        "result_classification": result_classification,
        "reason": reason,
        "source_execution_status": status,
        "executed": executed,
        "exit_code": exit_code,
        "mutation_detected": mutation_detected,
        "blocked_reason": evidence.get("blocked_reason"),
        "classification_status": evidence.get("classification_status"),
        "stdout_present": bool(evidence.get("stdout")),
        "stderr_present": bool(evidence.get("stderr")),
        "operator_action": operator_action,
        "correction_plan_generated": False,
        "file_mutation_performed": False,
    }


def build_loop_read_only_command_diagnosis_payload(execution_payload: dict[str, Any]) -> dict[str, Any]:
    """Diagnose read-only command execution evidence without corrections.

    The function is intentionally evidence-only.  It does not execute another
    command, generate a correction plan, write files, mutate Project Sources,
    adopt artifacts, or deploy anything.  Its job is to make blocked vs failed
    outcomes machine-readable for the next release slice.
    """
    evidence_items = [item for item in execution_payload.get("command_evidence") or [] if isinstance(item, dict)]
    diagnoses = [_diagnose_single_read_only_command(item) for item in evidence_items]
    classifications = [item["result_classification"] for item in diagnoses]
    blocked_count = classifications.count("blocked")
    failed_count = classifications.count("failed")
    passed_count = classifications.count("passed")
    if failed_count:
        result_classification = "failed"
        status = "diagnosis_failed_result"
        decision = "stop_for_operator_review"
    elif blocked_count:
        result_classification = "blocked"
        status = "diagnosis_blocked_result"
        decision = "stop_for_operator_review"
    elif passed_count and passed_count == len(diagnoses):
        result_classification = "passed"
        status = "diagnosis_passed_result"
        decision = "continue_to_next_planned_slice_after_acceptance"
    else:
        result_classification = "blocked"
        status = "diagnosis_no_command_evidence"
        decision = "stop_for_operator_review"
    source_schema_ok = execution_payload.get("schema") == LOOP_READ_ONLY_COMMAND_EXECUTION_SCHEMA
    if not source_schema_ok:
        result_classification = "blocked"
        status = "diagnosis_blocked_source_schema"
        decision = "stop_for_operator_review"
    return {
        "ok": True,
        "schema": LOOP_READ_ONLY_COMMAND_DIAGNOSIS_SCHEMA,
        "schema_version": LOOP_READ_ONLY_COMMAND_DIAGNOSIS_SCHEMA_VERSION,
        "action": "loop_read_only_command_diagnosis",
        "status": status,
        "mode": "read_only_command_diagnosis",
        "execution_mode": "local_read_only_result_diagnosis",
        "source_schema": execution_payload.get("schema"),
        "source_status": execution_payload.get("status"),
        "target_id": execution_payload.get("target_id"),
        "target_path": execution_payload.get("target_path"),
        "loop_id": execution_payload.get("loop_id"),
        "executed_state": "DIAGNOSE_STUB",
        "source_executed_state": execution_payload.get("executed_state"),
        "final_state": execution_payload.get("final_state"),
        "result_classification": result_classification,
        "decision": decision,
        "summary": {
            "diagnosed_command_count": len(diagnoses),
            "passed_command_count": passed_count,
            "blocked_command_count": blocked_count,
            "failed_command_count": failed_count,
            "mutation_detected": any(bool(item.get("mutation_detected")) for item in diagnoses),
            "correction_plan_generated": False,
            "files_mutated": False,
        },
        "diagnoses": diagnoses,
        "blocked_reasons": sorted({str(item.get("reason")) for item in diagnoses if item.get("result_classification") == "blocked"}),
        "failed_reasons": sorted({str(item.get("reason")) for item in diagnoses if item.get("result_classification") == "failed"}),
        "correction_plan": None,
        "dry_run": False,
        "side_effects_performed": False,
        "safety": {
            "side_effects_performed": False,
            "mutation_allowed": False,
            "commands_executed": int((execution_payload.get("summary") or {}).get("commands_executed") or 0),
            "deployment_performed": False,
            "kubernetes_mutation_performed": False,
            "project_source_mutation_performed": False,
            "artifact_adoption_performed": False,
            "chatgpt_project_deletion_performed": False,
            "correction_plan_generated": False,
            "files_mutated": False,
        },
        "operator_instruction": "Read-only command result diagnosis only. It classifies existing command evidence as passed, blocked, or failed; it does not generate corrections, mutate files, deploy, mutate Project Sources, adopt artifacts, or delete ChatGPT Projects.",
    }


def _bounded_correction_steps_for_diagnosis(diagnosis: dict[str, Any]) -> list[dict[str, Any]]:
    classification = str(diagnosis.get("result_classification") or "blocked")
    reason = str(diagnosis.get("reason") or "unknown_read_only_result")
    command = str(diagnosis.get("command") or "")
    if classification == "blocked":
        if reason == "blocked_not_allowlisted":
            operator_focus = "replace the validation command with an allowlisted read-only command"
        elif reason in {"blocked_outside_allowed_paths", "blocked_unsafe_path_argument", "blocked_path_outside_repo", "blocked_missing_target", "blocked_non_json_target"}:
            operator_focus = "repair the target path declaration or allowed_paths coverage"
        elif reason == "evidence_gate_not_passed":
            operator_focus = "repair read-only evidence-gate inputs before command execution"
        else:
            operator_focus = "inspect blocked command evidence and tighten target declarations"
        return [
            {
                "step": 1,
                "action": "inspect_blocked_read_only_command_evidence",
                "reason": reason,
                "command": command,
                "mutation_allowed": False,
                "operator_intent": operator_focus,
            },
            {
                "step": 2,
                "action": "prepare_target_declaration_adjustment_for_human_review",
                "reason": reason,
                "mutation_allowed": False,
                "writes_files": False,
                "future_slice_required_for_mutation": True,
            },
            {
                "step": 3,
                "action": "rerun_read_only_evidence_gate_after_operator_approval",
                "mutation_allowed": False,
                "commands_to_run": [
                    "pb loop run --target <target.json> --read-only-execution --evidence-gate --json",
                ],
            },
        ]
    if classification == "failed":
        if reason == "read_only_validation_command_failed":
            operator_focus = "inspect stdout/stderr and identify the validation input defect"
        elif reason == "read_only_validation_timeout":
            operator_focus = "inspect timeout evidence and reduce command scope before retrying"
        elif reason == "read_only_validation_mutation_detected":
            operator_focus = "stop immediately because a read-only command changed file evidence"
        else:
            operator_focus = "inspect failed command evidence before any correction"
        return [
            {
                "step": 1,
                "action": "inspect_failed_read_only_command_evidence",
                "reason": reason,
                "command": command,
                "mutation_allowed": False,
                "operator_intent": operator_focus,
            },
            {
                "step": 2,
                "action": "draft_non_mutating_correction_hypothesis",
                "reason": reason,
                "mutation_allowed": False,
                "writes_files": False,
                "future_slice_required_for_mutation": True,
            },
            {
                "step": 3,
                "action": "request_operator_review_before_any_file_change",
                "mutation_allowed": False,
                "commands_to_run": [],
            },
        ]
    return [
        {
            "step": 1,
            "action": "no_correction_required",
            "reason": reason,
            "command": command,
            "mutation_allowed": False,
            "operator_intent": "continue only after release acceptance and next-slice authorization",
        }
    ]


def build_loop_read_only_correction_plan_payload(diagnosis_payload: dict[str, Any]) -> dict[str, Any]:
    """Generate a bounded correction plan from diagnosis evidence without mutation.

    v0.1.102 may create a proposal-only correction plan.  It does not run new
    commands, retry validation, write files, mutate Project Sources, adopt
    artifacts, deploy, or delete ChatGPT Projects.  File mutation remains
    deferred to a later sandbox-only slice.
    """
    source_schema_ok = diagnosis_payload.get("schema") == LOOP_READ_ONLY_COMMAND_DIAGNOSIS_SCHEMA
    diagnoses = [item for item in diagnosis_payload.get("diagnoses") or [] if isinstance(item, dict)]
    result_classification = str(diagnosis_payload.get("result_classification") or "blocked")
    source_status = str(diagnosis_payload.get("status") or "")
    plan_entries: list[dict[str, Any]] = []
    if source_schema_ok:
        for index, item in enumerate(diagnoses, start=1):
            classification = str(item.get("result_classification") or "blocked")
            entry = {
                "index": index,
                "command": item.get("command"),
                "source_classification": classification,
                "source_reason": item.get("reason"),
                "plan_type": "no_correction_required" if classification == "passed" else "bounded_operator_correction_plan",
                "steps": _bounded_correction_steps_for_diagnosis(item),
                "mutation_allowed": False,
                "writes_files": False,
                "executes_commands": False,
                "project_source_mutation_allowed": False,
                "artifact_adoption_allowed": False,
                "deployment_allowed": False,
            }
            plan_entries.append(entry)
    correction_required_count = sum(1 for item in plan_entries if item.get("plan_type") == "bounded_operator_correction_plan")
    no_correction_count = sum(1 for item in plan_entries if item.get("plan_type") == "no_correction_required")
    if not source_schema_ok:
        ok = False
        status = "correction_plan_blocked_source_schema"
        decision = "stop_for_operator_review"
    elif not plan_entries:
        ok = True
        status = "correction_plan_blocked_no_diagnosis_evidence"
        decision = "stop_for_operator_review"
    elif correction_required_count:
        ok = True
        status = f"correction_plan_generated_{result_classification}_result"
        decision = "operator_review_required_before_mutation"
    else:
        ok = True
        status = "correction_plan_not_required"
        decision = "continue_to_next_planned_slice_after_acceptance"
    return {
        "ok": ok,
        "schema": LOOP_READ_ONLY_CORRECTION_PLAN_SCHEMA,
        "schema_version": LOOP_READ_ONLY_CORRECTION_PLAN_SCHEMA_VERSION,
        "action": "loop_read_only_correction_plan",
        "status": status,
        "mode": "read_only_correction_plan",
        "execution_mode": "local_proposal_only_correction_planning",
        "source_schema": diagnosis_payload.get("schema"),
        "source_status": source_status,
        "source_result_classification": result_classification,
        "target_id": diagnosis_payload.get("target_id"),
        "target_path": diagnosis_payload.get("target_path"),
        "loop_id": diagnosis_payload.get("loop_id"),
        "executed_state": "CORRECT_STUB",
        "source_executed_state": diagnosis_payload.get("executed_state"),
        "final_state": diagnosis_payload.get("final_state"),
        "decision": decision,
        "summary": {
            "diagnosed_command_count": len(diagnoses),
            "correction_plan_entry_count": len(plan_entries),
            "correction_required_count": correction_required_count,
            "no_correction_required_count": no_correction_count,
            "correction_plan_generated": correction_required_count > 0,
            "commands_executed": 0,
            "files_mutated": False,
            "mutation_allowed": False,
            "deployment_performed": False,
            "project_source_mutation_performed": False,
            "artifact_adoption_performed": False,
        },
        "correction_plan": {
            "schema": "promptbranch.loop.correction_plan.proposal",
            "schema_version": "1.0",
            "plan_scope": "proposal_only_no_file_mutation",
            "entries": plan_entries,
            "write_actions": [],
            "file_changes": [],
            "commands_to_execute_now": [],
            "future_slice_required_for_file_mutation": True,
        } if plan_entries else None,
        "dry_run": False,
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
            "correction_plan_generated": correction_required_count > 0,
            "files_mutated": False,
            "correction_plan_only": True,
        },
        "operator_instruction": "Correction-plan generation only. It proposes bounded operator review steps from diagnosis evidence; it does not write files, retry commands, deploy, mutate Project Sources, adopt artifacts, or delete ChatGPT Projects.",
    }


def _classify_sandbox_fixture_path(fixture_path: str, *, repo_root: Path, allowed_paths: list[str]) -> dict[str, Any]:
    raw = str(fixture_path or "").strip()
    if not raw:
        return {"allowed": False, "status": "blocked_missing_sandbox_fixture_path", "reason": "sandbox_mutation.fixture_path is required"}
    path = Path(raw)
    if path.is_absolute() or ".." in path.parts or raw.startswith("~") or _path_has_glob(raw):
        return {
            "allowed": False,
            "status": "blocked_unsafe_sandbox_fixture_path",
            "reason": "sandbox fixture path must be literal repo-relative without parent traversal, home prefix, or glob",
            "path_argument": raw,
        }
    normalized = raw.replace("\\", "/").strip("/")
    if not (normalized == "examples/loop-sandbox" or normalized.startswith("examples/loop-sandbox/")):
        return {
            "allowed": False,
            "status": "blocked_non_sandbox_fixture_path",
            "reason": "v0.1.103 allows mutation only under examples/loop-sandbox/",
            "path_argument": normalized,
        }
    resolved = (repo_root / normalized).resolve()
    try:
        rel_path = str(resolved.relative_to(repo_root))
    except ValueError:
        return {
            "allowed": False,
            "status": "blocked_sandbox_fixture_outside_repo",
            "reason": "sandbox fixture resolved outside repo root",
            "path_argument": normalized,
        }
    if not resolved.is_file():
        return {
            "allowed": False,
            "status": "blocked_missing_sandbox_fixture",
            "reason": "sandbox fixture file does not exist",
            "path_argument": rel_path,
        }
    if not _path_matches_allowed_patterns(rel_path, allowed_paths):
        return {
            "allowed": False,
            "status": "blocked_sandbox_fixture_outside_allowed_paths",
            "reason": "sandbox fixture is not covered by target.allowed_paths",
            "path_argument": rel_path,
        }
    return {
        "allowed": True,
        "status": "allowlisted_sandbox_fixture_path",
        "reason": "sandbox fixture path is repo-relative, under examples/loop-sandbox/, and covered by allowed_paths",
        "path_argument": rel_path,
        "target_path": str(resolved),
    }


def _copy_fixture_to_temporary_sandbox(source: Path, *, repo_root: Path, sandbox_root: Path) -> Path:
    rel = source.resolve().relative_to(repo_root)
    destination = sandbox_root / rel
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    return destination


def build_loop_sandbox_file_mutation_payload(
    plan: dict[str, Any],
    correction_payload: dict[str, Any],
    *,
    repo_root: str | Path | None = None,
) -> dict[str, Any]:
    """Perform the first controlled file mutation inside a temporary sandbox only.

    v0.1.103 deliberately limits write capability to a copied fixture under a
    temporary workspace.  The repository fixture is snapshotted before/after and
    must remain unchanged.  No correction retry, Project Source mutation,
    artifact adoption, deployment, or ChatGPT Project deletion is performed.
    """
    root = Path.cwd().resolve() if repo_root is None else Path(repo_root).expanduser().resolve()
    source_schema_ok = correction_payload.get("schema") == LOOP_READ_ONLY_CORRECTION_PLAN_SCHEMA
    source_plan_generated = bool((correction_payload.get("summary") or {}).get("correction_plan_generated"))
    sandbox_config = plan.get("sandbox_mutation") if isinstance(plan.get("sandbox_mutation"), dict) else {}
    checks = plan.get("checks") if isinstance(plan.get("checks"), dict) else {}
    if checks:
        allowed_paths = [str(item.get("path")) for item in checks.get("allowed_paths") or [] if isinstance(item, dict) and item.get("path")]
    else:
        allowed_paths = [str(item) for item in plan.get("allowed_paths") or []]

    blocked_reasons: list[str] = []
    operation = str(sandbox_config.get("operation") or "").strip()
    replacement_contents = sandbox_config.get("replacement_contents")
    fixture_path = str(sandbox_config.get("fixture_path") or "")
    classification = _classify_sandbox_fixture_path(fixture_path, repo_root=root, allowed_paths=allowed_paths)

    if not source_schema_ok:
        blocked_reasons.append("correction_plan_source_schema_invalid")
    if not source_plan_generated:
        blocked_reasons.append("correction_plan_not_generated")
    if operation != "replace_contents":
        blocked_reasons.append("sandbox_mutation_operation_not_allowlisted")
    if not isinstance(replacement_contents, str) or not replacement_contents:
        blocked_reasons.append("sandbox_mutation_replacement_contents_missing")
    if isinstance(replacement_contents, str) and len(replacement_contents.encode("utf-8")) > 4096:
        blocked_reasons.append("sandbox_mutation_replacement_too_large")
    if not classification.get("allowed"):
        blocked_reasons.append(str(classification.get("status") or "sandbox_fixture_not_allowlisted"))

    repo_before: dict[str, Any] | None = None
    repo_after: dict[str, Any] | None = None
    sandbox_before: dict[str, Any] | None = None
    sandbox_after: dict[str, Any] | None = None
    sandbox_deleted = False
    mutation_performed = False
    sandbox_rel_path = classification.get("path_argument") or fixture_path
    sandbox_workspace: str | None = None
    expected_before_sha = str(sandbox_config.get("expected_before_sha256") or "").strip()
    actual_before_sha: str | None = None

    if not blocked_reasons:
        source_path = Path(str(classification["target_path"]))
        repo_before = _safe_stat_snapshot(source_path, repo_root=root)
        actual_before_sha = str(repo_before.get("sha256") or "")
        if expected_before_sha and actual_before_sha != expected_before_sha:
            blocked_reasons.append("sandbox_fixture_expected_hash_mismatch")

    if not blocked_reasons:
        source_path = Path(str(classification["target_path"]))
        sandbox_dir = tempfile.mkdtemp(prefix="promptbranch-loop-sandbox-")
        sandbox_workspace = sandbox_dir
        try:
            sandbox_root = Path(sandbox_dir)
            sandbox_file = _copy_fixture_to_temporary_sandbox(source_path, repo_root=root, sandbox_root=sandbox_root)
            sandbox_before = _safe_stat_snapshot(sandbox_file, repo_root=sandbox_root)
            sandbox_file.write_text(str(replacement_contents), encoding="utf-8")
            mutation_performed = True
            sandbox_after = _safe_stat_snapshot(sandbox_file, repo_root=sandbox_root)
            repo_after = _safe_stat_snapshot(source_path, repo_root=root)
            if repo_before != repo_after:
                blocked_reasons.append("repository_fixture_changed")
        finally:
            shutil.rmtree(sandbox_dir, ignore_errors=True)
            sandbox_deleted = True
    elif classification.get("target_path"):
        source_path = Path(str(classification["target_path"]))
        repo_before = _safe_stat_snapshot(source_path, repo_root=root)
        repo_after = _safe_stat_snapshot(source_path, repo_root=root)

    ok = not blocked_reasons and mutation_performed and repo_before == repo_after and sandbox_before != sandbox_after
    return {
        "ok": ok,
        "schema": LOOP_SANDBOX_FILE_MUTATION_SCHEMA,
        "schema_version": LOOP_SANDBOX_FILE_MUTATION_SCHEMA_VERSION,
        "action": "loop_sandbox_file_mutation",
        "status": "sandbox_file_mutation_applied" if ok else "sandbox_file_mutation_blocked",
        "mode": "sandbox_file_mutation",
        "execution_mode": "local_temporary_sandbox_fixture_mutation",
        "source_schema": correction_payload.get("schema"),
        "source_status": correction_payload.get("status"),
        "source_result_classification": correction_payload.get("source_result_classification"),
        "target_id": plan.get("target_id"),
        "target_path": plan.get("target_path"),
        "loop_id": plan.get("loop_id"),
        "executed_state": "ACT_STUB",
        "source_executed_state": correction_payload.get("executed_state"),
        "final_state": plan.get("final_state"),
        "decision": "stop_after_sandbox_mutation_evidence" if ok else "stop_for_operator_review",
        "blocked_reasons": sorted(set(blocked_reasons)),
        "sandbox_mutation_request": {
            "operation": operation,
            "fixture_path": fixture_path,
            "allowlist_status": classification.get("status"),
            "allowlist_reason": classification.get("reason"),
            "expected_before_sha256": expected_before_sha or None,
            "actual_before_sha256": actual_before_sha,
        },
        "evidence": {
            "repository_fixture_before": repo_before,
            "repository_fixture_after": repo_after,
            "sandbox_fixture_before": sandbox_before,
            "sandbox_fixture_after": sandbox_after,
            "sandbox_workspace": sandbox_workspace,
            "sandbox_workspace_deleted_after_evidence": sandbox_deleted,
            "sandbox_relative_path": sandbox_rel_path,
        },
        "summary": {
            "sandbox_mutation_performed": mutation_performed,
            "sandbox_file_mutated": mutation_performed,
            "repository_file_mutated": bool(repo_before != repo_after) if repo_before is not None and repo_after is not None else False,
            "project_source_mutation_performed": False,
            "artifact_adoption_performed": False,
            "deployment_performed": False,
            "commands_executed": 0,
            "files_mutated": mutation_performed,
        },
        "dry_run": False,
        "side_effects_performed": mutation_performed,
        "safety": {
            "side_effects_performed": mutation_performed,
            "mutation_allowed": True,
            "sandbox_file_mutation_performed": mutation_performed,
            "repository_file_mutation_performed": bool(repo_before != repo_after) if repo_before is not None and repo_after is not None else False,
            "commands_executed": False,
            "deployment_performed": False,
            "kubernetes_mutation_performed": False,
            "project_source_mutation_performed": False,
            "artifact_adoption_performed": False,
            "chatgpt_project_deletion_performed": False,
            "correction_plan_required": True,
            "correction_plan_source_required": True,
            "sandbox_only": True,
        },
        "operator_instruction": "First controlled file mutation in a temporary sandbox fixture only. The repository fixture is copied, the sandbox copy is mutated, before/after hashes are recorded, and the repository file must remain unchanged. No correction retry, deployment, Project Source mutation, artifact adoption, or ChatGPT Project deletion is performed.",
    }


def _sandbox_snapshot_sha(snapshot: dict[str, Any] | None) -> str | None:
    if not isinstance(snapshot, dict):
        return None
    value = snapshot.get("sha256")
    return str(value) if value else None


def build_loop_sandbox_mutation_verification_payload(mutation_payload: dict[str, Any]) -> dict[str, Any]:
    """Verify sandbox mutation evidence and rollback/cleanup gate.

    v0.1.104 does not perform a second mutation and does not promote the
    sandbox change to the repository.  It validates the evidence produced by
    v0.1.103, confirms the temporary sandbox changed, confirms the repository
    fixture did not change, and treats deletion of the temporary sandbox
    workspace as the rollback evidence for this sandbox-only stage.
    """
    evidence = mutation_payload.get("evidence") if isinstance(mutation_payload.get("evidence"), dict) else {}
    summary = mutation_payload.get("summary") if isinstance(mutation_payload.get("summary"), dict) else {}
    safety = mutation_payload.get("safety") if isinstance(mutation_payload.get("safety"), dict) else {}

    repo_before = evidence.get("repository_fixture_before") if isinstance(evidence.get("repository_fixture_before"), dict) else None
    repo_after = evidence.get("repository_fixture_after") if isinstance(evidence.get("repository_fixture_after"), dict) else None
    sandbox_before = evidence.get("sandbox_fixture_before") if isinstance(evidence.get("sandbox_fixture_before"), dict) else None
    sandbox_after = evidence.get("sandbox_fixture_after") if isinstance(evidence.get("sandbox_fixture_after"), dict) else None
    sandbox_deleted = bool(evidence.get("sandbox_workspace_deleted_after_evidence"))

    repo_before_sha = _sandbox_snapshot_sha(repo_before)
    repo_after_sha = _sandbox_snapshot_sha(repo_after)
    sandbox_before_sha = _sandbox_snapshot_sha(sandbox_before)
    sandbox_after_sha = _sandbox_snapshot_sha(sandbox_after)

    gates = [
        {
            "name": "source_schema_is_sandbox_file_mutation",
            "passed": mutation_payload.get("schema") == LOOP_SANDBOX_FILE_MUTATION_SCHEMA,
            "detail": "source schema must be promptbranch.loop.sandbox_file_mutation",
        },
        {
            "name": "source_mutation_payload_ok",
            "passed": bool(mutation_payload.get("ok")) and mutation_payload.get("status") == "sandbox_file_mutation_applied",
            "detail": "source mutation payload must be applied successfully",
        },
        {
            "name": "sandbox_mutation_was_performed",
            "passed": bool(summary.get("sandbox_mutation_performed")) and bool(safety.get("sandbox_file_mutation_performed")),
            "detail": "sandbox mutation evidence must show a sandbox file was mutated",
        },
        {
            "name": "repository_fixture_unchanged",
            "passed": bool(repo_before and repo_after and repo_before == repo_after and repo_before_sha == repo_after_sha),
            "detail": "repository fixture before/after snapshots and hashes must match",
        },
        {
            "name": "sandbox_fixture_changed",
            "passed": bool(sandbox_before and sandbox_after and sandbox_before != sandbox_after and sandbox_before_sha != sandbox_after_sha),
            "detail": "temporary sandbox fixture before/after snapshots and hashes must differ",
        },
        {
            "name": "temporary_sandbox_workspace_deleted",
            "passed": sandbox_deleted,
            "detail": "temporary sandbox workspace deletion is required rollback evidence",
        },
        {
            "name": "no_project_source_mutation",
            "passed": summary.get("project_source_mutation_performed") is False and safety.get("project_source_mutation_performed") is False,
            "detail": "Project Source mutation must remain false",
        },
        {
            "name": "no_artifact_adoption",
            "passed": summary.get("artifact_adoption_performed") is False and safety.get("artifact_adoption_performed") is False,
            "detail": "artifact adoption must remain false",
        },
        {
            "name": "no_deployment_or_kubernetes_mutation",
            "passed": summary.get("deployment_performed") is False and safety.get("deployment_performed") is False and safety.get("kubernetes_mutation_performed") is False,
            "detail": "deployment and Kubernetes mutation must remain false",
        },
    ]
    failed = [str(item["name"]) for item in gates if not item.get("passed")]
    ok = not failed
    return {
        "ok": ok,
        "schema": LOOP_SANDBOX_MUTATION_VERIFICATION_SCHEMA,
        "schema_version": LOOP_SANDBOX_MUTATION_VERIFICATION_SCHEMA_VERSION,
        "action": "loop_sandbox_mutation_verification",
        "status": "sandbox_mutation_verification_passed" if ok else "sandbox_mutation_verification_blocked",
        "mode": "sandbox_mutation_verification",
        "execution_mode": "local_sandbox_mutation_verification_and_rollback_gate",
        "source_schema": mutation_payload.get("schema"),
        "source_status": mutation_payload.get("status"),
        "target_id": mutation_payload.get("target_id"),
        "target_path": mutation_payload.get("target_path"),
        "loop_id": mutation_payload.get("loop_id"),
        "executed_state": "VERIFY_STUB",
        "source_executed_state": mutation_payload.get("executed_state"),
        "final_state": mutation_payload.get("final_state"),
        "decision": "stop_after_sandbox_verification_evidence" if ok else "stop_for_operator_review",
        "blocked_reasons": failed,
        "verification_gates": gates,
        "rollback_evidence": {
            "rollback_required": True,
            "rollback_strategy": "delete_temporary_sandbox_workspace",
            "rollback_performed": sandbox_deleted,
            "rollback_verified": sandbox_deleted,
            "sandbox_workspace": evidence.get("sandbox_workspace"),
            "sandbox_workspace_deleted_after_evidence": sandbox_deleted,
            "repository_fixture_restored_by_design": bool(repo_before and repo_after and repo_before == repo_after),
        },
        "evidence_summary": {
            "repository_fixture_before_sha256": repo_before_sha,
            "repository_fixture_after_sha256": repo_after_sha,
            "sandbox_fixture_before_sha256": sandbox_before_sha,
            "sandbox_fixture_after_sha256": sandbox_after_sha,
            "repository_fixture_unchanged": bool(repo_before and repo_after and repo_before == repo_after),
            "sandbox_fixture_changed": bool(sandbox_before and sandbox_after and sandbox_before != sandbox_after),
            "temporary_workspace_deleted": sandbox_deleted,
        },
        "summary": {
            "verification_gate_count": len(gates),
            "passed_gate_count": sum(1 for item in gates if item.get("passed")),
            "failed_gate_count": len(failed),
            "sandbox_mutation_verified": ok,
            "rollback_verified": sandbox_deleted,
            "repository_file_mutated": bool(summary.get("repository_file_mutated")),
            "project_source_mutation_performed": False,
            "artifact_adoption_performed": False,
            "deployment_performed": False,
            "commands_executed": 0,
            "files_mutated": False,
        },
        "dry_run": False,
        "side_effects_performed": False,
        "safety": {
            "side_effects_performed": False,
            "verification_only": True,
            "mutation_allowed": False,
            "sandbox_file_mutation_performed": False,
            "repository_file_mutation_performed": False,
            "commands_executed": False,
            "deployment_performed": False,
            "kubernetes_mutation_performed": False,
            "project_source_mutation_performed": False,
            "artifact_adoption_performed": False,
            "chatgpt_project_deletion_performed": False,
            "rollback_gate_verified": sandbox_deleted,
            "sandbox_only": True,
        },
        "operator_instruction": "Sandbox mutation verification and rollback evidence gate only. It verifies that the temporary sandbox fixture changed, the repository fixture did not change, and the temporary sandbox workspace was deleted as rollback evidence. It performs no new mutation, command retry, deployment, Project Source mutation, artifact adoption, or ChatGPT Project deletion.",
    }

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
                "executed": bool(item.get("executed", False)),
                "exit_code": item.get("exit_code"),
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


def build_loop_read_only_evidence_gate(report: dict[str, Any]) -> dict[str, Any]:
    """Build a machine-checkable gate over a read-only evidence report.

    This does not execute commands or inspect external systems.  It only
    normalizes whether the evidence report is clean enough to let a future
    loop slice proceed to the next *dry-run* step.
    """
    summary = report.get("evidence_summary") if isinstance(report.get("evidence_summary"), dict) else {}
    assertions = report.get("safety_assertions") if isinstance(report.get("safety_assertions"), dict) else {}
    declared_command_count = int(summary.get("declared_command_count") or 0)
    skipped_command_count = int(summary.get("skipped_command_count") or 0)
    unsafe_path_count = int(summary.get("unsafe_path_count") or 0)
    commands_executed = int(summary.get("commands_executed") or 0)
    gates = [
        {
            "name": "evidence_report_ok",
            "passed": bool(report.get("ok")) and report.get("status") == "evidence_clean",
            "detail": "source evidence report is clean",
        },
        {
            "name": "source_schema_is_read_only_execution",
            "passed": report.get("source_schema") == LOOP_READ_ONLY_EXECUTION_SCHEMA,
            "detail": "gate only accepts promptbranch.loop.read_only_execution evidence",
        },
        {
            "name": "no_unsafe_paths",
            "passed": unsafe_path_count == 0,
            "detail": f"unsafe_path_count={unsafe_path_count}",
        },
        {
            "name": "no_commands_executed",
            "passed": commands_executed == 0,
            "detail": f"commands_executed={commands_executed}",
        },
        {
            "name": "all_declared_commands_skipped",
            "passed": declared_command_count == skipped_command_count,
            "detail": f"declared={declared_command_count} skipped={skipped_command_count}",
        },
        {
            "name": "no_files_mutated",
            "passed": assertions.get("files_mutated") is False,
            "detail": "files_mutated=false required",
        },
        {
            "name": "no_deployment_performed",
            "passed": assertions.get("deployment_performed") is False,
            "detail": "deployment_performed=false required",
        },
        {
            "name": "no_kubernetes_mutation_performed",
            "passed": assertions.get("kubernetes_mutation_performed") is False,
            "detail": "kubernetes_mutation_performed=false required",
        },
        {
            "name": "no_project_source_mutation_performed",
            "passed": assertions.get("project_source_mutation_performed") is False,
            "detail": "project_source_mutation_performed=false required",
        },
        {
            "name": "no_artifact_adoption_performed",
            "passed": assertions.get("artifact_adoption_performed") is False,
            "detail": "artifact_adoption_performed=false required",
        },
    ]
    failed = [gate["name"] for gate in gates if not gate.get("passed")]
    passed = not failed
    return {
        "ok": passed,
        "schema": LOOP_READ_ONLY_EVIDENCE_GATE_SCHEMA,
        "schema_version": LOOP_READ_ONLY_EVIDENCE_GATE_SCHEMA_VERSION,
        "action": "loop_evidence_gate",
        "status": "gate_passed" if passed else "gate_blocked",
        "decision": "continue_to_next_dry_run_step" if passed else "stop_for_operator_review",
        "source_schema": report.get("schema"),
        "source_status": report.get("status"),
        "target_id": report.get("target_id"),
        "target_path": report.get("target_path"),
        "loop_id": report.get("loop_id"),
        "execution_mode": report.get("execution_mode"),
        "executed_state": report.get("executed_state"),
        "final_state": report.get("final_state"),
        "gate_summary": {
            "gate_count": len(gates),
            "passed_gate_count": sum(1 for gate in gates if gate.get("passed")),
            "failed_gate_count": len(failed),
            "unsafe_path_count": unsafe_path_count,
            "declared_command_count": declared_command_count,
            "skipped_command_count": skipped_command_count,
            "commands_executed": commands_executed,
            "all_declared_commands_skipped": declared_command_count == skipped_command_count,
            "side_effects_performed": False,
        },
        "gates": gates,
        "blocked_reasons": failed,
        "side_effects_performed": False,
        "safety_assertions": {
            "commands_executed": False,
            "files_mutated": False,
            "deployment_performed": False,
            "kubernetes_mutation_performed": False,
            "project_source_mutation_performed": False,
            "artifact_adoption_performed": False,
            "chatgpt_project_deletion_performed": False,
        },
        "operator_instruction": "Evidence gate only. It makes a continue/block decision from existing read-only evidence and performs no commands, file mutation, deployment, Project Source mutation, artifact adoption, or ChatGPT Project deletion.",
    }



def render_loop_read_only_command_execution_text(payload: dict[str, Any]) -> str:
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    lines = [
        f"status={payload.get('status')}",
        f"schema={payload.get('schema')}",
        f"target_id={payload.get('target_id') or 'none'}",
        f"execution_mode={payload.get('execution_mode') or 'none'}",
        f"commands_executed={summary.get('commands_executed', 0)}",
        f"blocked_command_count={summary.get('blocked_command_count', 0)}",
        f"mutation_detected={str(bool(summary.get('mutation_detected'))).lower()}",
    ]
    for item in payload.get("command_evidence") or []:
        lines.append(
            "command_evidence={command} status={status} executed={executed} exit_code={exit_code}".format(
                command=item.get("command"),
                status=item.get("execution_status"),
                executed=str(bool(item.get("executed"))).lower(),
                exit_code=item.get("exit_code"),
            )
        )
    for reason in payload.get("blocked_reasons") or []:
        lines.append(f"blocked_reason={reason}")
    lines.append(f"side_effects_performed={str(bool(payload.get('side_effects_performed'))).lower()}")
    return "\n".join(lines) + "\n"


def render_loop_read_only_command_diagnosis_text(payload: dict[str, Any]) -> str:
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    lines = [
        f"status={payload.get('status')}",
        f"schema={payload.get('schema')}",
        f"result_classification={payload.get('result_classification')}",
        f"decision={payload.get('decision')}",
        f"target_id={payload.get('target_id') or 'none'}",
        f"execution_mode={payload.get('execution_mode') or 'none'}",
        f"diagnosed_command_count={summary.get('diagnosed_command_count', 0)}",
        f"passed_command_count={summary.get('passed_command_count', 0)}",
        f"blocked_command_count={summary.get('blocked_command_count', 0)}",
        f"failed_command_count={summary.get('failed_command_count', 0)}",
        f"mutation_detected={str(bool(summary.get('mutation_detected'))).lower()}",
        f"correction_plan_generated={str(bool(summary.get('correction_plan_generated'))).lower()}",
        f"files_mutated={str(bool(summary.get('files_mutated'))).lower()}",
    ]
    for item in payload.get("diagnoses") or []:
        lines.append(
            "diagnosis={command} classification={classification} reason={reason} action={action}".format(
                command=item.get("command"),
                classification=item.get("result_classification"),
                reason=item.get("reason"),
                action=item.get("operator_action"),
            )
        )
    lines.append(f"side_effects_performed={str(bool(payload.get('side_effects_performed'))).lower()}")
    return "\n".join(lines) + "\n"



def render_loop_sandbox_file_mutation_text(payload: dict[str, Any]) -> str:
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    request = payload.get("sandbox_mutation_request") if isinstance(payload.get("sandbox_mutation_request"), dict) else {}
    lines = [
        f"status={payload.get('status')}",
        f"schema={payload.get('schema')}",
        f"source_status={payload.get('source_status')}",
        f"target_id={payload.get('target_id') or 'none'}",
        f"execution_mode={payload.get('execution_mode') or 'none'}",
        f"operation={request.get('operation') or 'none'}",
        f"fixture_path={request.get('fixture_path') or 'none'}",
        f"allowlist_status={request.get('allowlist_status') or 'none'}",
        f"sandbox_mutation_performed={str(bool(summary.get('sandbox_mutation_performed'))).lower()}",
        f"repository_file_mutated={str(bool(summary.get('repository_file_mutated'))).lower()}",
        f"commands_executed={summary.get('commands_executed', 0)}",
    ]
    for reason in payload.get("blocked_reasons") or []:
        lines.append(f"blocked_reason={reason}")
    lines.append(f"side_effects_performed={str(bool(payload.get('side_effects_performed'))).lower()}")
    return "\n".join(lines) + "\n"

def render_loop_read_only_correction_plan_text(payload: dict[str, Any]) -> str:
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    lines = [
        f"status={payload.get('status')}",
        f"schema={payload.get('schema')}",
        f"source_result_classification={payload.get('source_result_classification')}",
        f"decision={payload.get('decision')}",
        f"target_id={payload.get('target_id') or 'none'}",
        f"execution_mode={payload.get('execution_mode') or 'none'}",
        f"correction_plan_entry_count={summary.get('correction_plan_entry_count', 0)}",
        f"correction_required_count={summary.get('correction_required_count', 0)}",
        f"correction_plan_generated={str(bool(summary.get('correction_plan_generated'))).lower()}",
        f"commands_executed={summary.get('commands_executed', 0)}",
        f"files_mutated={str(bool(summary.get('files_mutated'))).lower()}",
    ]
    plan = payload.get("correction_plan") if isinstance(payload.get("correction_plan"), dict) else {}
    for entry in plan.get("entries") or []:
        lines.append(
            "correction_plan_entry={command} classification={classification} reason={reason} type={plan_type}".format(
                command=entry.get("command"),
                classification=entry.get("source_classification"),
                reason=entry.get("source_reason"),
                plan_type=entry.get("plan_type"),
            )
        )
        for step in entry.get("steps") or []:
            lines.append(
                "correction_step={step} action={action} mutation_allowed={mutation}".format(
                    step=step.get("step"),
                    action=step.get("action"),
                    mutation=str(bool(step.get("mutation_allowed"))).lower(),
                )
            )
    lines.append(f"side_effects_performed={str(bool(payload.get('side_effects_performed'))).lower()}")
    return "\n".join(lines) + "\n"


def render_loop_sandbox_mutation_verification_text(payload: dict[str, Any]) -> str:
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    rollback = payload.get("rollback_evidence") if isinstance(payload.get("rollback_evidence"), dict) else {}
    evidence = payload.get("evidence_summary") if isinstance(payload.get("evidence_summary"), dict) else {}
    lines = [
        f"status={payload.get('status')}",
        f"schema={payload.get('schema')}",
        f"source_status={payload.get('source_status')}",
        f"target_id={payload.get('target_id') or 'none'}",
        f"execution_mode={payload.get('execution_mode') or 'none'}",
        f"sandbox_mutation_verified={str(bool(summary.get('sandbox_mutation_verified'))).lower()}",
        f"rollback_verified={str(bool(summary.get('rollback_verified'))).lower()}",
        f"repository_fixture_unchanged={str(bool(evidence.get('repository_fixture_unchanged'))).lower()}",
        f"sandbox_fixture_changed={str(bool(evidence.get('sandbox_fixture_changed'))).lower()}",
        f"temporary_workspace_deleted={str(bool(evidence.get('temporary_workspace_deleted'))).lower()}",
        f"rollback_strategy={rollback.get('rollback_strategy') or 'none'}",
        f"failed_gate_count={summary.get('failed_gate_count', 0)}",
    ]
    for reason in payload.get("blocked_reasons") or []:
        lines.append(f"blocked_reason={reason}")
    lines.append(f"side_effects_performed={str(bool(payload.get('side_effects_performed'))).lower()}")
    return "\n".join(lines) + "\n"

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


def render_loop_read_only_evidence_gate_text(payload: dict[str, Any]) -> str:
    summary = payload.get("gate_summary") if isinstance(payload.get("gate_summary"), dict) else {}
    lines = [
        f"status={payload.get('status')}",
        f"schema={payload.get('schema')}",
        f"decision={payload.get('decision')}",
        f"target_id={payload.get('target_id') or 'none'}",
        f"execution_mode={payload.get('execution_mode') or 'none'}",
        f"gate_count={summary.get('gate_count', 0)}",
        f"passed_gate_count={summary.get('passed_gate_count', 0)}",
        f"failed_gate_count={summary.get('failed_gate_count', 0)}",
        f"commands_executed={summary.get('commands_executed', 0)}",
        f"unsafe_path_count={summary.get('unsafe_path_count', 0)}",
    ]
    for gate in payload.get("gates") or []:
        lines.append(
            "gate={name} passed={passed} detail={detail}".format(
                name=gate.get("name"),
                passed=str(bool(gate.get("passed"))).lower(),
                detail=gate.get("detail") or "",
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
