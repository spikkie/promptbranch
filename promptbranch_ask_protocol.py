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
    base_release: str | None = None,
    repair_reason: str | None = None,
    intent_kind: str = "software_release_request",
    infer_target_version: bool = True,
) -> dict[str, Any]:
    """Build the Promptbranch ask.request envelope used by protocol-aware asks."""

    artifact_payload = dict(artifact or {})
    current_version = artifact_payload.get("current_version") or artifact_payload.get("artifact_version")
    inferred_target = target_version or (infer_next_normal_version(str(current_version) if current_version else None) if infer_target_version else None)
    if inferred_target:
        artifact_payload["target_version"] = inferred_target
    elif not infer_target_version:
        artifact_payload["target_version_policy"] = "not_applicable_for_non_release_parallel_plan"
    artifact_payload.setdefault("release_type", release_type)
    artifact_payload.setdefault("target_version_policy", "explicit_required")
    artifact_payload.setdefault("download_policy", "direct_url_only")
    if base_release is not None:
        artifact_payload["base_release"] = base_release
    elif artifact_payload.get("release_type") == "repair":
        artifact_payload.setdefault("base_release", current_version)
    if repair_reason is not None:
        artifact_payload["repair_reason"] = repair_reason
    elif artifact_payload.get("release_type") == "repair":
        artifact_payload.setdefault("repair_reason", "repair release; no scope advancement")
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
        "protocol_decisions": {
            "reply_envelope_required": True,
            "manual_mode_allowed": False,
            "multiple_answers_policy": "explicit_answer_id_required",
            "artifact_url_policy": "temporary_store_answer_id",
            "download_policy": "direct_url_only",
            "non_zip_artifacts": "unsupported_in_mvp",
        },
    }


def render_protocol_ask_prompt(envelope: dict[str, Any], *, user_prompt: str) -> str:
    """Render the protocol envelope plus user request into the actual ChatGPT prompt."""

    return (
        "Promptbranch protocol request. You MUST answer the current request with exactly one "
        "machine-readable reply envelope. Do not summarize a previous response, do not omit "
        "the markers, and do not put the JSON in a Markdown code fence. The automation will "
        "reject the answer unless it contains one block beginning with "
        f"{BEGIN_REPLY_MARKER} and ending with {END_REPLY_MARKER}. The JSON inside the block "
        "MUST include the exact request_id, correlation_id, input baseline, target version, "
        "and release_type from the request below. For smoke/no-output tasks, still return a "
        "valid envelope with status no_artifact and result_type no_change. Human-readable "
        "explanation may appear outside the envelope, but automation will use only the JSON envelope.\n\n"
        "BEGIN_PROMPTBRANCH_REQUEST_JSON\n"
        + json.dumps(envelope, indent=2, ensure_ascii=False)
        + "\nEND_PROMPTBRANCH_REQUEST_JSON\n\n"
        "User request:\n"
        + user_prompt
    )


