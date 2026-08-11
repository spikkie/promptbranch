from __future__ import annotations

import sys

import ast
import hashlib
import json
import re
import tempfile
from pathlib import Path
from typing import Any, Iterable, Sequence

from promptbranch_skillrun import build_skillrun_evidence, utc_now, validate_skillrun_evidence
from promptbranch_operational_evidence import validate_operational_lifecycle_evidence

SCHEMA = "promptbranch.ai.application"
SCHEMA_VERSION = "1.3"
DEFAULT_DECLARATION = ".promptbranch-ai.json"
SUPPORTED_LEVELS = ("declaration", "structural", "registry", "executable", "operational")
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
            f"{label}.level must be declaration, structural, registry, executable, or operational"
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
        "registry",
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

    registry = _require_object(root["registry"], "registry")
    _require_exact_keys(
        registry,
        {"path", "schema", "schema_version"},
        {"path", "schema", "schema_version"},
        "registry",
    )
    registry_path = _safe_relative(registry["path"], "registry.path")
    if registry["schema"] != "promptbranch.ai.registry":
        raise ApplicationArchitectureError(
            "registry.schema must be promptbranch.ai.registry"
        )
    if registry["schema_version"] != "1.1":
        raise ApplicationArchitectureError(
            "registry.schema_version must be 1.1"
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
    command_levels = {command["level"] for command in commands}
    if "structural" not in command_levels:
        raise ApplicationArchitectureError(
            "validation.commands must include at least one structural command"
        )
    if "registry" not in command_levels:
        raise ApplicationArchitectureError(
            "validation.commands must include at least one registry command"
        )
    if "executable" not in command_levels:
        raise ApplicationArchitectureError(
            "validation.commands must include at least one executable command"
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
        "registry": {
            "path": registry_path,
            "schema": "promptbranch.ai.registry",
            "schema_version": "1.1",
        },
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
        "registry": declaration["registry"],
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
        "requested_level": "registry",
        "proven_level": "declaration",
        "max_supported_level": "operational",
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



def _registry_list(value: object, label: str) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not value:
        raise ApplicationArchitectureError(f"{label} must be a non-empty array")
    result: list[dict[str, Any]] = []
    for index, item in enumerate(value):
        result.append(_require_object(item, f"{label}[{index}]"))
    return result


def _registry_id(value: object, label: str) -> str:
    text = _non_empty_string(value, label)
    if not IDENTIFIER_RE.fullmatch(text):
        raise ApplicationArchitectureError(
            f"{label} must contain only letters, digits, dots, underscores, or hyphens"
        )
    return text


def _python_top_level_symbols(path: Path) -> set[str]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, SyntaxError) as exc:
        raise ApplicationArchitectureError(f"cannot inspect Python symbols in {path}: {exc}") from exc
    return {
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
    }


def _literal_bool(node: ast.AST | None, default: bool) -> bool:
    if isinstance(node, ast.Constant) and isinstance(node.value, bool):
        return node.value
    return default


def _tool_risk(node: ast.AST | None) -> str:
    if node is None:
        return "read"
    if isinstance(node, ast.Attribute):
        return node.attr.lower()
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value.strip().lower()
    return "unknown"


def _static_mcp_tools(path: Path) -> dict[str, dict[str, Any]]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, SyntaxError) as exc:
        raise ApplicationArchitectureError(f"cannot inspect MCP tool registry {path}: {exc}") from exc
    result: dict[str, dict[str, Any]] = {}
    for node in tree.body:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        collection = next(
            (target.id for target in targets if isinstance(target, ast.Name) and target.id in {"READ_ONLY_MCP_TOOLS", "CONTROLLED_PROCESS_MCP_TOOLS"}),
            None,
        )
        if collection is None:
            continue
        value = node.value
        if not isinstance(value, (ast.Tuple, ast.List)):
            continue
        for item in value.elts:
            if not isinstance(item, ast.Call):
                continue
            func_name = item.func.id if isinstance(item.func, ast.Name) else None
            if func_name != "McpToolSpec":
                continue
            keywords = {kw.arg: kw.value for kw in item.keywords if kw.arg}
            name_node = keywords.get("name")
            if not isinstance(name_node, ast.Constant) or not isinstance(name_node.value, str):
                continue
            tool_id = name_node.value
            result[tool_id] = {
                "id": tool_id,
                "collection": collection,
                "risk": _tool_risk(keywords.get("risk")),
                "read_only": _literal_bool(keywords.get("read_only"), True),
            }
    return result


