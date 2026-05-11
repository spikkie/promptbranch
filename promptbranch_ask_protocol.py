from __future__ import annotations

import json
import re
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


_VERSION_PARTS_RE = re.compile(r"^v?(?P<base>\d+\.\d+\.)(?P<patch>\d+)(?:\.(?P<repair>\d+))?$")


def infer_next_normal_version(current_version: str | None) -> str | None:
    """Infer the next normal release version without advancing repair state."""

    if not current_version:
        return None
    value = str(current_version).strip()
    match = _VERSION_PARTS_RE.match(value)
    if not match:
        return None
    patch = int(match.group("patch")) + 1
    return f"v{match.group('base')}{patch}"


def build_ask_request_envelope(
    *,
    prompt: str,
    request_id: str,
    correlation_id: str | None = None,
    workspace: dict[str, Any] | None = None,
    task: dict[str, Any] | None = None,
    artifact: dict[str, Any] | None = None,
    target_version: str | None = None,
    release_type: str = "normal",
    intent_kind: str = "software_release_request",
) -> dict[str, Any]:
    """Build the Promptbranch ask.request envelope used by protocol-aware asks."""

    artifact_payload = dict(artifact or {})
    current_version = artifact_payload.get("current_version") or artifact_payload.get("artifact_version")
    inferred_target = target_version or infer_next_normal_version(str(current_version) if current_version else None)
    if inferred_target:
        artifact_payload["target_version"] = inferred_target
    artifact_payload.setdefault("release_type", release_type)
    return {
        "schema": REQUEST_SCHEMA,
        "schema_version": REQUEST_SCHEMA_VERSION,
        "request_id": request_id,
        "correlation_id": correlation_id or request_id,
        "workspace": workspace or {},
        "task": task or {"conversation_id": "current", "turn_policy": "assistant_may_return_one_protocol_reply"},
        "artifact": artifact_payload,
        "intent": {"kind": intent_kind, "summary": prompt},
        "constraints": {
            "preserve_baseline": True,
            "zip_root_must_be_repo_contents": True,
            "no_patch_files": True,
            "no_wrapper_folder": True,
            "no_cache_files": True,
            "no_nested_zips": True,
            "no_auto_adopt": True,
        },
        "expected_reply": {
            "schema": REPLY_SCHEMA,
            "schema_version": REPLY_SCHEMA_VERSION,
            "required_sections": ["status", "summary", "baseline", "changes", "artifacts", "validation", "next_step"],
            "markers": {"begin": BEGIN_REPLY_MARKER, "end": END_REPLY_MARKER},
        },
    }


