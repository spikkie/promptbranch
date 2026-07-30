from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Iterable

from promptbranch_application_architecture import (
    DEFAULT_DECLARATION,
    GENERIC_RUNTIME_CAPABILITIES,
    ApplicationArchitectureError,
    validate_application_architecture,
)

TEMPLATE_SCHEMA = "promptbranch.ai.template.plan"
TEMPLATE_SCHEMA_VERSION = "1.0"
MIGRATION_SCHEMA = "promptbranch.ai.migration.report"
MIGRATION_SCHEMA_VERSION = "1.0"
DIFFERENTIAL_SCHEMA = "promptbranch.ai.differential"
DIFFERENTIAL_SCHEMA_VERSION = "1.0"
DIFFERENTIAL_REPORT_SCHEMA = "promptbranch.ai.differential.report"
DIFFERENTIAL_REPORT_SCHEMA_VERSION = "1.0"
APPLICATION_KINDS = {"runtime_application", "domain_module"}
MUTATION_KINDS = {"none", "remove", "empty", "json_add_unknown_field", "json_set"}
OUTCOMES = {"pass", "fail"}


class ApplicationMigrationError(ValueError):
    """Raised when template, migration, or differential inputs are invalid."""


def _safe_relative(value: str, label: str, *, allow_dot: bool = False) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ApplicationMigrationError(f"{label} must be a non-empty string")
    text = value.strip()
    if "\\" in text:
        raise ApplicationMigrationError(f"{label} must use forward slashes")
    path = Path(text)
    if path.is_absolute() or ".." in path.parts:
        raise ApplicationMigrationError(f"{label} must be repository-relative without traversal")
    if text == "." and not allow_dot:
        raise ApplicationMigrationError(f"{label} may not be the repository root")
    return path.as_posix()


def _identifier(value: str, label: str) -> str:
    import re

    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", value.strip()):
        raise ApplicationMigrationError(
            f"{label} must contain only letters, digits, dots, underscores, or hyphens"
        )
    return value.strip()


def _exact_keys(value: dict[str, Any], required: Iterable[str], label: str) -> None:
    required_set = set(required)
    missing = sorted(required_set - set(value))
    unknown = sorted(set(value) - required_set)
    if missing:
        raise ApplicationMigrationError(f"{label} missing required fields: {', '.join(missing)}")
    if unknown:
        raise ApplicationMigrationError(f"{label} contains unknown fields: {', '.join(unknown)}")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _json_text(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def _skill_text(name: str, application_id: str) -> str:
    return f"""---
name: {name}
description: Execute the bounded PBAI-001 proof for {application_id} using repository-local read-only tools.
risk: read
allowed_tools:
  - filesystem.read
  - filesystem.list
prechecks:
  - repo_path_exists
  - architecture_declaration_exists
  - tool_read_only
---

## Procedure

1. Read the tracked `.promptbranch-ai.json` declaration.
2. List the tracked `.promptbranch` AI control directory.
3. Return bounded read-only evidence only; never mutate repository, publication, release, or adoption state.
"""


def _tools_text() -> str:
    return """from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ToolRisk(str, Enum):
    READ = "read"


@dataclass(frozen=True)
class McpToolSpec:
    name: str
    risk: ToolRisk
    read_only: bool = True


# Domain modules expose only the Promptbranch tools they are contractually
# permitted to request. Promptbranch remains the runtime provider.
READ_ONLY_MCP_TOOLS = (
    McpToolSpec(name="filesystem.read", risk=ToolRisk.READ, read_only=True),
    McpToolSpec(name="filesystem.list", risk=ToolRisk.READ, read_only=True),
)
"""


def _actors_text(application_id: str, owned_capabilities: list[str]) -> str:
    return f'''from __future__ import annotations


def domain_architecture_actor() -> dict[str, object]:
    """Return the bounded domain actor contract without executing generic runtime work."""
    return {{
        "application_id": {application_id!r},
        "owned_capabilities": {owned_capabilities!r},
        "delegates_generic_runtime_to": "promptbranch",
        "read_only": True,
    }}
'''


def _validators_text() -> str:
    return '''from __future__ import annotations


def validate_domain_result(value: object) -> bool:
    """Fail closed unless the proof result is an explicit successful object."""
    return isinstance(value, dict) and value.get("ok") is True
'''


def _evidence_text() -> str:
    return '''from __future__ import annotations


def validate_domain_evidence(value: object) -> bool:
    return isinstance(value, dict) and bool(value.get("schema")) and bool(value.get("evidence_id"))
'''


def _authority_text() -> str:
    return '''from __future__ import annotations


def controlled_execution_adapter() -> dict[str, object]:
    return {"controller": "promptbranch.controlled_execution", "delegated": True, "self_grant": False}


def release_lifecycle_adapter() -> dict[str, object]:
    return {"controller": "promptbranch.release.lifecycle", "delegated": True, "self_grant": False}


def publication_adapter() -> dict[str, object]:
    return {"controller": "promptbranch.release.publication", "delegated": True, "self_grant": False}


def artifact_registry_adapter() -> dict[str, object]:
    return {"controller": "promptbranch.artifact.registry", "delegated": True, "self_grant": False}
'''


def _schema(application_id: str) -> dict[str, Any]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": f"https://promptbranch.local/{application_id}/schemas/domain-proof.schema.json",
        "title": f"{application_id} domain proof",
        "type": "object",
        "additionalProperties": False,
        "required": ["schema", "ok"],
        "properties": {
            "schema": {"const": f"{application_id}.domain_proof"},
            "ok": {"const": True},
        },
    }


