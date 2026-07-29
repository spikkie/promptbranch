from __future__ import annotations

from copy import deepcopy

from promptbranch_skillrun import build_skillrun_evidence, sha256_json, validate_skillrun_evidence


SKILL = {
    "id": "promptbranch.skill.application-architecture-proof",
    "name": "application-architecture-proof",
    "path": ".promptbranch/skills/application-architecture-proof/SKILL.md",
    "path_sha256": "a" * 64,
    "validators": ["promptbranch.validator.application-architecture"],
}
TOOLS = ["filesystem.read", "filesystem.list"]


def _run() -> dict:
    return {
        "ok": True,
        "planner": "skill-procedure",
        "mode": "mcp_stdio",
        "status": "completed",
        "plan": [
            {"name": "filesystem.read", "arguments": {"path": ".promptbranch-ai.json", "max_bytes": 60000}},
            {"name": "filesystem.list", "arguments": {"path": ".promptbranch", "max_entries": 80}},
        ],
        "results": [
            {"ok": True, "path": ".promptbranch-ai.json", "bytes": 4025},
            {"ok": True, "path": ".promptbranch", "entries": ["ai-registry.json", "skills"]},
        ],
    }


def _evidence() -> dict:
    return build_skillrun_evidence(
        application_id="promptbranch.runtime",
        runtime_provider="promptbranch",
        application_version="v0.1.114.1",
        skill=SKILL,
        request="Prove executable application architecture using bounded read-only tools.",
        run=_run(),
        started_at="2026-07-29T13:00:00Z",
        finished_at="2026-07-29T13:00:01Z",
    )


def _rehash(evidence: dict) -> None:
    body = deepcopy(evidence)
    body.pop("evidence_sha256", None)
    evidence["evidence_sha256"] = sha256_json(body)


def test_valid_skillrun_evidence_passes() -> None:
    evidence = _evidence()
    payload = validate_skillrun_evidence(evidence, expected_skill=SKILL, allowed_tools=TOOLS, max_steps=2)
    assert payload["ok"] is True
    assert payload["status"] == "skillrun_validated"
    assert payload["step_count"] == 2
    assert payload["ordered_tools"] == TOOLS


def test_evidence_hash_tamper_fails() -> None:
    evidence = _evidence()
    evidence["request"] = "tampered"
    payload = validate_skillrun_evidence(evidence, expected_skill=SKILL, allowed_tools=TOOLS, max_steps=2)
    assert payload["ok"] is False
    assert any("evidence_sha256" in error for error in payload["errors"])


def test_result_digest_tamper_fails_even_when_outer_hash_is_recomputed() -> None:
    evidence = _evidence()
    evidence["steps"][0]["result"]["bytes"] = 999
    _rehash(evidence)
    payload = validate_skillrun_evidence(evidence, expected_skill=SKILL, allowed_tools=TOOLS, max_steps=2)
    assert payload["ok"] is False
    assert any("result_sha256 mismatch" in error for error in payload["errors"])


def test_mutation_safety_claim_fails_closed() -> None:
    evidence = _evidence()
    evidence["safety"]["state_mutated"] = True
    _rehash(evidence)
    payload = validate_skillrun_evidence(evidence, expected_skill=SKILL, allowed_tools=TOOLS, max_steps=2)
    assert payload["ok"] is False
    assert "safety.state_mutated must be False" in payload["errors"]


def test_wrong_tool_order_fails_closed() -> None:
    evidence = _evidence()
    evidence["steps"].reverse()
    for index, step in enumerate(evidence["steps"], 1):
        step["index"] = index
    evidence["execution"]["ordered_tools"] = [step["tool_id"] for step in evidence["steps"]]
    _rehash(evidence)
    payload = validate_skillrun_evidence(evidence, expected_skill=SKILL, allowed_tools=TOOLS, max_steps=2)
    assert payload["ok"] is False
    assert "executed tool order does not match executable registry contract" in payload["errors"]


def test_excessive_step_count_fails_closed() -> None:
    evidence = _evidence()
    extra = deepcopy(evidence["steps"][-1])
    extra["index"] = 3
    extra["step_id"] = f"{SKILL['id']}:003"
    evidence["steps"].append(extra)
    evidence["execution"]["step_count"] = 3
    evidence["execution"]["ordered_tools"].append(extra["tool_id"])
    _rehash(evidence)
    payload = validate_skillrun_evidence(evidence, expected_skill=SKILL, allowed_tools=TOOLS + [extra["tool_id"]], max_steps=2)
    assert payload["ok"] is False
    assert "step count exceeds executable contract max_steps" in payload["errors"]
