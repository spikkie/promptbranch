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
SCHEMA = ROOT / "promptbranch_protocol" / "schemas" / "application.architecture.schema.json"


def _base_declaration(*, kind: str = "runtime_application") -> dict:
    app_id = "sample-runtime" if kind == "runtime_application" else "sample-domain"
    provider = app_id if kind == "runtime_application" else "promptbranch"
    delegated = [] if kind == "runtime_application" else list(GENERIC_RUNTIME_CAPABILITIES)
    owned = list(GENERIC_RUNTIME_CAPABILITIES) if kind == "runtime_application" else ["domain_assessment"]
    return {
        "schema": "promptbranch.ai.application",
        "schema_version": "1.0",
        "application": {"id": app_id, "kind": kind},
        "version_authority": {"path": "VERSION", "format": "plain", "sole": True},
        "runtime": {"provider": provider, "contract_version": "1.0"},
        "layers": {layer: [f"layers/{index:02d}-{layer}.txt"] for index, layer in enumerate(LAYER_NAMES, 1)},
        "delegation": {
            "generic_runtime_provider": provider,
            "delegated_capabilities": delegated,
            "owned_capabilities": owned,
        },
        "authority": {
            "self_grant_allowed": False,
            "mutation": {
                "controller": "controlled.execution",
                "requires_explicit_request": True,
                "requires_verified_evidence": True,
            },
            "release": {
                "controller": "release.lifecycle",
                "requires_explicit_request": True,
                "requires_verified_evidence": True,
            },
            "publication": {
                "controller": "release.publication",
                "requires_explicit_request": True,
                "requires_verified_evidence": True,
            },
            "adoption": {
                "controller": "artifact.registry",
                "requires_explicit_request": True,
                "requires_verified_evidence": True,
            },
        },
        "validation": {
            "commands": [
                {
                    "id": "structural",
                    "level": "structural",
                    "argv": ["python3", "-m", "pytest", "-q"],
                    "cwd": ".",
                    "timeout_seconds": 60,
                }
            ]
        },
    }