def build_application_template(
    *,
    kind: str,
    application_id: str,
    version_path: str = "VERSION",
    runtime_provider: str = "promptbranch",
    contract_version: str = "1.0",
) -> dict[str, Any]:
    kind = str(kind).strip()
    if kind not in APPLICATION_KINDS:
        raise ApplicationMigrationError("kind must be runtime_application or domain_module")
    application_id = _identifier(application_id, "application_id")
    version_path = _safe_relative(version_path, "version_path")
    runtime_provider = _identifier(runtime_provider, "runtime_provider")
    if kind == "runtime_application" and runtime_provider != application_id:
        raise ApplicationMigrationError("runtime_application runtime_provider must equal application_id")
    if kind == "domain_module" and runtime_provider == application_id:
        raise ApplicationMigrationError("domain_module must use a different generic runtime provider")

    if kind == "runtime_application":
        delegated: list[str] = []
        owned = list(GENERIC_RUNTIME_CAPABILITIES)
    else:
        delegated = list(GENERIC_RUNTIME_CAPABILITIES)
        owned = [
            "domain_instructions",
            "domain_actors",
            "domain_skills",
            "domain_tools",
            "domain_validators",
            "domain_knowledge",
            "domain_contracts",
            "domain_evidence",
            "domain_authority_hooks",
            "domain_lifecycle_hooks",
        ]

    proof_skill_name = "application-architecture-proof"
    layers = {
        "instructions_policy": ["PROJECT_SETTINGS.md", "AGENTS.md"],
        "runtime_actors": [".promptbranch/ai/actors.py"],
        "skills": [".promptbranch/skills"],
        "tools": [".promptbranch/ai/tools.py"],
        "validators": [".promptbranch/ai/validators.py"],
        "knowledge_context": [".promptbranch/ai/knowledge"],
        "state_contracts": [".promptbranch/ai/contracts"],
        "evidence_records": [".promptbranch/ai/evidence.py"],
        "controller_authority": [".promptbranch/ai/authority.py"],
        "lifecycle_recovery": [".promptbranch/ai/lifecycle"],
    }
    declaration = {
        "schema": "promptbranch.ai.application",
        "schema_version": "1.3",
        "application": {"id": application_id, "kind": kind},
        "version_authority": {"path": version_path, "format": "plain", "sole": True},
        "runtime": {"provider": runtime_provider, "contract_version": contract_version},
        "registry": {
            "path": ".promptbranch/ai-registry.json",
            "schema": "promptbranch.ai.registry",
            "schema_version": "1.1",
        },
        "layers": layers,
        "delegation": {
            "generic_runtime_provider": runtime_provider,
            "delegated_capabilities": delegated,
            "owned_capabilities": owned,
        },
        "authority": {
            "self_grant_allowed": False,
            "mutation": {
                "controller": "promptbranch.controlled_execution",
                "requires_explicit_request": True,
                "requires_verified_evidence": True,
            },
            "release": {
                "controller": "promptbranch.release.lifecycle",
                "requires_explicit_request": True,
                "requires_verified_evidence": True,
            },
            "publication": {
                "controller": "promptbranch.release.publication",
                "requires_explicit_request": True,
                "requires_verified_evidence": True,
            },
            "adoption": {
                "controller": "promptbranch.artifact.registry",
                "requires_explicit_request": True,
                "requires_verified_evidence": True,
            },
        },
        "validation": {
            "commands": [
                {
                    "id": "pbai-001-structural",
                    "level": "structural",
                    "argv": ["pb", "application", "architecture", "validate", "--repo-path", ".", "--level", "structural", "--json"],
                    "cwd": ".",
                    "timeout_seconds": 120,
                },
                {
                    "id": "pbai-001-registry",
                    "level": "registry",
                    "argv": ["pb", "application", "architecture", "validate", "--repo-path", ".", "--level", "registry", "--json"],
                    "cwd": ".",
                    "timeout_seconds": 120,
                },
                {
                    "id": "pbai-001-executable",
                    "level": "executable",
                    "argv": ["pb", "application", "architecture", "validate", "--repo-path", ".", "--level", "executable", "--json"],
                    "cwd": ".",
                    "timeout_seconds": 180,
                },
            ]
        },
    }

    agent_id = f"{application_id}.agent.domain"
    skill_id = f"{application_id}.skill.architecture-proof"
    validator_id = f"{application_id}.validator.domain-result"
    state_id = f"{application_id}.state.domain-proof"
    evidence_id = f"{application_id}.evidence.domain-proof"
    registry = {
        "schema": "promptbranch.ai.registry",
        "schema_version": "1.1",
        "application_id": application_id,
        "runtime_provider": runtime_provider,
        "agents": [
            {
                "id": agent_id,
                "path": ".promptbranch/ai/actors.py",
                "symbol": "domain_architecture_actor",
                "capabilities": owned,
                "skills": [skill_id],
                "tools": ["filesystem.read", "filesystem.list"],
                "validators": [validator_id],
                "state_contracts": [state_id],
                "evidence_contracts": [evidence_id],
            }
        ],
        "skills": [
            {
                "id": skill_id,
                "path": f".promptbranch/skills/{proof_skill_name}/SKILL.md",
                "name": proof_skill_name,
                "tools": ["filesystem.read", "filesystem.list"],
                "validators": [validator_id],
                "execution": {
                    "proof": True,
                    "request": f"Execute the tracked PBAI-001 proof for {application_id} using only repository-bounded read-only tools.",
                    "ordered_tools": ["filesystem.read", "filesystem.list"],
                    "validators": [validator_id],
                    "evidence_contract": evidence_id,
                    "max_steps": 2,
                    "timeout_seconds": 30,
                },
            }
        ],
        "tools": [
            {
                "id": "filesystem.read",
                "provider": runtime_provider,
                "path": ".promptbranch/ai/tools.py",
                "collection": "READ_ONLY_MCP_TOOLS",
                "risk": "read",
                "read_only": True,
            },
            {
                "id": "filesystem.list",
                "provider": runtime_provider,
                "path": ".promptbranch/ai/tools.py",
                "collection": "READ_ONLY_MCP_TOOLS",
                "risk": "read",
                "read_only": True,
            },
        ],
        "validators": [
            {
                "id": validator_id,
                "path": ".promptbranch/ai/validators.py",
                "symbol": "validate_domain_result",
                "levels": ["structural", "registry", "executable"],
            }
        ],
        "state_contracts": [
            {
                "id": state_id,
                "path": ".promptbranch/ai/contracts/domain-proof.schema.json",
                "schema": f"{application_id}.domain_proof",
            }
        ],
        "evidence_contracts": [
            {
                "id": evidence_id,
                "path": ".promptbranch/ai/evidence.py",
                "symbol": "validate_domain_evidence",
            }
        ],
        "controllers": [
            {
                "id": "promptbranch.controlled_execution",
                "path": ".promptbranch/ai/authority.py",
                "symbol": "controlled_execution_adapter",
                "boundaries": ["mutation"],
            },
            {
                "id": "promptbranch.release.lifecycle",
                "path": ".promptbranch/ai/authority.py",
                "symbol": "release_lifecycle_adapter",
                "boundaries": ["release"],
            },
            {
                "id": "promptbranch.release.publication",
                "path": ".promptbranch/ai/authority.py",
                "symbol": "publication_adapter",
                "boundaries": ["publication"],
            },
            {
                "id": "promptbranch.artifact.registry",
                "path": ".promptbranch/ai/authority.py",
                "symbol": "artifact_registry_adapter",
                "boundaries": ["adoption"],
            },
        ],
    }

    project_settings = f"""# Project settings

## PBAI-001 application architecture

- Application id: `{application_id}`
- Application kind: `{kind}`
- Generic runtime provider: `{runtime_provider}`
- The tracked declaration is `.promptbranch-ai.json`.
- `VERSION` (or the configured version authority) is the sole version source.
- Architecture validation is fail-closed and reports only the highest proven level.
- Mutation, release, publication, and adoption require explicit requests and verified Promptbranch evidence.
- Missing declarations or migration gaps require an explicit migration report; no silent compatibility fallback is permitted.
"""
    agents = f"""# Agent instructions

## PBAI-001 invariant

This repository is a `{kind}` named `{application_id}`. Follow the tracked `.promptbranch-ai.json` declaration and `.promptbranch/ai-registry.json`. Execute only registered skills, use only bounded tools, validate every result, preserve evidence, and never self-grant mutation, release, publication, or adoption authority.
"""
    lifecycle = """# Lifecycle and recovery

Promptbranch owns generic correction, release, publication, adoption, verification, and recovery. This application supplies project-local gates and domain evidence only. Any failed gate leaves accepted/current unchanged.
"""
    knowledge = f"""# Authoritative domain context

This directory contains the reviewed knowledge and project context for `{application_id}`. Replace this template text with authoritative, versioned domain sources before production use.
"""

    files: dict[str, str] = {
        DEFAULT_DECLARATION: _json_text(declaration),
        ".promptbranch/ai-registry.json": _json_text(registry),
        f".promptbranch/skills/{proof_skill_name}/SKILL.md": _skill_text(proof_skill_name, application_id),
        ".promptbranch/ai/actors.py": _actors_text(application_id, owned),
        ".promptbranch/ai/tools.py": _tools_text(),
        ".promptbranch/ai/validators.py": _validators_text(),
        ".promptbranch/ai/evidence.py": _evidence_text(),
        ".promptbranch/ai/authority.py": _authority_text(),
        ".promptbranch/ai/contracts/domain-proof.schema.json": _json_text(_schema(application_id)),
        ".promptbranch/ai/knowledge/README.md": knowledge,
        ".promptbranch/ai/lifecycle/README.md": lifecycle,
        "PROJECT_SETTINGS.md": project_settings,
        "AGENTS.md": agents,
    }
    if version_path == "VERSION":
        files["VERSION"] = "v0.1.0\n"

    manifest = [
        {"path": path, "sha256": _sha256_bytes(text.encode("utf-8")), "size_bytes": len(text.encode("utf-8"))}
        for path, text in sorted(files.items())
    ]
    return {
        "ok": True,
        "action": "application_architecture_template",
        "status": "template_plan_ready",
        "schema": TEMPLATE_SCHEMA,
        "schema_version": TEMPLATE_SCHEMA_VERSION,
        "application_id": application_id,
        "kind": kind,
        "runtime_provider": runtime_provider,
        "version_path": version_path,
        "files": files,
        "manifest": manifest,
        "file_count": len(files),
        "safety": {"plan_only": True, "state_mutated": False, "explicit_write_required": True},
    }