def _skill_frontmatter(path: Path) -> dict[str, Any]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise ApplicationArchitectureError(f"cannot read skill {path}: {exc}") from exc
    if not lines or lines[0].strip() != "---":
        raise ApplicationArchitectureError(f"skill {path} is missing YAML frontmatter")
    try:
        end = next(index for index, line in enumerate(lines[1:], 1) if line.strip() == "---")
    except StopIteration as exc:
        raise ApplicationArchitectureError(f"skill {path} has unterminated YAML frontmatter") from exc
    data: dict[str, Any] = {}
    current_list: str | None = None
    for raw in lines[1:end]:
        line = raw.rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line.startswith("  - ") and current_list:
            data.setdefault(current_list, []).append(line[4:].strip())
            continue
        if ":" not in line:
            raise ApplicationArchitectureError(f"skill {path} has unsupported frontmatter line: {line}")
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if value:
            data[key] = value
            current_list = None
        else:
            data[key] = []
            current_list = key
    return data


def _path_owned_by_layers(rel: str, declaration: dict[str, Any], allowed_layers: Sequence[str]) -> bool:
    candidate = Path(rel)
    for layer in allowed_layers:
        for owner in declaration["layers"][layer]:
            owner_path = Path(owner)
            if candidate == owner_path or owner_path in candidate.parents:
                return True
    return False


