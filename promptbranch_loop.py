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
LOOP_SANDBOX_MUTATION_VERIFICATION_SCHEMA = "promptbranch.loop.sandbox_mutation_verification"
LOOP_SANDBOX_MUTATION_VERIFICATION_SCHEMA_VERSION = "1.0"
LOOP_SANDBOX_CORRECTION_PROMOTION_READINESS_SCHEMA = "promptbranch.loop.sandbox_correction_promotion_readiness"
LOOP_SANDBOX_CORRECTION_PROMOTION_READINESS_SCHEMA_VERSION = "1.0"
LOOP_SANDBOX_CORRECTION_PROMOTION_DECISION_SCHEMA = "promptbranch.loop.sandbox_correction_promotion_decision"
LOOP_SANDBOX_CORRECTION_PROMOTION_DECISION_SCHEMA_VERSION = "1.0"
LOOP_CONTROLLED_CORRECTION_EXECUTION_ENVELOPE_DESIGN_SCHEMA = "promptbranch.loop.controlled_correction_execution_envelope_design"
LOOP_CONTROLLED_CORRECTION_EXECUTION_ENVELOPE_DESIGN_SCHEMA_VERSION = "1.0"
CONTROLLED_CORRECTION_EXECUTION_ENVELOPE_SCHEMA = "promptbranch.loop.controlled_correction_execution_envelope"
CONTROLLED_CORRECTION_EXECUTION_ENVELOPE_SCHEMA_VERSION = "1.0"
CONTROLLED_CORRECTION_PROMOTION_DECISION_RECORD = "docs/project/correction-promotion-decision-v0.1.106.json"

PROMOTION_READINESS_REPOSITORY_MARKERS: tuple[tuple[str, str], ...] = (
    ("VERSION", "file"),
    ("pyproject.toml", "file"),
    ("promptbranch_cli.py", "file"),
    ("promptbranch_loop.py", "file"),
    ("examples/loop-targets", "dir"),
    ("examples/loop-sandbox", "dir"),
)

SANDBOX_PROMOTION_REQUIRED_GATES = (
    "correction_plan_schema_valid",
    "correction_plan_generated",
    "sandbox_fixture_allowlisted",
    "mutation_operation_allowlisted",
    "before_hash_matches",
    "after_hash_matches",
    "mutation_result_verified",
    "sandbox_validation_passed",
    "sandbox_validation_read_only",
    "repository_fixture_unchanged",
    "rollback_attempted",
    "rollback_restored_before_snapshot",
    "sandbox_workspace_deleted",
)

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


def _classify_sandbox_validation_command(
    command: str,
    *,
    fixture_rel_path: str,
) -> dict[str, Any]:
    try:
        argv = shlex.split(command)
    except ValueError as exc:
        return {
            "allowed": False,
            "status": "sandbox_validation_command_parse_error",
            "reason": str(exc),
            "argv": [],
        }
    if len(argv) != 4 or argv[:3] != ["python3", "-m", "json.tool"]:
        return {
            "allowed": False,
            "status": "sandbox_validation_command_not_allowlisted",
            "reason": "v0.1.104 allows only: python3 -m json.tool <sandbox-fixture-relative-path>",
            "argv": argv,
        }
    normalized_arg = str(Path(argv[3])).replace("\\", "/").strip("/")
    normalized_fixture = str(Path(fixture_rel_path)).replace("\\", "/").strip("/")
    if normalized_arg != normalized_fixture:
        return {
            "allowed": False,
            "status": "sandbox_validation_command_target_mismatch",
            "reason": "sandbox validation command must target the exact copied fixture",
            "argv": argv,
            "path_argument": normalized_arg,
        }
    return {
        "allowed": True,
        "status": "allowlisted_sandbox_json_validation",
        "reason": "exact read-only JSON syntax validation command targets the copied sandbox fixture",
        "argv": argv,
        "path_argument": normalized_arg,
    }