def write_application_template(
    output_dir: str | Path,
    *,
    kind: str,
    application_id: str,
    version_path: str = "VERSION",
    runtime_provider: str = "promptbranch",
    contract_version: str = "1.0",
    force: bool = False,
) -> dict[str, Any]:
    plan = build_application_template(
        kind=kind,
        application_id=application_id,
        version_path=version_path,
        runtime_provider=runtime_provider,
        contract_version=contract_version,
    )
    root = Path(output_dir).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    conflicts = [path for path in plan["files"] if (root / path).exists()]
    if conflicts and not force:
        return {
            **{key: value for key, value in plan.items() if key != "files"},
            "ok": False,
            "status": "template_write_conflict",
            "output_dir": str(root),
            "conflicts": sorted(conflicts),
            "written": [],
            "safety": {"plan_only": False, "state_mutated": False, "explicit_write_required": True},
        }
    written: list[str] = []
    for rel, text in sorted(plan["files"].items()):
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        written.append(rel)
    return {
        **{key: value for key, value in plan.items() if key != "files"},
        "ok": True,
        "status": "template_written",
        "output_dir": str(root),
        "conflicts": sorted(conflicts),
        "written": written,
        "safety": {"plan_only": False, "state_mutated": True, "explicit_write_required": True},
    }