def _load_application_registry(repo: Path, declaration: dict[str, Any]) -> dict[str, Any]:
    registry_rel = declaration["registry"]["path"]
    path = repo / registry_rel
    if not path.is_file():
        raise ApplicationArchitectureError(f"AI application registry not found: {registry_rel}")
    try:
        root = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ApplicationArchitectureError(f"invalid AI application registry: {exc}") from exc
    registry = _require_object(root, "application registry")
    required = {
        "schema", "schema_version", "application_id", "runtime_provider", "agents", "skills", "tools",
        "validators", "state_contracts", "evidence_contracts", "controllers",
    }
    _require_exact_keys(registry, required, required, "application registry")
    if registry["schema"] != declaration["registry"]["schema"] or registry["schema_version"] != declaration["registry"]["schema_version"]:
        raise ApplicationArchitectureError("application registry schema identity does not match declaration")
    application_id = _registry_id(registry["application_id"], "application registry.application_id")
    runtime_provider = _registry_id(registry["runtime_provider"], "application registry.runtime_provider")
    if application_id != declaration["application"]["id"]:
        raise ApplicationArchitectureError("application registry.application_id does not match declaration")
    if runtime_provider != declaration["runtime"]["provider"]:
        raise ApplicationArchitectureError("application registry.runtime_provider does not match declaration")

    specs = {
        "agents": ({"id", "path", "symbol", "capabilities", "skills", "tools", "validators", "state_contracts", "evidence_contracts"}, {"id", "path", "symbol", "capabilities", "skills", "tools", "validators", "state_contracts", "evidence_contracts"}, "runtime_actors"),
        "skills": ({"id", "path", "name", "tools", "validators"}, {"id", "path", "name", "tools", "validators", "execution"}, "skills"),
        "tools": ({"id", "provider", "path", "collection", "risk", "read_only"}, {"id", "provider", "path", "collection", "risk", "read_only"}, "tools"),
        "validators": ({"id", "path", "symbol", "levels"}, {"id", "path", "symbol", "levels"}, "validators"),
        "state_contracts": ({"id", "path", "schema"}, {"id", "path", "schema"}, "state_contracts"),
        "evidence_contracts": ({"id", "path", "symbol"}, {"id", "path", "symbol"}, "evidence_records"),
        "controllers": ({"id", "path", "symbol", "boundaries"}, {"id", "path", "symbol", "boundaries"}, None),
    }
    normalized: dict[str, list[dict[str, Any]]] = {}
    all_ids: dict[str, str] = {}
    for kind, (required_keys, allowed_keys, layer) in specs.items():
        entries = _registry_list(registry[kind], f"application registry.{kind}")
        normalized[kind] = []
        for index, raw in enumerate(entries):
            label = f"application registry.{kind}[{index}]"
            _require_exact_keys(raw, required_keys, allowed_keys, label)
            item = dict(raw)
            item["id"] = _registry_id(item["id"], f"{label}.id")
            if item["id"] in all_ids:
                raise ApplicationArchitectureError(
                    f"registry id {item['id']} is ambiguous across {all_ids[item['id']]} and {kind}"
                )
            all_ids[item["id"]] = kind
            item["path"] = _safe_relative(item["path"], f"{label}.path")
            if layer and not _path_owned_by_layers(item["path"], declaration, [layer]):
                raise ApplicationArchitectureError(
                    f"{label}.path is not owned by declared layer {layer}: {item['path']}"
                )
            if kind == "controllers" and not _path_owned_by_layers(
                item["path"], declaration, ["runtime_actors", "controller_authority", "lifecycle_recovery"]
            ):
                raise ApplicationArchitectureError(
                    f"{label}.path is not owned by a declared controller-capable layer: {item['path']}"
                )
            if kind == "skills" and "execution" in item:
                execution = _require_object(item["execution"], f"{label}.execution")
                execution_keys = {"proof", "request", "ordered_tools", "validators", "evidence_contract", "max_steps", "timeout_seconds"}
                _require_exact_keys(execution, execution_keys, execution_keys, f"{label}.execution")
                if execution["proof"] is not True:
                    raise ApplicationArchitectureError(f"{label}.execution.proof must be true")
                request = _non_empty_string(execution["request"], f"{label}.execution.request")
                ordered_tools = _string_list(execution["ordered_tools"], f"{label}.execution.ordered_tools")
                validators = _string_list(execution["validators"], f"{label}.execution.validators")
                evidence_contract = _registry_id(execution["evidence_contract"], f"{label}.execution.evidence_contract")
                max_steps = execution["max_steps"]
                timeout_seconds = execution["timeout_seconds"]
                if isinstance(max_steps, bool) or not isinstance(max_steps, int) or max_steps <= 0 or max_steps > 100:
                    raise ApplicationArchitectureError(f"{label}.execution.max_steps must satisfy 0 < max_steps <= 100")
                if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, (int, float)) or timeout_seconds <= 0 or timeout_seconds > 300:
                    raise ApplicationArchitectureError(f"{label}.execution.timeout_seconds must satisfy 0 < timeout_seconds <= 300")
                if len(ordered_tools) > max_steps:
                    raise ApplicationArchitectureError(f"{label}.execution.ordered_tools exceeds max_steps")
                item["execution"] = {
                    "proof": True,
                    "request": request,
                    "ordered_tools": ordered_tools,
                    "validators": validators,
                    "evidence_contract": evidence_contract,
                    "max_steps": max_steps,
                    "timeout_seconds": timeout_seconds,
                }
            normalized[kind].append(item)
    normalized["_path"] = registry_rel  # type: ignore[assignment]
    normalized["_application_id"] = application_id  # type: ignore[assignment]
    normalized["_runtime_provider"] = runtime_provider  # type: ignore[assignment]
    return normalized


