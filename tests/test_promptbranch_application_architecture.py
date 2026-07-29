from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

from promptbranch_application_architecture import (
    ApplicationArchitectureError,
    GENERIC_RUNTIME_CAPABILITIES,
    LAYER_NAMES,
    load_application_declaration,
    plan_application_architecture,
    validate_application_architecture,
)

ROOT = Path(__file__).resolve().parents[1]
DECLARATION = ROOT / ".promptbranch-ai.json"
REGISTRY = ROOT / ".promptbranch" / "ai-registry.json"
ARCH_SCHEMA = ROOT / "promptbranch_protocol" / "schemas" / "application.architecture.schema.json"
REGISTRY_SCHEMA = ROOT / "promptbranch_protocol" / "schemas" / "application.registry.schema.json"


def _base_declaration(*, kind: str = "runtime_application") -> dict:
    app_id = "sample-runtime" if kind == "runtime_application" else "sample-domain"
    provider = app_id if kind == "runtime_application" else "promptbranch"
    delegated = [] if kind == "runtime_application" else list(GENERIC_RUNTIME_CAPABILITIES)
    owned = list(GENERIC_RUNTIME_CAPABILITIES) if kind == "runtime_application" else ["domain_assessment"]
    return {
        "schema": "promptbranch.ai.application",
        "schema_version": "1.1",
        "application": {"id": app_id, "kind": kind},
        "version_authority": {"path": "VERSION", "format": "plain", "sole": True},
        "runtime": {"provider": provider, "contract_version": "1.0"},
        "registry": {"path": ".promptbranch/ai-registry.json", "schema": "promptbranch.ai.registry", "schema_version": "1.0"},
        "layers": {
            "instructions_policy": ["PROJECT_SETTINGS.md"],
            "runtime_actors": ["agent.py"],
            "skills": [".promptbranch/skills"],
            "tools": ["tools.py"],
            "validators": ["validator.py"],
            "knowledge_context": ["KNOWLEDGE.md"],
            "state_contracts": ["schemas"],
            "evidence_records": ["evidence.py"],
            "controller_authority": ["controllers.py"],
            "lifecycle_recovery": ["lifecycle.py"],
        },
        "delegation": {
            "generic_runtime_provider": provider,
            "delegated_capabilities": delegated,
            "owned_capabilities": owned,
        },
        "authority": {
            "self_grant_allowed": False,
            "mutation": {"controller": "controlled.execution", "requires_explicit_request": True, "requires_verified_evidence": True},
            "release": {"controller": "release.lifecycle", "requires_explicit_request": True, "requires_verified_evidence": True},
            "publication": {"controller": "release.publication", "requires_explicit_request": True, "requires_verified_evidence": True},
            "adoption": {"controller": "artifact.registry", "requires_explicit_request": True, "requires_verified_evidence": True},
        },
        "validation": {
            "commands": [
                {"id": "structural", "level": "structural", "argv": ["python3", "-m", "pytest", "-q"], "cwd": ".", "timeout_seconds": 60},
                {"id": "registry", "level": "registry", "argv": ["python3", "-m", "pytest", "-q"], "cwd": ".", "timeout_seconds": 60},
            ]
        },
    }


