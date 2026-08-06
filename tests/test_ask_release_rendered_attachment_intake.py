from __future__ import annotations

import asyncio
import hashlib
import zipfile
from argparse import Namespace
from pathlib import Path

from promptbranch_ask_protocol import parse_promptbranch_reply
from promptbranch_browser_auth.client import _select_correlated_artifact_turn_snapshot
from promptbranch_cli import (
    _materialize_ask_release_rendered_candidate,
    _validate_ask_release_candidate_result,
)


def _build_zip(path: Path, version: str = "v0.1.124") -> dict[str, object]:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("VERSION", version + "\n")
        archive.writestr("README.md", "# rendered attachment intake\n")
    data = path.read_bytes()
    with zipfile.ZipFile(path) as archive:
        entry_count = len(archive.infolist())
    return {
        "sha256": hashlib.sha256(data).hexdigest(),
        "size_bytes": len(data),
        "entry_count": entry_count,
        "content": data,
    }


def _protocol_result(metadata: dict[str, object], *, sha256: str | None = None) -> dict[str, object]:
    filename = "chatgpt_claudecode_workflow-2_v0.1.124.zip"
    request_id = "req-rendered-attachment-test"
    artifact = {
        "filename": filename,
        "version": "v0.1.124",
        "role": "candidate_release",
        "media_type": "application/zip",
        "size_bytes": metadata["size_bytes"],
        "sha256": sha256 or metadata["sha256"],
        "entry_count": metadata["entry_count"],
        "download_available": True,
        "download_url": f"sandbox:/mnt/data/{filename}",
    }
    return {
        "ok": True,
        "status": "reply_validated",
        "reply_validation_ok": True,
        "request_id": request_id,
        "correlation_id": request_id,
        "conversation_url": "https://chatgpt.com/g/g-p-demo/c/conversation-1",
        "conversation_id": "conversation-1",
        "message": {"id": "message-1", "index": 1, "turn_index": 1},
        "answer": {"id": "answer-1", "index": 1, "turn_index": 2},
        "selected_answer": {
            "message_id": "message-1",
            "message_index": 1,
            "message_turn_index": 1,
            "answer_id": "answer-1",
            "answer_index": 1,
            "answer_turn_index": 2,
        },
        "reply": {
            "schema": "promptbranch.ask.reply",
            "schema_version": "1.0",
            "request_id": request_id,
            "correlation_id": request_id,
            "status": "completed",
            "result_type": "release_candidate",
            "summary": "Rendered attachment test candidate.",
            "baseline": {
                "input_baseline": "chatgpt_claudecode_workflow-2_v0.1.123.2.6.zip",
                "input_version": "v0.1.123.2.6",
                "target_version": "v0.1.124",
                "release_type": "normal",
            },
            "changes": [],
            "artifacts": [artifact],
            "validation": {"ok": True},
            "next_step": {"operator_action": "run_candidate_lifecycle", "recommended_command": "pb artifact candidate-run --json"},
            "confidence": 0.99,
        },
    }


class _FakeRenderedAttachmentBackend:
    def __init__(self, content: bytes) -> None:
        self.content = content
        self.calls: list[dict[str, object]] = []

    async def download_chat_artifact(self, **kwargs):
        self.calls.append(dict(kwargs))
        target = Path(str(kwargs["target_path"]))
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(self.content)
        return {
            "ok": True,
            "status": "artifact_browser_downloaded",
            "target_path": str(target),
            "size_bytes": len(self.content),
            "download_performed": True,
            "attachment_detected": True,
            "attachment_proven": True,
            "rendered_attachment_detected": True,
            "control_kind": "link",
            "correlation_mode": "request_id",
            "correlated_turn_index": 3,
        }


def test_exact_correlated_turn_is_selected_over_older_filename_match() -> None:
    snapshots = [
        {"filename_match": True, "request_id_match": False, "answer_id_match": False, "answer_turn_index_match": False},
        {"filename_match": True, "request_id_match": True, "answer_id_match": False, "answer_turn_index_match": False},
    ]
    selected = _select_correlated_artifact_turn_snapshot(snapshots, correlation_required=True)
    assert selected == {
        "ok": True,
        "status": "correlated_turn_selected",
        "mode": "request_id",
        "indexes": [1],
        "index": 1,
    }