def _validate_application_registry(repo: Path, declaration: dict[str, Any]) -> dict[str, Any]:
    registry = _load_application_registry(repo, declaration)
    errors: list[str] = []
    indexes = {
        kind: {item["id"]: item for item in registry[kind]}
        for kind in ("agents", "skills", "tools", "validators", "state_contracts", "evidence_contracts", "controllers")
    }

    def require_refs(owner: str, refs: object, target: str) -> list[str]:
        try:
            values = _string_list(refs, f"{owner}.{target}")
        except ApplicationArchitectureError as exc:
            errors.append(str(exc))
            return []
        for ref in values:
            if ref not in indexes[target]:
                errors.append(f"{owner}.{target} reference does not resolve: {ref}")
        return values

    symbol_cache: dict[str, set[str]] = {}
    def require_symbol(owner: str, rel: str, symbol: object) -> None:
        symbol_name = _registry_id(symbol, f"{owner}.symbol")
        path = repo / rel
        if not path.is_file():
            errors.append(f"{owner}.path is missing: {rel}")
            return
        if rel not in symbol_cache:
            try:
                symbol_cache[rel] = _python_top_level_symbols(path)
            except ApplicationArchitectureError as exc:
                errors.append(str(exc))
                return
        if symbol_name not in symbol_cache[rel]:
            errors.append(f"{owner}.symbol does not resolve in {rel}: {symbol_name}")

    for agent in registry["agents"]:
        owner = f"agent {agent['id']}"
        require_symbol(owner, agent["path"], agent["symbol"])
        require_refs(owner, agent["skills"], "skills")
        capabilities = _string_list(agent["capabilities"], f"{owner}.capabilities")
        if capabilities:
            unknown = sorted(set(capabilities) - set(declaration["delegation"]["owned_capabilities"]))
            if unknown:
                errors.append(f"{owner}.capabilities are not declared as owned: {', '.join(unknown)}")
        require_refs(owner, agent["tools"], "tools")
        require_refs(owner, agent["validators"], "validators")
        require_refs(owner, agent["state_contracts"], "state_contracts")
        require_refs(owner, agent["evidence_contracts"], "evidence_contracts")
    agent_capabilities = {
        capability
        for agent in registry["agents"]
        for capability in (agent.get("capabilities") if isinstance(agent.get("capabilities"), list) else [])
    }
    expected_capabilities = set(declaration["delegation"]["owned_capabilities"])
    if agent_capabilities != expected_capabilities:
        missing = sorted(expected_capabilities - agent_capabilities)
        extra = sorted(agent_capabilities - expected_capabilities)
        errors.append(
            "registered agent capabilities must exactly cover declared owned capabilities"
            + (f"; missing={missing}" if missing else "")
            + (f"; extra={extra}" if extra else "")
        )

    for skill in registry["skills"]:
        owner = f"skill {skill['id']}"
        path = repo / skill["path"]
        if not path.is_file():
            errors.append(f"{owner}.path is missing: {skill['path']}")
            continue
        try:
            frontmatter = _skill_frontmatter(path)
        except ApplicationArchitectureError as exc:
            errors.append(str(exc))
            continue
        name = _non_empty_string(skill["name"], f"{owner}.name")
        if frontmatter.get("name") != name:
            errors.append(f"{owner}.name does not match SKILL.md frontmatter")
        tools = require_refs(owner, skill["tools"], "tools")
        front_tools = frontmatter.get("allowed_tools") if isinstance(frontmatter.get("allowed_tools"), list) else []
        if tools and tools != front_tools:
            errors.append(f"{owner}.tools do not exactly match SKILL.md allowed_tools")
        skill_validators = require_refs(owner, skill["validators"], "validators")
        execution = skill.get("execution") if isinstance(skill.get("execution"), dict) else None
        if execution:
            execution_tools = require_refs(f"{owner}.execution", execution["ordered_tools"], "tools")
            execution_validators = require_refs(f"{owner}.execution", execution["validators"], "validators")
            evidence_ref = execution["evidence_contract"]
            if evidence_ref not in indexes["evidence_contracts"]:
                errors.append(f"{owner}.execution.evidence_contract does not resolve: {evidence_ref}")
            if execution_tools != tools:
                errors.append(f"{owner}.execution.ordered_tools must exactly match the skill tool order")
            if execution_validators != skill_validators:
                errors.append(f"{owner}.execution.validators must exactly match the skill validators")
            non_read_only = [tool_id for tool_id in execution_tools if not bool(indexes["tools"].get(tool_id, {}).get("read_only"))]
            if non_read_only:
                errors.append(f"{owner}.execution proof may use only read-only tools: {', '.join(non_read_only)}")

    proof_skills = [skill for skill in registry["skills"] if isinstance(skill.get("execution"), dict) and skill["execution"].get("proof") is True]
    if len(proof_skills) != 1:
        errors.append("application registry must define exactly one executable proof skill")

    tool_paths = {item["path"] for item in registry["tools"]}
    if len(tool_paths) != 1:
        errors.append("registered tools must resolve through one authoritative MCP tool registry path")
        static_tools: dict[str, dict[str, Any]] = {}
    else:
        rel = next(iter(tool_paths))
        try:
            static_tools = _static_mcp_tools(repo / rel)
        except ApplicationArchitectureError as exc:
            errors.append(str(exc))
            static_tools = {}
    registered_tool_ids = set(indexes["tools"])
    if static_tools and registered_tool_ids != set(static_tools):
        errors.append(
            "registered tool ids must exactly match the authoritative MCP manifest"
            f"; missing={sorted(set(static_tools)-registered_tool_ids)}"
            f"; extra={sorted(registered_tool_ids-set(static_tools))}"
        )
    for tool in registry["tools"]:
        owner = f"tool {tool['id']}"
        if tool["provider"] != declaration["runtime"]["provider"]:
            errors.append(f"{owner}.provider does not match runtime provider")
        actual = static_tools.get(tool["id"])
        if actual:
            for field in ("collection", "risk", "read_only"):
                if tool[field] != actual[field]:
                    errors.append(f"{owner}.{field} does not match authoritative MCP manifest")

    for validator in registry["validators"]:
        owner = f"validator {validator['id']}"
        require_symbol(owner, validator["path"], validator["symbol"])
        levels = _string_list(validator["levels"], f"{owner}.levels")
        unknown = sorted(set(levels) - set(KNOWN_LEVELS))
        if unknown:
            errors.append(f"{owner}.levels contains unknown proof levels: {', '.join(unknown)}")

    for contract in registry["state_contracts"]:
        owner = f"state contract {contract['id']}"
        path = repo / contract["path"]
        if not path.is_file():
            errors.append(f"{owner}.path is missing: {contract['path']}")
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"{owner}.path is not valid JSON: {exc}")
            continue
        if not isinstance(payload, dict) or not payload.get("$schema") or not payload.get("$id"):
            errors.append(f"{owner}.path is not a self-identifying JSON schema")
        expected_schema = _non_empty_string(contract["schema"], f"{owner}.schema")
        declared_const = ((payload.get("properties") or {}).get("schema") or {}).get("const") if isinstance(payload, dict) else None
        if declared_const != expected_schema:
            errors.append(f"{owner}.schema does not match schema const in {contract['path']}")

    for evidence in registry["evidence_contracts"]:
        require_symbol(f"evidence contract {evidence['id']}", evidence["path"], evidence["symbol"])

    boundary_to_controller = {
        boundary: declaration["authority"][boundary]["controller"]
        for boundary in AUTHORITY_BOUNDARIES
    }
    for controller in registry["controllers"]:
        owner = f"controller {controller['id']}"
        require_symbol(owner, controller["path"], controller["symbol"])
        boundaries = _string_list(controller["boundaries"], f"{owner}.boundaries")
        unknown = sorted(set(boundaries) - set(AUTHORITY_BOUNDARIES))
        if unknown:
            errors.append(f"{owner}.boundaries contains unknown authority boundaries: {', '.join(unknown)}")
        for boundary in boundaries:
            if boundary_to_controller.get(boundary) != controller["id"]:
                errors.append(f"{owner} is not the declared controller for boundary {boundary}")
    for boundary, controller_id in boundary_to_controller.items():
        controller = indexes["controllers"].get(controller_id)
        if not controller:
            errors.append(f"authority.{boundary}.controller does not resolve: {controller_id}")
        elif boundary not in controller.get("boundaries", []):
            errors.append(f"authority.{boundary}.controller does not claim boundary {boundary}")

    referenced = {
        "skills": {ref for agent in registry["agents"] for ref in agent.get("skills", [])},
        "tools": {ref for agent in registry["agents"] for ref in agent.get("tools", [])}
                 | {ref for skill in registry["skills"] for ref in skill.get("tools", [])},
        "validators": {ref for agent in registry["agents"] for ref in agent.get("validators", [])}
                      | {ref for skill in registry["skills"] for ref in skill.get("validators", [])},
        "state_contracts": {ref for agent in registry["agents"] for ref in agent.get("state_contracts", [])},
        "evidence_contracts": {ref for agent in registry["agents"] for ref in agent.get("evidence_contracts", [])},
        "controllers": set(boundary_to_controller.values()),
    }
    for kind, refs in referenced.items():
        orphaned = sorted(set(indexes[kind]) - refs)
        if orphaned:
            errors.append(f"application registry contains unreferenced {kind}: {', '.join(orphaned)}")
    if not any("registry" in validator.get("levels", []) for validator in registry["validators"]):
        errors.append("application registry must include at least one registry-level validator")
    if not any("executable" in validator.get("levels", []) for validator in registry["validators"]):
        errors.append("application registry must include at least one executable-level validator")
    if proof_skills:
        evidence_ref = proof_skills[0]["execution"]["evidence_contract"]
        if evidence_ref not in referenced["evidence_contracts"]:
            referenced["evidence_contracts"].add(evidence_ref)

    return {
        "ok": not errors,
        "path": registry["_path"],
        "schema": declaration["registry"]["schema"],
        "schema_version": declaration["registry"]["schema_version"],
        "application_id": registry["_application_id"],
        "runtime_provider": registry["_runtime_provider"],
        "counts": {kind: len(indexes[kind]) for kind in indexes},
        "resolved_ids": {kind: sorted(indexes[kind]) for kind in indexes},
        "reference_resolution": "complete" if not errors else "failed",
        "authority_resolution": "bounded" if not errors else "failed",
        "executable_proof_skill": proof_skills[0]["id"] if len(proof_skills) == 1 else None,
        "error_count": len(errors),
        "errors": errors,
    }