def render_release_candidate_artifact_prompt(envelope: dict[str, Any], *, user_prompt: str) -> str:
    """Render the strict two-component release-candidate artifact prompt.

    A successful answer must expose one rendered downloadable ZIP outside the
    protocol envelope and then emit exactly one marked JSON envelope.  This
    release-specific renderer intentionally avoids the generic "exactly one
    reply envelope" lead-in because that wording can bias ChatGPT toward a
    JSON-only response with no materialized attachment.
    """

    artifact = envelope.get("artifact") if isinstance(envelope.get("artifact"), dict) else {}
    request_id = str(envelope.get("request_id") or "")
    correlation_id = str(envelope.get("correlation_id") or request_id)
    expected_artifact = str(artifact.get("expected_output_artifact") or "")
    baseline = str(artifact.get("current_baseline") or "")
    current_version = str(artifact.get("current_version") or "")
    target_version = str(artifact.get("expected_output_version") or artifact.get("target_version") or "")
    release_type = str(artifact.get("release_type") or "normal")

    failure_reply = {
        "schema": REPLY_SCHEMA,
        "schema_version": REPLY_SCHEMA_VERSION,
        "request_id": request_id,
        "correlation_id": correlation_id,
        "status": "failed",
        "result_type": "release_candidate",
        "summary": "A non-empty factual explanation of why the ZIP could not be physically created or attached.",
        "baseline": {
            "input_baseline": baseline,
            "input_version": current_version,
            "target_version": target_version,
            "release_type": release_type,
        },
        "changes": [],
        "artifacts": [],
        "validation": {
            "ok": False,
            "physical_artifact_created": False,
            "attachment_rendered": False,
        },
        "next_step": {
            "operator_action": "inspect_artifact_creation_failure",
            "recommended_command": "Do not run the candidate lifecycle because no materialized candidate was returned.",
        },
        "confidence": 1.0,
    }

    return (
        "Promptbranch release-candidate artifact request.\n\n"
        "MANDATORY FINAL RESPONSE FORMAT\n\n"
        "A successful final response MUST contain exactly two output components, in this exact order:\n\n"
        "COMPONENT 1 — REAL DOWNLOADABLE ZIP OUTPUT\n\n"
        "Create and expose exactly one real downloadable ChatGPT file attachment or rendered clickable "
        "download link with this exact filename:\n\n"
        f"{expected_artifact}\n\n"
        "The ZIP file must be physically created for this exact request before the final response is written.\n\n"
        "The ZIP output must appear as a separate rendered attachment or clickable download link in the "
        "assistant response, outside the Promptbranch JSON envelope.\n\n"
        "A filename written as plain text is not an attachment.\n\n"
        "A filesystem path written as plain text is not an attachment.\n\n"
        "A sandbox path written only inside JSON is not an attachment.\n\n"
        "This by itself is invalid:\n\n"
        f"\"download_url\": \"sandbox:/mnt/data/{expected_artifact}\"\n\n"
        "A Markdown download link is acceptable only when it is rendered as a real clickable ChatGPT download "
        "link to the physical file, for example:\n\n"
        f"[Download {expected_artifact}](actual-created-file-reference)\n\n"
        "The rendered ZIP attachment or download link is a required output component. It does not count as "
        "human-readable explanation and does not violate the requirement to return exactly one Promptbranch "
        "reply envelope.\n\n"
        "COMPONENT 2 — EXACTLY ONE PROMPTBRANCH REPLY ENVELOPE\n\n"
        "After the ZIP file has been physically created and exposed as Component 1, output exactly one "
        "machine-readable reply envelope.\n\n"
        f"The envelope must begin with:\n\n{BEGIN_REPLY_MARKER}\n\nand end with:\n\n{END_REPLY_MARKER}\n\n"
        "Do not put the envelope in a Markdown code fence.\n\n"
        "Do not output a second envelope.\n\n"
        "Do not output prose, headings, explanations, status messages, or any other content before, between, "
        "or after the two required components.\n\n"
        "The successful final response shape MUST be exactly:\n\n"
        "<one rendered downloadable ZIP attachment or clickable download link>\n\n"
        f"{BEGIN_REPLY_MARKER}\n{{\n  \"schema\": \"{REPLY_SCHEMA}\",\n  \"...\": \"metadata describing the exact ZIP exposed above\"\n}}\n{END_REPLY_MARKER}\n\n"
        "FAILURE RESPONSE FORMAT\n\n"
        "When the ZIP cannot be physically created or cannot be exposed as a rendered downloadable attachment "
        "or clickable link, do not invent a download URL and do not claim success.\n\n"
        "In that failure case, output exactly one component:\n\n"
        f"{BEGIN_REPLY_MARKER}\n"
        + json.dumps(failure_reply, indent=2, ensure_ascii=False)
        + f"\n{END_REPLY_MARKER}\n\n"
        "PROMPTBRANCH REQUEST\n\n"
        "BEGIN_PROMPTBRANCH_REQUEST_JSON\n"
        + json.dumps(envelope, indent=2, ensure_ascii=False)
        + "\nEND_PROMPTBRANCH_REQUEST_JSON\n\n"
        "RELEASE-CANDIDATE IMPLEMENTATION REQUEST\n\n"
        + str(user_prompt or "").strip()
        + "\n\nFINAL REMINDER\n\n"
        "The required successful output is not “one JSON envelope containing a ZIP path.”\n\n"
        "The required successful output is:\n\n"
        "ONE REAL DOWNLOADABLE ZIP FILE\n+\nONE BEGIN_PROMPTBRANCH_REPLY_JSON ... "
        "END_PROMPTBRANCH_REPLY_JSON ENVELOPE\n\n"
        "Create the ZIP first. Expose the ZIP second. Construct the envelope last."
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


def _error_payload(status: str, *, detail: str | None = None, block_count: int = 0, json_error: str | None = None, **extra: Any) -> dict[str, Any]:
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
    for key, value in extra.items():
        if value is not None:
            payload[key] = value
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
    source = raw.get("source") if isinstance(raw.get("source"), dict) else {}
    filename = raw.get("filename") or raw.get("name") or raw.get("artifact")
    return {
        "index": index,
        "valid": bool(filename),
        "status": "candidate_found" if filename else "artifact_filename_missing",
        "kind": raw.get("kind") or "unknown",
        "filename": filename,
        "version": raw.get("version"),
        "role": raw.get("role"),
        "media_type": raw.get("media_type"),
        "sha256": raw.get("sha256"),
        "size_bytes": raw.get("size_bytes"),
        "entry_count": raw.get("entry_count"),
        "download": {
            "available": bool(download.get("available") or raw.get("download_available")),
            "url": download.get("url") or raw.get("download_url"),
            "link_text": download.get("link_text") or raw.get("link_text") or filename,
            "url_seen_at": download.get("url_seen_at") or raw.get("url_seen_at"),
            "url_temporary": bool(download.get("url_temporary", raw.get("url_temporary", True))),
            "requires_browser_context": bool(
                download.get("requires_browser_context")
                or raw.get("requires_browser_context")
                or str(download.get("url") or raw.get("download_url") or "").startswith("sandbox:")
            ),
            "attachment_id": download.get("attachment_id") or raw.get("attachment_id"),
            "file_id": download.get("file_id") or raw.get("file_id"),
            "attachment_detected": bool(download.get("attachment_detected") or raw.get("attachment_detected")),
            "attachment_proven": bool(download.get("attachment_proven") or raw.get("attachment_proven")),
            "ui_attachment": bool(download.get("ui_attachment") or raw.get("ui_attachment")),
        },
        "source": {
            "request_id": source.get("request_id"),
            "answer_id": source.get("answer_id"),
            "url_seen_at": source.get("url_seen_at") or download.get("url_seen_at"),
            "url_temporary": bool(source.get("url_temporary", download.get("url_temporary", True))),
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

    kind = str(classified.get("kind") or "").strip().lower()
    role = str(classified.get("role") or "").strip()
    if not filename:
        issues.append("artifact_filename_missing")
    if filename and not filename.endswith(".zip"):
        issues.append("artifact_not_zip")
    if kind and kind != "zip":
        issues.append("unsupported_artifact_type")
    if role and role not in {"candidate_release", "repair_candidate", "visual_artifact_roundtrip_output", "smoke_test_artifact"}:
        issues.append("unsupported_artifact_role")
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

def _parse_reply_json_block(block_text: str) -> tuple[Any | None, dict[str, Any] | None]:
    """Parse a reply JSON block, tolerating only safe trailing marker fragments.

    ChatGPT sometimes emits a balanced JSON object followed by a truncated copy of
    the Promptbranch end marker, for example ``END_PROMPTBRANCH_REPLY_JSO_``.  In
    that case the protocol object is already complete and should be parsed.  This
    helper intentionally does not repair malformed JSON strings, embedded raw
    quotes, missing commas, or any non-marker trailing prose.
    """

    source = str(block_text or "").strip()
    try:
        return json.loads(source), None
    except json.JSONDecodeError as exc:
        primary_exc = exc

    decoder = json.JSONDecoder()
    try:
        parsed, consumed = decoder.raw_decode(source)
    except json.JSONDecodeError as exc:
        line_start = max(0, int(getattr(primary_exc, "pos", 0)) - 240)
        line_end = min(len(source), int(getattr(primary_exc, "pos", 0)) + 240)
        return None, {
            "json_error": str(primary_exc),
            "json_error_lineno": getattr(primary_exc, "lineno", None),
            "json_error_colno": getattr(primary_exc, "colno", None),
            "json_error_pos": getattr(primary_exc, "pos", None),
            "json_error_context": source[line_start:line_end],
            "json_recovery_attempted": True,
            "json_recovery_status": "no_balanced_json_object",
            "json_recovery_error": str(exc),
        }

    trailing = source[consumed:].strip()
    normalized = re.sub(r"\s+", "", trailing)
    marker_prefix = END_REPLY_MARKER
    if trailing and not (marker_prefix.startswith(normalized) or marker_prefix.startswith(normalized.rstrip("_"))):
        line_start = max(0, int(getattr(primary_exc, "pos", 0)) - 240)
        line_end = min(len(source), int(getattr(primary_exc, "pos", 0)) + 240)
        return None, {
            "json_error": str(primary_exc),
            "json_error_lineno": getattr(primary_exc, "lineno", None),
            "json_error_colno": getattr(primary_exc, "colno", None),
            "json_error_pos": getattr(primary_exc, "pos", None),
            "json_error_context": source[line_start:line_end],
            "json_recovery_attempted": True,
            "json_recovery_status": "trailing_text_not_marker_fragment",
            "json_trailing_fragment": trailing[:160],
        }

    return parsed, {
        "json_recovery_attempted": True,
        "json_recovery_status": "truncated_end_marker_after_balanced_json",
        "json_trailing_fragment": trailing[:160],
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
    parsed, parse_meta = _parse_reply_json_block(block.text)
    if parsed is None:
        return _error_payload(
            "reply_schema_invalid",
            detail="reply block is not valid JSON",
            block_count=1,
            **(parse_meta or {}),
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
        payload = {
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
        if isinstance(parse_meta, dict):
            payload.update(parse_meta)
        return payload
    payload = {
        "ok": True,
        "action": "promptbranch_reply_parse",
        "status": "valid",
        "schema": REPLY_SCHEMA,
        "schema_version": REPLY_SCHEMA_VERSION,
        "block_count": 1,
        "request_id": parsed.get("request_id"),
        "correlation_id": parsed.get("correlation_id"),
        "answer_id": parsed.get("answer_id"),
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
    if isinstance(parse_meta, dict):
        payload.update(parse_meta)
    return payload