def _write_repo(tmp_path: Path, data: dict | None = None) -> tuple[Path, dict]:
    repo = tmp_path / "repo"
    repo.mkdir(parents=True)
    payload = copy.deepcopy(data or _base_declaration())
    (repo / "VERSION").write_text("v1.2.3\n", encoding="utf-8")
    for entries in payload["layers"].values():
        for rel in entries:
            path = repo / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f"asset:{rel}\n", encoding="utf-8")
    (repo / ".promptbranch-ai.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return repo, payload


def _rewrite(repo: Path, payload: dict) -> None:
    (repo / ".promptbranch-ai.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def test_promptbranch_runtime_declaration_passes_structural_validation() -> None:
    payload = validate_application_architecture(ROOT, level="structural")
    assert payload["ok"] is True, payload.get("errors")
    assert payload["status"] == "structural_validated"
    assert payload["proven_level"] == "structural"
    assert payload["max_supported_level"] == "structural"
    assert payload["declaration"]["application"] == {
        "id": "promptbranch",
        "kind": "runtime_application",
    }
    assert payload["layer_count"] == 10
    assert list(payload["layers"]) == list(LAYER_NAMES)
    assert payload["safety"]["read_only"] is True
    assert payload["safety"]["commands_executed"] is False
    assert payload["safety"]["adoption_authority_granted"] is False


def test_schema_and_tracked_declaration_are_strict() -> None:
    declaration = json.loads(DECLARATION.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    assert declaration["schema"] == "promptbranch.ai.application"
    assert declaration["schema_version"] == "1.0"
    assert schema["additionalProperties"] is False
    assert schema["properties"]["layers"]["additionalProperties"] is False
    assert schema["properties"]["authority"]["properties"]["self_grant_allowed"]["const"] is False


def test_plan_is_read_only_and_does_not_overclaim() -> None:
    payload = plan_application_architecture(ROOT)
    assert payload["ok"] is True
    assert payload["status"] == "planned_read_only"
    assert payload["proven_level"] == "declaration"
    assert payload["requested_level"] == "structural"
    assert payload["max_supported_level"] == "structural"
    assert len(payload["layer_plan"]) == 10
    assert payload["safety"] == {
        "read_only": True,
        "commands_executed": False,
        "state_mutated": False,
        "release_authority_granted": False,
        "publication_authority_granted": False,
        "adoption_authority_granted": False,
    }


def test_cli_plan_and_structural_validate_emit_json() -> None:
    plan = subprocess.run(
        [sys.executable, "promptbranch_cli.py", "application", "architecture", "plan", "--repo-path", str(ROOT), "--json"],
        cwd=ROOT,
        check=False,
        text=True,
        capture_output=True,
    )
    assert plan.returncode == 0, plan.stderr + plan.stdout
    plan_payload = json.loads(plan.stdout)
    assert plan_payload["status"] == "planned_read_only"
    assert plan_payload["proven_level"] == "declaration"

    validate = subprocess.run(
        [sys.executable, "promptbranch_cli.py", "application", "architecture", "validate", "--repo-path", str(ROOT), "--level", "structural", "--json"],
        cwd=ROOT,
        check=False,
        text=True,
        capture_output=True,
    )
    assert validate.returncode == 0, validate.stderr + validate.stdout
    validate_payload = json.loads(validate.stdout)
    assert validate_payload["status"] == "structural_validated"
    assert validate_payload["proven_level"] == "structural"


def test_unknown_top_level_field_fails_closed(tmp_path: Path) -> None:
    repo, payload = _write_repo(tmp_path)
    payload["unexpected"] = True
    _rewrite(repo, payload)
    with pytest.raises(ApplicationArchitectureError, match="unknown fields"):
        load_application_declaration(repo)


def test_missing_and_empty_layers_fail_closed(tmp_path: Path) -> None:
    repo, payload = _write_repo(tmp_path)
    del payload["layers"]["tools"]
    _rewrite(repo, payload)
    with pytest.raises(ApplicationArchitectureError, match="missing required fields: tools"):
        load_application_declaration(repo)

    repo2, payload2 = _write_repo(tmp_path / "empty")
    payload2["layers"]["tools"] = []
    _rewrite(repo2, payload2)
    with pytest.raises(ApplicationArchitectureError, match="layers.tools must be a non-empty array"):
        load_application_declaration(repo2)


def test_absolute_path_and_traversal_fail_closed(tmp_path: Path) -> None:
    repo, payload = _write_repo(tmp_path)
    payload["layers"]["tools"] = ["/etc/passwd"]
    _rewrite(repo, payload)
    with pytest.raises(ApplicationArchitectureError, match="repository-relative path"):
        load_application_declaration(repo)

    repo2, payload2 = _write_repo(tmp_path / "traversal")
    payload2["layers"]["tools"] = ["../outside"]
    _rewrite(repo2, payload2)
    with pytest.raises(ApplicationArchitectureError, match="without traversal"):
        load_application_declaration(repo2)


def test_repeated_layer_path_is_ambiguous_and_rejected(tmp_path: Path) -> None:
    repo, payload = _write_repo(tmp_path)
    payload["layers"]["tools"] = list(payload["layers"]["skills"])
    _rewrite(repo, payload)
    with pytest.raises(ApplicationArchitectureError, match="unambiguous ownership"):
        load_application_declaration(repo)


def test_structural_validation_fails_on_missing_or_empty_asset_without_overclaiming(tmp_path: Path) -> None:
    repo, payload = _write_repo(tmp_path)
    missing_rel = payload["layers"]["validators"][0]
    (repo / missing_rel).unlink()
    result = validate_application_architecture(repo, level="structural")
    assert result["ok"] is False
    assert result["status"] == "structural_invalid"
    assert result["proven_level"] == "declaration"
    assert any("path_missing" in error for error in result["errors"])

    empty_rel = payload["layers"]["tools"][0]
    (repo / empty_rel).write_text("", encoding="utf-8")
    result2 = validate_application_architecture(repo, level="structural")
    assert result2["ok"] is False
    assert result2["proven_level"] == "declaration"
    assert any("file_empty" in error for error in result2["errors"])


def test_runtime_delegation_contract_is_exact(tmp_path: Path) -> None:
    repo, payload = _write_repo(tmp_path)
    payload["delegation"]["owned_capabilities"].remove("verification")
    _rewrite(repo, payload)
    with pytest.raises(ApplicationArchitectureError, match="generic runtime contract"):
        load_application_declaration(repo)

    repo2, payload2 = _write_repo(tmp_path / "delegated")
    payload2["delegation"]["delegated_capabilities"] = ["verification"]
    _rewrite(repo2, payload2)
    with pytest.raises(ApplicationArchitectureError, match="may not delegate"):
        load_application_declaration(repo2)


def test_domain_module_must_delegate_generic_runtime_and_cannot_self_provide(tmp_path: Path) -> None:
    repo, payload = _write_repo(tmp_path, _base_declaration(kind="domain_module"))
    result = validate_application_architecture(repo, level="structural")
    assert result["ok"] is True
    assert result["declaration"]["application"]["kind"] == "domain_module"

    payload["delegation"]["generic_runtime_provider"] = payload["application"]["id"]
    payload["runtime"]["provider"] = payload["application"]["id"]
    _rewrite(repo, payload)
    with pytest.raises(ApplicationArchitectureError, match="another provider"):
        load_application_declaration(repo)


def test_self_granted_or_unbounded_authority_is_rejected(tmp_path: Path) -> None:
    repo, payload = _write_repo(tmp_path)
    payload["authority"]["self_grant_allowed"] = True
    _rewrite(repo, payload)
    with pytest.raises(ApplicationArchitectureError, match="must be false"):
        load_application_declaration(repo)

    repo2, payload2 = _write_repo(tmp_path / "implicit")
    payload2["authority"]["adoption"]["controller"] = "self"
    _rewrite(repo2, payload2)
    with pytest.raises(ApplicationArchitectureError, match="may not self-grant"):
        load_application_declaration(repo2)

    repo3, payload3 = _write_repo(tmp_path / "evidence")
    payload3["authority"]["release"]["requires_verified_evidence"] = False
    _rewrite(repo3, payload3)
    with pytest.raises(ApplicationArchitectureError, match="requires_verified_evidence must be true"):
        load_application_declaration(repo3)


def test_shell_or_unbounded_validation_command_is_rejected(tmp_path: Path) -> None:
    repo, payload = _write_repo(tmp_path)
    payload["validation"]["commands"][0]["argv"] = ["bash", "-lc", "pytest"]
    _rewrite(repo, payload)
    with pytest.raises(ApplicationArchitectureError, match="may not invoke a shell"):
        load_application_declaration(repo)

    repo2, payload2 = _write_repo(tmp_path / "timeout")
    payload2["validation"]["commands"][0]["timeout_seconds"] = 14401
    _rewrite(repo2, payload2)
    with pytest.raises(ApplicationArchitectureError, match="0 < timeout <= 14400"):
        load_application_declaration(repo2)


def test_version_authority_is_sole_present_and_supported(tmp_path: Path) -> None:
    repo, payload = _write_repo(tmp_path)
    payload["version_authority"]["sole"] = False
    _rewrite(repo, payload)
    with pytest.raises(ApplicationArchitectureError, match="sole must be true"):
        load_application_declaration(repo)

    repo2, _payload2 = _write_repo(tmp_path / "missing")
    (repo2 / "VERSION").unlink()
    result = validate_application_architecture(repo2, level="declaration")
    assert result["ok"] is False
    assert result["status"] == "declaration_invalid"
    assert result["proven_level"] == "none"



def test_repository_root_is_not_a_layer_asset(tmp_path: Path) -> None:
    repo, payload = _write_repo(tmp_path)
    payload["layers"]["tools"] = ["."]
    _rewrite(repo, payload)
    with pytest.raises(ApplicationArchitectureError, match="repository asset, not the repository root"):
        load_application_declaration(repo)


def test_backslash_paths_are_rejected_as_non_portable(tmp_path: Path) -> None:
    repo, payload = _write_repo(tmp_path)
    payload["layers"]["tools"] = [r"..\outside"]
    _rewrite(repo, payload)
    with pytest.raises(ApplicationArchitectureError, match="portable forward-slash"):
        load_application_declaration(repo)


def test_runtime_provider_must_match_delegation_provider(tmp_path: Path) -> None:
    repo, payload = _write_repo(tmp_path)
    payload["runtime"]["provider"] = "different-runtime"
    _rewrite(repo, payload)
    with pytest.raises(ApplicationArchitectureError, match="runtime.provider must equal"):
        load_application_declaration(repo)


def test_unimplemented_levels_fail_closed_and_never_overclaim(tmp_path: Path) -> None:
    repo, _payload = _write_repo(tmp_path)
    for level in ("registry", "executable", "operational"):
        result = validate_application_architecture(repo, level=level)
        assert result["ok"] is False
        assert result["status"] == "validation_level_not_implemented"
        assert result["requested_level"] == level
        assert result["proven_level"] == "declaration"
        assert result["max_supported_level"] == "structural"