def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _execute_registered_skill(
    repo: Path,
    skill: dict[str, Any],
    *,
    profile_dir: str | Path | None = None,
) -> dict[str, Any]:
    from promptbranch_mcp import agent_run

    execution = skill["execution"]
    interpreter = Path(sys.executable).expanduser()
    if not interpreter.is_absolute() or not interpreter.is_file():
        return {
            "ok": False,
            "status": "python_authority_invalid",
            "candidate_python": str(interpreter),
        }

    handle = tempfile.NamedTemporaryFile("w", prefix="promptbranch-executable-proof-", suffix=".py", delete=False)
    launcher_path = Path(handle.name)
    runtime_root = Path(__file__).resolve().parent
    handle.write(
        f"#!{interpreter}\n"
        "import sys\n"
        f"sys.path.insert(0, {str(runtime_root)!r})\n"
        "from promptbranch_cli import main\n"
        "raise SystemExit(main())\n"
    )
    handle.close()
    launcher_path.chmod(0o700)
    try:
        return agent_run(
            execution["request"],
            repo_path=repo,
            profile_dir=profile_dir,
            skill=skill["name"],
            proposal_mode="deterministic",
            command=str(launcher_path),
            mcp_timeout_seconds=float(execution["timeout_seconds"]),
        )
    finally:
        launcher_path.unlink(missing_ok=True)