def render_protocol_ask_prompt(envelope: dict[str, Any], *, user_prompt: str) -> str:
    """Render the protocol envelope plus user request into the actual ChatGPT prompt."""

    return (
        "Promptbranch protocol request. Return exactly one valid reply envelope between "
        f"{BEGIN_REPLY_MARKER} and {END_REPLY_MARKER}. Human-readable explanation may appear outside "
        "the envelope, but automation will use only the JSON envelope.\n\n"
        "BEGIN_PROMPTBRANCH_REQUEST_JSON\n"
        + json.dumps(envelope, indent=2, ensure_ascii=False)
        + "\nEND_PROMPTBRANCH_REQUEST_JSON\n\n"
        "User request:\n"
        + user_prompt
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



_VERSION_RE = re.compile(r"v?\d+\.\d+\.\d+(?:\.\d+)?")


def version_from_artifact_filename(filename: str | None) -> str | None:
    """Extract a canonical version token from an artifact ZIP filename."""

    if not filename:
        return None
    match = _VERSION_RE.search(str(filename))
    if not match:
        return None
    value = match.group(0)
    return value if value.startswith("v") else f"v{value}"


def repo_prefix_from_artifact_filename(filename: str | None, *, version: str | None = None) -> str | None:
    """Infer the project/repo artifact prefix before the version token."""

    if not filename:
        return None
    name = str(filename)
    if name.endswith(".zip"):
        name = name[:-4]
    token = version or version_from_artifact_filename(filename)
    if token:
        for candidate in (token, token.removeprefix("v")):
            idx = name.find(candidate)
            if idx > 0:
                prefix = name[:idx].rstrip("_.-")
                return prefix or None
    return None


def _candidate_with_classification(
    candidate: dict[str, Any],
    *,
    expected_filename: str | None = None,
    expected_version: str | None = None,
    expected_repo: str | None = None,
) -> dict[str, Any]:
    classified = dict(candidate)
    filename = str(classified.get("filename") or "")
    declared_version = classified.get("version")
    filename_version = version_from_artifact_filename(filename)
    expected_version_norm = version_from_artifact_filename(expected_version) or expected_version
    repo_prefix = repo_prefix_from_artifact_filename(filename, version=filename_version)
    issues: list[str] = []

    if not filename:
        issues.append("artifact_filename_missing")
    if filename and not filename.endswith(".zip"):
        issues.append("artifact_not_zip")
    if declared_version and filename_version and str(declared_version) != filename_version:
        issues.append("artifact_declared_version_mismatch")
    if expected_filename and filename != expected_filename:
        issues.append("artifact_wrong_filename")
    if expected_version_norm and filename_version != expected_version_norm:
        issues.append("artifact_wrong_version")
    if expected_repo and repo_prefix != expected_repo:
        issues.append("artifact_wrong_project")

    classified["filename_version"] = filename_version
    classified["repo_prefix"] = repo_prefix
    classified["expected_filename"] = expected_filename
    classified["expected_version"] = expected_version_norm
    classified["expected_repo"] = expected_repo
    classified["classification_errors"] = issues
    if issues:
        classified["valid"] = False
        classified["status"] = issues[0]
    elif filename:
        classified["valid"] = True
        classified["status"] = "candidate_found"
    return classified


def classify_artifact_candidates(
    candidates: list[dict[str, Any]],
    *,
    expected_filename: str | None = None,
    expected_version: str | None = None,
    expected_repo: str | None = None,
) -> dict[str, Any]:
    """Classify parsed reply artifacts without downloading or mutating state."""

    classified = [
        _candidate_with_classification(
            item,
            expected_filename=expected_filename,
            expected_version=expected_version,
            expected_repo=expected_repo,
        )
        for item in candidates
        if isinstance(item, dict)
    ]
    zip_candidates = [item for item in classified if str(item.get("filename") or "").endswith(".zip")]
    valid_zip_candidates = [item for item in zip_candidates if item.get("valid")]

    if not zip_candidates:
        status = "artifact_candidate_missing"
        selected = None
        ok = False
    elif expected_filename:
        matches = [item for item in valid_zip_candidates if item.get("filename") == expected_filename]
        if len(matches) == 1:
            status = "candidate_selected"
            selected = matches[0]
            ok = True
        elif len(matches) > 1:
            status = "artifact_candidate_ambiguous"
            selected = None
            ok = False
        else:
            status = "artifact_wrong_filename"
            selected = None
            ok = False
    elif len(valid_zip_candidates) == 1:
        status = "candidate_selected"
        selected = valid_zip_candidates[0]
        ok = True
    elif len(valid_zip_candidates) > 1:
        status = "artifact_candidate_ambiguous"
        selected = None
        ok = False
    else:
        errors = zip_candidates[0].get("classification_errors") if len(zip_candidates) == 1 and isinstance(zip_candidates[0], dict) else None
        status = str(errors[0]) if isinstance(errors, list) and errors else "artifact_candidate_invalid"
        selected = None
        ok = False

    return {
        "ok": ok,
        "status": status,
        "artifact_candidate_count": len(classified),
        "zip_candidate_count": len(zip_candidates),
        "valid_zip_candidate_count": len(valid_zip_candidates),
        "selected_candidate": selected,
        "artifact_candidates": classified,
        "expected_filename": expected_filename,
        "expected_version": version_from_artifact_filename(expected_version) or expected_version,
        "expected_repo": expected_repo,
        "automation_performed": False,
        "download_performed": False,
        "migration_performed": False,
        "adoption_performed": False,
    }

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
