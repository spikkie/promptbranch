from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

BEHAVIORAL_SURFACE_REL = Path("docs/project/promptbranch-behavioral-surface-v0.1.109.1.json")
BEHAVIORAL_SURFACE_SCHEMA = "promptbranch.project.behavioral_surface"
BEHAVIORAL_SURFACE_SCHEMA_VERSION = "1.0"
_ALLOWED_KINDS = {"instruction", "skill", "agent", "tool", "prompt"}


def _root(repo_path: str | Path) -> Path:
    return Path(repo_path).expanduser().resolve()


def _load_registry(root: Path) -> dict[str, Any]:
    path = root / BEHAVIORAL_SURFACE_REL
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"missing behavioral surface registry: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid behavioral surface registry {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"behavioral surface registry must be an object: {path}")
    return payload


def _declared_location_errors(root: Path, entry_id: str, label: str, location: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    path_value = str(location.get("path") or "")
    if not path_value:
        return [f"{entry_id}: {label}.path is required"]
    path = root / path_value
    if not path.is_file():
        return [f"{entry_id}: {label} file missing: {path_value}"]
    text = path.read_text(encoding="utf-8", errors="replace")
    token = location.get("token")
    if token and str(token) not in text:
        errors.append(f"{entry_id}: {label} token not found in {path_value}: {token!r}")
    symbol = location.get("symbol")
    if symbol:
        pattern = re.compile(rf"(?:^|\n)\s*(?:async\s+def|def|class)\s+{re.escape(str(symbol))}\b|\b{re.escape(str(symbol))}\s*[:=]", re.MULTILINE)
        if not pattern.search(text):
            errors.append(f"{entry_id}: {label} symbol not found in {path_value}: {symbol}")
    return errors


def _owner_exists(root: Path, entry: dict[str, Any]) -> list[str]:
    entry_id = str(entry.get("id") or "<missing-id>")
    owner = entry.get("owner") if isinstance(entry.get("owner"), dict) else {}
    return _declared_location_errors(root, entry_id, "owner", owner)


def _discovery(root: Path) -> dict[str, Any]:
    result: dict[str, Any] = {"operator_instruction_occurrences": {}, "system_prompt_occurrences": {}}
    for rel in ("promptbranch_cli.py", "promptbranch_loop.py", "promptbranch_parallel_ask.py"):
        path = root / rel
        if path.is_file():
            result["operator_instruction_occurrences"][rel] = path.read_text(encoding="utf-8", errors="replace").count("operator_instruction")
    for rel in ("promptbranch_mcp.py", "ollama_mcp_verification_harness/verify_ollama_mcp_trust.py", "ollama_mcp_verification_harness_v2/verify_ollama_mcp_trust_v2.py"):
        path = root / rel
        if path.is_file():
            result["system_prompt_occurrences"][rel] = len(re.findall(r'[\"\']role[\"\']\s*:\s*[\"\']system[\"\']', path.read_text(encoding="utf-8", errors="replace")))
    return result


def build_behavioral_surface_show_payload(repo_path: str | Path = ".", *, kind: str | None = None, consumer: str | None = None) -> dict[str, Any]:
    root = _root(repo_path)
    try:
        registry = _load_registry(root)
    except ValueError as exc:
        return {"ok": False, "action": "behavioral_surface_show", "status": "behavioral_surface_missing", "repo_path": str(root), "registry_path": str(root / BEHAVIORAL_SURFACE_REL), "error": str(exc)}
    entries = registry.get("entries") if isinstance(registry.get("entries"), list) else []
    selected = [entry for entry in entries if isinstance(entry, dict)]
    if kind:
        selected = [entry for entry in selected if entry.get("kind") == kind]
    if consumer:
        selected = [entry for entry in selected if consumer.lower() in str(entry.get("consumer") or "").lower()]
    counts = Counter(str(entry.get("kind") or "unknown") for entry in entries if isinstance(entry, dict))
    return {
        "ok": True,
        "action": "behavioral_surface_show",
        "status": "behavioral_surface_loaded",
        "repo_path": str(root),
        "registry_path": str(root / BEHAVIORAL_SURFACE_REL),
        "schema": registry.get("schema"),
        "schema_version": registry.get("schema_version"),
        "registry_version": registry.get("registry_version"),
        "entry_count": len(entries),
        "selected_count": len(selected),
        "counts_by_kind": dict(sorted(counts.items())),
        "filters": {"kind": kind, "consumer": consumer},
        "entries": selected,
        "discovery": _discovery(root),
        "mutation_performed": False,
        "writes_attempted": 0,
    }


def validate_behavioral_surface(repo_path: str | Path = ".") -> dict[str, Any]:
    root = _root(repo_path)
    errors: list[str] = []
    warnings: list[str] = []
    try:
        registry = _load_registry(root)
    except ValueError as exc:
        return {"ok": False, "action": "behavioral_surface_validate", "status": "behavioral_surface_missing", "repo_path": str(root), "registry_path": str(root / BEHAVIORAL_SURFACE_REL), "errors": [str(exc)], "error_count": 1, "mutation_performed": False, "writes_attempted": 0}
    if registry.get("schema") != BEHAVIORAL_SURFACE_SCHEMA:
        errors.append(f"schema must be {BEHAVIORAL_SURFACE_SCHEMA}")
    if registry.get("schema_version") != BEHAVIORAL_SURFACE_SCHEMA_VERSION:
        errors.append(f"schema_version must be {BEHAVIORAL_SURFACE_SCHEMA_VERSION}")
    if registry.get("validation_mode") != "read_only":
        errors.append("validation_mode must be read_only")
    if registry.get("remote_mutation_allowed") is not False:
        errors.append("remote_mutation_allowed must be false")
    entries = registry.get("entries")
    if not isinstance(entries, list) or not entries:
        errors.append("entries must be a non-empty list")
        entries = []
    ids: set[str] = set()
    kinds: set[str] = set()
    tool_entries: dict[str, dict[str, Any]] = {}
    for index, raw in enumerate(entries):
        if not isinstance(raw, dict):
            errors.append(f"entry {index} must be an object")
            continue
        entry_id = str(raw.get("id") or "")
        kind = str(raw.get("kind") or "")
        if not entry_id:
            errors.append(f"entry {index} missing id")
        elif entry_id in ids:
            errors.append(f"duplicate behavioral surface id: {entry_id}")
        ids.add(entry_id)
        if kind not in _ALLOWED_KINDS:
            errors.append(f"{entry_id or index}: unsupported kind: {kind!r}")
        kinds.add(kind)
        for field in ("name", "consumer", "execution_boundary", "risk", "mutation_authority"):
            if raw.get(field) in (None, ""):
                errors.append(f"{entry_id or index}: {field} is required")
        tests = raw.get("tests") if isinstance(raw.get("tests"), list) else []
        if not tests:
            errors.append(f"{entry_id or index}: at least one test path is required")
        for test_path in tests:
            if not (root / str(test_path)).is_file():
                errors.append(f"{entry_id or index}: test file missing: {test_path}")
        errors.extend(_owner_exists(root, raw))
        if kind in {"skill", "agent"}:
            allowed_tools = raw.get("allowed_tools") if isinstance(raw.get("allowed_tools"), list) else []
            if kind == "skill" and not raw.get("skill_name"):
                errors.append(f"{entry_id}: skill_name is required")
            for tool in allowed_tools:
                if not isinstance(tool, str) or not tool:
                    errors.append(f"{entry_id}: invalid allowed tool: {tool!r}")
        elif kind == "tool":
            tool_name = str(raw.get("tool_name") or "")
            if not tool_name:
                errors.append(f"{entry_id}: tool_name is required")
            elif tool_name in tool_entries:
                errors.append(f"duplicate tool ownership: {tool_name}")
            tool_entries[tool_name] = raw
            if raw.get("exposure") not in {"read_only", "controlled_process", "blocked"}:
                errors.append(f"{entry_id}: invalid tool exposure")
            dispatcher = raw.get("dispatcher") if isinstance(raw.get("dispatcher"), dict) else {}
            if not dispatcher:
                errors.append(f"{entry_id}: dispatcher is required")
            else:
                errors.extend(_declared_location_errors(root, entry_id, "dispatcher", dispatcher))
        elif kind == "prompt":
            for field in ("recipient", "role", "template_token", "output_contract", "parser", "retry_behavior"):
                if raw.get(field) in (None, ""):
                    errors.append(f"{entry_id}: prompt field {field} is required")
    required_kinds = set((registry.get("coverage") or {}).get("required_kinds") or []) if isinstance(registry.get("coverage"), dict) else set()
    missing_kinds = sorted(required_kinds - kinds)
    if missing_kinds:
        errors.append(f"missing behavioral surface kinds: {missing_kinds}")

    try:
        from promptbranch_mcp import (BLOCKED_WRITE_MCP_TOOL_NAMES, CONTROLLED_PROCESS_MCP_TOOLS, CONTROLLED_PROCESS_TOOL_ALIASES, READ_ONLY_MCP_TOOLS, BUILTIN_SKILL_DOCS, _tool_input_schema)
        actual_read = {item.name for item in READ_ONLY_MCP_TOOLS}
        actual_process = {item.name for item in CONTROLLED_PROCESS_MCP_TOOLS}
        actual_blocked = set(BLOCKED_WRITE_MCP_TOOL_NAMES)
        expected_read = {name for name, entry in tool_entries.items() if entry.get("exposure") == "read_only"}
        expected_process = {name for name, entry in tool_entries.items() if entry.get("exposure") == "controlled_process"}
        expected_blocked = {name for name, entry in tool_entries.items() if entry.get("exposure") == "blocked"}
        if actual_read != expected_read:
            errors.append(f"read-only tool inventory drift: registry={sorted(expected_read)} runtime={sorted(actual_read)}")
        if actual_process != expected_process:
            errors.append(f"controlled-process tool inventory drift: registry={sorted(expected_process)} runtime={sorted(actual_process)}")
        if actual_blocked != expected_blocked:
            errors.append(f"blocked tool inventory drift: registry={sorted(expected_blocked)} runtime={sorted(actual_blocked)}")
        for alias, target in CONTROLLED_PROCESS_TOOL_ALIASES.items():
            if target not in actual_process:
                errors.append(f"tool alias {alias} targets missing controlled tool {target}")
        for name in sorted(actual_read | actual_process):
            schema = _tool_input_schema(name)
            if not isinstance(schema, dict) or schema.get("type") != "object":
                errors.append(f"tool input schema missing or invalid: {name}")
        for raw in entries:
            if not isinstance(raw, dict) or raw.get("kind") != "skill":
                continue
            for tool in raw.get("allowed_tools") or []:
                if tool not in actual_read | actual_process:
                    errors.append(f"{raw.get('id')}: unknown allowed tool: {tool}")
            projection = raw.get("projection") if isinstance(raw.get("projection"), dict) else None
            owner = raw.get("owner") if isinstance(raw.get("owner"), dict) else {}
            skill_name = str(raw.get("skill_name") or "")
            if projection and projection.get("kind") == "builtin_skill_doc":
                file_text = (root / str(owner.get("path"))).read_text(encoding="utf-8").strip()
                builtin_text = str(BUILTIN_SKILL_DOCS.get(skill_name) or "").strip()
                if not builtin_text:
                    errors.append(f"{raw.get('id')}: builtin skill projection missing: {skill_name}")
                elif file_text != builtin_text:
                    errors.append(f"{raw.get('id')}: file-backed skill differs from BUILTIN_SKILL_DOCS projection")
    except Exception as exc:
        errors.append(f"runtime behavioral surface inspection failed: {exc}")

    discovery = _discovery(root)
    operator_files = set((registry.get("coverage") or {}).get("operator_instruction_files") or []) if isinstance(registry.get("coverage"), dict) else set()
    for rel, count in discovery.get("operator_instruction_occurrences", {}).items():
        if count and rel not in operator_files:
            errors.append(f"unregistered operator-instruction owner: {rel}")
    system_files = set((registry.get("coverage") or {}).get("system_prompt_files") or []) if isinstance(registry.get("coverage"), dict) else set()
    for rel, count in discovery.get("system_prompt_occurrences", {}).items():
        if count and rel not in system_files:
            errors.append(f"unregistered system-prompt owner: {rel}")
    if discovery.get("system_prompt_occurrences", {}).get("ollama_mcp_verification_harness/verify_ollama_mcp_trust.py", 0):
        warnings.append("Verification-harness system prompts are inventoried as discovered test surfaces, not production agent authorities.")
    counts = Counter(str(entry.get("kind") or "unknown") for entry in entries if isinstance(entry, dict))
    return {
        "ok": not errors,
        "action": "behavioral_surface_validate",
        "status": "behavioral_surface_consistent" if not errors else "behavioral_surface_drift",
        "repo_path": str(root),
        "registry_path": str(root / BEHAVIORAL_SURFACE_REL),
        "schema": registry.get("schema"),
        "schema_version": registry.get("schema_version"),
        "registry_version": registry.get("registry_version"),
        "entry_count": len(entries),
        "counts_by_kind": dict(sorted(counts.items())),
        "error_count": len(errors),
        "errors": errors,
        "warnings": warnings,
        "discovery": discovery,
        "mutation_performed": False,
        "writes_attempted": 0,
        "remote_mutation_allowed": False,
    }