def _validate_executable_architecture(
    repo: Path,
    declaration: dict[str, Any],
    registry_payload: dict[str, Any],
    *,
    profile_dir: str | Path | None = None,
    proof_skill: str | None = None,
) -> dict[str, Any]:
    if not registry_payload.get("ok"):
        return {
            "ok": False,
            "status": "executable_blocked_by_registry",
            "proven_level": "structural",
            "errors": list(registry_payload.get("errors") or []),
        }
    registry = _load_application_registry(repo, declaration)
    proof_skills = [
        skill for skill in registry["skills"]
        if isinstance(skill.get("execution"), dict) and skill["execution"].get("proof") is True
    ]
    if proof_skill:
        proof_skills = [skill for skill in proof_skills if skill["id"] == proof_skill or skill["name"] == proof_skill]
    if len(proof_skills) != 1:
        return {
            "ok": False,
            "status": "executable_contract_invalid",
            "proven_level": "registry",
            "errors": ["exactly one executable proof skill must be selected"],
        }
    skill = dict(proof_skills[0])
    skill["path_sha256"] = _sha256_file(repo / skill["path"])
    started_at = utc_now()
    run = _execute_registered_skill(repo, skill, profile_dir=profile_dir)
    finished_at = utc_now()
    evidence = build_skillrun_evidence(
        application_id=declaration["application"]["id"],
        runtime_provider=declaration["runtime"]["provider"],
        application_version=declaration["_version"],
        skill=skill,
        request=skill["execution"]["request"],
        run=run,
        started_at=started_at,
        finished_at=finished_at,
    )
    evidence_validation = validate_skillrun_evidence(
        evidence,
        expected_skill=skill,
        allowed_tools=skill["execution"]["ordered_tools"],
        max_steps=skill["execution"]["max_steps"],
    )
    errors: list[str] = []
    if not run.get("ok"):
        errors.append(f"registered skill execution failed: {run.get('status')}")
    actual_order = [str(item.get("name") or "") for item in run.get("plan", []) if isinstance(item, dict)]
    if actual_order != skill["execution"]["ordered_tools"]:
        errors.append("executed tool order does not match registry contract")
    if len(actual_order) > skill["execution"]["max_steps"]:
        errors.append("executed step count exceeds registry max_steps")
    if not evidence_validation.get("ok"):
        errors.extend(evidence_validation.get("errors") or [])
    return {
        "ok": not errors,
        "status": "executable_validated" if not errors else "executable_invalid",
        "proven_level": "executable" if not errors else "registry",
        "proof_skill": {
            "id": skill["id"],
            "name": skill["name"],
            "path": skill["path"],
            "path_sha256": skill["path_sha256"],
            "ordered_tools": skill["execution"]["ordered_tools"],
            "max_steps": skill["execution"]["max_steps"],
            "timeout_seconds": skill["execution"]["timeout_seconds"],
        },
        "run": run,
        "evidence": evidence,
        "evidence_validation": evidence_validation,
        "error_count": len(errors),
        "errors": errors,
        "safety": {
            "bounded": True,
            "read_only_tools_only": True,
            "mcp_transport": "stdio",
            "commands_executed": True,
            "state_mutated": False,
            "release_authority_granted": False,
            "publication_authority_granted": False,
            "adoption_authority_granted": False,
        },
    }