def _candidate_paths(repo: Path, names: list[str]) -> list[str]:
    return [name for name in names if (repo / name).exists()]


def build_application_migration_report(
    repo_path: str | Path = ".",
    *,
    kind: str | None = None,
    application_id: str | None = None,
    runtime_provider: str = "promptbranch",
    config: str = DEFAULT_DECLARATION,
) -> dict[str, Any]:
    repo = Path(repo_path).expanduser().resolve()
    if not repo.is_dir():
        raise ApplicationMigrationError(f"repository path not found: {repo}")
    config = _safe_relative(config, "config")
    declaration_exists = (repo / config).is_file()
    inferred_id = application_id or repo.name.replace("_", "-")
    inferred_id = _identifier(inferred_id, "application_id")
    requested_kind = kind or "domain_module"
    if requested_kind not in APPLICATION_KINDS:
        raise ApplicationMigrationError("kind must be runtime_application or domain_module")
    version_candidates = _candidate_paths(repo, ["VERSION", "pyproject.toml", "src/version.py"])
    discovered = {
        "instructions_policy": _candidate_paths(repo, ["PROJECT_SETTINGS.md", "AGENTS.md", "README.md"]),
        "runtime_actors": _candidate_paths(repo, ["src", "promptbranch_orchestration.py", "agents"]),
        "skills": _candidate_paths(repo, [".promptbranch/skills", "skills"]),
        "tools": _candidate_paths(repo, ["tools", "src", "promptbranch_mcp.py"]),
        "validators": _candidate_paths(repo, ["scripts/validate.sh", "scripts/validate-project-control-surface.py", "validators", "tests"]),
        "knowledge_context": _candidate_paths(repo, ["corpus", "knowledge", "docs/architecture"]),
        "state_contracts": _candidate_paths(repo, ["schemas", "contracts"]),
        "evidence_records": _candidate_paths(repo, ["evidence", "docs/project/definition-of-done.md", "fixtures"]),
        "controller_authority": _candidate_paths(repo, ["PROJECT_SETTINGS.md", ".promptbranch-repo.json", "docs/architecture/integration-boundary.md"]),
        "lifecycle_recovery": _candidate_paths(repo, ["scripts/run-release-lifecycle.sh", ".promptbranch-release.json", ".promptbranch-release.yml", "docs/project/migration.md"]),
    }
    gaps: list[dict[str, str]] = []
    if not declaration_exists:
        gaps.append({"code": "declaration_missing", "path": config, "required_action": "review and add a tracked declaration"})
    if not version_candidates:
        gaps.append({"code": "version_authority_missing", "path": "VERSION", "required_action": "add one sole version authority"})
    for layer, paths in discovered.items():
        if not paths:
            gaps.append({"code": "layer_unresolved", "path": layer, "required_action": "select or create at least one authoritative asset"})
    validation: dict[str, Any] | None = None
    if declaration_exists:
        validation = validate_application_architecture(repo, config, level="structural")
        if not validation.get("ok"):
            for error in validation.get("errors") or []:
                gaps.append({"code": "structural_validation_failed", "path": config, "required_action": str(error)})
    template_plan = build_application_template(
        kind=requested_kind,
        application_id=inferred_id,
        version_path=version_candidates[0] if version_candidates and version_candidates[0] == "VERSION" else "VERSION",
        runtime_provider=runtime_provider if requested_kind == "domain_module" else inferred_id,
    )
    status = "already_migrated" if declaration_exists and validation and validation.get("ok") else "migration_required"
    return {
        "ok": True,
        "action": "application_architecture_migration_report",
        "status": status,
        "schema": MIGRATION_SCHEMA,
        "schema_version": MIGRATION_SCHEMA_VERSION,
        "repo_path": str(repo),
        "application_id": inferred_id,
        "requested_kind": requested_kind,
        "runtime_provider": runtime_provider,
        "declaration": {"path": config, "exists": declaration_exists},
        "version_authority_candidates": version_candidates,
        "discovered_layer_candidates": discovered,
        "gap_count": len(gaps),
        "gaps": gaps,
        "current_structural_validation": validation,
        "template_manifest": template_plan["manifest"],
        "recommended_commands": [
            f"pb application architecture template --kind {requested_kind} --application-id {inferred_id} --output-dir . --json",
            f"pb application architecture validate --repo-path . --level structural --json",
            f"pb application architecture validate --repo-path . --level registry --json",
        ],
        "not_performed": [
            "declaration_write",
            "registry_write",
            "asset_creation",
            "existing_file_overwrite",
            "validation_command_execution",
            "release",
            "publication",
            "adoption",
        ],
        "safety": {"read_only": True, "state_mutated": False, "silent_migration": False},
    }


