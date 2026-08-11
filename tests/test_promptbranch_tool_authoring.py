from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

import promptbranch_tool_authoring as tool_authoring
from promptbranch_mcp import skill_validate

ROOT = Path(__file__).resolve().parents[1]


def _example() -> dict:
    return json.loads((ROOT / tool_authoring.EXAMPLE_REL).read_text(encoding="utf-8"))


def test_tracked_tool_authoring_skill_is_valid_and_read_only() -> None:
    payload = skill_validate("promptbranch-tool-authoring", repo_path=ROOT)
    assert payload["ok"] is True, payload
    skill = payload["skill"]
    assert skill["risk"] == "read"
    assert skill["allowed_tools"] == ["filesystem.read", "filesystem.list"]
    assert payload["process_tools"] == []


def test_tool_authoring_source_contract_is_valid() -> None:
    payload = tool_authoring.validate_tool_authoring_source(ROOT)
    assert payload["ok"] is True, payload
    assert payload["version"] == "v0.1.128.1"
    assert payload["execution_authority_granted"] is False
    assert payload["mutation_authority_granted"] is False
    assert payload["release_authority_granted"] is False
    assert payload["publication_authority_granted"] is False
    assert payload["adoption_authority_granted"] is False


def test_tool_spec_example_is_deterministic_and_fail_closed() -> None:
    payload = tool_authoring.validate_tool_spec(_example())
    assert payload["ok"] is True, payload
    assert payload["authority"] == tool_authoring.AUTHORITY_EXPECTED
    assert payload["execution_authority_granted"] is False
    assert payload["mutation_authority_granted"] is False


def test_tool_spec_rejects_unbounded_input_and_authority_escalation() -> None:
    spec = _example()
    spec["input_schema"]["additionalProperties"] = True
    spec["authority"]["execution"] = "granted"
    payload = tool_authoring.validate_tool_spec(spec)
    assert payload["ok"] is False
    assert "input_schema_must_reject_additional_properties" in payload["errors"]
    assert "authority_not_fail_closed:execution" in payload["errors"]


def test_tool_spec_rejects_risk_read_only_mismatch_and_unknown_fields() -> None:
    spec = _example()
    spec["risk"] = "write"
    spec["read_only"] = True
    spec["command"] = ["rm", "-rf", "."]
    payload = tool_authoring.validate_tool_spec(spec)
    assert payload["ok"] is False
    assert "non_read_risk_requires_read_only_false" in payload["errors"]
    assert "unknown_fields:command" in payload["errors"]


def test_portable_bundle_export_is_byte_deterministic(tmp_path: Path) -> None:
    first = tmp_path / "first.zip"
    second = tmp_path / "second.zip"
    one = tool_authoring.export_tool_authoring_bundle(ROOT, first)
    two = tool_authoring.export_tool_authoring_bundle(ROOT, second)
    assert one["ok"] is True
    assert two["ok"] is True
    assert first.read_bytes() == second.read_bytes()
    assert hashlib.sha256(first.read_bytes()).hexdigest() == one["sha256"] == two["sha256"]
    assert one["entry_count"] == len(tool_authoring.BUNDLE_ENTRIES)


def test_portable_bundle_contains_project_source_agent_adapter_and_no_authority(tmp_path: Path) -> None:
    target = tmp_path / "tool-authoring.zip"
    payload = tool_authoring.export_tool_authoring_bundle(ROOT, target)
    assert payload["verification"]["ok"] is True
    manifest = payload["verification"]["manifest"]
    assert manifest["source_version"] == "v0.1.128.1"
    assert manifest["failure_semantics"] == "fail_closed"
    assert manifest["authority"] == {
        "tool_authoring_only": True,
        "execution_authority_granted": False,
        "mutation_authority_granted": False,
        "release_authority_granted": False,
        "publication_authority_granted": False,
        "adoption_authority_granted": False,
    }
    with zipfile.ZipFile(target) as archive:
        project_source = archive.read("promptbranch-tool-authoring/PROJECT_SOURCE.md").decode("utf-8")
        agents = archive.read("promptbranch-tool-authoring/AGENTS.md").decode("utf-8")
    assert "proposal-only" in project_source
    assert "grants no execution" in project_source
    assert "Do not register, implement, execute, publish, or adopt" in agents


def test_bundle_verifier_rejects_tampering(tmp_path: Path) -> None:
    source = tmp_path / "source.zip"
    tampered = tmp_path / "tampered.zip"
    tool_authoring.export_tool_authoring_bundle(ROOT, source)
    with zipfile.ZipFile(source, "r") as inp, zipfile.ZipFile(tampered, "w", compression=zipfile.ZIP_STORED) as out:
        for info in inp.infolist():
            content = inp.read(info.filename)
            if info.filename.endswith("SKILL.md"):
                content += b"\nexecution authority granted\n"
            out.writestr(info, content)
    payload = tool_authoring.verify_tool_authoring_bundle(tampered)
    assert payload["ok"] is False
    assert any(item.startswith("digest_mismatch:") for item in payload["errors"])