def _base_registry(declaration: dict) -> dict:
    app_id = declaration["application"]["id"]
    provider = declaration["runtime"]["provider"]
    capabilities = list(declaration["delegation"]["owned_capabilities"])
    return {
        "schema": "promptbranch.ai.registry",
        "schema_version": "1.0",
        "application_id": app_id,
        "runtime_provider": provider,
        "agents": [{
            "id": f"{app_id}.agent.main", "path": "agent.py", "symbol": "run_agent",
            "capabilities": capabilities, "skills": [f"{app_id}.skill.inspect"], "tools": ["filesystem.read"],
            "validators": [f"{app_id}.validator.main"], "state_contracts": [f"{app_id}.state.main"],
            "evidence_contracts": [f"{app_id}.evidence.main"],
        }],
        "skills": [{
            "id": f"{app_id}.skill.inspect", "path": ".promptbranch/skills/inspect/SKILL.md", "name": "inspect",
            "tools": ["filesystem.read"], "validators": [f"{app_id}.validator.main"],
        }],
        "tools": [{
            "id": "filesystem.read", "provider": provider, "path": "tools.py", "collection": "READ_ONLY_MCP_TOOLS",
            "risk": "read", "read_only": True,
        }],
        "validators": [{
            "id": f"{app_id}.validator.main", "path": "validator.py", "symbol": "validate", "levels": ["structural", "registry"],
        }],
        "state_contracts": [{
            "id": f"{app_id}.state.main", "path": "schemas/state.schema.json", "schema": f"{app_id}.state",
        }],
        "evidence_contracts": [{
            "id": f"{app_id}.evidence.main", "path": "evidence.py", "symbol": "build_evidence",
        }],
        "controllers": [
            {"id": "controlled.execution", "path": "controllers.py", "symbol": "control", "boundaries": ["mutation"]},
            {"id": "release.lifecycle", "path": "controllers.py", "symbol": "control", "boundaries": ["release"]},
            {"id": "release.publication", "path": "controllers.py", "symbol": "control", "boundaries": ["publication"]},
            {"id": "artifact.registry", "path": "controllers.py", "symbol": "control", "boundaries": ["adoption"]},
        ],
    }


def _write_repo(tmp_path: Path, data: dict | None = None) -> tuple[Path, dict, dict]:
    repo = tmp_path / "repo"
    repo.mkdir(parents=True)
    declaration = copy.deepcopy(data or _base_declaration())
    registry = _base_registry(declaration)
    (repo / "VERSION").write_text("v1.2.3\n", encoding="utf-8")
    files = {
        "PROJECT_SETTINGS.md": "policy\n",
        "agent.py": "def run_agent():\n    return None\n",
        "tools.py": '''\nfrom enum import Enum\nclass ToolRisk(Enum):\n    READ = "read"\nclass McpToolSpec:\n    def __init__(self, **kwargs): pass\nREAD_ONLY_MCP_TOOLS = (McpToolSpec(name="filesystem.read"),)\nCONTROLLED_PROCESS_MCP_TOOLS = ()\n''',
        "validator.py": "def validate():\n    return True\n",
        "KNOWLEDGE.md": "knowledge\n",
        "evidence.py": "def build_evidence():\n    return {}\n",
        "controllers.py": "def control():\n    return None\n",
        "lifecycle.py": "def recover():\n    return None\n",
    }
    for rel, text in files.items():
        path = repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    skill = repo / ".promptbranch/skills/inspect/SKILL.md"
    skill.parent.mkdir(parents=True, exist_ok=True)
    skill.write_text("---\nname: inspect\ndescription: inspect\nrisk: read\nallowed_tools:\n  - filesystem.read\nprechecks:\n  - repo_path_exists\n---\n\n## Procedure\n\n1. Inspect.\n", encoding="utf-8")
    schema = repo / "schemas/state.schema.json"
    schema.parent.mkdir(parents=True, exist_ok=True)
    schema.write_text(json.dumps({
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://example.invalid/state.schema.json",
        "type": "object",
        "properties": {"schema": {"const": f"{declaration['application']['id']}.state"}},
    }, indent=2) + "\n", encoding="utf-8")
    (repo / ".promptbranch").mkdir(parents=True, exist_ok=True)
    (repo / ".promptbranch/ai-registry.json").write_text(json.dumps(registry, indent=2) + "\n", encoding="utf-8")
    (repo / ".promptbranch-ai.json").write_text(json.dumps(declaration, indent=2) + "\n", encoding="utf-8")
    return repo, declaration, registry