def build_loop_sandbox_mutation_verification_payload(
    plan: dict[str, Any],
    correction_payload: dict[str, Any],
    *,
    repo_root: str | Path | None = None,
    timeout_seconds: float = 15.0,
) -> dict[str, Any]:
    """Mutate, verify, roll back, and delete one copied sandbox fixture.

    v0.1.104 keeps all write authority inside a temporary workspace. The copied
    fixture must match the declared before hash, the mutation must match the
    declared after hash, the allowlisted validation command must pass without
    changing the file, rollback must restore the exact before snapshot, and the
    repository fixture must remain unchanged. Any missing or contradictory
    evidence blocks the result and stops for operator review.
    """
    root = Path.cwd().resolve() if repo_root is None else Path(repo_root).expanduser().resolve()
    source_schema_ok = correction_payload.get("schema") == LOOP_READ_ONLY_CORRECTION_PLAN_SCHEMA
    source_plan_generated = bool((correction_payload.get("summary") or {}).get("correction_plan_generated"))
    sandbox_config = plan.get("sandbox_mutation") if isinstance(plan.get("sandbox_mutation"), dict) else {}
    checks = plan.get("checks") if isinstance(plan.get("checks"), dict) else {}
    if checks:
        allowed_paths = [str(item.get("path")) for item in checks.get("allowed_paths") or [] if isinstance(item, dict) and item.get("path")]
        validation_commands = [str(item.get("command")) for item in checks.get("validation_commands") or [] if isinstance(item, dict) and item.get("command")]
    else:
        allowed_paths = [str(item) for item in plan.get("allowed_paths") or []]
        validation_commands = [str(item) for item in plan.get("validation_commands") or []]

    operation = str(sandbox_config.get("operation") or "").strip()
    replacement_contents = sandbox_config.get("replacement_contents")
    fixture_path = str(sandbox_config.get("fixture_path") or "")
    expected_before_sha = str(sandbox_config.get("expected_before_sha256") or "").strip()
    expected_after_sha = str(sandbox_config.get("expected_after_sha256") or "").strip()
    classification = _classify_sandbox_fixture_path(fixture_path, repo_root=root, allowed_paths=allowed_paths)
    validation_command = validation_commands[0] if len(validation_commands) == 1 else ""
    validation_classification = _classify_sandbox_validation_command(
        validation_command,
        fixture_rel_path=str(classification.get("path_argument") or fixture_path),
    ) if validation_command else {
        "allowed": False,
        "status": "sandbox_validation_command_count_invalid",
        "reason": "exactly one sandbox validation command is required",
        "argv": [],
    }

    blocked_reasons: list[str] = []
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
    if not expected_before_sha:
        blocked_reasons.append("sandbox_mutation_expected_before_sha256_missing")
    if not expected_after_sha:
        blocked_reasons.append("sandbox_mutation_expected_after_sha256_missing")
    if not classification.get("allowed"):
        blocked_reasons.append(str(classification.get("status") or "sandbox_fixture_not_allowlisted"))
    if len(validation_commands) != 1:
        blocked_reasons.append("sandbox_validation_command_count_invalid")
    if not validation_classification.get("allowed"):
        blocked_reasons.append(str(validation_classification.get("status") or "sandbox_validation_command_not_allowlisted"))

    repo_before: dict[str, Any] | None = None
    repo_after: dict[str, Any] | None = None
    sandbox_before: dict[str, Any] | None = None
    sandbox_after: dict[str, Any] | None = None
    sandbox_after_validation: dict[str, Any] | None = None
    sandbox_after_rollback: dict[str, Any] | None = None
    sandbox_workspace: str | None = None
    sandbox_deleted = False
    mutation_performed = False
    mutation_verified = False
    validation_executed = False
    validation_passed = False
    validation_mutation_detected = False
    rollback_attempted = False
    rollback_succeeded = False
    validation_evidence: dict[str, Any] = {
        "command": validation_command or None,
        "classification": validation_classification,
        "executed": False,
        "exit_code": None,
        "stdout": "",
        "stderr": "",
        "timed_out": False,
    }
    actual_before_sha: str | None = None
    actual_after_sha: str | None = None
    source_path: Path | None = None
    original_bytes: bytes | None = None

    if classification.get("target_path"):
        source_path = Path(str(classification["target_path"]))
        repo_before = _safe_stat_snapshot(source_path, repo_root=root)
        actual_before_sha = str(repo_before.get("sha256") or "")
        if expected_before_sha and actual_before_sha != expected_before_sha:
            blocked_reasons.append("sandbox_fixture_expected_before_hash_mismatch")

    if not blocked_reasons and source_path is not None:
        original_bytes = source_path.read_bytes()
        sandbox_dir = tempfile.mkdtemp(prefix="promptbranch-loop-sandbox-")
        sandbox_workspace = sandbox_dir
        sandbox_root = Path(sandbox_dir)
        sandbox_file: Path | None = None
        try:
            sandbox_file = _copy_fixture_to_temporary_sandbox(source_path, repo_root=root, sandbox_root=sandbox_root)
            sandbox_before = _safe_stat_snapshot(sandbox_file, repo_root=sandbox_root)
            try:
                sandbox_file.write_text(str(replacement_contents), encoding="utf-8")
                mutation_performed = True
                sandbox_after = _safe_stat_snapshot(sandbox_file, repo_root=sandbox_root)
                actual_after_sha = str((sandbox_after or {}).get("sha256") or "")
                if sandbox_after == sandbox_before:
                    blocked_reasons.append("sandbox_mutation_produced_no_change")
                if actual_after_sha != expected_after_sha:
                    blocked_reasons.append("sandbox_mutation_expected_after_hash_mismatch")
                if sandbox_file.read_text(encoding="utf-8") != replacement_contents:
                    blocked_reasons.append("sandbox_mutation_contents_mismatch")
                mutation_verified = not any(
                    reason in blocked_reasons
                    for reason in {
                        "sandbox_mutation_produced_no_change",
                        "sandbox_mutation_expected_after_hash_mismatch",
                        "sandbox_mutation_contents_mismatch",
                    }
                )

                if mutation_verified:
                    validation_executed = True
                    validation_evidence["executed"] = True
                    try:
                        completed = subprocess.run(
                            list(validation_classification.get("argv") or []),
                            cwd=sandbox_root,
                            capture_output=True,
                            text=True,
                            timeout=max(0.1, float(timeout_seconds)),
                            check=False,
                        )
                        validation_evidence.update({
                            "exit_code": int(completed.returncode),
                            "stdout": completed.stdout[-4096:],
                            "stderr": completed.stderr[-4096:],
                        })
                        validation_passed = completed.returncode == 0
                        if not validation_passed:
                            blocked_reasons.append("sandbox_mutation_validation_failed")
                    except subprocess.TimeoutExpired as exc:
                        validation_evidence.update({
                            "timed_out": True,
                            "stdout": str(exc.stdout or "")[-4096:],
                            "stderr": str(exc.stderr or "")[-4096:],
                        })
                        blocked_reasons.append("sandbox_mutation_validation_timeout")
                    sandbox_after_validation = _safe_stat_snapshot(sandbox_file, repo_root=sandbox_root)
                    validation_mutation_detected = sandbox_after_validation != sandbox_after
                    if validation_mutation_detected:
                        blocked_reasons.append("sandbox_validation_command_mutated_fixture")
            except Exception as exc:
                blocked_reasons.append("sandbox_mutation_execution_failed")
                validation_evidence["mutation_error"] = str(exc)
            finally:
                if sandbox_file is not None and original_bytes is not None:
                    rollback_attempted = True
                    try:
                        sandbox_file.write_bytes(original_bytes)
                        sandbox_after_rollback = _safe_stat_snapshot(sandbox_file, repo_root=sandbox_root)
                        rollback_succeeded = sandbox_after_rollback == sandbox_before
                        if not rollback_succeeded:
                            blocked_reasons.append("sandbox_rollback_evidence_mismatch")
                    except Exception as exc:
                        blocked_reasons.append("sandbox_rollback_failed")
                        validation_evidence["rollback_error"] = str(exc)
        finally:
            repo_after = _safe_stat_snapshot(source_path, repo_root=root)
            if repo_before != repo_after:
                blocked_reasons.append("repository_fixture_changed")
            shutil.rmtree(sandbox_dir, ignore_errors=True)
            sandbox_deleted = not Path(sandbox_dir).exists()
            if not sandbox_deleted:
                blocked_reasons.append("sandbox_workspace_cleanup_failed")
    elif source_path is not None:
        repo_after = _safe_stat_snapshot(source_path, repo_root=root)

    gates = [
        {"name": "correction_plan_schema_valid", "passed": source_schema_ok},
        {"name": "correction_plan_generated", "passed": source_plan_generated},
        {"name": "sandbox_fixture_allowlisted", "passed": bool(classification.get("allowed"))},
        {"name": "mutation_operation_allowlisted", "passed": operation == "replace_contents"},
        {"name": "before_hash_matches", "passed": bool(expected_before_sha and actual_before_sha == expected_before_sha)},
        {"name": "after_hash_matches", "passed": bool(expected_after_sha and actual_after_sha == expected_after_sha)},
        {"name": "mutation_result_verified", "passed": mutation_verified},
        {"name": "sandbox_validation_passed", "passed": validation_executed and validation_passed},
        {"name": "sandbox_validation_read_only", "passed": validation_executed and not validation_mutation_detected},
        {"name": "repository_fixture_unchanged", "passed": repo_before is not None and repo_before == repo_after},
        {"name": "rollback_attempted", "passed": rollback_attempted},
        {"name": "rollback_restored_before_snapshot", "passed": rollback_succeeded},
        {"name": "sandbox_workspace_deleted", "passed": sandbox_deleted},
    ]
    failed_gates = [str(item["name"]) for item in gates if not item.get("passed")]
    for gate_name in failed_gates:
        blocked_reasons.append(f"gate_failed:{gate_name}")
    ok = not blocked_reasons and all(bool(item.get("passed")) for item in gates)

    return {
        "ok": ok,
        "schema": LOOP_SANDBOX_MUTATION_VERIFICATION_SCHEMA,
        "schema_version": LOOP_SANDBOX_MUTATION_VERIFICATION_SCHEMA_VERSION,
        "action": "loop_sandbox_mutation_verification",
        "status": "sandbox_mutation_verified_and_rolled_back" if ok else "sandbox_mutation_verification_blocked",
        "mode": "sandbox_mutation_verification",
        "execution_mode": "local_temporary_sandbox_mutate_verify_rollback",
        "source_schema": correction_payload.get("schema"),
        "source_status": correction_payload.get("status"),
        "source_result_classification": correction_payload.get("source_result_classification"),
        "target_id": plan.get("target_id"),
        "target_path": plan.get("target_path"),
        "loop_id": plan.get("loop_id"),
        "executed_state": "VERIFY_STUB",
        "source_executed_state": correction_payload.get("executed_state"),
        "final_state": plan.get("final_state"),
        "decision": "stop_after_verified_sandbox_rollback_evidence" if ok else "stop_for_operator_review",
        "blocked_reasons": sorted(set(blocked_reasons)),
        "sandbox_mutation_request": {
            "operation": operation,
            "fixture_path": fixture_path,
            "allowlist_status": classification.get("status"),
            "allowlist_reason": classification.get("reason"),
            "expected_before_sha256": expected_before_sha or None,
            "actual_before_sha256": actual_before_sha,
            "expected_after_sha256": expected_after_sha or None,
            "actual_after_sha256": actual_after_sha,
        },
        "verification_gate": {
            "gate_count": len(gates),
            "passed_gate_count": sum(1 for item in gates if item.get("passed")),
            "failed_gate_count": len(failed_gates),
            "gates": gates,
        },
        "validation_evidence": validation_evidence,
        "rollback_evidence": {
            "attempted": rollback_attempted,
            "succeeded": rollback_succeeded,
            "sandbox_fixture_before": sandbox_before,
            "sandbox_fixture_after_rollback": sandbox_after_rollback,
        },
        "evidence": {
            "repository_fixture_before": repo_before,
            "repository_fixture_after": repo_after,
            "sandbox_fixture_before": sandbox_before,
            "sandbox_fixture_after_mutation": sandbox_after,
            "sandbox_fixture_after_validation": sandbox_after_validation,
            "sandbox_fixture_after_rollback": sandbox_after_rollback,
            "sandbox_workspace": sandbox_workspace,
            "sandbox_workspace_deleted_after_evidence": sandbox_deleted,
            "sandbox_relative_path": classification.get("path_argument") or fixture_path,
        },
        "summary": {
            "sandbox_mutation_performed": mutation_performed,
            "sandbox_mutation_verified": mutation_verified,
            "sandbox_validation_executed": validation_executed,
            "sandbox_validation_passed": validation_passed,
            "sandbox_rollback_attempted": rollback_attempted,
            "sandbox_rollback_succeeded": rollback_succeeded,
            "sandbox_final_state_restored": rollback_succeeded,
            "repository_file_mutated": bool(repo_before != repo_after) if repo_before is not None and repo_after is not None else False,
            "project_source_mutation_performed": False,
            "artifact_adoption_performed": False,
            "deployment_performed": False,
            "commands_executed": 1 if validation_executed else 0,
            "transient_sandbox_files_mutated": 1 if mutation_performed else 0,
        },
        "dry_run": False,
        "side_effects_performed": mutation_performed,
        "safety": {
            "side_effects_performed": mutation_performed,
            "mutation_allowed": True,
            "sandbox_file_mutation_performed": mutation_performed,
            "sandbox_mutation_verified": mutation_verified,
            "sandbox_final_state_restored": rollback_succeeded,
            "repository_file_mutation_performed": bool(repo_before != repo_after) if repo_before is not None and repo_after is not None else False,
            "commands_executed": validation_executed,
            "deployment_performed": False,
            "kubernetes_mutation_performed": False,
            "project_source_mutation_performed": False,
            "artifact_adoption_performed": False,
            "chatgpt_project_deletion_performed": False,
            "correction_plan_required": True,
            "correction_plan_source_required": True,
            "sandbox_only": True,
            "rollback_required": True,
            "stop_after_evidence": True,
        },
        "operator_instruction": "Sandbox-only mutation verification complete only when the copied fixture matches the declared after hash, the allowlisted sandbox validation passes without mutation, rollback restores the exact before snapshot, the repository fixture remains unchanged, and the temporary workspace is deleted. Any failed gate stops for operator review. No deployment, Project Source mutation, artifact adoption, or ChatGPT Project deletion is performed.",
    }