def write_migration_report(report: dict[str, Any], output: str | Path) -> Path:
    target = Path(output).expanduser().resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(_json_text(report), encoding="utf-8")
    return target


def _load_differential_config(repo: Path, config: str) -> dict[str, Any]:
    rel = _safe_relative(config, "differential config")
    path = repo / rel
    if not path.is_file():
        raise ApplicationMigrationError(f"differential config not found: {rel}")
    try:
        root = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ApplicationMigrationError(f"invalid differential config: {exc}") from exc
    if not isinstance(root, dict):
        raise ApplicationMigrationError("differential config must be an object")
    _exact_keys(root, {"schema", "schema_version", "reference", "promptbranch", "cases"}, "differential config")
    if root["schema"] != DIFFERENTIAL_SCHEMA or root["schema_version"] != DIFFERENTIAL_SCHEMA_VERSION:
        raise ApplicationMigrationError("unsupported differential config schema")
    reference = root["reference"]
    if not isinstance(reference, dict):
        raise ApplicationMigrationError("reference must be an object")
    _exact_keys(reference, {"id", "argv", "cwd", "timeout_seconds"}, "reference")
    _identifier(reference["id"], "reference.id")
    if not isinstance(reference["argv"], list) or not reference["argv"] or not all(isinstance(x, str) and x for x in reference["argv"]):
        raise ApplicationMigrationError("reference.argv must be a non-empty string array")
    if Path(reference["argv"][0]).name.lower() in {"sh", "bash", "zsh", "fish", "cmd", "powershell", "pwsh"}:
        raise ApplicationMigrationError("reference.argv may not invoke a shell")
    reference["cwd"] = _safe_relative(reference["cwd"], "reference.cwd", allow_dot=True)
    timeout = reference["timeout_seconds"]
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or timeout <= 0 or timeout > 300:
        raise ApplicationMigrationError("reference.timeout_seconds must satisfy 0 < timeout <= 300")
    pb = root["promptbranch"]
    if not isinstance(pb, dict):
        raise ApplicationMigrationError("promptbranch must be an object")
    _exact_keys(pb, {"config", "level"}, "promptbranch")
    pb["config"] = _safe_relative(pb["config"], "promptbranch.config")
    if pb["level"] not in {"declaration", "structural", "registry", "executable"}:
        raise ApplicationMigrationError("promptbranch.level is unsupported for differential validation")
    cases = root["cases"]
    if not isinstance(cases, list) or not cases:
        raise ApplicationMigrationError("cases must be a non-empty array")
    normalized_cases: list[dict[str, Any]] = []
    ids: set[str] = set()
    for index, case in enumerate(cases):
        label = f"cases[{index}]"
        if not isinstance(case, dict):
            raise ApplicationMigrationError(f"{label} must be an object")
        _exact_keys(case, {"id", "mutation", "expect_reference", "expect_promptbranch"}, label)
        case_id = _identifier(case["id"], f"{label}.id")
        if case_id in ids:
            raise ApplicationMigrationError("case ids must be unique")
        ids.add(case_id)
        if case["expect_reference"] not in OUTCOMES or case["expect_promptbranch"] not in OUTCOMES:
            raise ApplicationMigrationError(f"{label} expected outcomes must be pass or fail")
        mutation = case["mutation"]
        if not isinstance(mutation, dict) or "kind" not in mutation:
            raise ApplicationMigrationError(f"{label}.mutation must contain kind")
        kind = mutation["kind"]
        if kind not in MUTATION_KINDS:
            raise ApplicationMigrationError(f"{label}.mutation.kind is unsupported")
        required = {"kind"}
        if kind in {"remove", "empty"}:
            required |= {"path"}
        elif kind == "json_add_unknown_field":
            required |= {"path", "field", "value"}
        elif kind == "json_set":
            required |= {"path", "pointer", "value"}
        _exact_keys(mutation, required, f"{label}.mutation")
        if "path" in mutation:
            mutation["path"] = _safe_relative(mutation["path"], f"{label}.mutation.path")
        normalized_cases.append({**case, "id": case_id, "mutation": dict(mutation)})
    return {**root, "reference": reference, "promptbranch": pb, "cases": normalized_cases, "_path": rel}


