from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Iterable, Sequence

SCHEMA = "promptbranch.ai.application"
SCHEMA_VERSION = "1.0"
DEFAULT_DECLARATION = ".promptbranch-ai.json"
SUPPORTED_LEVELS = ("declaration", "structural")
KNOWN_LEVELS = ("declaration", "structural", "registry", "executable", "operational")
APPLICATION_KINDS = {"runtime_application", "domain_module"}
VERSION_FORMATS = {"plain", "python", "toml"}
LAYER_NAMES = (
    "instructions_policy",
    "runtime_actors",
    "skills",
    "tools",
    "validators",
    "knowledge_context",
    "state_contracts",
    "evidence_records",
    "controller_authority",
    "lifecycle_recovery",
)
GENERIC_RUNTIME_CAPABILITIES = (
    "agent_execution",
    "skill_execution",
    "tool_dispatch",
    "validation_orchestration",
    "evidence_ledger",
    "project_state_transition",
    "correction",
    "release",
    "publication",
    "adoption",
    "verification",
)
AUTHORITY_BOUNDARIES = ("mutation", "release", "publication", "adoption")
SHELL_EXECUTABLES = {"sh", "bash", "zsh", "fish", "cmd", "powershell", "pwsh"}
SHELL_TOKENS = {";", "&&", "||", "|", ">", ">>", "<", "<<"}
VERSION_RE = re.compile(r"^v?\d+\.\d+\.\d+(?:\.\d+)*$")
CONTRACT_VERSION_RE = re.compile(r"^\d+\.\d+(?:\.\d+)?$")
IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


class ApplicationArchitectureError(ValueError):
    """Raised when a tracked AI application declaration is invalid."""


def _safe_relative(value: object, label: str, *, allow_dot: bool = False) -> str:
    if not isinstance(value, str):
        raise ApplicationArchitectureError(f"{label} must be a string")
    text = value.strip()
    if "\\" in text:
        raise ApplicationArchitectureError(
            f"{label} must use portable forward-slash repository-relative syntax"
        )
    if text == ".":
        if allow_dot:
            return text
        raise ApplicationArchitectureError(
            f"{label} must identify a repository asset, not the repository root"
        )
    path = Path(text)
    if not text or path.is_absolute() or ".." in path.parts:
        raise ApplicationArchitectureError(
            f"{label} must be a non-empty repository-relative path without traversal"
        )
    return path.as_posix()