def test_multiple_correlated_attachment_turns_fail_ambiguous() -> None:
    snapshots = [
        {"filename_match": True, "request_id_match": True, "answer_id_match": False, "answer_turn_index_match": False},
        {"filename_match": True, "request_id_match": True, "answer_id_match": False, "answer_turn_index_match": False},
    ]
    selected = _select_correlated_artifact_turn_snapshot(snapshots, correlation_required=True)
    assert selected["ok"] is False
    assert selected["status"] == "artifact_correlated_answer_ambiguous"
    assert selected["indexes"] == [0, 1]


def test_top_level_download_fields_are_normalized_for_replay() -> None:
    filename = "chatgpt_claudecode_workflow-2_v0.1.124.zip"
    reply = _protocol_result({"sha256": "a" * 64, "size_bytes": 123, "entry_count": 4})["reply"]
    text = "BEGIN_PROMPTBRANCH_REPLY_JSON\n" + __import__("json").dumps(reply) + "\nEND_PROMPTBRANCH_REPLY_JSON"
    parsed = parse_promptbranch_reply(text)
    candidate = parsed["artifact_candidates"][0]
    assert candidate["download"]["url"] == f"sandbox:/mnt/data/{filename}"
    assert candidate["download"]["available"] is True
    assert candidate["download"]["requires_browser_context"] is True
    assert candidate["sha256"] == "a" * 64
    assert candidate["size_bytes"] == 123
    assert candidate["entry_count"] == 4


def test_rendered_attachment_is_downloaded_verified_and_correlated(tmp_path: Path) -> None:
    source = tmp_path / "source.zip"
    metadata = _build_zip(source)
    backend = _FakeRenderedAttachmentBackend(metadata["content"])
    args = Namespace(
        profile_dir=str(tmp_path / "profile"),
        keep_open=False,
        artifact_materialization_timeout_seconds=10.0,
    )
    expected = {
        "expected_artifact": "chatgpt_claudecode_workflow-2_v0.1.124.zip",
        "expected_version": "v0.1.124",
        "expected_role": "candidate_release",
    }

    materialized = asyncio.run(
        _materialize_ask_release_rendered_candidate(backend, args, _protocol_result(metadata), expected)
    )
    validated = _validate_ask_release_candidate_result(materialized, expected)

    assert validated["ok"] is True
    assert validated["status"] == "reply_validated"
    assert validated["artifact_materialization_proven"] is True
    assert validated["download_performed"] is True
    assert validated["browser_download_performed"] is True
    assert validated["verification_performed"] is True
    assert validated["envelope_metadata_verified"] is True
    assert validated["download_proof_status"] == "chatgpt_rendered_attachment_downloaded_verified"
    assert backend.calls[0]["request_id"] == "req-rendered-attachment-test"
    assert backend.calls[0]["answer_id"] == "answer-1"
    assert backend.calls[0]["answer_turn_index"] == 2
    artifact_download = validated["reply"]["artifacts"][0]["download"]
    assert artifact_download["attachment_detected"] is True
    assert artifact_download["attachment_proven"] is True
    assert artifact_download["ui_attachment"] is True


def test_downloaded_attachment_hash_mismatch_fails_closed(tmp_path: Path) -> None:
    source = tmp_path / "source.zip"
    metadata = _build_zip(source)
    backend = _FakeRenderedAttachmentBackend(metadata["content"])
    args = Namespace(
        profile_dir=str(tmp_path / "profile"),
        keep_open=False,
        artifact_materialization_timeout_seconds=10.0,
    )
    expected = {
        "expected_artifact": "chatgpt_claudecode_workflow-2_v0.1.124.zip",
        "expected_version": "v0.1.124",
        "expected_role": "candidate_release",
    }

    materialized = asyncio.run(
        _materialize_ask_release_rendered_candidate(
            backend,
            args,
            _protocol_result(metadata, sha256="0" * 64),
            expected,
        )
    )
    validated = _validate_ask_release_candidate_result(materialized, expected)

    assert validated["ok"] is False
    assert validated["status"] == "envelope_artifact_metadata_mismatch"
    assert validated["artifact_materialization_proven"] is False
    assert validated["download_performed"] is True
    assert validated["verification_performed"] is True
    assert validated["envelope_metadata_verification"]["mismatches"] == ["sha256"]