def _apply_mutation(root: Path, mutation: dict[str, Any]) -> None:
    kind = mutation["kind"]
    if kind == "none":
        return
    target = root / mutation["path"]
    if kind == "remove":
        if target.is_dir():
            shutil.rmtree(target)
        else:
            target.unlink(missing_ok=True)
        return
    if kind == "empty":
        if target.is_dir():
            shutil.rmtree(target)
            target.mkdir(parents=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("", encoding="utf-8")
        return
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ApplicationMigrationError(f"cannot mutate JSON {mutation['path']}: {exc}") from exc
    if kind == "json_add_unknown_field":
        if not isinstance(payload, dict):
            raise ApplicationMigrationError("json_add_unknown_field target must be an object")
        payload[mutation["field"]] = mutation["value"]
    elif kind == "json_set":
        pointer = str(mutation["pointer"])
        if not pointer.startswith("/"):
            raise ApplicationMigrationError("json_set pointer must begin with /")
        parts = [part.replace("~1", "/").replace("~0", "~") for part in pointer[1:].split("/")]
        node: Any = payload
        for part in parts[:-1]:
            if isinstance(node, dict):
                node = node[part]
            elif isinstance(node, list):
                node = node[int(part)]
            else:
                raise ApplicationMigrationError("json_set pointer does not resolve")
        last = parts[-1]
        if isinstance(node, dict):
            node[last] = mutation["value"]
        elif isinstance(node, list):
            node[int(last)] = mutation["value"]
        else:
            raise ApplicationMigrationError("json_set pointer does not resolve")
    target.write_text(_json_text(payload), encoding="utf-8")


def _copy_repo(source: Path, destination: Path) -> None:
    ignored = shutil.ignore_patterns(".git", ".pb_profile", ".pytest_cache", "__pycache__", "*.pyc", "dist", "*.zip")
    shutil.copytree(source, destination, ignore=ignored)


def _run_reference(root: Path, config: dict[str, Any]) -> dict[str, Any]:
    reference = config["reference"]
    cwd = root if reference["cwd"] == "." else root / reference["cwd"]
    started = time.monotonic()
    try:
        result = subprocess.run(
            reference["argv"],
            cwd=cwd,
            text=True,
            capture_output=True,
            timeout=float(reference["timeout_seconds"]),
            check=False,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
        timed_out = False
        returncode = result.returncode
        stdout = result.stdout
        stderr = result.stderr
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        returncode = 124
        stdout = exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr = exc.stderr.decode() if isinstance(exc.stderr, bytes) else (exc.stderr or "")
    return {
        "ok": returncode == 0 and not timed_out,
        "outcome": "pass" if returncode == 0 and not timed_out else "fail",
        "returncode": returncode,
        "timed_out": timed_out,
        "duration_seconds": round(time.monotonic() - started, 6),
        "stdout_tail": stdout[-4000:],
        "stderr_tail": stderr[-4000:],
    }


def differential_validate_application(
    repo_path: str | Path = ".",
    *,
    config: str = ".promptbranch/ai-differential.json",
) -> dict[str, Any]:
    repo = Path(repo_path).expanduser().resolve()
    if not repo.is_dir():
        raise ApplicationMigrationError(f"repository path not found: {repo}")
    differential = _load_differential_config(repo, config)
    results: list[dict[str, Any]] = []
    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="promptbranch-ai-differential-") as tmp:
        base = Path(tmp)
        for index, case in enumerate(differential["cases"]):
            case_root = base / f"{index:03d}-{case['id']}"
            _copy_repo(repo, case_root)
            _apply_mutation(case_root, case["mutation"])
            reference = _run_reference(case_root, differential)
            pb = validate_application_architecture(
                case_root,
                differential["promptbranch"]["config"],
                level=differential["promptbranch"]["level"],
            )
            pb_outcome = "pass" if pb.get("ok") else "fail"
            relation = "equivalent"
            if reference["outcome"] == "pass" and pb_outcome == "fail":
                relation = "promptbranch_stronger"
            elif reference["outcome"] == "fail" and pb_outcome == "pass":
                relation = "promptbranch_weaker"
            expected_ok = (
                reference["outcome"] == case["expect_reference"]
                and pb_outcome == case["expect_promptbranch"]
            )
            stronger_ok = not (reference["outcome"] == "fail" and pb_outcome == "pass")
            case_ok = expected_ok and stronger_ok
            if not case_ok:
                errors.append(
                    f"case {case['id']} mismatch: reference={reference['outcome']} "
                    f"promptbranch={pb_outcome} expected={case['expect_reference']}/{case['expect_promptbranch']}"
                )
            results.append(
                {
                    "id": case["id"],
                    "mutation": case["mutation"],
                    "expected": {
                        "reference": case["expect_reference"],
                        "promptbranch": case["expect_promptbranch"],
                    },
                    "reference": reference,
                    "promptbranch": {
                        "ok": bool(pb.get("ok")),
                        "outcome": pb_outcome,
                        "status": pb.get("status"),
                        "proven_level": pb.get("proven_level"),
                        "errors": list(pb.get("errors") or []),
                    },
                    "relation": relation,
                    "ok": case_ok,
                }
            )
    weaker_cases = [item["id"] for item in results if item["relation"] == "promptbranch_weaker"]
    stronger_cases = [item["id"] for item in results if item["relation"] == "promptbranch_stronger"]
    ok = not errors and not weaker_cases
    return {
        "ok": ok,
        "action": "application_architecture_differential_validate",
        "status": "equivalent_or_stronger" if ok else "differential_validation_failed",
        "schema": DIFFERENTIAL_REPORT_SCHEMA,
        "schema_version": DIFFERENTIAL_REPORT_SCHEMA_VERSION,
        "repo_path": str(repo),
        "config": differential["_path"],
        "reference_validator": differential["reference"]["id"],
        "promptbranch_level": differential["promptbranch"]["level"],
        "case_count": len(results),
        "passed_case_count": sum(1 for item in results if item["ok"]),
        "stronger_cases": stronger_cases,
        "weaker_cases": weaker_cases,
        "results": results,
        "errors": errors,
        "safety": {
            "source_repo_read_only": True,
            "isolated_case_copies": True,
            "shell_execution": False,
            "timeouts_bounded": True,
            "state_mutated": False,
            "release_authority_granted": False,
        },
    }