def _require_object(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ApplicationArchitectureError(f"{label} must be an object")
    return value


def _require_exact_keys(
    value: dict[str, Any], required: Iterable[str], allowed: Iterable[str], label: str
) -> None:
    required_set = set(required)
    allowed_set = set(allowed)
    missing = sorted(required_set - set(value))
    unknown = sorted(set(value) - allowed_set)
    if missing:
        raise ApplicationArchitectureError(
            f"{label} missing required fields: {', '.join(missing)}"
        )
    if unknown:
        raise ApplicationArchitectureError(
            f"{label} contains unknown fields: {', '.join(unknown)}"
        )


def _non_empty_string(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ApplicationArchitectureError(f"{label} must be a non-empty string")
    return value.strip()


def _string_list(value: object, label: str, *, allow_empty: bool = False) -> list[str]:
    if not isinstance(value, list):
        raise ApplicationArchitectureError(f"{label} must be an array")
    if not allow_empty and not value:
        raise ApplicationArchitectureError(f"{label} must be a non-empty array")
    result: list[str] = []
    for index, item in enumerate(value):
        result.append(_non_empty_string(item, f"{label}[{index}]"))
    if len(result) != len(set(result)):
        raise ApplicationArchitectureError(f"{label} must not contain duplicates")
    return result


def _read_version(repo: Path, authority: dict[str, Any]) -> str:
    path = repo / authority["path"]
    if not path.is_file():
        raise ApplicationArchitectureError(
            f"version authority file not found: {authority['path']}"
        )
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        raise ApplicationArchitectureError(
            f"version authority file is empty: {authority['path']}"
        )
    if authority["format"] == "plain":
        version = text
    elif authority["format"] == "python":
        match = re.search(
            r"(?m)^\s*(?:PACKAGE_VERSION|VERSION)\s*=\s*['\"]([^'\"]+)['\"]\s*$",
            text,
        )
        if not match:
            raise ApplicationArchitectureError(
                f"version authority {authority['path']} does not define PACKAGE_VERSION or VERSION"
            )
        version = match.group(1).strip()
    else:
        match = re.search(r"(?m)^\s*version\s*=\s*['\"]([^'\"]+)['\"]\s*$", text)
        if not match:
            raise ApplicationArchitectureError(
                f"version authority {authority['path']} does not define version"
            )
        version = match.group(1).strip()
    if not VERSION_RE.fullmatch(version):
        raise ApplicationArchitectureError(
            f"version authority value is not a supported version: {version!r}"
        )
    return version if version.startswith("v") else f"v{version}"


def _validate_command(command: object, index: int) -> dict[str, Any]:
    label = f"validation.commands[{index}]"
    obj = _require_object(command, label)
    _require_exact_keys(
        obj,
        {"id", "level", "argv", "cwd", "timeout_seconds"},
        {"id", "level", "argv", "cwd", "timeout_seconds"},
        label,
    )
    command_id = _non_empty_string(obj["id"], f"{label}.id")
    if not IDENTIFIER_RE.fullmatch(command_id):
        raise ApplicationArchitectureError(
            f"{label}.id must contain only letters, digits, dots, underscores, or hyphens"
        )
    level = _non_empty_string(obj["level"], f"{label}.level")
    if level not in SUPPORTED_LEVELS:
        raise ApplicationArchitectureError(
            f"{label}.level must be declaration or structural"
        )
    argv = _string_list(obj["argv"], f"{label}.argv")
    executable = Path(argv[0]).name.lower()
    if executable in SHELL_EXECUTABLES:
        raise ApplicationArchitectureError(f"{label}.argv may not invoke a shell")
    if any(token in SHELL_TOKENS or "$(`" in token for token in argv):
        raise ApplicationArchitectureError(
            f"{label}.argv contains unsupported shell-like syntax"
        )
    cwd = _safe_relative(obj["cwd"], f"{label}.cwd", allow_dot=True)
    timeout = obj["timeout_seconds"]
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)):
        raise ApplicationArchitectureError(f"{label}.timeout_seconds must be numeric")
    if timeout <= 0 or timeout > 14400:
        raise ApplicationArchitectureError(
            f"{label}.timeout_seconds must satisfy 0 < timeout <= 14400"
        )
    return {
        "id": command_id,
        "level": level,
        "argv": argv,
        "cwd": cwd,
        "timeout_seconds": timeout,
    }


