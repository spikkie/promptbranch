from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

SCHEMA = "promptbranch.ai.skill_run"
SCHEMA_VERSION = "1.0"
RFC3339_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_json(value: object) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _result_payload(result: Mapping[str, Any]) -> dict[str, Any]:
    return deepcopy(dict(result))


def build_skillrun_evidence(
    *,
    application_id: str,
    runtime_provider: str,
    application_version: str,
    skill: Mapping[str, Any],
    request: str,
    run: Mapping[str, Any],
    started_at: str,
    finished_at: str,
) -> dict[str, Any]:
    plan = run.get("plan") if isinstance(run.get("plan"), list) else []
    results = run.get("results") if isinstance(run.get("results"), list) else []
    steps: list[dict[str, Any]] = []
    for index, planned in enumerate(plan, 1):
        planned_obj = planned if isinstance(planned, Mapping) else {}
        result_obj = results[index - 1] if index - 1 < len(results) and isinstance(results[index - 1], Mapping) else {}
        arguments = planned_obj.get("arguments") if isinstance(planned_obj.get("arguments"), Mapping) else {}
        result_payload = _result_payload(result_obj)
        steps.append(
            {
                "index": index,
                "step_id": f"{skill['id']}:{index:03d}",
                "tool_id": str(planned_obj.get("name") or ""),
                "arguments": deepcopy(dict(arguments)),
                "arguments_sha256": sha256_json(arguments),
                "result": result_payload,
                "result_sha256": sha256_json(result_payload),
                "ok": bool(result_obj.get("ok")),
            }
        )
    validators = [
        {"id": str(validator_id), "status": "passed" if run.get("ok") else "failed"}
        for validator_id in skill.get("validators", [])
    ]
    body: dict[str, Any] = {
        "schema": SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "application": {
            "id": application_id,
            "version": application_version,
            "runtime_provider": runtime_provider,
        },
        "skill": {
            "id": str(skill["id"]),
            "name": str(skill["name"]),
            "path": str(skill["path"]),
            "path_sha256": str(skill.get("path_sha256") or ""),
        },
        "request": request,
        "execution": {
            "started_at": started_at,
            "finished_at": finished_at,
            "planner": str(run.get("planner") or ""),
            "mode": str(run.get("mode") or ""),
            "status": str(run.get("status") or ""),
            "step_count": len(steps),
            "ordered_tools": [step["tool_id"] for step in steps],
        },
        "steps": steps,
        "validators": validators,
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
        "outcome": {
            "ok": bool(run.get("ok")),
            "status": "verified" if run.get("ok") else "failed",
        },
    }
    body["run_id"] = sha256_json(body)[:24]
    body["evidence_sha256"] = sha256_json(body)
    return body


