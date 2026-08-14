from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

SCHEMA = "promptbranch.application.pilot"
SCHEMA_VERSION = "1.0"
DEFAULT_CONFIG = "examples/application-pilot/k8s-game-mvp.pilot.json"


class ApplicationPilotError(ValueError):
    """Raised when the read-only external-application pilot contract is invalid."""


def _object(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ApplicationPilotError(f"{label} must be an object")
    return value


def _exact_keys(value: dict[str, Any], required: Iterable[str], label: str) -> None:
    expected = set(required)
    actual = set(value)
    missing = sorted(expected - actual)
    unknown = sorted(actual - expected)
    if missing:
        raise ApplicationPilotError(f"{label} missing required fields: {', '.join(missing)}")
    if unknown:
        raise ApplicationPilotError(f"{label} contains unknown fields: {', '.join(unknown)}")


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ApplicationPilotError(f"{label} must be a non-empty string")
    return value.strip()


def _relative(value: object, label: str) -> str:
    text = _text(value, label)
    if "\\" in text:
        raise ApplicationPilotError(f"{label} must use forward slashes")
    path = Path(text)
    if path.is_absolute() or ".." in path.parts or text == ".":
        raise ApplicationPilotError(f"{label} must be a repository-relative path without traversal")
    return path.as_posix()


def _text_list(value: object, label: str) -> list[str]:
    if not isinstance(value, list) or not value:
        raise ApplicationPilotError(f"{label} must be a non-empty array")
    result = [_text(item, f"{label}[{index}]") for index, item in enumerate(value)]
    if len(result) != len(set(result)):
        raise ApplicationPilotError(f"{label} must not contain duplicates")
    return result


def _path_list(value: object, label: str) -> list[str]:
    return [_relative(item, f"{label}[{index}]") for index, item in enumerate(_text_list(value, label))]


def _argv_list(value: object, label: str) -> list[list[str]]:
    if not isinstance(value, list) or not value:
        raise ApplicationPilotError(f"{label} must be a non-empty array")
    result: list[list[str]] = []
    shell_names = {"sh", "bash", "zsh", "fish", "cmd", "powershell", "pwsh"}
    shell_tokens = {";", "&&", "||", "|", ">", ">>", "<", "<<"}
    for index, raw in enumerate(value):
        if not isinstance(raw, list) or not raw:
            raise ApplicationPilotError(f"{label}[{index}] must be a non-empty argv array")
        argv = [_text(item, f"{label}[{index}] item") for item in raw]
        if Path(argv[0]).name.lower() in shell_names:
            raise ApplicationPilotError(f"{label}[{index}] may not invoke a shell")
        if any(item in shell_tokens for item in argv):
            raise ApplicationPilotError(f"{label}[{index}] contains shell syntax")
        result.append(argv)
    return result


def load_application_pilot_definition(
    control_repo: str | Path = ".", config: str = DEFAULT_CONFIG
) -> dict[str, Any]:
    root = Path(control_repo).expanduser().resolve()
    config_rel = _relative(config, "config")
    path = root / config_rel
    if not path.is_file():
        raise ApplicationPilotError(f"application pilot definition not found: {config_rel}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ApplicationPilotError(f"invalid application pilot definition: {exc}") from exc
    return validate_application_pilot_definition(payload, config_path=config_rel)


def validate_application_pilot_definition(
    payload: object, *, config_path: str = DEFAULT_CONFIG
) -> dict[str, Any]:
    root = _object(payload, "pilot definition")
    required = {
        "schema",
        "schema_version",
        "pilot",
        "target",
        "architecture",
        "definition_of_done",
        "tests",
        "authority",
        "bootstrap",
        "execution_plan",
    }
    _exact_keys(root, required, "pilot definition")
    if root["schema"] != SCHEMA or root["schema_version"] != SCHEMA_VERSION:
        raise ApplicationPilotError("unsupported application pilot schema or schema_version")

    pilot = _object(root["pilot"], "pilot")
    _exact_keys(pilot, {"id", "application_repo_id", "vertical_slice", "visible_output"}, "pilot")
    normalized_pilot = {key: _text(pilot[key], f"pilot.{key}") for key in pilot}

    target = _object(root["target"], "target")
    _exact_keys(target, {"goal", "path"}, "target")
    normalized_target = {"goal": _text(target["goal"], "target.goal"), "path": _relative(target["path"], "target.path")}

    architecture = _object(root["architecture"], "architecture")
    _exact_keys(architecture, {"declaration_path", "documentation_path"}, "architecture")
    normalized_architecture = {
        "declaration_path": _relative(architecture["declaration_path"], "architecture.declaration_path"),
        "documentation_path": _relative(architecture["documentation_path"], "architecture.documentation_path"),
    }

    dod = _object(root["definition_of_done"], "definition_of_done")
    _exact_keys(dod, {"path", "requirements"}, "definition_of_done")
    normalized_dod = {
        "path": _relative(dod["path"], "definition_of_done.path"),
        "requirements": _text_list(dod["requirements"], "definition_of_done.requirements"),
    }

    tests = _object(root["tests"], "tests")
    _exact_keys(tests, {"path", "commands"}, "tests")
    normalized_tests = {
        "path": _relative(tests["path"], "tests.path"),
        "commands": _argv_list(tests["commands"], "tests.commands"),
    }

    authority = _object(root["authority"], "authority")
    authority_fields = {
        "mutation_allowed",
        "git_mutation_allowed",
        "project_source_mutation_allowed",
        "deployment_allowed",
        "acceptance_requires_human",
        "rollback_contract_required_before_mutation",
    }
    _exact_keys(authority, authority_fields, "authority")
    for field in authority_fields:
        if not isinstance(authority[field], bool):
            raise ApplicationPilotError(f"authority.{field} must be boolean")
    if authority["mutation_allowed"] is not False:
        raise ApplicationPilotError("pilot bootstrap authority requires mutation_allowed=false")
    if authority["git_mutation_allowed"] is not False:
        raise ApplicationPilotError("pilot bootstrap authority requires git_mutation_allowed=false")
    if authority["project_source_mutation_allowed"] is not False:
        raise ApplicationPilotError("pilot bootstrap authority requires project_source_mutation_allowed=false")
    if authority["deployment_allowed"] is not False:
        raise ApplicationPilotError("pilot bootstrap authority requires deployment_allowed=false")
    if authority["acceptance_requires_human"] is not True:
        raise ApplicationPilotError("pilot bootstrap authority requires acceptance_requires_human=true")
    if authority["rollback_contract_required_before_mutation"] is not True:
        raise ApplicationPilotError("pilot bootstrap requires a rollback contract before later mutation")

    bootstrap = _object(root["bootstrap"], "bootstrap")
    _exact_keys(bootstrap, {"required_repo_marker", "proposed_paths"}, "bootstrap")
    marker = _relative(bootstrap["required_repo_marker"], "bootstrap.required_repo_marker")
    proposed_paths = _path_list(bootstrap["proposed_paths"], "bootstrap.proposed_paths")

    execution = _object(root["execution_plan"], "execution_plan")
    _exact_keys(execution, {"mode", "max_iterations"}, "execution_plan")
    mode = _text(execution["mode"], "execution_plan.mode")
    if mode != "read_only":
        raise ApplicationPilotError("pilot bootstrap execution_plan.mode must be read_only")
    max_iterations = execution["max_iterations"]
    if isinstance(max_iterations, bool) or not isinstance(max_iterations, int) or max_iterations != 1:
        raise ApplicationPilotError("pilot bootstrap execution_plan.max_iterations must equal 1")

    contract_paths = {
        normalized_target["path"],
        normalized_architecture["declaration_path"],
        normalized_architecture["documentation_path"],
        normalized_dod["path"],
        normalized_tests["path"],
    }
    missing_from_bootstrap = sorted(contract_paths - set(proposed_paths))
    if missing_from_bootstrap:
        raise ApplicationPilotError(
            "bootstrap.proposed_paths must include all target/architecture/DoD/test paths: "
            + ", ".join(missing_from_bootstrap)
        )

    return {
        "schema": SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "config_path": config_path,
        "pilot": normalized_pilot,
        "target": normalized_target,
        "architecture": normalized_architecture,
        "definition_of_done": normalized_dod,
        "tests": normalized_tests,
        "authority": dict(authority),
        "bootstrap": {"required_repo_marker": marker, "proposed_paths": proposed_paths},
        "execution_plan": {"mode": mode, "max_iterations": max_iterations},
    }


def build_application_pilot_validation(
    control_repo: str | Path = ".", config: str = DEFAULT_CONFIG
) -> dict[str, Any]:
    root = Path(control_repo).expanduser().resolve()
    definition = load_application_pilot_definition(root, config)
    return {
        "ok": True,
        "action": "application_pilot_validate",
        "status": "pilot_definition_valid",
        "control_repo": str(root),
        "definition": definition,
        "safety": {
            "read_only": True,
            "target_repo_mutated": False,
            "git_commands_executed": False,
            "project_source_mutated": False,
            "deployment_performed": False,
            "artifact_adopted": False,
        },
    }


def build_application_pilot_plan(
    control_repo: str | Path,
    target_repo: str | Path,
    config: str = DEFAULT_CONFIG,
) -> dict[str, Any]:
    control = Path(control_repo).expanduser().resolve()
    target = Path(target_repo).expanduser().resolve()
    definition = load_application_pilot_definition(control, config)

    if target == control:
        raise ApplicationPilotError("external application repository must be separate from the Promptbranch control repository")
    if not target.is_dir():
        raise ApplicationPilotError(f"external application repository directory does not exist: {target}")

    marker_rel = definition["bootstrap"]["required_repo_marker"]
    marker = target / marker_rel
    if not marker.exists():
        raise ApplicationPilotError(
            f"external application repository is not an established repository: required marker missing: {marker_rel}"
        )

    proposed = list(definition["bootstrap"]["proposed_paths"])
    existing = [path for path in proposed if (target / path).exists()]
    missing = [path for path in proposed if not (target / path).exists()]

    steps = [
        {"step": 1, "action": "inspect_external_repository", "mode": "read_only", "target": str(target)},
        {"step": 2, "action": "bind_application_identity", "mode": "read_only", "repo_id": definition["pilot"]["application_repo_id"]},
        {"step": 3, "action": "propose_target_contract", "mode": "read_only", "path": definition["target"]["path"]},
        {"step": 4, "action": "propose_application_architecture", "mode": "read_only", "paths": [definition["architecture"]["declaration_path"], definition["architecture"]["documentation_path"]]},
        {"step": 5, "action": "propose_definition_of_done", "mode": "read_only", "path": definition["definition_of_done"]["path"]},
        {"step": 6, "action": "propose_application_tests", "mode": "read_only", "path": definition["tests"]["path"], "commands": definition["tests"]["commands"]},
        {"step": 7, "action": "stop_before_mutation", "mode": "read_only", "reason": "external application mutation requires the later controlled-change authority slice"},
    ]

    return {
        "ok": True,
        "action": "application_pilot_plan",
        "status": "pilot_bootstrap_plan_ready",
        "pilot_id": definition["pilot"]["id"],
        "control_repo": str(control),
        "target_repo": str(target),
        "repo_binding": {
            "control_and_target_distinct": True,
            "required_repo_marker": marker_rel,
            "repo_marker_present": True,
            "application_repo_id": definition["pilot"]["application_repo_id"],
        },
        "target": definition["target"],
        "architecture": definition["architecture"],
        "definition_of_done": definition["definition_of_done"],
        "tests": definition["tests"],
        "bootstrap": {
            "proposed_paths": proposed,
            "existing_paths": existing,
            "missing_paths": missing,
            "mutation_performed": False,
        },
        "execution_plan": {
            "mode": "read_only",
            "max_iterations": 1,
            "steps": steps,
            "commands_executed": [],
        },
        "authority": definition["authority"],
        "safety": {
            "read_only": True,
            "target_repo_mutated": False,
            "git_commands_executed": False,
            "git_mutation_performed": False,
            "project_source_mutated": False,
            "deployment_performed": False,
            "artifact_adopted": False,
            "acceptance_performed": False,
        },
        "next_authorized_capability": "controlled_external_application_change_execution",
    }