def load_application_declaration(
    repo_path: str | Path = ".", config: str = DEFAULT_DECLARATION
) -> dict[str, Any]:
    repo = Path(repo_path).expanduser().resolve()
    config_rel = _safe_relative(config, "config")
    declaration_path = repo / config_rel
    if not declaration_path.is_file():
        raise ApplicationArchitectureError(
            f"AI application declaration not found: {config_rel}"
        )
    try:
        data = json.loads(declaration_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ApplicationArchitectureError(f"invalid AI application declaration: {exc}") from exc
    root = _require_object(data, "declaration")
    required_top = {
        "schema",
        "schema_version",
        "application",
        "version_authority",
        "runtime",
        "layers",
        "delegation",
        "authority",
        "validation",
    }
    _require_exact_keys(root, required_top, required_top, "declaration")
    if root["schema"] != SCHEMA or root["schema_version"] != SCHEMA_VERSION:
        raise ApplicationArchitectureError(
            "unsupported AI application declaration schema or schema_version"
        )

    application = _require_object(root["application"], "application")
    _require_exact_keys(application, {"id", "kind"}, {"id", "kind"}, "application")
    application_id = _non_empty_string(application["id"], "application.id")
    if not IDENTIFIER_RE.fullmatch(application_id):
        raise ApplicationArchitectureError(
            "application.id must contain only letters, digits, dots, underscores, or hyphens"
        )
    kind = _non_empty_string(application["kind"], "application.kind")
    if kind not in APPLICATION_KINDS:
        raise ApplicationArchitectureError(
            "application.kind must be runtime_application or domain_module"
        )

    version_authority = _require_object(root["version_authority"], "version_authority")
    _require_exact_keys(
        version_authority,
        {"path", "format", "sole"},
        {"path", "format", "sole"},
        "version_authority",
    )
    version_authority["path"] = _safe_relative(
        version_authority["path"], "version_authority.path"
    )
    version_format = _non_empty_string(version_authority["format"], "version_authority.format")
    if version_format not in VERSION_FORMATS:
        raise ApplicationArchitectureError(
            "version_authority.format must be plain, python, or toml"
        )
    if version_authority["sole"] is not True:
        raise ApplicationArchitectureError("version_authority.sole must be true")

    runtime = _require_object(root["runtime"], "runtime")
    _require_exact_keys(runtime, {"provider", "contract_version"}, {"provider", "contract_version"}, "runtime")
    runtime_provider = _non_empty_string(runtime["provider"], "runtime.provider")
    contract_version = _non_empty_string(runtime["contract_version"], "runtime.contract_version")
    if not CONTRACT_VERSION_RE.fullmatch(contract_version):
        raise ApplicationArchitectureError(
            "runtime.contract_version must be a dotted numeric contract version"
        )

    layers = _require_object(root["layers"], "layers")
    _require_exact_keys(layers, set(LAYER_NAMES), set(LAYER_NAMES), "layers")
    normalized_layers: dict[str, list[str]] = {}
    all_layer_paths: list[str] = []
    for layer in LAYER_NAMES:
        entries = _string_list(layers[layer], f"layers.{layer}")
        normalized = [_safe_relative(entry, f"layers.{layer} entry") for entry in entries]
        normalized_layers[layer] = normalized
        all_layer_paths.extend(normalized)
    duplicates = sorted({path for path in all_layer_paths if all_layer_paths.count(path) > 1})
    if duplicates:
        raise ApplicationArchitectureError(
            "layer paths must have unambiguous ownership; repeated paths: " + ", ".join(duplicates)
        )

    delegation = _require_object(root["delegation"], "delegation")
    _require_exact_keys(
        delegation,
        {"generic_runtime_provider", "delegated_capabilities", "owned_capabilities"},
        {"generic_runtime_provider", "delegated_capabilities", "owned_capabilities"},
        "delegation",
    )
    generic_provider = _non_empty_string(
        delegation["generic_runtime_provider"], "delegation.generic_runtime_provider"
    )
    delegated = _string_list(
        delegation["delegated_capabilities"],
        "delegation.delegated_capabilities",
        allow_empty=True,
    )
    owned = _string_list(delegation["owned_capabilities"], "delegation.owned_capabilities")
    if runtime_provider != generic_provider:
        raise ApplicationArchitectureError(
            "runtime.provider must equal delegation.generic_runtime_provider"
        )
    generic_set = set(GENERIC_RUNTIME_CAPABILITIES)
    delegated_set = set(delegated)
    owned_set = set(owned)
    if kind == "runtime_application":
        if generic_provider != application_id:
            raise ApplicationArchitectureError(
                "runtime_application must name itself as generic_runtime_provider"
            )
        if delegated:
            raise ApplicationArchitectureError(
                "runtime_application may not delegate generic runtime capabilities"
            )
        if owned_set != generic_set:
            missing = sorted(generic_set - owned_set)
            extra = sorted(owned_set - generic_set)
            details = []
            if missing:
                details.append("missing " + ", ".join(missing))
            if extra:
                details.append("unknown " + ", ".join(extra))
            raise ApplicationArchitectureError(
                "runtime_application owned_capabilities must equal the generic runtime contract"
                + (": " + "; ".join(details) if details else "")
            )
    else:
        if generic_provider == application_id:
            raise ApplicationArchitectureError(
                "domain_module must delegate generic runtime capabilities to another provider"
            )
        if delegated_set != generic_set:
            missing = sorted(generic_set - delegated_set)
            extra = sorted(delegated_set - generic_set)
            details = []
            if missing:
                details.append("missing " + ", ".join(missing))
            if extra:
                details.append("unknown " + ", ".join(extra))
            raise ApplicationArchitectureError(
                "domain_module delegated_capabilities must equal the generic runtime contract"
                + (": " + "; ".join(details) if details else "")
            )
        if owned_set & generic_set:
            raise ApplicationArchitectureError(
                "domain_module may not claim generic runtime capabilities as owned"
            )

    authority = _require_object(root["authority"], "authority")
    _require_exact_keys(
        authority,
        {"self_grant_allowed", *AUTHORITY_BOUNDARIES},
        {"self_grant_allowed", *AUTHORITY_BOUNDARIES},
        "authority",
    )
    if authority["self_grant_allowed"] is not False:
        raise ApplicationArchitectureError("authority.self_grant_allowed must be false")
    normalized_authority: dict[str, Any] = {"self_grant_allowed": False}
    for boundary in AUTHORITY_BOUNDARIES:
        label = f"authority.{boundary}"
        item = _require_object(authority[boundary], label)
        _require_exact_keys(
            item,
            {"controller", "requires_explicit_request", "requires_verified_evidence"},
            {"controller", "requires_explicit_request", "requires_verified_evidence"},
            label,
        )
        controller = _non_empty_string(item["controller"], f"{label}.controller")
        if controller.lower() in {"self", "application", "unbounded", "implicit"}:
            raise ApplicationArchitectureError(
                f"{label}.controller may not self-grant authority"
            )
        if item["requires_explicit_request"] is not True:
            raise ApplicationArchitectureError(
                f"{label}.requires_explicit_request must be true"
            )
        if item["requires_verified_evidence"] is not True:
            raise ApplicationArchitectureError(
                f"{label}.requires_verified_evidence must be true"
            )
        normalized_authority[boundary] = {
            "controller": controller,
            "requires_explicit_request": True,
            "requires_verified_evidence": True,
        }

    validation = _require_object(root["validation"], "validation")
    _require_exact_keys(validation, {"commands"}, {"commands"}, "validation")
    commands_raw = validation["commands"]
    if not isinstance(commands_raw, list) or not commands_raw:
        raise ApplicationArchitectureError("validation.commands must be a non-empty array")
    commands = [_validate_command(command, index) for index, command in enumerate(commands_raw)]
    command_ids = [command["id"] for command in commands]
    if len(command_ids) != len(set(command_ids)):
        raise ApplicationArchitectureError("validation.commands ids must be unique")
    if "structural" not in {command["level"] for command in commands}:
        raise ApplicationArchitectureError(
            "validation.commands must include at least one structural command"
        )

    normalized = {
        "schema": SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "application": {"id": application_id, "kind": kind},
        "version_authority": {
            "path": version_authority["path"],
            "format": version_format,
            "sole": True,
        },
        "runtime": {"provider": runtime_provider, "contract_version": contract_version},
        "layers": normalized_layers,
        "delegation": {
            "generic_runtime_provider": generic_provider,
            "delegated_capabilities": delegated,
            "owned_capabilities": owned,
        },
        "authority": normalized_authority,
        "validation": {"commands": commands},
        "_declaration_path": config_rel,
    }
    normalized["_version"] = _read_version(repo, normalized["version_authority"])
    return normalized


def _asset_state(repo: Path, rel: str) -> dict[str, Any]:
    path = repo / rel
    if path.is_file():
        try:
            content = path.read_bytes()
        except OSError as exc:
            return {"path": rel, "kind": "file", "ok": False, "error": str(exc)}
        return {
            "path": rel,
            "kind": "file",
            "ok": bool(content.strip()),
            "size_bytes": len(content),
            "error": None if content.strip() else "file_empty",
        }
    if path.is_dir():
        files = [candidate for candidate in path.rglob("*") if candidate.is_file()]
        non_empty = []
        for candidate in files:
            try:
                if candidate.read_bytes().strip():
                    non_empty.append(candidate)
            except OSError:
                continue
        return {
            "path": rel,
            "kind": "directory",
            "ok": bool(non_empty),
            "file_count": len(files),
            "non_empty_file_count": len(non_empty),
            "error": None if non_empty else "directory_has_no_non_empty_files",
        }
    return {"path": rel, "kind": "missing", "ok": False, "error": "path_missing"}


def _declaration_summary(declaration: dict[str, Any]) -> dict[str, Any]:
    return {
        "path": declaration["_declaration_path"],
        "schema": declaration["schema"],
        "schema_version": declaration["schema_version"],
        "application": declaration["application"],
        "version": declaration["_version"],
        "version_authority": declaration["version_authority"],
        "runtime": declaration["runtime"],
    }


def plan_application_architecture(
    repo_path: str | Path = ".", config: str = DEFAULT_DECLARATION
) -> dict[str, Any]:
    repo = Path(repo_path).expanduser().resolve()
    declaration = load_application_declaration(repo, config)
    layer_plan = [
        {"layer": layer, "paths": declaration["layers"][layer], "required": True}
        for layer in LAYER_NAMES
    ]
    return {
        "ok": True,
        "action": "application_architecture_plan",
        "status": "planned_read_only",
        "repo_path": str(repo),
        "declaration": _declaration_summary(declaration),
        "requested_level": "structural",
        "proven_level": "declaration",
        "max_supported_level": "structural",
        "layer_plan": layer_plan,
        "delegation": declaration["delegation"],
        "authority": declaration["authority"],
        "validation_commands": declaration["validation"]["commands"],
        "safety": {
            "read_only": True,
            "commands_executed": False,
            "state_mutated": False,
            "release_authority_granted": False,
            "publication_authority_granted": False,
            "adoption_authority_granted": False,
        },
    }


def validate_application_architecture(
    repo_path: str | Path = ".",
    config: str = DEFAULT_DECLARATION,
    *,
    level: str = "structural",
) -> dict[str, Any]:
    repo = Path(repo_path).expanduser().resolve()
    requested_level = str(level or "structural").strip().lower()
    if requested_level not in KNOWN_LEVELS:
        return {
            "ok": False,
            "action": "application_architecture_validate",
            "status": "unknown_validation_level",
            "repo_path": str(repo),
            "requested_level": requested_level,
            "proven_level": "none",
            "max_supported_level": "structural",
            "errors": [f"unknown validation level: {requested_level}"],
        }
    try:
        declaration = load_application_declaration(repo, config)
    except ApplicationArchitectureError as exc:
        return {
            "ok": False,
            "action": "application_architecture_validate",
            "status": "declaration_invalid",
            "repo_path": str(repo),
            "requested_level": requested_level,
            "proven_level": "none",
            "max_supported_level": "structural",
            "declaration_path": config,
            "errors": [str(exc)],
            "safety": {"read_only": True, "state_mutated": False},
        }

    declaration_summary = _declaration_summary(declaration)
    if requested_level == "declaration":
        return {
            "ok": True,
            "action": "application_architecture_validate",
            "status": "declaration_validated",
            "repo_path": str(repo),
            "requested_level": requested_level,
            "proven_level": "declaration",
            "max_supported_level": "structural",
            "declaration": declaration_summary,
            "errors": [],
            "safety": {"read_only": True, "state_mutated": False},
        }
    if requested_level not in SUPPORTED_LEVELS:
        return {
            "ok": False,
            "action": "application_architecture_validate",
            "status": "validation_level_not_implemented",
            "repo_path": str(repo),
            "requested_level": requested_level,
            "proven_level": "declaration",
            "max_supported_level": "structural",
            "declaration": declaration_summary,
            "errors": [
                f"{requested_level} validation is not implemented; highest supported level is structural"
            ],
            "safety": {"read_only": True, "state_mutated": False},
        }

    layer_results: dict[str, list[dict[str, Any]]] = {}
    errors: list[str] = []
    for layer in LAYER_NAMES:
        results = [_asset_state(repo, rel) for rel in declaration["layers"][layer]]
        layer_results[layer] = results
        for result in results:
            if not result["ok"]:
                errors.append(
                    f"layers.{layer} asset {result['path']} failed structural validation: {result['error']}"
                )

    command_cwds = []
    for command in declaration["validation"]["commands"]:
        cwd_state = _asset_state(repo, command["cwd"]) if command["cwd"] != "." else {
            "path": ".", "kind": "directory", "ok": True, "error": None
        }
        command_cwds.append({"id": command["id"], **cwd_state})
        if not cwd_state["ok"]:
            errors.append(
                f"validation command {command['id']} cwd failed structural validation: {cwd_state['error']}"
            )

    return {
        "ok": not errors,
        "action": "application_architecture_validate",
        "status": "structural_validated" if not errors else "structural_invalid",
        "repo_path": str(repo),
        "requested_level": requested_level,
        "proven_level": "structural" if not errors else "declaration",
        "max_supported_level": "structural",
        "declaration": declaration_summary,
        "required_layers": list(LAYER_NAMES),
        "layer_count": len(LAYER_NAMES),
        "layers": layer_results,
        "delegation": declaration["delegation"],
        "authority": declaration["authority"],
        "validation_commands": declaration["validation"]["commands"],
        "validation_command_cwds": command_cwds,
        "error_count": len(errors),
        "errors": errors,
        "safety": {
            "read_only": True,
            "commands_executed": False,
            "state_mutated": False,
            "release_authority_granted": False,
            "publication_authority_granted": False,
            "adoption_authority_granted": False,
        },
    }


__all__ = [
    "ApplicationArchitectureError",
    "DEFAULT_DECLARATION",
    "GENERIC_RUNTIME_CAPABILITIES",
    "KNOWN_LEVELS",
    "LAYER_NAMES",
    "SCHEMA",
    "SCHEMA_VERSION",
    "SUPPORTED_LEVELS",
    "load_application_declaration",
    "plan_application_architecture",
    "validate_application_architecture",
]