def _sandbox_promotion_snapshot(snapshot: Any) -> dict[str, Any] | None:
    if not isinstance(snapshot, dict):
        return None
    return {
        "path": snapshot.get("path"),
        "exists": snapshot.get("exists"),
        "is_file": snapshot.get("is_file"),
        "size": snapshot.get("size"),
        "sha256": snapshot.get("sha256"),
    }


def _sandbox_promotion_evidence_assessment(payload: dict[str, Any]) -> dict[str, Any]:
    request = payload.get("sandbox_mutation_request") if isinstance(payload.get("sandbox_mutation_request"), dict) else {}
    gate = payload.get("verification_gate") if isinstance(payload.get("verification_gate"), dict) else {}
    validation = payload.get("validation_evidence") if isinstance(payload.get("validation_evidence"), dict) else {}
    classification = validation.get("classification") if isinstance(validation.get("classification"), dict) else {}
    rollback = payload.get("rollback_evidence") if isinstance(payload.get("rollback_evidence"), dict) else {}
    evidence = payload.get("evidence") if isinstance(payload.get("evidence"), dict) else {}
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    safety = payload.get("safety") if isinstance(payload.get("safety"), dict) else {}
    gates = gate.get("gates") if isinstance(gate.get("gates"), list) else []
    observed_gates = {
        str(item.get("name")): item.get("passed") is True
        for item in gates
        if isinstance(item, dict) and item.get("name")
    }

    checks = {
        "schema_exact": payload.get("schema") == LOOP_SANDBOX_MUTATION_VERIFICATION_SCHEMA,
        "schema_version_exact": payload.get("schema_version") == LOOP_SANDBOX_MUTATION_VERIFICATION_SCHEMA_VERSION,
        "payload_ok": payload.get("ok") is True,
        "terminal_status_exact": payload.get("status") == "sandbox_mutation_verified_and_rolled_back",
        "terminal_decision_exact": payload.get("decision") == "stop_after_verified_sandbox_rollback_evidence",
        "blocked_reasons_empty": payload.get("blocked_reasons") == [],
        "target_id_present": isinstance(payload.get("target_id"), str) and bool(str(payload.get("target_id")).strip()),
        "operation_exact": request.get("operation") == "replace_contents",
        "fixture_path_present": isinstance(request.get("fixture_path"), str) and bool(str(request.get("fixture_path")).strip()),
        "before_hash_exact": bool(request.get("expected_before_sha256")) and request.get("expected_before_sha256") == request.get("actual_before_sha256"),
        "after_hash_exact": bool(request.get("expected_after_sha256")) and request.get("expected_after_sha256") == request.get("actual_after_sha256"),
        "gate_count_exact": gate.get("gate_count") == len(SANDBOX_PROMOTION_REQUIRED_GATES),
        "passed_gate_count_exact": gate.get("passed_gate_count") == len(SANDBOX_PROMOTION_REQUIRED_GATES),
        "failed_gate_count_zero": gate.get("failed_gate_count") == 0,
        "gate_names_exact": set(observed_gates) == set(SANDBOX_PROMOTION_REQUIRED_GATES),
        "all_required_gates_passed": all(observed_gates.get(name) is True for name in SANDBOX_PROMOTION_REQUIRED_GATES),
        "validation_allowlisted": classification.get("allowed") is True and classification.get("status") == "allowlisted_sandbox_json_validation",
        "validation_executed": validation.get("executed") is True,
        "validation_exit_zero": validation.get("exit_code") == 0,
        "validation_not_timed_out": validation.get("timed_out") is False,
        "rollback_attempted": rollback.get("attempted") is True,
        "rollback_succeeded": rollback.get("succeeded") is True,
        "repository_snapshot_equal": evidence.get("repository_fixture_before") == evidence.get("repository_fixture_after"),
        "sandbox_mutation_changed_snapshot": evidence.get("sandbox_fixture_before") != evidence.get("sandbox_fixture_after_mutation"),
        "sandbox_validation_read_only": evidence.get("sandbox_fixture_after_mutation") == evidence.get("sandbox_fixture_after_validation"),
        "sandbox_rollback_snapshot_equal": evidence.get("sandbox_fixture_before") == evidence.get("sandbox_fixture_after_rollback"),
        "workspace_deleted": evidence.get("sandbox_workspace_deleted_after_evidence") is True,
        "summary_mutation_verified": summary.get("sandbox_mutation_verified") is True,
        "summary_validation_passed": summary.get("sandbox_validation_passed") is True,
        "summary_rollback_succeeded": summary.get("sandbox_rollback_succeeded") is True,
        "summary_repository_unchanged": summary.get("repository_file_mutated") is False,
        "single_validation_command": summary.get("commands_executed") == 1,
        "single_transient_fixture_mutation": summary.get("transient_sandbox_files_mutated") == 1,
        "sandbox_only": safety.get("sandbox_only") is True,
        "rollback_required": safety.get("rollback_required") is True,
        "stop_after_evidence": safety.get("stop_after_evidence") is True,
        "repository_mutation_forbidden": safety.get("repository_file_mutation_performed") is False,
        "deployment_forbidden": safety.get("deployment_performed") is False,
        "kubernetes_mutation_forbidden": safety.get("kubernetes_mutation_performed") is False,
        "project_source_mutation_forbidden": safety.get("project_source_mutation_performed") is False,
        "artifact_adoption_forbidden": safety.get("artifact_adoption_performed") is False,
        "project_deletion_forbidden": safety.get("chatgpt_project_deletion_performed") is False,
    }
    failed_checks = sorted(name for name, passed in checks.items() if not passed)
    canonical = {
        "schema": payload.get("schema"),
        "schema_version": payload.get("schema_version"),
        "status": payload.get("status"),
        "decision": payload.get("decision"),
        "target_id": payload.get("target_id"),
        "source_schema": payload.get("source_schema"),
        "source_status": payload.get("source_status"),
        "source_result_classification": payload.get("source_result_classification"),
        "sandbox_mutation_request": {
            "operation": request.get("operation"),
            "fixture_path": request.get("fixture_path"),
            "allowlist_status": request.get("allowlist_status"),
            "expected_before_sha256": request.get("expected_before_sha256"),
            "actual_before_sha256": request.get("actual_before_sha256"),
            "expected_after_sha256": request.get("expected_after_sha256"),
            "actual_after_sha256": request.get("actual_after_sha256"),
        },
        "verification_gates": [
            {"name": name, "passed": observed_gates.get(name) is True}
            for name in SANDBOX_PROMOTION_REQUIRED_GATES
        ],
        "validation": {
            "command": validation.get("command"),
            "classification_status": classification.get("status"),
            "argv": classification.get("argv"),
            "executed": validation.get("executed"),
            "exit_code": validation.get("exit_code"),
            "timed_out": validation.get("timed_out"),
            "stdout_sha256": hashlib.sha256(str(validation.get("stdout") or "").encode("utf-8")).hexdigest(),
            "stderr_sha256": hashlib.sha256(str(validation.get("stderr") or "").encode("utf-8")).hexdigest(),
        },
        "snapshots": {
            "repository_before": _sandbox_promotion_snapshot(evidence.get("repository_fixture_before")),
            "repository_after": _sandbox_promotion_snapshot(evidence.get("repository_fixture_after")),
            "sandbox_before": _sandbox_promotion_snapshot(evidence.get("sandbox_fixture_before")),
            "sandbox_after_mutation": _sandbox_promotion_snapshot(evidence.get("sandbox_fixture_after_mutation")),
            "sandbox_after_validation": _sandbox_promotion_snapshot(evidence.get("sandbox_fixture_after_validation")),
            "sandbox_after_rollback": _sandbox_promotion_snapshot(evidence.get("sandbox_fixture_after_rollback")),
        },
        "summary": {
            key: summary.get(key)
            for key in (
                "sandbox_mutation_performed",
                "sandbox_mutation_verified",
                "sandbox_validation_executed",
                "sandbox_validation_passed",
                "sandbox_rollback_attempted",
                "sandbox_rollback_succeeded",
                "sandbox_final_state_restored",
                "repository_file_mutated",
                "project_source_mutation_performed",
                "artifact_adoption_performed",
                "deployment_performed",
                "commands_executed",
                "transient_sandbox_files_mutated",
            )
        },
        "safety": {
            key: safety.get(key)
            for key in (
                "repository_file_mutation_performed",
                "deployment_performed",
                "kubernetes_mutation_performed",
                "project_source_mutation_performed",
                "artifact_adoption_performed",
                "chatgpt_project_deletion_performed",
                "sandbox_only",
                "rollback_required",
                "stop_after_evidence",
            )
        },
    }
    canonical_json = json.dumps(canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return {
        "complete": not failed_checks,
        "failed_checks": failed_checks,
        "checks": checks,
        "canonical_evidence": canonical,
        "determinism_fingerprint_sha256": hashlib.sha256(canonical_json.encode("utf-8")).hexdigest(),
        "sandbox_workspace": evidence.get("sandbox_workspace"),
    }


def build_loop_sandbox_correction_promotion_readiness_payload(
    evidence_payloads: list[dict[str, Any]],
    *,
    required_runs: int = 3,
    execution_blockers: list[str] | None = None,
    target_path: str | None = None,
) -> dict[str, Any]:
    blockers = sorted(set(str(item) for item in (execution_blockers or []) if str(item).strip()))
    run_assessments = [
        {"run_index": index, **_sandbox_promotion_evidence_assessment(payload)}
        for index, payload in enumerate(evidence_payloads, start=1)
        if isinstance(payload, dict)
    ]
    fingerprints = [str(item.get("determinism_fingerprint_sha256")) for item in run_assessments]
    workspace_paths = [str(item.get("sandbox_workspace")) for item in run_assessments if item.get("sandbox_workspace")]
    evidence_count_exact = len(run_assessments) == required_runs
    all_runs_complete = evidence_count_exact and all(item.get("complete") is True for item in run_assessments)
    deterministic = all_runs_complete and len(set(fingerprints)) == 1
    independent_workspaces = evidence_count_exact and len(workspace_paths) == required_runs and len(set(workspace_paths)) == required_runs

    readiness_checks = {
        "required_run_count_valid": 2 <= required_runs <= 5,
        "evidence_run_count_exact": evidence_count_exact,
        "all_runs_complete": all_runs_complete,
        "determinism_fingerprint_equal": deterministic,
        "independent_temporary_workspaces": independent_workspaces,
        "no_execution_blockers": not blockers,
    }
    failed_readiness_checks = sorted(name for name, passed in readiness_checks.items() if not passed)
    if blockers or not readiness_checks["required_run_count_valid"] or not evidence_count_exact:
        status = "blocked"
        decision = "stop_for_operator_review"
    elif all_runs_complete and deterministic and independent_workspaces:
        status = "ready"
        decision = "ready_for_explicit_v0.1.106_go_no_go_decision"
    else:
        status = "not_ready"
        decision = "remain_sandbox_only_and_collect_or_repair_evidence"

    return {
        "ok": status == "ready",
        "schema": LOOP_SANDBOX_CORRECTION_PROMOTION_READINESS_SCHEMA,
        "schema_version": LOOP_SANDBOX_CORRECTION_PROMOTION_READINESS_SCHEMA_VERSION,
        "action": "sandbox_correction_promotion_readiness_check",
        "status": status,
        "decision": decision,
        "target_path": target_path,
        "required_run_count": required_runs,
        "observed_run_count": len(run_assessments),
        "readiness_checks": readiness_checks,
        "failed_readiness_checks": failed_readiness_checks,
        "execution_blockers": blockers,
        "determinism": {
            "deterministic": deterministic,
            "fingerprints": fingerprints,
            "unique_fingerprint_count": len(set(fingerprints)),
            "independent_temporary_workspaces": independent_workspaces,
            "workspace_count": len(workspace_paths),
            "unique_workspace_count": len(set(workspace_paths)),
        },
        "evidence_runs": run_assessments,
        "authority": {
            "assessment_only": True,
            "promotion_decision_recorded": False,
            "broader_mutation_authority_granted": False,
            "repository_mutation_authority_granted": False,
            "deployment_authority_granted": False,
            "kubernetes_mutation_authority_granted": False,
            "project_source_mutation_authority_granted": False,
            "artifact_adoption_authority_granted": False,
            "chatgpt_project_deletion_authority_granted": False,
        },
        "safety": {
            "sandbox_only": True,
            "existing_sandbox_contract_reused": True,
            "new_mutation_operations_enabled": False,
            "repository_files_mutated": False,
            "deployment_performed": False,
            "project_source_mutation_performed": False,
            "artifact_adoption_performed": False,
            "chatgpt_project_deletion_performed": False,
        },
        "next_slice": {
            "version": "v0.1.106",
            "slice": "Controlled correction promotion decision record",
            "permitted_only_when_status_ready": True,
        },
        "operator_instruction": "This readiness result assesses deterministic completeness of repeated sandbox-only evidence. Even status ready grants no broader correction, repository, deployment, Project Source, artifact-adoption, or Project-deletion authority. Only v0.1.106 may record an explicit GO/NO-GO promotion decision.",
    }


def _promotion_readiness_repository_markers_present(root: Path) -> bool:
    for relative_path, kind in PROMOTION_READINESS_REPOSITORY_MARKERS:
        candidate = root / relative_path
        if kind == "file" and not candidate.is_file():
            return False
        if kind == "dir" and not candidate.is_dir():
            return False
    return True


def _path_is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _resolve_promotion_readiness_repository(
    target_path: str | Path,
    *,
    repo_root: str | Path | None,
) -> tuple[Path, Path | None, list[str]]:
    explicit_root = Path(repo_root).expanduser().resolve() if repo_root is not None else None
    target = Path(target_path).expanduser()
    if target.is_absolute():
        resolved_target = target.resolve()
    elif explicit_root is not None:
        resolved_target = (explicit_root / target).resolve()
    else:
        resolved_target = (Path.cwd() / target).resolve()

    if explicit_root is not None:
        if not _promotion_readiness_repository_markers_present(explicit_root):
            return resolved_target, None, ["explicit_repo_root_missing_authoritative_markers"]
        if not _path_is_within(resolved_target, explicit_root):
            return resolved_target, None, ["target_outside_repository_root"]
        return resolved_target, explicit_root, []

    candidates: list[Path] = []
    for candidate in (resolved_target.parent, *resolved_target.parents):
        candidate = candidate.resolve()
        if candidate in candidates:
            continue
        if _promotion_readiness_repository_markers_present(candidate):
            candidates.append(candidate)
    if not candidates:
        return resolved_target, None, ["repository_root_not_found_from_target"]
    if len(candidates) != 1:
        rendered = "|".join(str(item) for item in sorted(candidates, key=str))
        return resolved_target, None, [f"repository_root_ambiguous:{rendered}"]
    root = candidates[0]
    if not _path_is_within(resolved_target, root):
        return resolved_target, None, ["target_outside_repository_root"]
    return resolved_target, root, []


def assess_loop_sandbox_correction_promotion_readiness(
    target_path: str | Path,
    *,
    repo_root: str | Path | None = None,
    required_runs: int = 3,
    timeout_seconds: float = 15.0,
) -> dict[str, Any]:
    resolved_target, root, resolution_blockers = _resolve_promotion_readiness_repository(
        target_path,
        repo_root=repo_root,
    )
    if not 2 <= required_runs <= 5:
        return build_loop_sandbox_correction_promotion_readiness_payload(
            [],
            required_runs=required_runs,
            execution_blockers=["required_run_count_must_be_between_2_and_5"],
            target_path=str(resolved_target),
        )
    if resolution_blockers or root is None:
        return build_loop_sandbox_correction_promotion_readiness_payload(
            [],
            required_runs=required_runs,
            execution_blockers=resolution_blockers or ["repository_root_resolution_failed"],
            target_path=str(resolved_target),
        )
    initial_plan = plan_loop_target_file(resolved_target, execute_stubbed=True)
    if not initial_plan.get("ok"):
        return build_loop_sandbox_correction_promotion_readiness_payload(
            [],
            required_runs=required_runs,
            execution_blockers=[f"target_plan_invalid:{initial_plan.get('error') or initial_plan.get('status')}"],
            target_path=str(resolved_target),
        )

    payloads: list[dict[str, Any]] = []
    blockers: list[str] = []
    for run_index in range(1, required_runs + 1):
        try:
            plan = plan_loop_target_file(resolved_target, execute_stubbed=True)
            execution = build_loop_read_only_execution_payload(plan, repo_root=root)
            gate = build_loop_read_only_evidence_gate(build_loop_read_only_evidence_report(execution))
            command = build_loop_read_only_command_execution_payload(execution, gate, repo_root=root, timeout_seconds=timeout_seconds)
            diagnosis = build_loop_read_only_command_diagnosis_payload(command)
            correction = build_loop_read_only_correction_plan_payload(diagnosis)
            sandbox = build_loop_sandbox_mutation_verification_payload(
                plan=plan,
                correction_payload=correction,
                repo_root=root,
                timeout_seconds=timeout_seconds,
            )
            payloads.append(sandbox)
        except Exception as exc:
            blockers.append(f"run_{run_index}_execution_error:{type(exc).__name__}:{exc}")
            break
    return build_loop_sandbox_correction_promotion_readiness_payload(
        payloads,
        required_runs=required_runs,
        execution_blockers=blockers,
        target_path=str(resolved_target),
    )


def render_loop_sandbox_correction_promotion_readiness_text(payload: dict[str, Any]) -> str:
    lines = [
        "Promptbranch sandbox correction promotion readiness",
        f"status: {payload.get('status')}",
        f"decision: {payload.get('decision')}",
        f"evidence runs: {payload.get('observed_run_count')}/{payload.get('required_run_count')}",
        f"deterministic: {bool((payload.get('determinism') or {}).get('deterministic'))}",
        "broader mutation authority granted: false",
        "promotion decision recorded: false",
    ]
    failed = payload.get("failed_readiness_checks") or []
    if failed:
        lines.append("failed readiness checks: " + ", ".join(str(item) for item in failed))
    blockers = payload.get("execution_blockers") or []
    if blockers:
        lines.append("execution blockers: " + ", ".join(str(item) for item in blockers))
    lines.append(str(payload.get("operator_instruction") or ""))
    return "\n".join(lines) + "\n"


PROMOTION_DECISION_MANDATORY_EVIDENCE = (
    "readiness_schema_exact",
    "readiness_schema_version_exact",
    "readiness_ok_true",
    "readiness_status_ready",
    "readiness_decision_exact",
    "target_path_present",
    "required_run_count_exact_three",
    "observed_run_count_exact_three",
    "readiness_checks_all_true",
    "failed_readiness_checks_empty",
    "execution_blockers_empty",
    "determinism_true",
    "unique_fingerprint_count_one",
    "workspace_count_exact_three",
    "unique_workspace_count_exact_three",
    "independent_temporary_workspaces_true",
    "evidence_run_count_exact_three",
    "every_evidence_run_complete",
    "every_evidence_run_failed_checks_empty",
    "evidence_fingerprint_singleton",
    "readiness_assessment_only_true",
    "promotion_not_previously_recorded",
    "no_broader_mutation_authority",
    "no_specific_mutation_authority",
    "sandbox_only_true",
    "existing_sandbox_contract_reused_true",
    "no_new_mutation_operations",
    "no_repository_mutation",
    "no_deployment",
    "no_project_source_mutation",
    "no_artifact_adoption",
    "no_project_deletion",
)


def build_loop_sandbox_correction_promotion_decision_payload(
    readiness_payload: dict[str, Any],
) -> dict[str, Any]:
    readiness = readiness_payload if isinstance(readiness_payload, dict) else {}
    readiness_checks = readiness.get("readiness_checks") if isinstance(readiness.get("readiness_checks"), dict) else {}
    determinism = readiness.get("determinism") if isinstance(readiness.get("determinism"), dict) else {}
    authority = readiness.get("authority") if isinstance(readiness.get("authority"), dict) else {}
    safety = readiness.get("safety") if isinstance(readiness.get("safety"), dict) else {}
    evidence_runs = readiness.get("evidence_runs") if isinstance(readiness.get("evidence_runs"), list) else []
    fingerprints = [
        str(item.get("determinism_fingerprint_sha256"))
        for item in evidence_runs
        if isinstance(item, dict) and item.get("determinism_fingerprint_sha256")
    ]
    unique_fingerprints = sorted(set(fingerprints))
    specific_authority_fields = (
        "repository_mutation_authority_granted",
        "deployment_authority_granted",
        "kubernetes_mutation_authority_granted",
        "project_source_mutation_authority_granted",
        "artifact_adoption_authority_granted",
        "chatgpt_project_deletion_authority_granted",
    )
    checks = {
        "readiness_schema_exact": readiness.get("schema") == LOOP_SANDBOX_CORRECTION_PROMOTION_READINESS_SCHEMA,
        "readiness_schema_version_exact": readiness.get("schema_version") == LOOP_SANDBOX_CORRECTION_PROMOTION_READINESS_SCHEMA_VERSION,
        "readiness_ok_true": readiness.get("ok") is True,
        "readiness_status_ready": readiness.get("status") == "ready",
        "readiness_decision_exact": readiness.get("decision") == "ready_for_explicit_v0.1.106_go_no_go_decision",
        "target_path_present": isinstance(readiness.get("target_path"), str) and bool(str(readiness.get("target_path")).strip()),
        "required_run_count_exact_three": readiness.get("required_run_count") == 3,
        "observed_run_count_exact_three": readiness.get("observed_run_count") == 3,
        "readiness_checks_all_true": bool(readiness_checks) and all(value is True for value in readiness_checks.values()),
        "failed_readiness_checks_empty": readiness.get("failed_readiness_checks") == [],
        "execution_blockers_empty": readiness.get("execution_blockers") == [],
        "determinism_true": determinism.get("deterministic") is True,
        "unique_fingerprint_count_one": determinism.get("unique_fingerprint_count") == 1,
        "workspace_count_exact_three": determinism.get("workspace_count") == 3,
        "unique_workspace_count_exact_three": determinism.get("unique_workspace_count") == 3,
        "independent_temporary_workspaces_true": determinism.get("independent_temporary_workspaces") is True,
        "evidence_run_count_exact_three": len(evidence_runs) == 3,
        "every_evidence_run_complete": len(evidence_runs) == 3 and all(isinstance(item, dict) and item.get("complete") is True for item in evidence_runs),
        "every_evidence_run_failed_checks_empty": len(evidence_runs) == 3 and all(isinstance(item, dict) and item.get("failed_checks") == [] for item in evidence_runs),
        "evidence_fingerprint_singleton": len(fingerprints) == 3 and len(unique_fingerprints) == 1,
        "readiness_assessment_only_true": authority.get("assessment_only") is True,
        "promotion_not_previously_recorded": authority.get("promotion_decision_recorded") is False,
        "no_broader_mutation_authority": authority.get("broader_mutation_authority_granted") is False,
        "no_specific_mutation_authority": all(authority.get(name) is False for name in specific_authority_fields),
        "sandbox_only_true": safety.get("sandbox_only") is True,
        "existing_sandbox_contract_reused_true": safety.get("existing_sandbox_contract_reused") is True,
        "no_new_mutation_operations": safety.get("new_mutation_operations_enabled") is False,
        "no_repository_mutation": safety.get("repository_files_mutated") is False,
        "no_deployment": safety.get("deployment_performed") is False,
        "no_project_source_mutation": safety.get("project_source_mutation_performed") is False,
        "no_artifact_adoption": safety.get("artifact_adoption_performed") is False,
        "no_project_deletion": safety.get("chatgpt_project_deletion_performed") is False,
    }
    failed_checks = [name for name in PROMOTION_DECISION_MANDATORY_EVIDENCE if checks.get(name) is not True]
    go = not failed_checks
    decision = "go" if go else "no_go"
    status = "promotion_go_recorded" if go else "promotion_no_go_recorded"
    stop_conditions = [
        {"name": name, "triggered": checks.get(name) is not True}
        for name in PROMOTION_DECISION_MANDATORY_EVIDENCE
    ]
    fingerprint = unique_fingerprints[0] if len(unique_fingerprints) == 1 else None
    return {
        "ok": True,
        "schema": LOOP_SANDBOX_CORRECTION_PROMOTION_DECISION_SCHEMA,
        "schema_version": LOOP_SANDBOX_CORRECTION_PROMOTION_DECISION_SCHEMA_VERSION,
        "action": "record_sandbox_correction_promotion_decision",
        "decision_version": "v0.1.106",
        "readiness_contract_version": "v0.1.105.1",
        "decision_record_id": f"v0.1.106:sandbox-correction-promotion:{fingerprint or 'no-fingerprint'}",
        "status": status,
        "decision": decision,
        "decision_scope": "controlled_execution_envelope_design_only" if go else "remain_sandbox_only",
        "source_readiness": {
            "schema": readiness.get("schema"),
            "schema_version": readiness.get("schema_version"),
            "status": readiness.get("status"),
            "decision": readiness.get("decision"),
            "target_path": readiness.get("target_path"),
            "required_run_count": readiness.get("required_run_count"),
            "observed_run_count": readiness.get("observed_run_count"),
            "failed_readiness_checks": readiness.get("failed_readiness_checks"),
            "execution_blockers": readiness.get("execution_blockers"),
            "determinism_fingerprint_sha256": fingerprint,
            "unique_fingerprint_count": determinism.get("unique_fingerprint_count"),
            "workspace_count": determinism.get("workspace_count"),
            "unique_workspace_count": determinism.get("unique_workspace_count"),
        },
        "mandatory_evidence": {
            "check_count": len(PROMOTION_DECISION_MANDATORY_EVIDENCE),
            "passed_check_count": sum(1 for name in PROMOTION_DECISION_MANDATORY_EVIDENCE if checks.get(name) is True),
            "failed_check_count": len(failed_checks),
            "checks": [{"name": name, "passed": checks.get(name) is True} for name in PROMOTION_DECISION_MANDATORY_EVIDENCE],
            "failed_checks": failed_checks,
        },
        "stop_conditions": stop_conditions,
        "triggered_stop_conditions": failed_checks,
        "authority": {
            "promotion_decision_recorded": True,
            "v0_1_107_execution_envelope_design_authorized": go,
            "correction_execution_authority_granted": False,
            "disposable_repository_mutation_authority_granted": False,
            "real_repository_mutation_authority_granted": False,
            "deployment_authority_granted": False,
            "kubernetes_mutation_authority_granted": False,
            "project_source_mutation_authority_granted": False,
            "artifact_adoption_authority_granted": False,
            "chatgpt_project_deletion_authority_granted": False,
        },
        "safety": {
            "decision_record_only": True,
            "sandbox_evidence_reused": True,
            "new_mutation_operations_enabled": False,
            "repository_files_mutated": False,
            "deployment_performed": False,
            "kubernetes_mutation_performed": False,
            "project_source_mutation_performed": False,
            "artifact_adoption_performed": False,
            "chatgpt_project_deletion_performed": False,
        },
        "next_slice": {
            "version": "v0.1.107",
            "slice": "Controlled correction execution envelope design",
            "permitted": go,
            "scope": "design_only_no_correction_execution",
        },
        "operator_instruction": (
            "GO records that the repeated sandbox evidence is sufficient to proceed only to v0.1.107 controlled execution-envelope design. "
            "It grants no correction execution, repository mutation, deployment, Kubernetes, Project Source, artifact-adoption, or Project-deletion authority."
            if go
            else
            "NO-GO records that one or more mandatory evidence or safety conditions failed. Remain sandbox-only and do not design or execute a broader correction envelope until a later explicit decision record passes every stop condition."
        ),
    }


def assess_loop_sandbox_correction_promotion_decision(
    target_path: str | Path,
    *,
    repo_root: str | Path | None = None,
    required_runs: int = 3,
    timeout_seconds: float = 15.0,
) -> dict[str, Any]:
    readiness = assess_loop_sandbox_correction_promotion_readiness(
        target_path,
        repo_root=repo_root,
        required_runs=required_runs,
        timeout_seconds=timeout_seconds,
    )
    return build_loop_sandbox_correction_promotion_decision_payload(readiness)


def render_loop_sandbox_correction_promotion_decision_text(payload: dict[str, Any]) -> str:
    source = payload.get("source_readiness") if isinstance(payload.get("source_readiness"), dict) else {}
    evidence = payload.get("mandatory_evidence") if isinstance(payload.get("mandatory_evidence"), dict) else {}
    lines = [
        "Promptbranch controlled correction promotion decision",
        f"decision: {str(payload.get('decision') or '').upper().replace('_', '-')}",
        f"status: {payload.get('status')}",
        f"readiness: {source.get('status')}",
        f"evidence runs: {source.get('observed_run_count')}/{source.get('required_run_count')}",
        f"mandatory evidence: {evidence.get('passed_check_count')}/{evidence.get('check_count')}",
        f"v0.1.107 design authorized: {bool((payload.get('authority') or {}).get('v0_1_107_execution_envelope_design_authorized'))}",
        "correction execution authority granted: false",
    ]
    triggered = payload.get("triggered_stop_conditions") or []
    if triggered:
        lines.append("triggered stop conditions: " + ", ".join(str(item) for item in triggered))
    lines.append(str(payload.get("operator_instruction") or ""))
    return "\n".join(lines) + "\n"



def _is_sha256_hex(value: Any) -> bool:
    text = str(value or "")
    return len(text) == 64 and all(ch in "0123456789abcdef" for ch in text)


def _blocked_execution_envelope_design_payload(
    *,
    target_path: str,
    blockers: list[str],
    checks: dict[str, bool] | None = None,
) -> dict[str, Any]:
    observed_checks = checks or {}
    failed_checks = sorted(name for name, passed in observed_checks.items() if passed is not True)
    return {
        "ok": False,
        "schema": LOOP_CONTROLLED_CORRECTION_EXECUTION_ENVELOPE_DESIGN_SCHEMA,
        "schema_version": LOOP_CONTROLLED_CORRECTION_EXECUTION_ENVELOPE_DESIGN_SCHEMA_VERSION,
        "action": "design_controlled_correction_execution_envelope",
        "design_version": "v0.1.107",
        "status": "execution_envelope_design_blocked",
        "decision": "stop_without_execution",
        "target_path": target_path,
        "design_checks": observed_checks,
        "failed_design_checks": failed_checks,
        "execution_blockers": sorted(set(str(item) for item in blockers if str(item).strip())),
        "execution_envelope": None,
        "determinism": {"canonical_design_sha256": None},
        "authority": {
            "design_record_emitted": False,
            "future_envelope_validation_authority_granted": False,
            "correction_execution_authority_granted": False,
            "disposable_repository_mutation_authority_granted": False,
            "real_repository_mutation_authority_granted": False,
            "deployment_authority_granted": False,
            "kubernetes_mutation_authority_granted": False,
            "project_source_mutation_authority_granted": False,
            "artifact_adoption_authority_granted": False,
            "chatgpt_project_deletion_authority_granted": False,
        },
        "safety": {
            "design_only": True,
            "commands_executed": 0,
            "files_mutated": False,
            "workspace_created": False,
            "repository_files_mutated": False,
            "deployment_performed": False,
            "kubernetes_mutation_performed": False,
            "project_source_mutation_performed": False,
            "artifact_adoption_performed": False,
            "chatgpt_project_deletion_performed": False,
        },
        "next_slice": {
            "version": "v0.1.108",
            "slice": "Controlled correction execution envelope validation gate",
            "permitted": False,
            "scope": "validation_only_no_correction_execution",
        },
        "operator_instruction": "Execution-envelope design is blocked. No command was executed, no workspace was created, and no file or repository was mutated.",
    }


def design_loop_controlled_correction_execution_envelope(
    target_path: str | Path,
    *,
    repo_root: str | Path | None = None,
    validation_timeout_seconds: float = 15.0,
    total_timeout_seconds: float = 60.0,
) -> dict[str, Any]:
    """Design a deterministic future correction envelope without executing it."""
    resolved_target, root, root_blockers = _resolve_promotion_readiness_repository(
        target_path,
        repo_root=repo_root,
    )
    if root_blockers or root is None:
        return _blocked_execution_envelope_design_payload(
            target_path=str(resolved_target),
            blockers=root_blockers or ["repository_root_resolution_failed"],
        )
    try:
        target_rel = resolved_target.relative_to(root).as_posix()
    except ValueError:
        return _blocked_execution_envelope_design_payload(
            target_path=str(resolved_target),
            blockers=["target_outside_repository_root"],
        )
    target, raw, target_error = load_loop_target(resolved_target)
    if target_error or target is None or not isinstance(raw, dict):
        return _blocked_execution_envelope_design_payload(
            target_path=target_rel,
            blockers=[f"target_invalid:{target_error or 'unknown'}"],
        )
    decision_path = root / CONTROLLED_CORRECTION_PROMOTION_DECISION_RECORD
    try:
        decision = json.loads(decision_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return _blocked_execution_envelope_design_payload(
            target_path=target_rel,
            blockers=[f"promotion_decision_record_unavailable:{type(exc).__name__}:{exc}"],
        )
    if not isinstance(decision, dict):
        return _blocked_execution_envelope_design_payload(
            target_path=target_rel,
            blockers=["promotion_decision_record_not_object"],
        )

    decision_authority = decision.get("authority") if isinstance(decision.get("authority"), dict) else {}
    decision_next = decision.get("next_slice") if isinstance(decision.get("next_slice"), dict) else {}
    decision_source = decision.get("source_readiness") if isinstance(decision.get("source_readiness"), dict) else {}
    sandbox = raw.get("sandbox_mutation") if isinstance(raw.get("sandbox_mutation"), dict) else {}
    fixture_path = str(sandbox.get("fixture_path") or "").replace("\\", "/").strip("/")
    operation = str(sandbox.get("operation") or "")
    replacement_contents = sandbox.get("replacement_contents")
    expected_before = str(sandbox.get("expected_before_sha256") or "")
    expected_after = str(sandbox.get("expected_after_sha256") or "")
    fixture_classification = _classify_sandbox_fixture_path(
        fixture_path,
        repo_root=root,
        allowed_paths=list(target.allowed_paths),
    )
    commands = list(target.validation_commands)
    validation_command = commands[0] if len(commands) == 1 else ""
    validation_classification = _classify_sandbox_validation_command(
        validation_command,
        fixture_rel_path=fixture_path,
    ) if validation_command else {"allowed": False, "status": "validation_command_count_invalid", "argv": []}
    fixture_abs = (root / fixture_path).resolve() if fixture_path else root
    actual_before = hashlib.sha256(fixture_abs.read_bytes()).hexdigest() if fixture_abs.is_file() else None
    replacement_bytes = replacement_contents.encode("utf-8") if isinstance(replacement_contents, str) else b""
    replacement_sha = hashlib.sha256(replacement_bytes).hexdigest() if replacement_bytes else None

    checks = {
        "promotion_decision_schema_exact": decision.get("schema") == LOOP_SANDBOX_CORRECTION_PROMOTION_DECISION_SCHEMA,
        "promotion_decision_version_exact": decision.get("decision_version") == "v0.1.106",
        "promotion_decision_go": decision.get("status") == "promotion_go_recorded" and decision.get("decision") == "go",
        "promotion_decision_design_scope_exact": decision.get("decision_scope") == "controlled_execution_envelope_design_only",
        "v0_1_107_design_authorized": decision_authority.get("v0_1_107_execution_envelope_design_authorized") is True,
        "promotion_decision_execution_authority_false": decision_authority.get("correction_execution_authority_granted") is False,
        "promotion_decision_broader_authority_false": all(
            decision_authority.get(name) is False
            for name in (
                "disposable_repository_mutation_authority_granted",
                "real_repository_mutation_authority_granted",
                "deployment_authority_granted",
                "kubernetes_mutation_authority_granted",
                "project_source_mutation_authority_granted",
                "artifact_adoption_authority_granted",
                "chatgpt_project_deletion_authority_granted",
            )
        ),
        "promotion_decision_next_slice_exact": decision_next.get("version") == "v0.1.107" and decision_next.get("scope") == "design_only_no_correction_execution" and decision_next.get("permitted") is True,
        "promotion_readiness_fingerprint_present": _is_sha256_hex(decision_source.get("determinism_fingerprint_sha256")),
        "target_schema_valid": target.raw.get("schema", LOOP_TARGET_SCHEMA) == LOOP_TARGET_SCHEMA,
        "target_contained_in_repository": _path_is_within(resolved_target, root),
        "deployment_not_requested_or_allowed": target.deployment_requested is False and target.deployment_allowed is False,
        "single_iteration_limit": target.max_iterations == 1,
        "single_mutable_fixture": fixture_classification.get("allowed") is True and fixture_path in target.allowed_paths,
        "operation_exact_replace_contents": operation == "replace_contents",
        "replacement_contents_present": isinstance(replacement_contents, str) and bool(replacement_contents),
        "replacement_size_within_limit": 0 < len(replacement_bytes) <= 4096,
        "expected_before_sha256_valid": _is_sha256_hex(expected_before),
        "expected_after_sha256_valid": _is_sha256_hex(expected_after),
        "repository_fixture_matches_pre_state": actual_before == expected_before,
        "replacement_matches_post_state": replacement_sha == expected_after,
        "single_validation_command": len(commands) == 1,
        "validation_command_allowlisted": validation_classification.get("allowed") is True,
        "validation_timeout_valid": isinstance(validation_timeout_seconds, (int, float)) and 0 < float(validation_timeout_seconds) <= 60,
        "total_timeout_valid": isinstance(total_timeout_seconds, (int, float)) and float(validation_timeout_seconds) < float(total_timeout_seconds) <= 300,
    }
    failed_checks = sorted(name for name, passed in checks.items() if passed is not True)
    if failed_checks:
        return _blocked_execution_envelope_design_payload(
            target_path=target_rel,
            blockers=[f"design_check_failed:{name}" for name in failed_checks],
            checks=checks,
        )

    envelope = {
        "schema": CONTROLLED_CORRECTION_EXECUTION_ENVELOPE_SCHEMA,
        "schema_version": CONTROLLED_CORRECTION_EXECUTION_ENVELOPE_SCHEMA_VERSION,
        "envelope_version": "v0.1.107",
        "envelope_id": f"v0.1.107:{target.target_id}:{expected_before[:12]}:{expected_after[:12]}",
        "design_scope": "future_disposable_repository_copy_only",
        "source_promotion_decision": {
            "record_path": CONTROLLED_CORRECTION_PROMOTION_DECISION_RECORD,
            "decision": "go",
            "decision_version": "v0.1.106",
            "readiness_fingerprint_sha256": decision_source.get("determinism_fingerprint_sha256"),
        },
        "allowed_target": {
            "kind": "future_disposable_repository_copy",
            "target_id": target.target_id,
            "target_definition_path": target_rel,
            "repository_binding": "must_be_explicitly_supplied_and_verified_by_future_validation_slice",
            "real_repository_forbidden": True,
            "current_repository_forbidden": True,
        },
        "allowed_files": {
            "mutable": [fixture_path],
            "read_only": [target_rel],
            "maximum_mutable_file_count": 1,
            "path_policy": "literal_repo_relative_no_glob_no_parent_traversal",
        },
        "allowed_operation": {
            "type": "replace_contents",
            "maximum_occurrences": 1,
            "replacement_contents_utf8": replacement_contents,
            "replacement_size_bytes": len(replacement_bytes),
            "expected_before_sha256": expected_before,
            "expected_after_sha256": expected_after,
        },
        "required_pre_state": {
            "target_file_exists": True,
            "target_file_sha256": expected_before,
            "repository_snapshot_required": True,
            "only_allowed_file_may_change": True,
        },
        "required_post_state": {
            "target_file_sha256": expected_after,
            "validation_must_pass": True,
            "unrelated_repository_paths_unchanged": True,
            "promotion_or_adoption_forbidden": True,
        },
        "validation": {
            "commands": [validation_command],
            "argv": [validation_classification.get("argv")],
            "maximum_command_count": 1,
            "read_only_required": True,
            "timeout_seconds": float(validation_timeout_seconds),
            "retry_count": 0,
        },
        "rollback": {
            "required": True,
            "trigger": "always_after_evidence_or_immediately_on_any_failure",
            "method": "restore_exact_pre_state_bytes",
            "required_restored_sha256": expected_before,
            "rollback_validation_required": True,
            "workspace_deletion_required": True,
        },
        "limits": {
            "maximum_iterations": 1,
            "maximum_mutated_files": 1,
            "maximum_write_operations": 1,
            "maximum_validation_commands": 1,
            "maximum_replacement_bytes": 4096,
            "automatic_retries": 0,
            "parallel_execution": False,
            "generic_shell_authority": False,
        },
        "timeouts": {
            "total_seconds": float(total_timeout_seconds),
            "validation_seconds": float(validation_timeout_seconds),
            "rollback_seconds": 15.0,
        },
        "required_evidence_bundle": {
            "schema": "promptbranch.loop.controlled_correction_execution_evidence",
            "schema_version": "1.0",
            "required_fields": [
                "envelope_sha256",
                "disposable_repository_identity",
                "repository_snapshot_before",
                "target_file_before_sha256",
                "target_file_after_sha256",
                "validation_command",
                "validation_exit_code",
                "validation_stdout_sha256",
                "validation_stderr_sha256",
                "repository_snapshot_after_validation",
                "rollback_attempted",
                "rollback_succeeded",
                "target_file_rollback_sha256",
                "repository_snapshot_after_rollback",
                "workspace_deleted",
            ],
            "all_fields_required": True,
            "missing_or_contradictory_evidence_blocks": True,
        },
        "promotion_authority": {
            "execution_authority_granted_by_this_design": False,
            "future_validation_gate_required": True,
            "artifact_adoption_forbidden": True,
            "project_source_mutation_forbidden": True,
            "deployment_forbidden": True,
        },
    }
    canonical_json = json.dumps(envelope, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    fingerprint = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()
    return {
        "ok": True,
        "schema": LOOP_CONTROLLED_CORRECTION_EXECUTION_ENVELOPE_DESIGN_SCHEMA,
        "schema_version": LOOP_CONTROLLED_CORRECTION_EXECUTION_ENVELOPE_DESIGN_SCHEMA_VERSION,
        "action": "design_controlled_correction_execution_envelope",
        "design_version": "v0.1.107",
        "status": "execution_envelope_design_ready",
        "decision": "design_complete_no_execution_authority",
        "target_path": target_rel,
        "design_checks": checks,
        "passed_design_check_count": len(checks),
        "failed_design_check_count": 0,
        "failed_design_checks": [],
        "execution_blockers": [],
        "execution_envelope": envelope,
        "determinism": {"canonical_design_sha256": fingerprint},
        "authority": {
            "design_record_emitted": True,
            "future_envelope_validation_authority_granted": True,
            "correction_execution_authority_granted": False,
            "disposable_repository_mutation_authority_granted": False,
            "real_repository_mutation_authority_granted": False,
            "deployment_authority_granted": False,
            "kubernetes_mutation_authority_granted": False,
            "project_source_mutation_authority_granted": False,
            "artifact_adoption_authority_granted": False,
            "chatgpt_project_deletion_authority_granted": False,
        },
        "safety": {
            "design_only": True,
            "commands_executed": 0,
            "files_mutated": False,
            "workspace_created": False,
            "repository_files_mutated": False,
            "deployment_performed": False,
            "kubernetes_mutation_performed": False,
            "project_source_mutation_performed": False,
            "artifact_adoption_performed": False,
            "chatgpt_project_deletion_performed": False,
        },
        "next_slice": {
            "version": "v0.1.108",
            "slice": "Controlled correction execution envelope validation gate",
            "permitted": True,
            "scope": "validation_only_no_correction_execution",
        },
        "operator_instruction": "The controlled execution envelope has been designed deterministically. This result grants validation of the envelope design only; it creates no workspace, executes no command, mutates no file or repository, and grants no correction execution authority.",
    }


def render_loop_controlled_correction_execution_envelope_design_text(payload: dict[str, Any]) -> str:
    authority = payload.get("authority") if isinstance(payload.get("authority"), dict) else {}
    lines = [
        "Promptbranch controlled correction execution envelope design",
        f"status: {payload.get('status')}",
        f"decision: {payload.get('decision')}",
        f"design fingerprint: {(payload.get('determinism') or {}).get('canonical_design_sha256')}",
        f"future validation authorized: {authority.get('future_envelope_validation_authority_granted') is True}",
        "correction execution authority granted: false",
        "repository mutation authority granted: false",
    ]
    blockers = payload.get("execution_blockers") or []
    if blockers:
        lines.append("execution blockers: " + ", ".join(str(item) for item in blockers))
    lines.append(str(payload.get("operator_instruction") or ""))
    return "\n".join(lines) + "\n"

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



def render_loop_sandbox_mutation_verification_text(payload: dict[str, Any]) -> str:
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
        f"sandbox_mutation_verified={str(bool(summary.get('sandbox_mutation_verified'))).lower()}",
        f"sandbox_validation_passed={str(bool(summary.get('sandbox_validation_passed'))).lower()}",
        f"sandbox_rollback_succeeded={str(bool(summary.get('sandbox_rollback_succeeded'))).lower()}",
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