def _rewrite_declaration(repo: Path, payload: dict) -> None:
    (repo / ".promptbranch-ai.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _rewrite_registry(repo: Path, payload: dict) -> None:
    (repo / ".promptbranch/ai-registry.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def test_promptbranch_runtime_passes_structural_and_registry_validation() -> None:
    structural = validate_application_architecture(ROOT, level="structural")
    assert structural["ok"] is True, structural.get("errors")
    assert structural["status"] == "structural_validated"
    assert structural["proven_level"] == "structural"
    registry = validate_application_architecture(ROOT, level="registry")
    assert registry["ok"] is True, registry.get("errors")
    assert registry["status"] == "registry_validated"
    assert registry["proven_level"] == "registry"
    assert registry["max_supported_level"] == "registry"
    assert registry["registry"]["reference_resolution"] == "complete"
    assert registry["registry"]["authority_resolution"] == "bounded"
    assert registry["registry"]["counts"] == {
        "agents": 1, "skills": 2, "tools": 10, "validators": 4,
        "state_contracts": 3, "evidence_contracts": 1, "controllers": 4,
    }
    assert registry["safety"]["commands_executed"] is False
    assert registry["safety"]["adoption_authority_granted"] is False


def test_schemas_and_tracked_files_are_strict() -> None:
    declaration = json.loads(DECLARATION.read_text(encoding="utf-8"))
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    arch_schema = json.loads(ARCH_SCHEMA.read_text(encoding="utf-8"))
    registry_schema = json.loads(REGISTRY_SCHEMA.read_text(encoding="utf-8"))
    assert declaration["schema_version"] == "1.1"
    assert declaration["registry"] == {"path": ".promptbranch/ai-registry.json", "schema": "promptbranch.ai.registry", "schema_version": "1.0"}
    assert registry["schema"] == "promptbranch.ai.registry"
    assert arch_schema["additionalProperties"] is False
    assert arch_schema["properties"]["registry"]["additionalProperties"] is False
    assert registry_schema["additionalProperties"] is False
    assert registry_schema["properties"]["controllers"]["items"]["$ref"] == "#/$defs/controller"


def test_plan_is_read_only_and_plans_registry_without_overclaiming() -> None:
    payload = plan_application_architecture(ROOT)
    assert payload["status"] == "planned_read_only"
    assert payload["requested_level"] == "registry"
    assert payload["proven_level"] == "declaration"
    assert payload["max_supported_level"] == "registry"
    assert payload["declaration"]["registry"]["path"] == ".promptbranch/ai-registry.json"
    assert payload["safety"]["commands_executed"] is False


def test_cli_registry_validate_emits_json() -> None:
    completed = subprocess.run(
        [sys.executable, "promptbranch_cli.py", "application", "architecture", "validate", "--repo-path", str(ROOT), "--level", "registry", "--json"],
        cwd=ROOT, check=False, text=True, capture_output=True,
    )
    assert completed.returncode == 0, completed.stderr + completed.stdout
    payload = json.loads(completed.stdout)
    assert payload["status"] == "registry_validated"
    assert payload["proven_level"] == "registry"


def test_unknown_declaration_field_fails_closed(tmp_path: Path) -> None:
    repo, declaration, _ = _write_repo(tmp_path)
    declaration["unexpected"] = True
    _rewrite_declaration(repo, declaration)
    with pytest.raises(ApplicationArchitectureError, match="unknown fields"):
        load_application_declaration(repo)


def test_missing_or_empty_layer_fails_closed(tmp_path: Path) -> None:
    repo, declaration, _ = _write_repo(tmp_path)
    del declaration["layers"]["tools"]
    _rewrite_declaration(repo, declaration)
    with pytest.raises(ApplicationArchitectureError, match="missing required fields: tools"):
        load_application_declaration(repo)
    repo2, declaration2, _ = _write_repo(tmp_path / "empty")
    declaration2["layers"]["tools"] = []
    _rewrite_declaration(repo2, declaration2)
    with pytest.raises(ApplicationArchitectureError, match="non-empty array"):
        load_application_declaration(repo2)


def test_unsafe_and_ambiguous_layer_paths_fail_closed(tmp_path: Path) -> None:
    repo, declaration, _ = _write_repo(tmp_path)
    declaration["layers"]["tools"] = ["../outside"]
    _rewrite_declaration(repo, declaration)
    with pytest.raises(ApplicationArchitectureError, match="without traversal"):
        load_application_declaration(repo)
    repo2, declaration2, _ = _write_repo(tmp_path / "duplicate")
    declaration2["layers"]["tools"] = list(declaration2["layers"]["runtime_actors"])
    _rewrite_declaration(repo2, declaration2)
    with pytest.raises(ApplicationArchitectureError, match="unambiguous ownership"):
        load_application_declaration(repo2)


def test_structural_failure_never_overclaims(tmp_path: Path) -> None:
    repo, declaration, _ = _write_repo(tmp_path)
    (repo / declaration["layers"]["validators"][0]).unlink()
    result = validate_application_architecture(repo, level="registry")
    assert result["ok"] is False
    assert result["status"] == "structural_invalid"
    assert result["proven_level"] == "declaration"


def test_delegation_and_authority_declaration_contracts_remain_fail_closed(tmp_path: Path) -> None:
    repo, declaration, _ = _write_repo(tmp_path)
    declaration["delegation"]["owned_capabilities"].remove("verification")
    _rewrite_declaration(repo, declaration)
    with pytest.raises(ApplicationArchitectureError, match="generic runtime contract"):
        load_application_declaration(repo)
    repo2, declaration2, _ = _write_repo(tmp_path / "authority")
    declaration2["authority"]["adoption"]["controller"] = "self"
    _rewrite_declaration(repo2, declaration2)
    with pytest.raises(ApplicationArchitectureError, match="may not self-grant"):
        load_application_declaration(repo2)


def test_domain_module_structural_contract_remains_supported(tmp_path: Path) -> None:
    repo, declaration, _ = _write_repo(tmp_path, _base_declaration(kind="domain_module"))
    result = validate_application_architecture(repo, level="structural")
    assert result["ok"] is True
    assert result["declaration"]["application"]["kind"] == "domain_module"
    declaration["runtime"]["provider"] = declaration["application"]["id"]
    declaration["delegation"]["generic_runtime_provider"] = declaration["application"]["id"]
    _rewrite_declaration(repo, declaration)
    with pytest.raises(ApplicationArchitectureError, match="another provider"):
        load_application_declaration(repo)


def test_registry_file_missing_or_schema_mismatch_fails_at_registry_only(tmp_path: Path) -> None:
    repo, declaration, registry = _write_repo(tmp_path)
    (repo / declaration["registry"]["path"]).unlink()
    result = validate_application_architecture(repo, level="registry")
    assert result["status"] == "registry_invalid"
    assert result["proven_level"] == "structural"
    repo2, _, registry2 = _write_repo(tmp_path / "schema")
    registry2["schema_version"] = "2.0"
    _rewrite_registry(repo2, registry2)
    result2 = validate_application_architecture(repo2, level="registry")
    assert result2["status"] == "registry_invalid"
    assert any("schema identity" in error for error in result2["errors"])


def test_registry_unknown_field_and_cross_kind_duplicate_id_fail_closed(tmp_path: Path) -> None:
    repo, _, registry = _write_repo(tmp_path)
    registry["unexpected"] = True
    _rewrite_registry(repo, registry)
    result = validate_application_architecture(repo, level="registry")
    assert any("unknown fields" in error for error in result["errors"])
    repo2, _, registry2 = _write_repo(tmp_path / "duplicate")
    registry2["skills"][0]["id"] = registry2["agents"][0]["id"]
    _rewrite_registry(repo2, registry2)
    result2 = validate_application_architecture(repo2, level="registry")
    assert any("ambiguous across" in error for error in result2["errors"])


@pytest.mark.parametrize("field,target", [
    ("skills", "missing.skill"), ("tools", "missing.tool"), ("validators", "missing.validator"),
    ("state_contracts", "missing.state"), ("evidence_contracts", "missing.evidence"),
])
def test_agent_references_must_resolve(tmp_path: Path, field: str, target: str) -> None:
    repo, _, registry = _write_repo(tmp_path)
    registry["agents"][0][field] = [target]
    _rewrite_registry(repo, registry)
    result = validate_application_architecture(repo, level="registry")
    assert result["status"] == "registry_invalid"
    assert any("does not resolve" in error for error in result["errors"])


def test_python_symbols_and_layer_ownership_must_resolve(tmp_path: Path) -> None:
    repo, _, registry = _write_repo(tmp_path)
    registry["validators"][0]["symbol"] = "missing_symbol"
    _rewrite_registry(repo, registry)
    result = validate_application_architecture(repo, level="registry")
    assert any("symbol does not resolve" in error for error in result["errors"])
    repo2, _, registry2 = _write_repo(tmp_path / "ownership")
    registry2["validators"][0]["path"] = "agent.py"
    _rewrite_registry(repo2, registry2)
    result2 = validate_application_architecture(repo2, level="registry")
    assert any("not owned by declared layer validators" in error for error in result2["errors"])


def test_skill_tools_must_match_frontmatter_and_resolve(tmp_path: Path) -> None:
    repo, _, registry = _write_repo(tmp_path)
    skill_path = repo / registry["skills"][0]["path"]
    skill_path.write_text(skill_path.read_text().replace("filesystem.read", "git.status"), encoding="utf-8")
    result = validate_application_architecture(repo, level="registry")
    assert any("do not exactly match" in error for error in result["errors"])


def test_registered_tools_must_exactly_match_static_mcp_manifest(tmp_path: Path) -> None:
    repo, _, registry = _write_repo(tmp_path)
    registry["tools"][0]["read_only"] = False
    _rewrite_registry(repo, registry)
    result = validate_application_architecture(repo, level="registry")
    assert any("read_only does not match" in error for error in result["errors"])
    repo2, _, registry2 = _write_repo(tmp_path / "missing")
    (repo2 / "tools.py").write_text((repo2 / "tools.py").read_text().replace('McpToolSpec(name="filesystem.read")', 'McpToolSpec(name="filesystem.read"), McpToolSpec(name="git.status")'), encoding="utf-8")
    result2 = validate_application_architecture(repo2, level="registry")
    assert any("exactly match the authoritative MCP manifest" in error for error in result2["errors"])


def test_state_schema_identity_must_match_registry(tmp_path: Path) -> None:
    repo, _, registry = _write_repo(tmp_path)
    registry["state_contracts"][0]["schema"] = "wrong.schema"
    _rewrite_registry(repo, registry)
    result = validate_application_architecture(repo, level="registry")
    assert any("does not match schema const" in error for error in result["errors"])


def test_agent_capabilities_must_exactly_cover_declared_ownership(tmp_path: Path) -> None:
    repo, _, registry = _write_repo(tmp_path)
    registry["agents"][0]["capabilities"].remove("verification")
    _rewrite_registry(repo, registry)
    result = validate_application_architecture(repo, level="registry")
    assert any("exactly cover" in error for error in result["errors"])


def test_authority_controller_references_must_resolve_and_be_bounded(tmp_path: Path) -> None:
    repo, declaration, registry = _write_repo(tmp_path)
    declaration["authority"]["adoption"]["controller"] = "missing.controller"
    _rewrite_declaration(repo, declaration)
    result = validate_application_architecture(repo, level="registry")
    assert any("does not resolve" in error for error in result["errors"])
    repo2, _, registry2 = _write_repo(tmp_path / "boundary")
    registry2["controllers"][-1]["boundaries"] = ["release"]
    _rewrite_registry(repo2, registry2)
    result2 = validate_application_architecture(repo2, level="registry")
    assert any("not the declared controller" in error or "does not claim" in error for error in result2["errors"])


def test_validation_commands_require_structural_and_registry_levels(tmp_path: Path) -> None:
    repo, declaration, _ = _write_repo(tmp_path)
    declaration["validation"]["commands"] = declaration["validation"]["commands"][:1]
    _rewrite_declaration(repo, declaration)
    with pytest.raises(ApplicationArchitectureError, match="registry command"):
        load_application_declaration(repo)


def test_executable_and_operational_fail_closed_at_proven_registry() -> None:
    for level in ("executable", "operational"):
        result = validate_application_architecture(ROOT, level=level)
        assert result["ok"] is False
        assert result["status"] == "validation_level_not_implemented"
        assert result["proven_level"] == "registry"
        assert result["max_supported_level"] == "registry"


def test_validation_is_read_only_and_executes_no_declared_commands(tmp_path: Path) -> None:
    repo, declaration, _ = _write_repo(tmp_path)
    marker = repo / "must-not-exist"
    declaration["validation"]["commands"][-1]["argv"] = ["python3", "-c", f"open({str(marker)!r}, 'w').write('bad')"]
    _rewrite_declaration(repo, declaration)
    result = validate_application_architecture(repo, level="registry")
    assert result["ok"] is True
    assert not marker.exists()
    assert result["safety"]["commands_executed"] is False
