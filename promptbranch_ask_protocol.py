from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

REPLY_SCHEMA = "promptbranch.ask.reply"
REQUEST_SCHEMA = "promptbranch.ask.request"
REPLY_SCHEMA_VERSION = "1.0"
REQUEST_SCHEMA_VERSION = "1.0"
BEGIN_REPLY_MARKER = "BEGIN_PROMPTBRANCH_REPLY_JSON"
END_REPLY_MARKER = "END_PROMPTBRANCH_REPLY_JSON"

REPLY_REQUIRED_FIELDS: tuple[str, ...] = (
    "schema",
    "schema_version",
    "request_id",
    "status",
    "result_type",
    "summary",
    "baseline",
    "changes",
    "artifacts",
    "validation",
    "next_step",
)

ALLOWED_REPLY_STATUSES: tuple[str, ...] = (
    "completed",
    "partial",
    "blocked",
    "needs_clarification",
    "failed",
    "no_artifact",
    "invalid_request",
)

ALLOWED_RESULT_TYPES: tuple[str, ...] = (
    "analysis_only",
    "release_candidate",
    "repair_candidate",
    "test_report",
    "diagnostic",
    "no_change",
)


@dataclass(frozen=True)
class ReplyBlock:
    index: int
    start: int
    end: int
    text: str


def extract_reply_blocks(text: str) -> list[ReplyBlock]:
    """Extract marked Promptbranch reply JSON blocks from answer text."""

    source = text or ""
    blocks: list[ReplyBlock] = []
    search_from = 0
    while True:
        begin = source.find(BEGIN_REPLY_MARKER, search_from)
        if begin < 0:
            break
        content_start = begin + len(BEGIN_REPLY_MARKER)
        end = source.find(END_REPLY_MARKER, content_start)
        if end < 0:
            # Missing end marker is an invalid single block candidate.
            blocks.append(ReplyBlock(index=len(blocks) + 1, start=begin, end=len(source), text=source[content_start:].strip()))
            break
        blocks.append(ReplyBlock(index=len(blocks) + 1, start=begin, end=end + len(END_REPLY_MARKER), text=source[content_start:end].strip()))
        search_from = end + len(END_REPLY_MARKER)
    return blocks


def _error_payload(status: str, *, detail: str | None = None, block_count: int = 0, json_error: str | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "ok": False,
        "action": "promptbranch_reply_parse",
        "status": status,
        "schema": REPLY_SCHEMA,
        "schema_version": REPLY_SCHEMA_VERSION,
        "block_count": block_count,
        "artifact_candidate_count": 0,
        "artifact_candidates": [],
    }
    if detail:
        payload["detail"] = detail
    if json_error:
        payload["json_error"] = json_error
    return payload


def _normalize_artifact_candidate(raw: Any, *, index: int) -> dict[str, Any]:
    if not isinstance(raw, dict):
        return {
            "index": index,
            "valid": False,
            "status": "artifact_candidate_invalid",
            "detail": "artifact candidate is not an object",
            "raw": raw,
        }
    download = raw.get("download") if isinstance(raw.get("download"), dict) else {}
    filename = raw.get("filename") or raw.get("name") or raw.get("artifact")
    return {
        "index": index,
        "valid": bool(filename),
        "status": "candidate_found" if filename else "artifact_filename_missing",
        "kind": raw.get("kind") or "unknown",
        "filename": filename,
        "version": raw.get("version"),
        "role": raw.get("role"),
        "download": {
            "available": bool(download.get("available")),
            "url": download.get("url"),
            "link_text": download.get("link_text"),
        },
        "raw": raw,
    }


def _validate_reply_object(reply: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for field in REPLY_REQUIRED_FIELDS:
        if field not in reply:
            errors.append(f"missing_required_field:{field}")
    if reply.get("schema") != REPLY_SCHEMA:
        errors.append("schema_mismatch")
    if str(reply.get("schema_version") or "") != REPLY_SCHEMA_VERSION:
        errors.append("schema_version_unsupported")
    status = str(reply.get("status") or "")
    if status and status not in ALLOWED_REPLY_STATUSES:
        errors.append("status_unsupported")
    result_type = str(reply.get("result_type") or "")
    if result_type and result_type not in ALLOWED_RESULT_TYPES:
        errors.append("result_type_unsupported")
    if "artifacts" in reply and not isinstance(reply.get("artifacts"), list):
        errors.append("artifacts_not_list")
    if "baseline" in reply and not isinstance(reply.get("baseline"), dict):
        errors.append("baseline_not_object")
    if "validation" in reply and not isinstance(reply.get("validation"), dict):
        errors.append("validation_not_object")
    if "next_step" in reply and not isinstance(reply.get("next_step"), dict):
        errors.append("next_step_not_object")
    return errors


def parse_promptbranch_reply(text: str) -> dict[str, Any]:
    """Parse and validate one Promptbranch reply envelope from assistant text.

    This function intentionally does not download, migrate, adopt, or mutate any
    artifact state. It only turns an assistant answer into validated protocol
    data plus artifact candidates.
    """

    blocks = extract_reply_blocks(text)
    if not blocks:
        return _error_payload(
            "reply_schema_missing",
            detail=f"no {BEGIN_REPLY_MARKER}/{END_REPLY_MARKER} block found",
            block_count=0,
        )
    if len(blocks) > 1:
        return _error_payload(
            "reply_schema_ambiguous",
            detail="multiple Promptbranch reply JSON blocks found",
            block_count=len(blocks),
        )
    block = blocks[0]
    try:
        parsed = json.loads(block.text)
    except json.JSONDecodeError as exc:
        return _error_payload(
            "reply_schema_invalid",
            detail="reply block is not valid JSON",
            block_count=1,
            json_error=str(exc),
        )
    if not isinstance(parsed, dict):
        return _error_payload(
            "reply_schema_invalid",
            detail="reply JSON root must be an object",
            block_count=1,
        )
    validation_errors = _validate_reply_object(parsed)
    artifacts = parsed.get("artifacts") if isinstance(parsed.get("artifacts"), list) else []
    artifact_candidates = [_normalize_artifact_candidate(item, index=i + 1) for i, item in enumerate(artifacts)]
    if validation_errors:
        return {
            "ok": False,
            "action": "promptbranch_reply_parse",
            "status": "reply_schema_invalid",
            "schema": REPLY_SCHEMA,
            "schema_version": REPLY_SCHEMA_VERSION,
            "block_count": 1,
            "validation_errors": validation_errors,
            "reply": parsed,
            "artifact_candidate_count": len(artifact_candidates),
            "artifact_candidates": artifact_candidates,
        }
    return {
        "ok": True,
        "action": "promptbranch_reply_parse",
        "status": "valid",
        "schema": REPLY_SCHEMA,
        "schema_version": REPLY_SCHEMA_VERSION,
        "block_count": 1,
        "request_id": parsed.get("request_id"),
        "correlation_id": parsed.get("correlation_id"),
        "reply_status": parsed.get("status"),
        "result_type": parsed.get("result_type"),
        "summary": parsed.get("summary"),
        "baseline": parsed.get("baseline"),
        "validation": parsed.get("validation"),
        "next_step": parsed.get("next_step"),
        "reply": parsed,
        "artifact_candidate_count": len(artifact_candidates),
        "artifact_candidates": artifact_candidates,
    }