def validate_skillrun_evidence(
    evidence: object,
    *,
    expected_skill: Mapping[str, Any] | None = None,
    allowed_tools: Sequence[str] | None = None,
    max_steps: int | None = None,
) -> dict[str, Any]:
    errors: list[str] = []
    if not isinstance(evidence, dict):
        return {"ok": False, "status": "skillrun_invalid", "errors": ["evidence must be an object"]}
    required = {
        "schema", "schema_version", "application", "skill", "request", "execution", "steps",
        "validators", "safety", "outcome", "run_id", "evidence_sha256",
    }
    unknown = sorted(set(evidence) - required)
    missing = sorted(required - set(evidence))
    if missing:
        errors.append("missing fields: " + ", ".join(missing))
    if unknown:
        errors.append("unknown fields: " + ", ".join(unknown))
    if evidence.get("schema") != SCHEMA or evidence.get("schema_version") != SCHEMA_VERSION:
        errors.append("unsupported SkillRun schema identity")
    expected_hash = evidence.get("evidence_sha256")
    hash_body = deepcopy(evidence)
    hash_body.pop("evidence_sha256", None)
    actual_hash = sha256_json(hash_body)
    if expected_hash != actual_hash:
        errors.append("evidence_sha256 does not match canonical evidence body")
    run_id_body = deepcopy(evidence)
    run_id_body.pop("evidence_sha256", None)
    run_id_body.pop("run_id", None)
    expected_run_id = sha256_json(run_id_body)[:24]
    if evidence.get("run_id") != expected_run_id:
        errors.append("run_id does not match canonical pre-identity evidence body")

    skill = evidence.get("skill") if isinstance(evidence.get("skill"), dict) else {}
    if expected_skill:
        for key in ("id", "name", "path"):
            if skill.get(key) != expected_skill.get(key):
                errors.append(f"skill.{key} does not match executable registry contract")
    execution = evidence.get("execution") if isinstance(evidence.get("execution"), dict) else {}
    for key in ("started_at", "finished_at"):
        if not isinstance(execution.get(key), str) or not RFC3339_RE.fullmatch(execution[key]):
            errors.append(f"execution.{key} must be UTC RFC3339")
    steps = evidence.get("steps") if isinstance(evidence.get("steps"), list) else []
    if not steps:
        errors.append("steps must be non-empty")
    if max_steps is not None and len(steps) > max_steps:
        errors.append("step count exceeds executable contract max_steps")
    ordered_tools: list[str] = []
    for index, raw in enumerate(steps, 1):
        if not isinstance(raw, dict):
            errors.append(f"steps[{index - 1}] must be an object")
            continue
        if raw.get("index") != index:
            errors.append(f"steps[{index - 1}].index must be sequential")
        tool_id = str(raw.get("tool_id") or "")
        ordered_tools.append(tool_id)
        arguments = raw.get("arguments") if isinstance(raw.get("arguments"), dict) else {}
        result = raw.get("result") if isinstance(raw.get("result"), dict) else {}
        if raw.get("arguments_sha256") != sha256_json(arguments):
            errors.append(f"steps[{index - 1}].arguments_sha256 mismatch")
        if raw.get("result_sha256") != sha256_json(result):
            errors.append(f"steps[{index - 1}].result_sha256 mismatch")
        if raw.get("ok") is not True or result.get("ok") is not True:
            errors.append(f"steps[{index - 1}] did not pass")
    if execution.get("step_count") != len(steps):
        errors.append("execution.step_count mismatch")
    if execution.get("ordered_tools") != ordered_tools:
        errors.append("execution.ordered_tools mismatch")
    if allowed_tools is not None:
        if ordered_tools != list(allowed_tools):
            errors.append("executed tool order does not match executable registry contract")
    validators = evidence.get("validators") if isinstance(evidence.get("validators"), list) else []
    if not validators or any(not isinstance(item, dict) or item.get("status") != "passed" for item in validators):
        errors.append("all registered validators must pass")
    safety = evidence.get("safety") if isinstance(evidence.get("safety"), dict) else {}
    required_safety = {
        "bounded": True,
        "read_only_tools_only": True,
        "mcp_transport": "stdio",
        "commands_executed": True,
        "state_mutated": False,
        "release_authority_granted": False,
        "publication_authority_granted": False,
        "adoption_authority_granted": False,
    }
    for key, value in required_safety.items():
        if safety.get(key) != value:
            errors.append(f"safety.{key} must be {value!r}")
    outcome = evidence.get("outcome") if isinstance(evidence.get("outcome"), dict) else {}
    if outcome.get("ok") is not True or outcome.get("status") != "verified":
        errors.append("SkillRun outcome must be verified")
    return {
        "ok": not errors,
        "status": "skillrun_validated" if not errors else "skillrun_invalid",
        "schema": SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "run_id": evidence.get("run_id"),
        "evidence_sha256": evidence.get("evidence_sha256"),
        "step_count": len(steps),
        "ordered_tools": ordered_tools,
        "error_count": len(errors),
        "errors": errors,
    }


__all__ = [
    "SCHEMA",
    "SCHEMA_VERSION",
    "build_skillrun_evidence",
    "sha256_json",
    "utc_now",
    "validate_skillrun_evidence",
]