def build_application_architecture_evidence(
    repo_path: str | Path = ".",
    config: str = DEFAULT_DECLARATION,
    *,
    profile_dir: str | Path | None = None,
    proof_skill: str | None = None,
) -> dict[str, Any]:
    result = validate_application_architecture(
        repo_path,
        config,
        level="executable",
        profile_dir=profile_dir,
        proof_skill=proof_skill,
    )
    return {
        "ok": bool(result.get("ok")),
        "action": "application_architecture_evidence",
        "status": "skillrun_evidence_validated" if result.get("ok") else result.get("status"),
        "repo_path": str(Path(repo_path).expanduser().resolve()),
        "proven_level": result.get("proven_level", "none"),
        "proof_skill": (result.get("executable") or {}).get("proof_skill") if isinstance(result.get("executable"), dict) else None,
        "evidence": (result.get("executable") or {}).get("evidence") if isinstance(result.get("executable"), dict) else None,
        "evidence_validation": (result.get("executable") or {}).get("evidence_validation") if isinstance(result.get("executable"), dict) else None,
        "errors": list(result.get("errors") or []),
        "safety": (result.get("executable") or {}).get("safety") if isinstance(result.get("executable"), dict) else result.get("safety"),
    }

def validate_application_architecture(
    repo_path: str | Path = ".",
    config: str = DEFAULT_DECLARATION,
    *,
    level: str = "registry",
    profile_dir: str | Path | None = None,
    proof_skill: str | None = None,
    operational_evidence: str | Path | None = None,
) -> dict[str, Any]:
    repo = Path(repo_path).expanduser().resolve()
    requested_level = str(level or "registry").strip().lower()
    common = {
        "action": "application_architecture_validate",
        "repo_path": str(repo),
        "requested_level": requested_level,
        "max_supported_level": "operational",
    }
    if requested_level not in KNOWN_LEVELS:
        return {
            **common,
            "ok": False,
            "status": "unknown_validation_level",
            "proven_level": "none",
            "errors": [f"unknown validation level: {requested_level}"],
        }
    try:
        declaration = load_application_declaration(repo, config)
    except ApplicationArchitectureError as exc:
        return {
            **common,
            "ok": False,
            "status": "declaration_invalid",
            "proven_level": "none",
            "declaration_path": config,
            "errors": [str(exc)],
            "safety": {"read_only": True, "state_mutated": False},
        }

    declaration_summary = _declaration_summary(declaration)
    if requested_level == "declaration":
        return {
            **common,
            "ok": True,
            "status": "declaration_validated",
            "proven_level": "declaration",
            "declaration": declaration_summary,
            "errors": [],
            "safety": {"read_only": True, "state_mutated": False},
        }
    layer_results: dict[str, list[dict[str, Any]]] = {}
    structural_errors: list[str] = []
    for layer in LAYER_NAMES:
        results = [_asset_state(repo, rel) for rel in declaration["layers"][layer]]
        layer_results[layer] = results
        for result in results:
            if not result["ok"]:
                structural_errors.append(
                    f"layers.{layer} asset {result['path']} failed structural validation: {result['error']}"
                )

    command_cwds = []
    for command in declaration["validation"]["commands"]:
        cwd_state = _asset_state(repo, command["cwd"]) if command["cwd"] != "." else {
            "path": ".", "kind": "directory", "ok": True, "error": None
        }
        command_cwds.append({"id": command["id"], **cwd_state})
        if not cwd_state["ok"]:
            structural_errors.append(
                f"validation command {command['id']} cwd failed structural validation: {cwd_state['error']}"
            )

    base = {
        **common,
        "declaration": declaration_summary,
        "required_layers": list(LAYER_NAMES),
        "layer_count": len(LAYER_NAMES),
        "layers": layer_results,
        "delegation": declaration["delegation"],
        "authority": declaration["authority"],
        "validation_commands": declaration["validation"]["commands"],
        "validation_command_cwds": command_cwds,
        "safety": {
            "read_only": True,
            "commands_executed": False,
            "state_mutated": False,
            "release_authority_granted": False,
            "publication_authority_granted": False,
            "adoption_authority_granted": False,
        },
    }
    if structural_errors:
        return {
            **base,
            "ok": False,
            "status": "structural_invalid",
            "proven_level": "declaration",
            "error_count": len(structural_errors),
            "errors": structural_errors,
        }
    if requested_level == "structural":
        return {
            **base,
            "ok": True,
            "status": "structural_validated",
            "proven_level": "structural",
            "error_count": 0,
            "errors": [],
        }

    try:
        registry = _validate_application_registry(repo, declaration)
    except ApplicationArchitectureError as exc:
        registry = {
            "ok": False,
            "path": declaration["registry"]["path"],
            "error_count": 1,
            "errors": [str(exc)],
            "reference_resolution": "failed",
            "authority_resolution": "failed",
        }
    if requested_level == "registry":
        return {
            **base,
            "ok": bool(registry["ok"]),
            "status": "registry_validated" if registry["ok"] else "registry_invalid",
            "proven_level": "registry" if registry["ok"] else "structural",
            "registry": registry,
            "error_count": int(registry.get("error_count") or 0),
            "errors": list(registry.get("errors") or []),
        }
    executable = _validate_executable_architecture(
        repo,
        declaration,
        registry,
        profile_dir=profile_dir,
        proof_skill=proof_skill,
    )
    if requested_level == "executable":
        return {
            **base,
            "ok": bool(executable["ok"]),
            "status": executable["status"],
            "proven_level": executable["proven_level"],
            "registry": registry,
            "executable": executable,
            "error_count": int(executable.get("error_count") or 0),
            "errors": list(executable.get("errors") or []),
            "safety": executable.get("safety", base["safety"]),
        }
    if not executable["ok"]:
        return {
            **base,
            "ok": False,
            "status": executable["status"],
            "proven_level": executable["proven_level"],
            "registry": registry,
            "executable": executable,
            "error_count": int(executable.get("error_count") or 0),
            "errors": list(executable.get("errors") or []),
            "safety": executable.get("safety", base["safety"]),
        }
    if operational_evidence is None:
        return {
            **base,
            "ok": False,
            "status": "operational_evidence_required",
            "proven_level": "executable",
            "registry": registry,
            "executable": executable,
            "error_count": 1,
            "errors": ["operational validation requires --evidence with verified lifecycle/adoption evidence"],
            "safety": executable.get("safety", base["safety"]),
        }
    operational = validate_operational_lifecycle_evidence(operational_evidence, repo_path=repo)
    return {
        **base,
        "ok": bool(operational.get("ok")),
        "status": operational.get("status"),
        "proven_level": operational.get("proven_level", "executable"),
        "registry": registry,
        "executable": executable,
        "operational": operational,
        "error_count": int(operational.get("error_count") or 0),
        "errors": list(operational.get("errors") or []),
        "safety": operational.get("safety", executable.get("safety", base["safety"])),
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
    "build_application_architecture_evidence",
    "load_application_declaration",
    "plan_application_architecture",
    "validate_application_architecture",
]
