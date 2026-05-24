from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import subprocess
import zipfile
import httpx
import pytest
from pathlib import Path


@pytest.fixture(autouse=True)
def _isolate_cli_defaults(monkeypatch, tmp_path) -> None:
    """Keep tests hermetic when a developer has Promptbranch defaults configured locally."""
    monkeypatch.setenv("CHATGPT_CLI_CONFIG", str(tmp_path / "missing-cli-config.json"))
    monkeypatch.delenv("CHATGPT_SERVICE_TIMEOUT_SECONDS", raising=False)

from promptbranch_cli import build_backend, main, make_parser, _normalize_global_options, _chat_list_payload, _verify_project_source_upload_change, cmd_artifact_adopt, cmd_artifact_candidate_test, cmd_artifact_candidate_status, cmd_artifact_mvp_status, cmd_release_doctor, cmd_release_config, cmd_release_install, cmd_release_test, cmd_release_adopt, cmd_release_policy_sync, cmd_release_git_sync, cmd_release_lifecycle, cmd_release_lifecycle_status, cmd_artifact_candidate_next, cmd_artifact_candidate_run, cmd_artifact_accept_candidate, _classify_protocol_submit_visibility_failure, _protocol_transcript_snapshot, _compare_protocol_transcript_snapshots, _persist_protocol_ask_debug_record, _protocol_fresh_turn_evidence, _validate_protocol_reply_against_request, _parse_protocol_reply_after_ask
from promptbranch_state import ConversationStateStore
from promptbranch_artifacts import ArtifactRegistry, ArtifactRecord



def test_protocol_reply_validation_allows_no_artifact_without_output_version() -> None:
    envelope = {
        "request_id": "req-no-artifact",
        "correlation_id": "corr-no-artifact",
        "artifact": {
            "current_baseline": "chatgpt_claudecode_workflow_v0.0.247.zip",
            "current_version": "v0.0.247",
            "target_version": "v0.0.247",
            "release_type": "normal",
        },
    }
    parsed = {
        "ok": True,
        "request_id": "req-no-artifact",
        "correlation_id": "corr-no-artifact",
        "status": "no_artifact",
        "result_type": "no_change",
        "baseline": {
            "input_artifact": "chatgpt_claudecode_workflow_v0.0.247.zip",
            "input_version": "v0.0.247",
            "output_artifact": None,
            "output_version": None,
            "target_version": "v0.0.247",
            "release_type": "normal",
        },
        "artifacts": [],
    }

    ok, errors = _validate_protocol_reply_against_request(parsed, envelope)

    assert ok is True
    assert errors == []




def test_protocol_reply_validation_allows_parser_shaped_no_artifact_without_output_version() -> None:
    envelope = {
        "request_id": "req-no-artifact",
        "correlation_id": "corr-no-artifact",
        "artifact": {
            "current_baseline": "chatgpt_claudecode_workflow_v0.0.247.zip",
            "current_version": "v0.0.247",
            "target_version": "v0.0.247",
            "release_type": "normal",
        },
    }
    parsed = {
        "ok": True,
        "status": "valid",
        "request_id": "req-no-artifact",
        "correlation_id": "corr-no-artifact",
        "reply_status": "no_artifact",
        "result_type": "no_change",
        "baseline": {
            "input_artifact": "chatgpt_claudecode_workflow_v0.0.247.zip",
            "input_version": "v0.0.247",
            "output_artifact": None,
            "output_version": None,
            "target_version": "v0.0.247",
            "release_type": "normal",
        },
        "reply": {
            "status": "no_artifact",
            "result_type": "no_change",
            "artifacts": [],
        },
        "artifact_candidate_count": 0,
        "artifact_candidates": [],
    }

    ok, errors = _validate_protocol_reply_against_request(parsed, envelope)

    assert ok is True
    assert errors == []

def test_protocol_reply_validation_rejects_wrong_no_artifact_target_echo() -> None:
    envelope = {
        "request_id": "req-no-artifact",
        "correlation_id": "corr-no-artifact",
        "artifact": {
            "current_baseline": "chatgpt_claudecode_workflow_v0.0.247.zip",
            "current_version": "v0.0.247",
            "target_version": "v0.0.247",
            "release_type": "normal",
        },
    }
    parsed = {
        "ok": True,
        "request_id": "req-no-artifact",
        "correlation_id": "corr-no-artifact",
        "status": "no_artifact",
        "result_type": "no_change",
        "baseline": {
            "input_artifact": "chatgpt_claudecode_workflow_v0.0.247.zip",
            "input_version": "v0.0.247",
            "output_artifact": None,
            "output_version": None,
            "target_version": "v0.0.999",
            "release_type": "normal",
        },
        "artifacts": [],
    }

    ok, errors = _validate_protocol_reply_against_request(parsed, envelope)

    assert ok is False
    assert errors == ["target_version_mismatch"]

def test_parser_accepts_service_options() -> None:
    parser = make_parser()
    args = parser.parse_args(
        [
            "--service-base-url",
            "http://localhost:8000",
            "--service-token",
            "secret",
            "ask",
            "hello",
        ]
    )
    assert args.service_base_url == "http://localhost:8000"
    assert args.service_token == "secret"
    assert args.command == "ask"


def test_global_options_after_subcommand_include_service_flags() -> None:
    argv = [
        "ask",
        "hello",
        "--service-base-url",
        "http://localhost:8000",
        "--service-token",
        "secret",
    ]
    normalized = _normalize_global_options(argv)
    assert normalized[:4] == [
        "--service-base-url",
        "http://localhost:8000",
        "--service-token",
        "secret",
    ]
    assert normalized[4:] == ["ask", "hello"]


def test_build_backend_uses_service_client_when_base_url_is_present() -> None:
    args = argparse.Namespace(
        service_base_url="http://localhost:8000",
        service_token="secret",
        service_timeout_seconds=123.0,
        project_url="https://chatgpt.com/g/demo/project",
        email=None,
        password=None,
        password_file=None,
        profile_dir="./.pb_profile",
        headless=False,
        use_playwright=False,
        browser_channel=None,
        enable_fedcm=False,
        keep_no_sandbox=False,
        max_retries=2,
        retry_backoff_seconds=2.0,
    )
    backend = build_backend(args)
    assert backend.__class__.__name__ == "ServiceBackend"


def test_main_can_ask_via_service_backend(monkeypatch, capsys, tmp_path) -> None:
    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            assert base_url == "http://localhost:8000"
            assert token == "secret"
            assert timeout == 900.0

        def ask_result(self, prompt: str, **kwargs):
            assert prompt == "hello"
            assert kwargs["project_url"] == "https://chatgpt.com/g/demo/project"
            return {"answer": "world", "conversation_url": "https://chatgpt.com/g/demo/c/123"}

    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    exit_code = main(
        [
            "--service-base-url",
            "http://localhost:8000",
            "--service-token",
            "secret",
            "--profile-dir",
            str(tmp_path),
            "--project-url",
            "https://chatgpt.com/g/demo/project",
            "ask",
            "hello",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.out.strip() == "world"






def test_protocol_fresh_turn_does_not_treat_old_prompt_prefix_as_fresh() -> None:
    envelope = {
        "request_id": "req-new",
        "task": {"conversation_id": "abc123"},
        "intent": {"summary": "Protocol smoke only. Return a valid promptbranch.ask.reply envelope with status no_artifact. Do not create a ZIP."},
    }
    payload = {
        "conversation_id": "abc123",
        "messages": [
            {"index": 1, "id": "u-old", "role": "user", "text": "Protocol smoke only. Return a valid promptbranch.ask.reply envelope with status no_artifact. Do not create a ZIP."},
        ],
    }
    marker = {"available": True, "message_count": 1, "latest_user_message_index": 1}

    evidence = _protocol_fresh_turn_evidence(payload, pre_ask_marker=marker, envelope=envelope)

    assert evidence["prompt_prefix_found"] is True
    assert evidence["prompt_prefix_message_count"] == 1
    assert evidence["prompt_prefix_fresh_message_count"] == 0
    assert evidence["newer_user_message_count"] == 0
    assert evidence["fresh_user_turn_visible"] is False


def test_protocol_fresh_turn_accepts_newer_prompt_prefix() -> None:
    envelope = {
        "request_id": "req-new",
        "task": {"conversation_id": "abc123"},
        "intent": {"summary": "Protocol smoke only. Return a valid promptbranch.ask.reply envelope with status no_artifact. Do not create a ZIP."},
    }
    payload = {
        "conversation_id": "abc123",
        "messages": [
            {"index": 1, "id": "u-old", "role": "user", "text": "old"},
            {"index": 2, "id": "u-new", "role": "user", "text": "Protocol smoke only. Return a valid promptbranch.ask.reply envelope with status no_artifact. Do not create a ZIP."},
        ],
    }
    marker = {"available": True, "message_count": 1, "latest_user_message_index": 1}

    evidence = _protocol_fresh_turn_evidence(payload, pre_ask_marker=marker, envelope=envelope)

    assert evidence["prompt_prefix_fresh_message_count"] == 1
    assert evidence["newer_user_message_count"] == 1
    assert evidence["fresh_user_turn_visible"] is True

def test_protocol_submit_visibility_failure_distinguishes_not_triggered() -> None:
    status, error, instruction = _classify_protocol_submit_visibility_failure(
        {"submit_evidence": {"clicked": False, "enter_fallback_used": False}},
        {"fresh_user_turn_visible": False},
    )

    assert status == "ask_submit_not_triggered"
    assert "clicked send button" in error
    assert "not proven submitted" in instruction




def test_protocol_submit_visibility_failure_distinguishes_old_turns_only() -> None:
    status, error, instruction = _classify_protocol_submit_visibility_failure(
        {
            "submit_evidence": {
                "clicked": True,
                "composer_cleared": True,
                "dom_user_turn_evidence": {"visible": True, "status": "user_turn_dom_visible"},
            }
        },
        {
            "fresh_user_turn_visible": False,
            "request_message_found": False,
            "newer_user_message_count": 0,
        },
    )

    assert status == "submit_clicked_old_turns_only"
    assert "no request-id match" in error
    assert "old or already-loaded" in instruction

def test_protocol_submit_visibility_failure_distinguishes_dom_visible_backend_stale() -> None:
    status, error, instruction = _classify_protocol_submit_visibility_failure(
        {
            "submit_evidence": {
                "clicked": True,
                "dom_user_turn_evidence": {"visible": True, "status": "user_turn_dom_visible"},
            }
        },
        {"fresh_user_turn_visible": False},
    )

    assert status == "submit_visible_but_task_reader_stale"
    assert "backend/task transcript" in error
    assert "browser DOM" in instruction



def test_protocol_submit_visibility_failure_distinguishes_selector_missed() -> None:
    status, error, instruction = _classify_protocol_submit_visibility_failure(
        {
            "submit_evidence": {
                "clicked": True,
                "composer_cleared": True,
                "before_user_turns": {
                    "count": 0,
                    "generic_turns": {"count": 12},
                },
                "dom_user_turn_evidence": {"visible": False, "status": "user_turn_dom_not_visible"},
            }
        },
        {"fresh_user_turn_visible": False},
    )

    assert status == "ask_clicked_composer_cleared_dom_selector_missed"
    assert "role-specific user-turn selectors" in error
    assert "DOM role selectors missed" in instruction


def test_protocol_submit_visibility_failure_distinguishes_composer_cleared_backend_stale() -> None:
    status, error, instruction = _classify_protocol_submit_visibility_failure(
        {
            "submit_evidence": {
                "clicked": True,
                "composer_cleared": True,
                "before_user_turns": {"count": 0, "generic_turns": {"count": 0}},
                "dom_user_turn_evidence": {"visible": False, "status": "user_turn_dom_not_visible"},
            }
        },
        {"fresh_user_turn_visible": False},
    )

    assert status == "ask_clicked_composer_cleared_backend_stale"
    assert "composer" in error
    assert "task transcript" in instruction


def test_protocol_submit_visibility_failure_distinguishes_unchanged_backend_snapshot() -> None:
    status, error, instruction = _classify_protocol_submit_visibility_failure(
        {
            "submit_evidence": {
                "clicked": True,
                "composer_cleared": True,
                "dom_user_turn_evidence": {"visible": False, "status": "user_turn_dom_not_visible"},
            }
        },
        {
            "fresh_user_turn_visible": False,
            "backend_refresh": {
                "attempt_count": 3,
                "snapshot_changed": False,
                "latest_message_id_changed": False,
                "fingerprint_changed": False,
            },
        },
    )

    assert status == "submit_visible_but_backend_snapshot_stale"
    assert "backend transcript snapshots did not change" in error
    assert "backend transcript snapshots stayed stale" in instruction


def test_protocol_submit_visibility_failure_distinguishes_wrong_conversation() -> None:
    status, error, instruction = _classify_protocol_submit_visibility_failure(
        {"submit_evidence": {"clicked": True, "composer_cleared": True}},
        {
            "fresh_user_turn_visible": False,
            "source_agreement": {
                "same_conversation_id": False,
                "expected_conversation_id": "expected",
                "actual_conversation_id": "actual",
            },
        },
    )

    assert status == "submit_clicked_target_conversation_lost"
    assert "different conversation" in error
    assert "different conversation" in instruction
    assert "refused" in instruction


def test_protocol_submit_visibility_failure_distinguishes_no_turn_materialized() -> None:
    status, error, instruction = _classify_protocol_submit_visibility_failure(
        {
            "submit_evidence": {
                "clicked": True,
                "composer_cleared": False,
                "dom_user_turn_evidence": {"visible": False, "status": "user_turn_dom_not_visible"},
            }
        },
        {"fresh_user_turn_visible": False},
    )

    assert status == "ask_clicked_but_no_turn_materialized"
    assert "no DOM or backend evidence" in error
    assert "submitted or attempted" in instruction

def test_protocol_submit_visibility_failure_preserves_unknown_without_browser_evidence() -> None:
    status, error, instruction = _classify_protocol_submit_visibility_failure(
        {"answer": "stale"},
        {"fresh_user_turn_visible": False},
    )

    assert status == "ask_submission_not_visible"
    assert "browser submit evidence was unavailable" in error
    assert "submit evidence was unavailable" in instruction

def test_protocol_transcript_snapshot_compares_ids_and_fingerprints() -> None:
    envelope = {"request_id": "req-1", "intent": {"summary": "Protocol smoke"}}
    before = {
        "conversation_id": "c1",
        "conversation_url": "https://chatgpt.com/c/c1",
        "messages": [
            {"id": "m1", "index": 1, "turn_index": 1, "text": "hello", "answers": []},
        ],
    }
    after = {
        "conversation_id": "c1",
        "conversation_url": "https://chatgpt.com/c/c1",
        "messages": [
            {"id": "m1", "index": 1, "turn_index": 1, "text": "hello", "answers": []},
            {"id": "m2", "index": 2, "turn_index": 2, "text": "req-1 Protocol smoke", "answers": []},
        ],
    }

    before_snapshot = _protocol_transcript_snapshot(before, source="before", envelope=envelope)
    after_snapshot = _protocol_transcript_snapshot(after, source="after", envelope=envelope)
    comparison = _compare_protocol_transcript_snapshots(before_snapshot, after_snapshot)

    assert before_snapshot["message_count"] == 1
    assert after_snapshot["message_count"] == 2
    assert after_snapshot["request_id_found"] is True
    assert after_snapshot["prompt_prefix_found"] is True
    assert comparison["message_count_delta"] == 1
    assert comparison["latest_user_message_id_changed"] is True
    assert comparison["fingerprint_changed"] is True


def test_protocol_ask_debug_record_writes_diagnostic_files(tmp_path) -> None:
    args = argparse.Namespace(profile_dir=str(tmp_path))
    result = {
        "ok": False,
        "status": "submit_visible_but_backend_snapshot_stale",
        "request": {"request_id": "req-debug"},
        "ask_submit_evidence": {"clicked": True, "composer_cleared": True},
        "pre_ask_marker": {
            "transcript_snapshot": {
                "available": True,
                "source": "pre",
                "message_count": 1,
                "raw_fingerprint": "sha256:before",
            }
        },
        "fresh_turn_evidence": {
            "attempts": [
                {"snapshot": {"available": True, "source": "after", "message_count": 1, "raw_fingerprint": "sha256:before"}}
            ],
            "backend_refresh": {"attempt_count": 1, "snapshot_changed": False},
        },
    }

    files = _persist_protocol_ask_debug_record(args, result)

    assert "request.json" in files
    assert "submit_evidence.json" in files
    assert "before_backend_snapshot.json" in files
    assert "after_backend_snapshots.jsonl" in files
    assert "classification.json" in files
    assert Path(files["classification.json"]).read_text(encoding="utf-8")


def test_ask_protocol_print_request_uses_current_baseline(monkeypatch, capsys, tmp_path) -> None:
    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

        def ask_result(self, *args, **kwargs):
            raise AssertionError("--print-request-json must not send the ask")

    project_url = "https://chatgpt.com/g/g-p-demo-claude-code/project"
    conversation_url = "https://chatgpt.com/g/g-p-demo-claude-code/c/abc123"
    store = ConversationStateStore(str(tmp_path))
    store.remember_project(project_url, project_name="Claude Code workflow in ChatGPT")
    store.remember(project_url, conversation_url, project_name="Claude Code workflow in ChatGPT")
    store.remember_artifact(
        project_url=project_url,
        artifact_ref="chatgpt_claudecode_workflow_v0.0.206.zip",
        artifact_version="v0.0.206",
        source_ref="chatgpt_claudecode_workflow_v0.0.206.zip",
        source_version="v0.0.206",
    )
    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(tmp_path),
        "--project-url", project_url,
        "ask", "continue v0.0.210",
        "--protocol", "--from-current-baseline", "--target-version", "v0.0.210", "--print-request-json",
    ])

    payload = json.loads(capsys.readouterr().out)
    request = payload["request"]
    assert exit_code == 0
    assert payload["action"] == "ask_protocol_request"
    assert payload["automation_performed"] is False
    assert request["schema"] == "promptbranch.ask.request"
    assert request["artifact"]["current_baseline"] == "chatgpt_claudecode_workflow_v0.0.206.zip"
    assert request["artifact"]["current_version"] == "v0.0.206"
    assert request["artifact"]["source_ref"] == "chatgpt_claudecode_workflow_v0.0.206.zip"
    assert request["artifact"]["target_version"] == "v0.0.210"
    assert request["constraints"]["no_auto_adopt"] is True


def test_ask_protocol_wraps_prompt_before_sending(monkeypatch, capsys, tmp_path) -> None:
    captured: dict[str, str] = {}

    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

        def ask_result(self, prompt: str, **kwargs):
            captured["prompt"] = prompt
            return {"answer": "ok", "conversation_url": "https://chatgpt.com/g/g-p-demo-claude-code/c/abc123"}

    project_url = "https://chatgpt.com/g/g-p-demo-claude-code/project"
    store = ConversationStateStore(str(tmp_path))
    store.remember_project(project_url, project_name="Claude Code workflow in ChatGPT")
    store.remember_artifact(
        project_url=project_url,
        artifact_ref="chatgpt_claudecode_workflow_v0.0.206.zip",
        artifact_version="v0.0.206",
        source_ref="chatgpt_claudecode_workflow_v0.0.206.zip",
        source_version="v0.0.206",
    )
    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(tmp_path),
        "--project-url", project_url,
        "ask", "continue next slice", "--protocol", "--target-version", "v0.0.210",
    ])

    assert exit_code == 0
    assert capsys.readouterr().out.strip() == "ok"
    assert "BEGIN_PROMPTBRANCH_REQUEST_JSON" in captured["prompt"]
    assert '"current_baseline": "chatgpt_claudecode_workflow_v0.0.206.zip"' in captured["prompt"]
    assert '"target_version": "v0.0.210"' in captured["prompt"]
    assert "BEGIN_PROMPTBRANCH_REPLY_JSON" in captured["prompt"]



def test_ask_protocol_parse_reply_validates_request_and_baseline(monkeypatch, capsys, tmp_path) -> None:
    captured: dict[str, object] = {"ask_called": False}
    project_url = "https://chatgpt.com/g/g-p-demo-claude-code/project"
    conversation_url = "https://chatgpt.com/g/g-p-demo-claude-code/c/abc123"
    reply = {
        "schema": "promptbranch.ask.reply",
        "schema_version": "1.0",
        "request_id": "req-v210",
        "correlation_id": "corr-v210",
        "status": "completed",
        "result_type": "release_candidate",
        "summary": "Built candidate.",
        "baseline": {
            "input_artifact": "chatgpt_claudecode_workflow_v0.0.210.zip",
            "input_version": "v0.0.210",
            "output_artifact": "chatgpt_claudecode_workflow_v0.0.211.zip",
            "output_version": "v0.0.211",
            "release_type": "normal",
        },
        "changes": [],
        "artifacts": [
            {
                "kind": "zip",
                "filename": "chatgpt_claudecode_workflow_v0.0.211.zip",
                "version": "v0.0.211",
                "role": "candidate_release",
                "download": {"available": True, "link_text": "chatgpt_claudecode_workflow_v0.0.211.zip", "url": None},
            }
        ],
        "validation": {"claimed": ["focused tests"], "not_claimed": ["full suite"]},
        "next_step": {"operator_action": "download_verify_test_adopt"},
    }
    answer_text = "BEGIN_PROMPTBRANCH_REPLY_JSON\n" + json.dumps(reply) + "\nEND_PROMPTBRANCH_REPLY_JSON\n"

    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            captured["client_timeout"] = timeout

        def ask_result(self, prompt: str, **kwargs):
            captured["ask_called"] = True
            captured["prompt"] = prompt
            captured["ask_kwargs"] = dict(kwargs)
            return {"answer": "Thinking\n\nStreaming interrupted. Waiting for the complete message...", "conversation_url": conversation_url}

        def get_chat(self, conversation_url: str, **kwargs):
            turns = [
                {"index": 1, "id": "u-old", "role": "user", "text": "previous ask"},
                {"index": 2, "id": "a-old", "role": "assistant", "text": "previous answer"},
            ]
            if captured.get("ask_called"):
                turns.extend([
                    {"index": 3, "id": "u-new", "role": "user", "text": str(captured["prompt"])},
                    {"index": 4, "id": "a-new", "role": "assistant", "text": answer_text},
                ])
            return {
                "ok": True,
                "conversation_url": conversation_url,
                "conversation_id": "abc123",
                "title": "Protocol run",
                "turns": turns,
            }

    store = ConversationStateStore(str(tmp_path))
    store.remember_project(project_url, project_name="Claude Code workflow in ChatGPT")
    store.remember(project_url, conversation_url, project_name="Claude Code workflow in ChatGPT")
    store.remember_artifact(
        project_url=project_url,
        artifact_ref="chatgpt_claudecode_workflow_v0.0.210.zip",
        artifact_version="v0.0.210",
        source_ref="chatgpt_claudecode_workflow_v0.0.210.zip",
        source_version="v0.0.210",
    )
    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(tmp_path),
        "--project-url", project_url,
        "ask", "continue next slice",
        "--protocol", "--target-version", "v0.0.211",
        "--request-id", "req-v210",
        "--correlation-id", "corr-v210",
        "--parse-reply", "--json",
    ])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert captured["client_timeout"] >= 222.0
    assert captured["ask_kwargs"]["expect_json"] is False
    assert payload["action"] == "ask_protocol_run"
    assert payload["status"] == "reply_validated"
    assert payload["reply_validation_ok"] is True
    assert payload["request_id"] == "req-v210"
    assert payload["correlation_id"] == "corr-v210"
    assert payload["artifact_candidate_count"] == 1
    assert payload["selected_answer"]["answer_id"] == "a-new"
    assert payload["ask_response"]["answer"] is None
    assert payload["ask_response"]["answer_source"] == "protocol_reply_authoritative"
    assert payload["ask_response"]["authoritative_reply_location"] == "reply"
    assert payload["ask_response"]["raw_browser_answer_preview"].startswith("Thinking")
    assert payload["ask_response"]["raw_browser_answer_complete"] is False
    assert payload["ask_response"]["selected_answer_id"] == "a-new"
    assert payload["pre_ask_marker"]["latest_answer_id"] == "a-old"
    assert payload["answer_selection"]["fresh_request_message_matched"] is True
    assert payload["download_performed"] is False
    assert payload["migration_performed"] is False
    assert payload["adoption_performed"] is False
    assert payload["request_persisted"] is True
    assert Path(payload["protocol_run_record_path"]).is_file()


def test_parse_protocol_reply_uses_state_snapshot_when_service_omits_conversation_url(tmp_path) -> None:
    project_url = "https://chatgpt.com/g/g-p-demo-claude-code/project"
    conversation_url = "https://chatgpt.com/g/g-p-demo-claude-code/c/abc123"
    request_id = "req-state-snapshot"
    correlation_id = "corr-state-snapshot"
    reply = {
        "schema": "promptbranch.ask.reply",
        "schema_version": "1.0",
        "request_id": request_id,
        "correlation_id": correlation_id,
        "status": "no_artifact",
        "result_type": "no_change",
        "summary": "Protocol smoke completed without an artifact.",
        "baseline": {
            "input_artifact": "chatgpt_claudecode_workflow_v0.0.247.zip",
            "input_version": "v0.0.247",
            "output_artifact": None,
            "output_version": None,
            "target_version": "v0.0.247",
            "release_type": "normal",
        },
        "changes": [],
        "artifacts": [],
        "validation": {"claimed": ["protocol smoke"], "not_claimed": []},
        "next_step": {"operator_action": "none"},
    }
    answer_text = "BEGIN_PROMPTBRANCH_REPLY_JSON\n" + json.dumps(reply) + "\nEND_PROMPTBRANCH_REPLY_JSON\n"
    envelope = {
        "schema": "promptbranch.ask.request",
        "schema_version": "1.0",
        "request_id": request_id,
        "correlation_id": correlation_id,
        "task": {"conversation_id": "current", "turn_policy": "assistant_may_return_one_protocol_reply"},
        "intent": {"summary": "protocol smoke"},
        "artifact": {
            "current_baseline": "chatgpt_claudecode_workflow_v0.0.247.zip",
            "current_version": "v0.0.247",
            "target_version": "v0.0.247",
            "release_type": "normal",
        },
    }

    store = ConversationStateStore(str(tmp_path))
    store.remember_project(project_url, project_name="Claude Code workflow in ChatGPT")
    store.remember(project_url, conversation_url, project_name="Claude Code workflow in ChatGPT")

    class FakeBackend:
        def __init__(self) -> None:
            self.calls: list[str] = []

        async def get_chat(self, url: str, **kwargs):
            self.calls.append(url)
            return {
                "ok": True,
                "conversation_url": url,
                "conversation_id": "abc123",
                "title": "Protocol run",
                "turns": [
                    {"index": 1, "id": "u-new", "role": "user", "text": f"{request_id} protocol smoke"},
                    {"index": 2, "id": "a-new", "role": "assistant", "text": answer_text},
                ],
            }

    args = argparse.Namespace(
        profile_dir=str(tmp_path),
        project_url=project_url,
        conversation_url=None,
        keep_open=False,
        answer_id=None,
        answer_index=None,
        protocol_fresh_turn_timeout_seconds=0.0,
        protocol_fresh_turn_poll_seconds=0.1,
    )
    backend = FakeBackend()

    result = asyncio.run(_parse_protocol_reply_after_ask(
        backend,
        args,
        envelope=envelope,
        ask_response={"ok": True, "answer": "submitted"},
        pre_ask_marker=None,
    ))

    assert result["ok"] is True
    assert result["status"] == "reply_validated"
    assert result["conversation_url"] == conversation_url
    assert backend.calls == [conversation_url]
    assert result["reply_validation_errors"] == []
    assert result["download_performed"] is False
    assert result["migration_performed"] is False
    assert result["adoption_performed"] is False


def test_ask_protocol_parse_reply_emits_json_on_ask_timeout(monkeypatch, capsys, tmp_path) -> None:
    project_url = "https://chatgpt.com/g/g-p-demo-claude-code/project"
    conversation_url = "https://chatgpt.com/g/g-p-demo-claude-code/c/abc123"
    captured: dict[str, object] = {}

    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            captured["client_timeout"] = timeout

        def ask_result(self, prompt: str, **kwargs):
            captured["ask_kwargs"] = dict(kwargs)
            raise TimeoutError("protocol smoke timed out")

    store = ConversationStateStore(str(tmp_path))
    store.remember_project(project_url, project_name="Claude Code workflow in ChatGPT")
    store.remember(project_url, conversation_url, project_name="Claude Code workflow in ChatGPT")
    store.remember_artifact(
        project_url=project_url,
        artifact_ref="chatgpt_claudecode_workflow_v0.0.209.zip",
        artifact_version="v0.0.209",
        source_ref="chatgpt_claudecode_workflow_v0.0.209.zip",
        source_version="v0.0.209",
    )
    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(tmp_path),
        "--project-url", project_url,
        "ask", "protocol smoke",
        "--protocol", "--target-version", "v0.0.210",
        "--request-id", "req-v210",
        "--correlation-id", "corr-v210",
        "--parse-reply", "--json",
        "--protocol-timeout-seconds", "3",
    ])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert captured["client_timeout"] >= 105.0
    assert captured["ask_kwargs"]["expect_json"] is False
    assert payload["ok"] is False
    assert payload["action"] == "ask_protocol_run"
    assert payload["status"] == "response_timeout"
    assert payload["timeout_layer"] == "unknown_response_wait"
    assert payload["error_type"] == "TimeoutError"
    assert payload["request_id"] == "req-v210"
    assert payload["correlation_id"] == "corr-v210"
    assert payload["current_baseline"] == "chatgpt_claudecode_workflow_v0.0.209.zip"
    assert payload["target_version"] == "v0.0.210"
    assert payload["protocol_timeout_seconds"] == 3.0
    assert payload["download_performed"] is False
    assert payload["migration_performed"] is False
    assert payload["adoption_performed"] is False
    assert payload["request_persisted"] is True
    assert Path(payload["protocol_run_record_path"]).is_file()



def test_ask_protocol_parse_reply_recovers_from_service_read_timeout_via_transcript(monkeypatch, capsys, tmp_path) -> None:
    project_url = "https://chatgpt.com/g/g-p-demo-claude-code/project"
    conversation_url = "https://chatgpt.com/g/g-p-demo-claude-code/c/abc123"
    request_id = "req-timeout-recovery"
    correlation_id = "corr-timeout-recovery"
    captured: dict[str, object] = {"ask_called": False}
    reply = {
        "schema": "promptbranch.ask.reply",
        "schema_version": "1.0",
        "request_id": request_id,
        "correlation_id": correlation_id,
        "status": "no_artifact",
        "result_type": "no_change",
        "summary": "Protocol smoke completed after service timeout.",
        "baseline": {
            "input_artifact": "chatgpt_claudecode_workflow_v0.0.247.zip",
            "input_version": "v0.0.247",
            "output_artifact": None,
            "output_version": "v0.0.247",
            "release_type": "normal",
        },
        "changes": [],
        "artifacts": [],
        "validation": {"claimed": ["protocol smoke"], "not_claimed": []},
        "next_step": {"operator_action": "none"},
    }
    answer_text = "BEGIN_PROMPTBRANCH_REPLY_JSON\n" + json.dumps(reply) + "\nEND_PROMPTBRANCH_REPLY_JSON\n"

    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            captured["client_timeout"] = timeout

        def ask_result(self, prompt: str, **kwargs):
            captured["ask_called"] = True
            captured["prompt"] = prompt
            raise httpx.ReadTimeout("service read timed out")

        def get_chat(self, conversation_url: str, **kwargs):
            assert captured["ask_called"] is True
            return {
                "ok": True,
                "conversation_url": conversation_url,
                "conversation_id": "abc123",
                "title": "Protocol run",
                "turns": [
                    {"index": 1, "id": "u-old", "role": "user", "text": "previous ask"},
                    {"index": 2, "id": "a-old", "role": "assistant", "text": "previous answer"},
                    {"index": 3, "id": "u-new", "role": "user", "text": str(captured["prompt"])},
                    {"index": 4, "id": "a-new", "role": "assistant", "text": answer_text},
                ],
            }

    store = ConversationStateStore(str(tmp_path))
    store.remember_project(project_url, project_name="Claude Code workflow in ChatGPT")
    store.remember(project_url, conversation_url, project_name="Claude Code workflow in ChatGPT")
    store.remember_artifact(
        project_url=project_url,
        artifact_ref="chatgpt_claudecode_workflow_v0.0.247.zip",
        artifact_version="v0.0.247",
        source_ref="chatgpt_claudecode_workflow_v0.0.247.zip",
        source_version="v0.0.247",
    )
    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(tmp_path),
        "--project-url", project_url,
        "ask", "protocol smoke",
        "--protocol", "--target-version", "v0.0.247",
        "--request-id", request_id,
        "--correlation-id", correlation_id,
        "--parse-reply", "--json",
    ])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["ok"] is True
    assert payload["status"] == "recovered_after_service_timeout"
    assert payload["reply_validation_ok"] is True
    assert payload["request_id"] == request_id
    assert payload["correlation_id"] == correlation_id
    assert payload["reply_status"] == "no_artifact"
    assert payload["result_type"] == "no_change"
    assert payload["artifact_candidate_count"] == 0
    assert payload["timeout_layer"] == "service_client"
    assert payload["service_timeout_recovery"]["source"] == "task_transcript_reparse"
    assert payload["download_performed"] is False
    assert payload["migration_performed"] is False
    assert payload["adoption_performed"] is False
    assert Path(payload["protocol_run_record_path"]).is_file()
    recorded = json.loads(Path(payload["protocol_run_record_path"]).read_text(encoding="utf-8"))
    assert recorded["status"] == "recovered_after_service_timeout"


def test_ask_protocol_parse_reply_preserves_partial_submit_evidence(monkeypatch, capsys, tmp_path) -> None:
    project_url = "https://chatgpt.com/g/g-p-demo-claude-code/project"
    conversation_url = "https://chatgpt.com/g/g-p-demo-claude-code/c/abc123"

    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            self.timeout = timeout

        def ask_result(self, prompt: str, **kwargs):
            return {
                "ok": False,
                "status": "assistant_response_timeout",
                "error": "Timed out waiting for an assistant response",
                "error_type": "ResponseTimeoutError",
                "timeout_layer": "assistant_response",
                "answer": None,
                "conversation_url": conversation_url,
                "submit_evidence": {
                    "status": "clicked_submit_button",
                    "clicked": True,
                    "composer_cleared": True,
                    "dom_user_turn_evidence": {"visible": True, "status": "user_turn_dom_visible"},
                },
                "partial_result": True,
                "debug_artifacts": ["debug_artifacts/response_wait.txt"],
            }

        def get_chat(self, conversation_url: str, **kwargs):  # pragma: no cover - should not be needed for partial service failure
            raise AssertionError("partial ask timeout should not parse task messages")

    store = ConversationStateStore(str(tmp_path))
    store.remember_project(project_url, project_name="Claude Code workflow in ChatGPT")
    store.remember(project_url, conversation_url, project_name="Claude Code workflow in ChatGPT")
    store.remember_artifact(
        project_url=project_url,
        artifact_ref="chatgpt_claudecode_workflow_v0.0.221.zip",
        artifact_version="v0.0.221",
        source_ref="chatgpt_claudecode_workflow_v0.0.221.zip",
        source_version="v0.0.221",
    )
    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(tmp_path),
        "--project-url", project_url,
        "ask", "protocol smoke",
        "--protocol", "--target-version", "v0.0.221",
        "--request-id", "req-v214",
        "--correlation-id", "corr-v214",
        "--parse-reply", "--json",
    ])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert payload["ok"] is False
    assert payload["status"] == "assistant_response_timeout"
    assert payload["timeout_layer"] == "assistant_response"
    assert payload["partial_submit_evidence_returned"] is True
    assert payload["ask_submit_evidence"]["clicked"] is True
    assert payload["ask_submit_evidence"]["dom_user_turn_evidence"]["visible"] is True
    assert payload["download_performed"] is False
    assert payload["migration_performed"] is False
    assert payload["adoption_performed"] is False
    assert payload["debug_artifacts"] == ["debug_artifacts/response_wait.txt"]


def test_ask_protocol_parse_reply_fails_closed_on_stale_answer(monkeypatch, capsys, tmp_path) -> None:
    project_url = "https://chatgpt.com/g/g-p-demo-claude-code/project"
    conversation_url = "https://chatgpt.com/g/g-p-demo-claude-code/c/abc123"
    captured: dict[str, object] = {"ask_called": False}

    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

        def ask_result(self, prompt: str, **kwargs):
            captured["ask_called"] = True
            captured["prompt"] = prompt
            return {"answer": "submitted", "conversation_url": conversation_url}

        def get_chat(self, conversation_url: str, **kwargs):
            return {
                "ok": True,
                "conversation_url": conversation_url,
                "conversation_id": "abc123",
                "title": "Protocol run",
                "turns": [
                    {"index": 1, "id": "u-old", "role": "user", "text": "previous ask"},
                    {"index": 2, "id": "a-old", "role": "assistant", "text": "previous answer without protocol envelope"},
                ],
            }

    store = ConversationStateStore(str(tmp_path))
    store.remember_project(project_url, project_name="Claude Code workflow in ChatGPT")
    store.remember(project_url, conversation_url, project_name="Claude Code workflow in ChatGPT")
    store.remember_artifact(
        project_url=project_url,
        artifact_ref="chatgpt_claudecode_workflow_v0.0.210.zip",
        artifact_version="v0.0.210",
        source_ref="chatgpt_claudecode_workflow_v0.0.210.zip",
        source_version="v0.0.210",
    )
    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(tmp_path),
        "--project-url", project_url,
        "ask", "protocol smoke",
        "--protocol", "--target-version", "v0.0.211",
        "--request-id", "req-v210",
        "--correlation-id", "corr-v210",
        "--parse-reply", "--json",
        "--protocol-fresh-turn-timeout-seconds", "0",
    ])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert captured["ask_called"] is True
    assert payload["action"] == "ask_protocol_run"
    assert payload["status"] == "ask_submission_not_visible"
    assert payload["pre_ask_marker"]["latest_answer_id"] == "a-old"
    assert payload["post_ask_marker"]["latest_answer_id"] == "a-old"
    assert payload["fresh_turn_evidence"]["fresh_user_turn_visible"] is False
    assert payload["fresh_turn_evidence"]["message_count_delta"] == 0
    assert payload["answer_selection"]["selected"] is None
    assert payload["download_performed"] is False
    assert payload["migration_performed"] is False
    assert payload["adoption_performed"] is False


def test_ask_protocol_parse_reply_polls_until_fresh_turn_is_visible(monkeypatch, capsys, tmp_path) -> None:
    project_url = "https://chatgpt.com/g/g-p-demo-claude-code/project"
    conversation_url = "https://chatgpt.com/g/g-p-demo-claude-code/c/abc123"
    captured: dict[str, object] = {"ask_called": False, "get_chat_calls": 0}
    reply = {
        "schema": "promptbranch.ask.reply",
        "schema_version": "1.0",
        "request_id": "req-v211",
        "correlation_id": "corr-v211",
        "status": "no_artifact",
        "result_type": "no_change",
        "summary": "Protocol smoke passed.",
        "baseline": {
            "input_artifact": "chatgpt_claudecode_workflow_v0.0.211.zip",
            "input_version": "v0.0.211",
            "output_artifact": "chatgpt_claudecode_workflow_v0.0.221.zip",
            "output_version": "v0.0.221",
            "release_type": "normal",
        },
        "changes": [],
        "artifacts": [],
        "validation": {"claimed": ["protocol smoke"], "not_claimed": []},
        "next_step": {"operator_action": "none"},
    }
    answer_text = "BEGIN_PROMPTBRANCH_REPLY_JSON\n" + json.dumps(reply) + "\nEND_PROMPTBRANCH_REPLY_JSON\n"

    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

        def ask_result(self, prompt: str, **kwargs):
            captured["ask_called"] = True
            captured["prompt"] = prompt
            return {"answer": "submitted", "conversation_url": conversation_url}

        def get_chat(self, conversation_url: str, **kwargs):
            captured["get_chat_calls"] = int(captured.get("get_chat_calls") or 0) + 1
            turns = [
                {"index": 1, "id": "u-old", "role": "user", "text": "previous ask"},
                {"index": 2, "id": "a-old", "role": "assistant", "text": "previous answer"},
            ]
            # call 1 = pre-marker; call 2 = first post-submit refresh without new turn;
            # call 3 = later refresh where the submitted user turn and answer are visible.
            if captured["get_chat_calls"] >= 3:
                turns.extend([
                    {"index": 3, "id": "u-new", "role": "user", "text": str(captured["prompt"])},
                    {"index": 4, "id": "a-new", "role": "assistant", "text": answer_text},
                ])
            return {
                "ok": True,
                "conversation_url": conversation_url,
                "conversation_id": "abc123",
                "title": "Protocol run",
                "turns": turns,
            }

    store = ConversationStateStore(str(tmp_path))
    store.remember_project(project_url, project_name="Claude Code workflow in ChatGPT")
    store.remember(project_url, conversation_url, project_name="Claude Code workflow in ChatGPT")
    store.remember_artifact(
        project_url=project_url,
        artifact_ref="chatgpt_claudecode_workflow_v0.0.211.zip",
        artifact_version="v0.0.211",
        source_ref="chatgpt_claudecode_workflow_v0.0.211.zip",
        source_version="v0.0.211",
    )
    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)
    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(tmp_path),
        "--project-url", project_url,
        "ask", "protocol smoke",
        "--protocol", "--target-version", "v0.0.221",
        "--request-id", "req-v211",
        "--correlation-id", "corr-v211",
        "--parse-reply", "--json",
        "--protocol-fresh-turn-timeout-seconds", "1",
        "--protocol-fresh-turn-poll-seconds", "0.1",
    ])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["action"] == "ask_protocol_run"
    assert payload["status"] == "reply_validated"
    assert payload["selected_answer"]["answer_id"] == "a-new"
    assert payload["fresh_turn_evidence"]["fresh_user_turn_visible"] is True
    assert payload["fresh_turn_evidence"]["attempt_count"] >= 2
    assert captured["get_chat_calls"] >= 3



def test_ask_protocol_parse_reply_fails_closed_when_service_returns_wrong_conversation(monkeypatch, capsys, tmp_path) -> None:
    project_url = "https://chatgpt.com/g/g-p-demo-claude-code/project"
    expected_conversation_url = "https://chatgpt.com/g/g-p-demo-claude-code/c/expected123"
    wrong_conversation_url = "https://chatgpt.com/g/g-p-demo-claude-code/c/wrong456"
    captured: dict[str, object] = {"ask_called": False, "get_chat_calls": 0}

    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

        def ask_result(self, prompt: str, **kwargs):
            captured["ask_called"] = True
            return {
                "ok": True,
                "answer": "stale wrong-conversation answer that must not be parsed",
                "conversation_url": wrong_conversation_url,
                "submit_evidence": {"clicked": True, "composer_cleared": True},
            }

        def get_chat(self, conversation_url: str, **kwargs):
            captured["get_chat_calls"] = int(captured.get("get_chat_calls") or 0) + 1
            assert conversation_url == expected_conversation_url
            return {
                "ok": True,
                "conversation_url": expected_conversation_url,
                "conversation_id": "expected123",
                "title": "Protocol run",
                "turns": [
                    {"index": 1, "id": "u-old", "role": "user", "text": "previous ask"},
                    {"index": 2, "id": "a-old", "role": "assistant", "text": "previous answer"},
                ],
            }

    store = ConversationStateStore(str(tmp_path))
    store.remember_project(project_url, project_name="Claude Code workflow in ChatGPT")
    store.remember(project_url, expected_conversation_url, project_name="Claude Code workflow in ChatGPT")
    store.remember_artifact(
        project_url=project_url,
        artifact_ref="chatgpt_claudecode_workflow_v0.0.100.zip",
        artifact_version="v0.0.100",
        source_ref="chatgpt_claudecode_workflow_v0.0.100.zip",
        source_version="v0.0.100",
    )
    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(tmp_path),
        "--project-url", project_url,
        "ask", "protocol smoke",
        "--protocol", "--target-version", "v0.0.101",
        "--request-id", "req-conv-lock",
        "--correlation-id", "corr-conv-lock",
        "--parse-reply", "--json",
    ])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert captured["ask_called"] is True
    assert captured["get_chat_calls"] == 1  # pre-marker only; no polling wrong conversation
    assert payload["action"] == "ask_protocol_run"
    assert payload["status"] == "submit_clicked_target_conversation_lost"
    assert payload["error_type"] == "conversation_lock_mismatch"
    assert payload["conversation_id"] == "expected123"
    assert payload["response_conversation_id"] == "wrong456"
    assert payload["conversation_lock"]["expected_conversation_id"] == "expected123"
    assert payload["conversation_lock"]["actual_conversation_id"] == "wrong456"
    assert payload["answer_selection"]["selected"] is None
    assert payload["download_performed"] is False
    assert payload["migration_performed"] is False
    assert payload["adoption_performed"] is False

def test_ask_protocol_parse_reply_fails_closed_on_request_id_mismatch(monkeypatch, capsys, tmp_path) -> None:
    project_url = "https://chatgpt.com/g/g-p-demo-claude-code/project"
    conversation_url = "https://chatgpt.com/g/g-p-demo-claude-code/c/abc123"
    captured: dict[str, object] = {"ask_called": False}
    reply = {
        "schema": "promptbranch.ask.reply",
        "schema_version": "1.0",
        "request_id": "wrong-request",
        "correlation_id": "corr-v210",
        "status": "completed",
        "result_type": "release_candidate",
        "summary": "Built candidate.",
        "baseline": {
            "input_artifact": "chatgpt_claudecode_workflow_v0.0.210.zip",
            "input_version": "v0.0.210",
            "output_artifact": "chatgpt_claudecode_workflow_v0.0.211.zip",
            "output_version": "v0.0.211",
            "release_type": "normal",
        },
        "changes": [],
        "artifacts": [],
        "validation": {"claimed": [], "not_claimed": []},
        "next_step": {"operator_action": "none"},
    }
    answer_text = "BEGIN_PROMPTBRANCH_REPLY_JSON\n" + json.dumps(reply) + "\nEND_PROMPTBRANCH_REPLY_JSON\n"

    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

        def ask_result(self, prompt: str, **kwargs):
            captured["ask_called"] = True
            captured["prompt"] = prompt
            return {"answer": "submitted", "conversation_url": conversation_url}

        def get_chat(self, conversation_url: str, **kwargs):
            turns = [
                {"index": 1, "id": "u-old", "role": "user", "text": "previous ask"},
                {"index": 2, "id": "a-old", "role": "assistant", "text": "previous answer"},
            ]
            if captured.get("ask_called"):
                turns.extend([
                    {"index": 3, "id": "u-new", "role": "user", "text": str(captured["prompt"])},
                    {"index": 4, "id": "a-new", "role": "assistant", "text": answer_text},
                ])
            return {
                "ok": True,
                "conversation_url": conversation_url,
                "conversation_id": "abc123",
                "title": "Protocol run",
                "turns": turns,
            }

    store = ConversationStateStore(str(tmp_path))
    store.remember_project(project_url, project_name="Claude Code workflow in ChatGPT")
    store.remember(project_url, conversation_url, project_name="Claude Code workflow in ChatGPT")
    store.remember_artifact(
        project_url=project_url,
        artifact_ref="chatgpt_claudecode_workflow_v0.0.210.zip",
        artifact_version="v0.0.210",
        source_ref="chatgpt_claudecode_workflow_v0.0.210.zip",
        source_version="v0.0.210",
    )
    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(tmp_path),
        "--project-url", project_url,
        "ask", "continue next slice",
        "--protocol", "--target-version", "v0.0.211",
        "--request-id", "req-v210",
        "--correlation-id", "corr-v210",
        "--parse-reply", "--json",
    ])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert payload["action"] == "ask_protocol_run"
    assert payload["status"] == "reply_validation_failed"
    assert payload["reply_validation_ok"] is False
    assert "request_id_mismatch" in payload["reply_validation_errors"]
    assert payload["selected_answer"]["answer_id"] == "a-new"
    assert payload["download_performed"] is False
    assert payload["migration_performed"] is False
    assert payload["adoption_performed"] is False
    assert payload["request_persisted"] is True
    assert Path(payload["protocol_run_record_path"]).is_file()

def test_main_json_ask_emits_full_payload_with_conversation_url(monkeypatch, capsys, tmp_path) -> None:
    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            assert base_url == "http://localhost:8000"
            assert token == "secret"
            assert timeout == 900.0

        def ask_result(self, prompt: str, **kwargs):
            assert prompt == "hello"
            assert kwargs["project_url"] == "https://chatgpt.com/g/demo/project"
            return {"answer": {"status": "ok"}, "conversation_url": "https://chatgpt.com/g/demo/c/123"}

    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    exit_code = main(
        [
            "--service-base-url",
            "http://localhost:8000",
            "--service-token",
            "secret",
            "--profile-dir",
            str(tmp_path),
            "--project-url",
            "https://chatgpt.com/g/demo/project",
            "ask",
            "--json",
            "hello",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    payload = json.loads(captured.out)
    assert payload["answer"] == {"status": "ok"}
    assert payload["conversation_url"] == "https://chatgpt.com/g/demo/c/123"


def test_main_can_create_project_via_service_backend(monkeypatch, capsys) -> None:
    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

        def create_project(self, name: str, **kwargs):
            assert name == "Demo"
            assert kwargs["icon"] == "folder"
            assert kwargs["color"] == "blue"
            assert kwargs["memory_mode"] == "project-only"
            return {"ok": True, "project_url": "https://chatgpt.com/g/new/project"}

    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    exit_code = main(
        [
            "--service-base-url",
            "http://localhost:8000",
            "project-create",
            "Demo",
            "--icon",
            "folder",
            "--color",
            "blue",
            "--memory-mode",
            "project-only",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert json.loads(captured.out)["project_url"] == "https://chatgpt.com/g/new/project"


def test_main_reuses_saved_project_conversation_for_follow_up_service_asks(monkeypatch, capsys, tmp_path) -> None:
    calls: list[str | None] = []
    conversation_url = "https://chatgpt.com/g/demo/c/123"

    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

        def ask_result(self, prompt: str, **kwargs):
            calls.append(kwargs.get("project_url"))
            if prompt == "first":
                return {"answer": "one", "conversation_url": conversation_url}
            return {"answer": "two", "conversation_url": conversation_url}

    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    first_exit_code = main(
        [
            "--service-base-url",
            "http://localhost:8000",
            "--profile-dir",
            str(tmp_path),
            "--project-url",
            "https://chatgpt.com/g/demo/project",
            "ask",
            "first",
        ]
    )
    second_exit_code = main(
        [
            "--service-base-url",
            "http://localhost:8000",
            "--profile-dir",
            str(tmp_path),
            "--project-url",
            "https://chatgpt.com/g/demo/project",
            "ask",
            "second",
        ]
    )

    captured = capsys.readouterr()
    assert first_exit_code == 0
    assert second_exit_code == 0
    assert calls == [
        "https://chatgpt.com/g/demo/project",
        "https://chatgpt.com/g/demo/c/123",
    ]
    assert captured.out.strip().splitlines() == ["one", "two"]


def test_main_can_ask_via_service_backend_from_env(monkeypatch, capsys, tmp_path) -> None:
    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            assert base_url == "http://localhost:8000"
            assert token == "secret"
            assert timeout == 900.0

        def ask_result(self, prompt: str, **kwargs):
            assert prompt == "hello"
            return {"answer": "world", "conversation_url": "https://chatgpt.com/g/demo/c/123"}

    monkeypatch.setenv("CHATGPT_SERVICE_BASE_URL", "http://localhost:8000")
    monkeypatch.setenv("CHATGPT_SERVICE_TOKEN", "secret")
    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    exit_code = main(
        [
            "--profile-dir",
            str(tmp_path),
            "ask",
            "hello",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.out.strip() == "world"


def test_main_can_ask_via_service_backend_from_config(monkeypatch, capsys, tmp_path) -> None:
    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            assert base_url == "http://localhost:8000"
            assert token == "secret"
            assert timeout == 123.0

        def ask_result(self, prompt: str, **kwargs):
            assert prompt == "hello"
            return {"answer": "world", "conversation_url": "https://chatgpt.com/g/demo/c/123"}

    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "service_base_url": "http://localhost:8000",
                "service_token": "secret",
                "service_timeout_seconds": 123,
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.delenv("CHATGPT_SERVICE_BASE_URL", raising=False)
    monkeypatch.delenv("CHATGPT_SERVICE_TOKEN", raising=False)
    monkeypatch.delenv("CHATGPT_SERVICE_TIMEOUT_SECONDS", raising=False)
    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    exit_code = main(
        [
            "--config",
            str(config_path),
            "--profile-dir",
            str(tmp_path),
            "ask",
            "hello",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.out.strip() == "world"


def test_main_can_ask_via_service_backend_from_default_config_path(monkeypatch, capsys, tmp_path) -> None:
    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            assert base_url == "http://localhost:8000"
            assert token == "secret"
            assert timeout == 123.0

        def ask_result(self, prompt: str, **kwargs):
            assert prompt == "hello"
            return {"answer": "world", "conversation_url": "https://chatgpt.com/g/demo/c/123"}

    config_dir = tmp_path / ".config" / "chatgpt-cli"
    config_dir.mkdir(parents=True)
    (config_dir / "config.json").write_text(
        json.dumps(
            {
                "service_base_url": "http://localhost:8000",
                "service_token": "secret",
                "service_timeout_seconds": 123,
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("CHATGPT_CLI_CONFIG", raising=False)
    monkeypatch.delenv("CHATGPT_SERVICE_BASE_URL", raising=False)
    monkeypatch.delenv("CHATGPT_SERVICE_TOKEN", raising=False)
    monkeypatch.delenv("CHATGPT_SERVICE_TIMEOUT_SECONDS", raising=False)
    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    exit_code = main(
        [
            "--profile-dir",
            str(tmp_path / "profile"),
            "ask",
            "hello",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.out.strip() == "world"


def test_main_can_list_projects_via_service_backend(monkeypatch, capsys, tmp_path) -> None:
    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            assert base_url == "http://localhost:8000"

        def list_projects(self, **kwargs):
            assert kwargs["project_url"] == "https://chatgpt.com/g/demo/project"
            return {
                "ok": True,
                "count": 2,
                "projects": [
                    {"name": "Alpha", "url": "https://chatgpt.com/g/demo-alpha/project", "is_current": False},
                    {"name": "Demo", "url": "https://chatgpt.com/g/demo/project", "is_current": True},
                ],
            }

    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    exit_code = main(
        [
            "--service-base-url",
            "http://localhost:8000",
            "--profile-dir",
            str(tmp_path),
            "--project-url",
            "https://chatgpt.com/g/demo/project",
            "project-list",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Alpha	https://chatgpt.com/g/demo-alpha/project" in captured.out
    assert "* Demo	https://chatgpt.com/g/demo/project" in captured.out


def test_main_project_list_json_emits_full_payload(monkeypatch, capsys, tmp_path) -> None:
    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

        def list_projects(self, **kwargs):
            return {
                "ok": True,
                "count": 1,
                "projects": [{"name": "Demo", "url": "https://chatgpt.com/g/demo/project", "is_current": True}],
            }

    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    exit_code = main(
        [
            "--service-base-url",
            "http://localhost:8000",
            "--profile-dir",
            str(tmp_path),
            "project-list",
            "--json",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    payload = json.loads(captured.out)
    assert payload["count"] == 1
    assert payload["projects"][0]["name"] == "Demo"


def test_main_project_list_current_filters_to_current(monkeypatch, capsys, tmp_path) -> None:
    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

        def list_projects(self, **kwargs):
            return {
                "ok": True,
                "count": 2,
                "projects": [
                    {"name": "Alpha", "url": "https://chatgpt.com/g/alpha/project", "is_current": False},
                    {"name": "Demo", "url": "https://chatgpt.com/g/demo/project", "is_current": True},
                ],
            }

    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(tmp_path),
        "project-list", "--current",
    ])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Demo	https://chatgpt.com/g/demo/project" in captured.out
    assert "Alpha	https://chatgpt.com/g/alpha/project" not in captured.out


def test_main_project_list_writes_global_cache(monkeypatch, capsys, tmp_path) -> None:
    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

        def list_projects(self, **kwargs):
            return {
                "ok": True,
                "count": 2,
                "projects": [
                    {"name": "Alpha", "url": "https://chatgpt.com/g/g-p-alpha-alpha/project", "is_current": False},
                    {"name": "Demo", "url": "https://chatgpt.com/g/g-p-demo-demo/project", "is_current": True},
                ],
            }

    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))

    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(tmp_path / "profile-a"),
        "project-list",
    ])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Demo	https://chatgpt.com/g/g-p-demo-demo/project" in captured.out
    cache_path = tmp_path / "xdg" / "promptbranch" / "project-list-cache.json"
    assert cache_path.exists()
    payload = json.loads(cache_path.read_text(encoding="utf-8"))
    assert payload["projects"][0]["name"] == "Demo"
    assert payload["projects"][1]["name"] == "Alpha"


def test_main_use_can_fall_back_to_global_project_cache(monkeypatch, capsys, tmp_path) -> None:
    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

        def list_projects(self, **kwargs):
            return {
                "ok": True,
                "count": 1,
                "projects": [
                    {"name": "Demo", "url": "https://chatgpt.com/g/g-p-demo-demo/project", "is_current": True},
                ],
            }

        def resolve_project(self, name: str, **kwargs):
            return {"ok": False, "error": "not_found", "name": name}

    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))

    profile_a = tmp_path / "profile-a"
    profile_b = tmp_path / "profile-b"

    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(profile_a),
        "project-list",
    ])
    assert exit_code == 0
    capsys.readouterr()

    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(profile_b),
        "use", "Demo",
    ])

    captured = capsys.readouterr()
    assert exit_code == 0
    payload = json.loads(captured.out)
    assert payload["resolved_via"] == "global_cache"
    state_payload = json.loads((profile_b / ".promptbranch_state.json").read_text(encoding="utf-8"))
    assert state_payload["current"]["project_home_url"] == "https://chatgpt.com/g/g-p-demo-demo/project"


def test_main_use_pick_selects_project_and_updates_state(monkeypatch, capsys, tmp_path) -> None:
    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

        def list_projects(self, **kwargs):
            return {
                "ok": True,
                "count": 2,
                "projects": [
                    {"name": "Alpha", "url": "https://chatgpt.com/g/g-p-alpha/project", "is_current": False},
                    {"name": "Demo", "url": "https://chatgpt.com/g/g-p-demo/project", "is_current": True},
                ],
            }

    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)
    monkeypatch.setattr("builtins.input", lambda prompt='': "1")

    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(tmp_path),
        "use", "--pick", "--json",
    ])

    captured = capsys.readouterr()
    assert exit_code == 0
    payload = json.loads(captured.out)
    assert payload["ok"] is True
    assert payload["selected_via"] == "pick"
    assert payload["project_name"] == "Alpha"
    assert payload["project_home_url"] == "https://chatgpt.com/g/g-p-alpha/project"

    state_payload = json.loads((tmp_path / ".promptbranch_state.json").read_text(encoding="utf-8"))
    assert state_payload["current"]["project_home_url"] == "https://chatgpt.com/g/g-p-alpha/project"
    assert state_payload["current"]["project_name"] == "Alpha"


def test_main_use_pick_with_filter_and_single_match_does_not_prompt(monkeypatch, capsys, tmp_path) -> None:
    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

        def list_projects(self, **kwargs):
            return {
                "ok": True,
                "count": 2,
                "projects": [
                    {"name": "Alpha Project", "url": "https://chatgpt.com/g/g-p-alpha/project", "is_current": False},
                    {"name": "Beta Project", "url": "https://chatgpt.com/g/g-p-beta/project", "is_current": False},
                ],
            }

    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    def _unexpected_input(prompt=''):
        raise AssertionError("input() should not be called for a single filtered match")

    monkeypatch.setattr("builtins.input", _unexpected_input)

    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(tmp_path),
        "use", "Alpha", "--pick", "--json",
    ])

    captured = capsys.readouterr()
    assert exit_code == 0
    payload = json.loads(captured.out)
    assert payload["project_name"] == "Alpha Project"


def test_main_use_without_target_or_pick_returns_usage_error(monkeypatch, capsys, tmp_path) -> None:
    exit_code = main(["--profile-dir", str(tmp_path), "use"])
    captured = capsys.readouterr()
    assert exit_code == 2
    assert "target is required unless --pick is used" in captured.err


def test_main_version_subcommand_outputs_release(capsys) -> None:
    exit_code = main(["version"])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.out.strip() == "promptbranch 0.0.269.1"


def test_main_project_source_list_json_emits_source_payload(monkeypatch, capsys, tmp_path) -> None:
    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

        def list_project_sources(self, **kwargs):
            return {
                "ok": True,
                "count": 2,
                "sources": [
                    {"title": "architecture-process_0.1.16.zip", "subtitle": "File", "identity": "architecture-process_0.1.16.zip File"},
                    {"title": "notes.txt", "subtitle": "Document", "identity": "notes.txt Document"},
                ],
            }

    store = ConversationStateStore(str(tmp_path))
    store.remember_project("https://chatgpt.com/g/g-p-demo-project/project", project_name="demo-project")
    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(tmp_path),
        "project-source-list", "--json",
    ])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["count"] == 2
    assert payload["sources"][0]["title"] == "architecture-process_0.1.16.zip"


def test_main_chat_list_json_emits_chat_payload(monkeypatch, capsys, tmp_path) -> None:
    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

        def list_project_chats(self, **kwargs):
            return {
                "ok": True,
                "count": 2,
                "chats": [
                    {"id": "abc", "title": "First chat", "conversation_url": "https://chatgpt.com/g/g-p-demo-project/c/abc"},
                    {"id": "def", "title": "Second chat", "conversation_url": "https://chatgpt.com/g/g-p-demo-project/c/def"},
                ],
            }

    store = ConversationStateStore(str(tmp_path))
    store.remember_project("https://chatgpt.com/g/g-p-demo-project/project", project_name="demo-project")
    store.remember("https://chatgpt.com/g/g-p-demo-project/project", "https://chatgpt.com/g/g-p-demo-project/c/def")
    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(tmp_path),
        "chat-list", "--json",
    ])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["count"] == 2
    assert any(item["is_current"] for item in payload["chats"])


def test_main_chat_use_by_index_updates_state(monkeypatch, capsys, tmp_path) -> None:
    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

        def list_project_chats(self, **kwargs):
            return {
                "ok": True,
                "count": 2,
                "chats": [
                    {"id": "abc", "title": "First chat", "conversation_url": "https://chatgpt.com/g/g-p-demo-project/c/abc"},
                    {"id": "def", "title": "Second chat", "conversation_url": "https://chatgpt.com/g/g-p-demo-project/c/def"},
                ],
            }

    store = ConversationStateStore(str(tmp_path))
    store.remember_project("https://chatgpt.com/g/g-p-demo-project/project", project_name="demo-project")
    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(tmp_path),
        "chat-use", "2", "--json",
    ])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["conversation_id"] == "def"
    assert store.snapshot()["conversation_id"] == "def"

def test_main_chat_use_by_index_prefers_lightweight_task_list(monkeypatch, capsys, tmp_path) -> None:
    calls: list[bool] = []

    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

        def list_project_chats(self, **kwargs):
            calls.append(bool(kwargs.get("include_history_fallback")))
            return {
                "ok": True,
                "count": 4,
                "chats": [
                    {"id": "a", "title": "One", "conversation_url": "https://chatgpt.com/g/g-p-demo-project/c/a"},
                    {"id": "b", "title": "Two", "conversation_url": "https://chatgpt.com/g/g-p-demo-project/c/b"},
                    {"id": "c", "title": "Three", "conversation_url": "https://chatgpt.com/g/g-p-demo-project/c/c"},
                    {"id": "d", "title": "Four", "conversation_url": "https://chatgpt.com/g/g-p-demo-project/c/d"},
                ],
            }

    store = ConversationStateStore(str(tmp_path))
    store.remember_project("https://chatgpt.com/g/g-p-demo-project/project", project_name="demo-project")
    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(tmp_path),
        "chat-use", "4", "--json",
    ])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["conversation_id"] == "d"
    assert calls == [False]


def test_main_chat_leave_clears_only_conversation(monkeypatch, capsys, tmp_path) -> None:
    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

    store = ConversationStateStore(str(tmp_path))
    project_url = "https://chatgpt.com/g/g-p-demo-project/project"
    conversation_url = "https://chatgpt.com/g/g-p-demo-project/c/abc"
    store.remember_project(project_url, project_name="demo-project")
    store.remember(project_url, conversation_url, project_name="demo-project")
    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(tmp_path),
        "chat-leave", "--json",
    ])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["conversation_url"] is None
    snapshot = store.snapshot(project_url)
    assert snapshot["resolved_project_home_url"] == project_url
    assert snapshot["conversation_url"] is None


def test_main_chat_show_json_fetches_selected_chat(monkeypatch, capsys, tmp_path) -> None:
    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

        def get_chat(self, conversation_url: str, **kwargs):
            assert conversation_url == "https://chatgpt.com/g/g-p-demo-project/c/abc"
            return {
                "ok": True,
                "conversation_id": "abc",
                "conversation_url": conversation_url,
                "title": "First chat",
                "turn_count": 1,
                "turns": [{"index": 1, "role": "user", "text": "hello"}],
            }

    store = ConversationStateStore(str(tmp_path))
    project_url = "https://chatgpt.com/g/g-p-demo-project/project"
    conversation_url = "https://chatgpt.com/g/g-p-demo-project/c/abc"
    store.remember_project(project_url, project_name="demo-project")
    store.remember(project_url, conversation_url, project_name="demo-project")
    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(tmp_path),
        "chat-show", "--json",
    ])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["conversation_id"] == "abc"
    assert payload["turns"][0]["text"] == "hello"


def test_test_suite_command_dispatches_to_runner(monkeypatch, capsys) -> None:
    async def fake_run_test_suite_async(**kwargs):
        assert kwargs['keep_project'] is True
        assert kwargs['only'] == ['project_list_debug']
        assert kwargs['profile'] == 'browser'
        return {'ok': True, 'action': 'test_suite'}

    monkeypatch.setattr('promptbranch_cli.run_test_suite_async', fake_run_test_suite_async)

    from promptbranch_cli import main

    rc = main(['test-suite', '--keep-project', '--only', 'project_list_debug'])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload['action'] == 'test_suite'


def test_test_suite_full_profile_dispatches_to_runner(monkeypatch, capsys) -> None:
    async def fake_run_test_suite_async(**kwargs):
        assert kwargs['profile'] == 'full'
        assert kwargs['path'] == '.'
        assert kwargs['package_zip'] == 'release.zip'
        return {'ok': True, 'action': 'test_suite', 'profile': 'full'}

    monkeypatch.setattr('promptbranch_cli.run_test_suite_async', fake_run_test_suite_async)

    from promptbranch_cli import main

    rc = main(['test-suite', '--profile', 'full', '--path', '.', '--package-zip', 'release.zip'])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload['profile'] == 'full'


def test_canonical_test_profile_shortcut_dispatches_to_runner(monkeypatch, capsys) -> None:
    async def fake_run_test_suite_async(**kwargs):
        assert kwargs['profile'] == 'agent'
        assert kwargs['path'] == '.'
        assert kwargs['package_zip'] == 'release.zip'
        return {'ok': True, 'action': 'test_suite', 'profile': 'agent'}

    monkeypatch.setattr('promptbranch_cli.run_test_suite_async', fake_run_test_suite_async)

    from promptbranch_cli import main

    rc = main(['test', 'agent', '--path', '.', '--package-zip', 'release.zip', '--json'])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload['profile'] == 'agent'


def test_src_add_positional_file_delegates_as_file_source(monkeypatch, capsys, tmp_path) -> None:
    calls: dict[str, object] = {}

    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

        def add_project_source(self, **kwargs):
            calls.update(kwargs)
            return {"ok": True, "action": "add"}

    file_path = tmp_path / "my_gitlab_0.0.4.zip"
    file_path.write_bytes(b"zip")
    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    exit_code = main(["--service-base-url", "http://localhost:8000", "src", "add", str(file_path)])

    assert exit_code == 0
    assert calls["source_kind"] == "file"
    assert calls["file_path"] == str(file_path)
    assert calls["display_name"] == "my_gitlab_0.0.4.zip"
    assert calls["overwrite_existing"] is True
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True


def test_main_project_source_add_file_normalizes_name_to_basename(monkeypatch, capsys, tmp_path) -> None:
    calls: dict[str, object] = {}

    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

        def add_project_source(self, **kwargs):
            calls.update(kwargs)
            return {"ok": True, "action": "add"}

    file_path = tmp_path / "candlecast-src-0.19.5.82.2.zip"
    file_path.write_bytes(b"zip")
    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    exit_code = main(
        [
            "--service-base-url",
            "http://localhost:8000",
            "project-source-add",
            "--file",
            str(file_path),
            "--name",
            "/tmp/releases/candlecast-src-0.19.5.82.2.zip",
        ]
    )

    assert exit_code == 0
    assert calls["display_name"] == "candlecast-src-0.19.5.82.2.zip"
    assert calls["overwrite_existing"] is True
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True


def test_phase1_canonical_parser_accepts_ws_task_src_test_and_doctor() -> None:
    parser = make_parser()

    ws_args = parser.parse_args(["ws", "use", "Demo"])
    assert ws_args.command == "ws"
    assert ws_args.ws_command == "use"
    assert ws_args.target == "Demo"

    task_args = parser.parse_args(["task", "show", "2", "--json"])
    assert task_args.command == "task"
    assert task_args.task_command == "show"
    assert task_args.target == "2"
    assert task_args.json is True

    src_args = parser.parse_args(["src", "add", "--file", "demo.zip"])
    assert src_args.command == "src"
    assert src_args.src_command == "add"
    assert src_args.type == "file"
    assert src_args.file == "demo.zip"
    assert src_args.no_overwrite is False

    src_no_overwrite_args = parser.parse_args(["src", "add", "--file", "demo.zip", "--no-overwrite"])
    assert src_no_overwrite_args.no_overwrite is True

    positional_src_args = parser.parse_args(["src", "add", "demo.zip"])
    assert positional_src_args.command == "src"
    assert positional_src_args.src_command == "add"
    assert positional_src_args.type == "file"
    assert positional_src_args.file_path == "demo.zip"
    assert positional_src_args.file is None

    test_args = parser.parse_args(["test", "smoke", "--only", "project_list_debug"])
    assert test_args.command == "test"
    assert test_args.test_command == "smoke"
    assert test_args.only == ["project_list_debug"]

    doctor_args = parser.parse_args(["doctor", "--json"])
    assert doctor_args.command == "doctor"
    assert doctor_args.json is True


def test_phase1_ws_use_delegates_to_existing_use_flow(monkeypatch, capsys, tmp_path) -> None:
    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

        def resolve_project(self, name: str, **kwargs):
            assert name == "my-project"
            return {"ok": True, "project_url": "https://chatgpt.com/g/g-p-demo-my-project/project"}

    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(tmp_path),
        "ws", "use", "my-project", "--json",
    ])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["current_project_home_url"] == "https://chatgpt.com/g/g-p-demo-my-project/project"

    snapshot = ConversationStateStore(str(tmp_path)).snapshot()
    assert snapshot["resolved_project_home_url"] == "https://chatgpt.com/g/g-p-demo-my-project/project"


def test_phase1_task_use_delegates_to_existing_chat_flow(monkeypatch, capsys, tmp_path) -> None:
    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

        def list_project_chats(self, **kwargs):
            return {
                "ok": True,
                "chats": [
                    {"id": "abc", "title": "First", "conversation_url": "https://chatgpt.com/g/g-p-demo-project/c/abc"},
                    {"id": "def", "title": "Second", "conversation_url": "https://chatgpt.com/g/g-p-demo-project/c/def"},
                ],
            }

    project_url = "https://chatgpt.com/g/g-p-demo-project/project"
    store = ConversationStateStore(str(tmp_path))
    store.remember_project(project_url, project_name="demo-project")
    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(tmp_path),
        "task", "use", "2", "--json",
    ])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["conversation_id"] == "def"
    assert store.snapshot(project_url)["conversation_id"] == "def"


def test_phase1_src_list_delegates_to_existing_source_flow(monkeypatch, capsys, tmp_path) -> None:
    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

        def list_project_sources(self, **kwargs):
            return {
                "ok": True,
                "sources": [
                    {"title": "notes.txt", "subtitle": "Document", "identity": "notes.txt Document"},
                ],
            }

    store = ConversationStateStore(str(tmp_path))
    store.remember_project("https://chatgpt.com/g/g-p-demo-project/project", project_name="demo-project")
    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(tmp_path),
        "src", "list", "--json",
    ])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["count"] == 1
    assert payload["sources"][0]["title"] == "notes.txt"


def test_phase1_doctor_reports_state_without_mutating(monkeypatch, capsys, tmp_path) -> None:
    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

    project_url = "https://chatgpt.com/g/g-p-demo-project/project"
    store = ConversationStateStore(str(tmp_path))
    store.remember_project(project_url, project_name="demo-project")
    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(tmp_path),
        "doctor", "--json",
    ])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["action"] == "doctor"
    assert payload["version"] == "0.0.269.1"
    assert payload["checks"]["workspace_selected"] is True


def test_phase2_task_messages_list_groups_flat_transcript(monkeypatch, capsys, tmp_path) -> None:
    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

        def get_chat(self, conversation_url: str, **kwargs):
            assert conversation_url == "https://chatgpt.com/g/g-p-demo-project/c/abc"
            return {
                "ok": True,
                "project_url": "https://chatgpt.com/g/g-p-demo-project/project",
                "conversation_url": conversation_url,
                "conversation_id": "abc",
                "title": "Phase 2 chat",
                "turns": [
                    {"index": 1, "id": "u1", "role": "user", "text": "first question"},
                    {"index": 2, "id": "a1", "role": "assistant", "text": "first answer"},
                    {"index": 3, "id": "u2", "role": "user", "text": "second question"},
                ],
            }

    project_url = "https://chatgpt.com/g/g-p-demo-project/project"
    conversation_url = "https://chatgpt.com/g/g-p-demo-project/c/abc"
    store = ConversationStateStore(str(tmp_path))
    store.remember_project(project_url, project_name="demo-project")
    store.remember(project_url, conversation_url, project_name="demo-project")
    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(tmp_path),
        "task", "messages", "list", "--json",
    ])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["action"] == "task_messages_list"
    assert payload["message_count"] == 2
    assert payload["messages"][0]["text"] == "first question"
    assert payload["messages"][0]["answer_count"] == 1
    assert payload["messages"][0]["answers"][0]["text"] == "first answer"
    assert payload["messages"][1]["answered"] is False


def test_phase2_task_message_show_selects_user_message(monkeypatch, capsys, tmp_path) -> None:
    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

        def get_chat(self, conversation_url: str, **kwargs):
            return {
                "ok": True,
                "conversation_url": conversation_url,
                "conversation_id": "abc",
                "title": "Phase 2 chat",
                "turns": [
                    {"index": 1, "id": "u1", "role": "user", "text": "first question"},
                    {"index": 2, "id": "a1", "role": "assistant", "text": "first answer"},
                    {"index": 3, "id": "u2", "role": "user", "text": "second question"},
                ],
            }

    project_url = "https://chatgpt.com/g/g-p-demo-project/project"
    conversation_url = "https://chatgpt.com/g/g-p-demo-project/c/abc"
    store = ConversationStateStore(str(tmp_path))
    store.remember_project(project_url, project_name="demo-project")
    store.remember(project_url, conversation_url, project_name="demo-project")
    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(tmp_path),
        "task", "message", "show", "2", "--json",
    ])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["action"] == "task_message_show"
    assert payload["message"]["id"] == "u2"
    assert payload["message"]["text"] == "second question"


def test_phase2_task_message_answer_outputs_answers(monkeypatch, capsys, tmp_path) -> None:
    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

        def get_chat(self, conversation_url: str, **kwargs):
            return {
                "ok": True,
                "conversation_url": conversation_url,
                "conversation_id": "abc",
                "title": "Phase 2 chat",
                "turns": [
                    {"index": 1, "id": "u1", "role": "user", "text": "first question"},
                    {"index": 2, "id": "a1", "role": "assistant", "text": "first answer"},
                    {"index": 3, "id": "a2", "role": "assistant", "text": "regenerated answer"},
                ],
            }

    project_url = "https://chatgpt.com/g/g-p-demo-project/project"
    conversation_url = "https://chatgpt.com/g/g-p-demo-project/c/abc"
    store = ConversationStateStore(str(tmp_path))
    store.remember_project(project_url, project_name="demo-project")
    store.remember(project_url, conversation_url, project_name="demo-project")
    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(tmp_path),
        "task", "message", "answer", "u1", "--json",
    ])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["action"] == "task_message_answer"
    assert payload["answer_count"] == 2
    assert [answer["text"] for answer in payload["answers"]] == ["first answer", "regenerated answer"]


def test_phase2_task_messages_list_accepts_raw_mapping_payload(monkeypatch, capsys, tmp_path) -> None:
    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

        def get_chat(self, conversation_url: str, **kwargs):
            return {
                "ok": True,
                "conversation_url": conversation_url,
                "conversation_id": "abc",
                "title": "Raw mapping chat",
                "current_node": "a1",
                "mapping": {
                    "root": {"id": "root", "parent": None, "message": None},
                    "u1": {
                        "parent": "root",
                        "message": {
                            "author": {"role": "user"},
                            "content": {"parts": ["raw question"]},
                        },
                    },
                    "a1": {
                        "parent": "u1",
                        "message": {
                            "author": {"role": "assistant"},
                            "content": {"parts": ["raw answer"]},
                        },
                    },
                },
            }

    project_url = "https://chatgpt.com/g/g-p-demo-project/project"
    conversation_url = "https://chatgpt.com/g/g-p-demo-project/c/abc"
    store = ConversationStateStore(str(tmp_path))
    store.remember_project(project_url, project_name="demo-project")
    store.remember(project_url, conversation_url, project_name="demo-project")
    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(tmp_path),
        "task", "messages", "list", "--json",
    ])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["message_count"] == 1
    assert payload["messages"][0]["text"] == "raw question"
    assert payload["messages"][0]["answers"][0]["text"] == "raw answer"




def test_task_answer_parse_latest_extracts_protocol_artifact_candidate(monkeypatch, capsys, tmp_path) -> None:
    reply = {
        "schema": "promptbranch.ask.reply",
        "schema_version": "1.0",
        "request_id": "req-test",
        "status": "completed",
        "result_type": "release_candidate",
        "summary": "Built candidate.",
        "baseline": {
            "input_artifact": "chatgpt_claudecode_workflow_v0.0.200.zip",
            "input_version": "v0.0.200",
            "output_artifact": "chatgpt_claudecode_workflow_v0.0.205.zip",
            "output_version": "v0.0.205",
            "release_type": "normal",
        },
        "changes": [],
        "artifacts": [
            {
                "kind": "zip",
                "filename": "chatgpt_claudecode_workflow_v0.0.205.zip",
                "version": "v0.0.205",
                "role": "candidate_release",
                "download": {"available": True, "link_text": "chatgpt_claudecode_workflow_v0.0.205.zip", "url": None},
            }
        ],
        "validation": {"claimed": ["focused tests"], "not_claimed": ["full suite"]},
        "next_step": {"operator_action": "download_verify_test_adopt"},
    }
    answer_text = "Intro\nBEGIN_PROMPTBRANCH_REPLY_JSON\n" + json.dumps(reply) + "\nEND_PROMPTBRANCH_REPLY_JSON\nOutro"

    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

        def get_chat(self, conversation_url: str, **kwargs):
            return {
                "ok": True,
                "conversation_url": conversation_url,
                "conversation_id": "abc",
                "title": "Protocol chat",
                "turns": [
                    {"index": 1, "id": "u1", "role": "user", "text": "implement v0.0.205"},
                    {"index": 2, "id": "a1", "role": "assistant", "text": answer_text},
                ],
            }

    project_url = "https://chatgpt.com/g/g-p-demo-project/project"
    conversation_url = "https://chatgpt.com/g/g-p-demo-project/c/abc"
    store = ConversationStateStore(str(tmp_path))
    store.remember_project(project_url, project_name="demo-project")
    store.remember(project_url, conversation_url, project_name="demo-project")
    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(tmp_path),
        "task", "answer", "parse", "--latest", "--json",
    ])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["action"] == "task_answer_parse"
    assert payload["status"] == "valid"
    assert payload["automation_performed"] is False
    assert payload["download_performed"] is False
    assert payload["migration_performed"] is False
    assert payload["adoption_performed"] is False
    assert payload["artifact_candidate_count"] == 1
    assert payload["artifact_candidates"][0]["filename"] == "chatgpt_claudecode_workflow_v0.0.205.zip"


def test_task_answer_parse_latest_fails_closed_without_protocol_block(monkeypatch, capsys, tmp_path) -> None:
    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

        def get_chat(self, conversation_url: str, **kwargs):
            return {
                "ok": True,
                "conversation_url": conversation_url,
                "conversation_id": "abc",
                "title": "Protocol chat",
                "turns": [
                    {"index": 1, "id": "u1", "role": "user", "text": "implement v0.0.205"},
                    {"index": 2, "id": "a1", "role": "assistant", "text": "plain answer without protocol envelope"},
                ],
            }

    project_url = "https://chatgpt.com/g/g-p-demo-project/project"
    conversation_url = "https://chatgpt.com/g/g-p-demo-project/c/abc"
    store = ConversationStateStore(str(tmp_path))
    store.remember_project(project_url, project_name="demo-project")
    store.remember(project_url, conversation_url, project_name="demo-project")
    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(tmp_path),
        "task", "answer", "parse", "--latest", "--json",
    ])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert payload["action"] == "task_answer_parse"
    assert payload["status"] == "reply_schema_missing"
    assert payload["download_performed"] is False
    assert payload["migration_performed"] is False
    assert payload["adoption_performed"] is False



def test_artifact_intake_from_last_answer_selects_expected_candidate(monkeypatch, capsys, tmp_path) -> None:
    reply = {
        "schema": "promptbranch.ask.reply",
        "schema_version": "1.0",
        "request_id": "req-test",
        "status": "completed",
        "result_type": "release_candidate",
        "summary": "Built candidate.",
        "baseline": {
            "input_artifact": "chatgpt_claudecode_workflow_v0.0.201.1.zip",
            "input_version": "v0.0.201.1",
            "output_artifact": "chatgpt_claudecode_workflow_v0.0.205.zip",
            "output_version": "v0.0.205",
            "release_type": "normal",
        },
        "changes": [],
        "artifacts": [
            {
                "kind": "zip",
                "filename": "chatgpt_claudecode_workflow_v0.0.205.zip",
                "version": "v0.0.205",
                "role": "candidate_release",
                "download": {"available": True, "link_text": "chatgpt_claudecode_workflow_v0.0.205.zip", "url": None},
            }
        ],
        "validation": {"claimed": ["focused tests"], "not_claimed": ["full suite"]},
        "next_step": {"operator_action": "download_verify_test_adopt"},
    }
    answer_text = "Intro\nBEGIN_PROMPTBRANCH_REPLY_JSON\n" + json.dumps(reply) + "\nEND_PROMPTBRANCH_REPLY_JSON\nOutro"

    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

        def get_chat(self, conversation_url: str, **kwargs):
            return {
                "ok": True,
                "conversation_url": conversation_url,
                "conversation_id": "abc",
                "title": "Protocol chat",
                "turns": [
                    {"index": 1, "id": "u1", "role": "user", "text": "implement v0.0.205"},
                    {"index": 2, "id": "a1", "role": "assistant", "text": answer_text},
                ],
            }

    project_url = "https://chatgpt.com/g/g-p-demo-project/project"
    conversation_url = "https://chatgpt.com/g/g-p-demo-project/c/abc"
    store = ConversationStateStore(str(tmp_path))
    store.remember_project(project_url, project_name="demo-project")
    store.remember(project_url, conversation_url, project_name="demo-project")
    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(tmp_path),
        "artifact", "intake", "--from-last-answer",
        "--expect-artifact", "chatgpt_claudecode_workflow_v0.0.205.zip",
        "--expect-version", "v0.0.205",
        "--expect-repo", "chatgpt_claudecode_workflow",
        "--json",
    ])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["action"] == "artifact_intake"
    assert payload["status"] == "artifact_candidates_found"
    assert payload["next_action"] == "download_verify"
    assert payload["selected_candidate"]["filename"] == "chatgpt_claudecode_workflow_v0.0.205.zip"
    assert payload["download_performed"] is False
    assert payload["migration_performed"] is False
    assert payload["adoption_performed"] is False




def test_artifact_intake_downloads_selected_candidate_to_inbox_only(monkeypatch, capsys, tmp_path) -> None:
    source_zip = tmp_path / "source.zip"
    source_zip.write_bytes(b"candidate bytes")
    expected_sha = hashlib.sha256(b"candidate bytes").hexdigest()
    reply = {
        "schema": "promptbranch.ask.reply",
        "schema_version": "1.0",
        "request_id": "req-download",
        "correlation_id": "corr-download",
        "status": "completed",
        "result_type": "release_candidate",
        "summary": "Built candidate.",
        "baseline": {
            "input_artifact": "chatgpt_claudecode_workflow_v0.0.205.zip",
            "input_version": "v0.0.205",
            "output_artifact": "chatgpt_claudecode_workflow_v0.0.205.zip",
            "output_version": "v0.0.205",
            "release_type": "normal",
        },
        "changes": [],
        "artifacts": [
            {
                "kind": "zip",
                "filename": "chatgpt_claudecode_workflow_v0.0.205.zip",
                "version": "v0.0.205",
                "role": "candidate_release",
                "download": {"available": True, "link_text": "chatgpt_claudecode_workflow_v0.0.205.zip", "url": source_zip.as_uri()},
            }
        ],
        "validation": {"claimed": ["focused tests"], "not_claimed": ["full suite"]},
        "next_step": {"operator_action": "download_verify_test_adopt"},
    }
    answer_text = "BEGIN_PROMPTBRANCH_REPLY_JSON\n" + json.dumps(reply) + "\nEND_PROMPTBRANCH_REPLY_JSON"

    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

        def get_chat(self, conversation_url: str, **kwargs):
            return {
                "ok": True,
                "conversation_url": conversation_url,
                "conversation_id": "abc",
                "title": "Protocol chat",
                "turns": [
                    {"index": 1, "id": "u1", "role": "user", "text": "implement v0.0.205"},
                    {"index": 2, "id": "a1", "role": "assistant", "text": answer_text},
                ],
            }

    project_url = "https://chatgpt.com/g/g-p-demo-project/project"
    conversation_url = "https://chatgpt.com/g/g-p-demo-project/c/abc"
    store = ConversationStateStore(str(tmp_path))
    store.remember_project(project_url, project_name="demo-project")
    store.remember(project_url, conversation_url, project_name="demo-project")
    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(tmp_path),
        "artifact", "intake", "--from-last-answer",
        "--expect-artifact", "chatgpt_claudecode_workflow_v0.0.205.zip",
        "--expect-version", "v0.0.205",
        "--expect-repo", "chatgpt_claudecode_workflow",
        "--download",
        "--json",
    ])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["action"] == "artifact_intake"
    assert payload["status"] == "downloaded"
    assert payload["download_performed"] is True
    assert payload["verification_performed"] is False
    assert payload["migration_performed"] is False
    assert payload["adoption_performed"] is False
    assert payload["project_source_mutated"] is False
    assert payload["artifact_registry_updated"] is False
    assert payload["state_artifact_updated"] is False
    assert payload["state_source_updated"] is False
    assert payload["download"]["filename"] == "chatgpt_claudecode_workflow_v0.0.205.zip"
    assert payload["download"]["size_bytes"] == len(b"candidate bytes")
    assert payload["download"]["sha256"] == expected_sha
    assert Path(payload["download"]["path"]).is_file()
    assert ".pb_profile" in payload["download"]["path"] or str(tmp_path) in payload["download"]["path"]
    assert payload["intake_record_path"].endswith("intake.json")
    intake_record = json.loads(Path(payload["intake_record_path"]).read_text(encoding="utf-8"))
    assert intake_record["status"] == "downloaded"
    assert intake_record["verification_performed"] is False
    assert intake_record["migration_performed"] is False
    assert intake_record["adoption_performed"] is False




def test_artifact_intake_downloads_and_verifies_candidate_only(monkeypatch, capsys, tmp_path) -> None:
    source_zip = tmp_path / "source-valid.zip"
    artifact_name = "chatgpt_claudecode_workflow_v0.0.205.zip"
    with zipfile.ZipFile(source_zip, "w") as archive:
        archive.writestr("VERSION", "v0.0.205\n")
        archive.writestr("README.md", "# demo\n")

    reply = {
        "schema": "promptbranch.ask.reply",
        "schema_version": "1.0",
        "request_id": "req-download-verify",
        "correlation_id": "corr-download-verify",
        "status": "completed",
        "result_type": "release_candidate",
        "summary": "Built candidate.",
        "baseline": {
            "input_artifact": "chatgpt_claudecode_workflow_v0.0.204.zip",
            "input_version": "v0.0.204",
            "output_artifact": artifact_name,
            "output_version": "v0.0.205",
            "release_type": "normal",
        },
        "changes": [],
        "artifacts": [
            {
                "kind": "zip",
                "filename": artifact_name,
                "version": "v0.0.205",
                "role": "candidate_release",
                "download": {"available": True, "link_text": artifact_name, "url": source_zip.as_uri()},
            }
        ],
        "validation": {"claimed": ["focused tests"], "not_claimed": ["full suite"]},
        "next_step": {"operator_action": "download_verify"},
    }
    answer_text = "BEGIN_PROMPTBRANCH_REPLY_JSON\n" + json.dumps(reply) + "\nEND_PROMPTBRANCH_REPLY_JSON"

    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

        def get_chat(self, conversation_url: str, **kwargs):
            return {
                "ok": True,
                "conversation_url": conversation_url,
                "conversation_id": "abc",
                "title": "Protocol chat",
                "turns": [
                    {"index": 1, "id": "u1", "role": "user", "text": "implement v0.0.205"},
                    {"index": 2, "id": "a1", "role": "assistant", "text": answer_text},
                ],
            }

    project_url = "https://chatgpt.com/g/g-p-demo-project/project"
    conversation_url = "https://chatgpt.com/g/g-p-demo-project/c/abc"
    store = ConversationStateStore(str(tmp_path))
    store.remember_project(project_url, project_name="demo-project")
    store.remember(project_url, conversation_url, project_name="demo-project")
    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(tmp_path),
        "artifact", "intake", "--from-last-answer",
        "--expect-artifact", artifact_name,
        "--expect-version", "v0.0.205",
        "--expect-repo", "chatgpt_claudecode_workflow",
        "--download",
        "--verify",
        "--json",
    ])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["action"] == "artifact_intake"
    assert payload["status"] == "download_verified"
    assert payload["intake_stage"] == "downloaded_verified"
    assert payload["download_performed"] is True
    assert payload["verification_performed"] is True
    assert payload["migration_performed"] is False
    assert payload["adoption_performed"] is False
    assert payload["project_source_mutated"] is False
    assert payload["artifact_registry_updated"] is False
    assert payload["state_artifact_updated"] is False
    assert payload["state_source_updated"] is False
    assert Path(payload["download"]["path"]).is_file()
    assert payload["verification"]["ok"] is True
    assert payload["zip_version"] == "v0.0.205"
    intake_record = json.loads(Path(payload["intake_record_path"]).read_text(encoding="utf-8"))
    assert intake_record["status"] == "download_verified"
    assert intake_record["accepted"] is False
    assert intake_record["migration_performed"] is False
    assert intake_record["adoption_performed"] is False


def test_artifact_intake_downloads_verifies_and_migrates_candidate_without_adoption(monkeypatch, capsys, tmp_path) -> None:
    source_zip = tmp_path / "source-valid-migrate.zip"
    artifact_name = "chatgpt_claudecode_workflow_v0.0.206.zip"
    with zipfile.ZipFile(source_zip, "w") as archive:
        archive.writestr("VERSION", "v0.0.206\n")
        archive.writestr("README.md", "# demo\n")
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    reply = {
        "schema": "promptbranch.ask.reply",
        "schema_version": "1.0",
        "request_id": "req-download-verify-migrate",
        "correlation_id": "corr-download-verify-migrate",
        "status": "completed",
        "result_type": "release_candidate",
        "summary": "Built candidate.",
        "baseline": {
            "input_artifact": "chatgpt_claudecode_workflow_v0.0.205.zip",
            "input_version": "v0.0.205",
            "output_artifact": artifact_name,
            "output_version": "v0.0.206",
            "release_type": "normal",
        },
        "changes": [],
        "artifacts": [
            {
                "kind": "zip",
                "filename": artifact_name,
                "version": "v0.0.206",
                "role": "candidate_release",
                "download": {"available": True, "link_text": artifact_name, "url": source_zip.as_uri()},
            }
        ],
        "validation": {"claimed": ["focused tests"], "not_claimed": ["full suite"]},
        "next_step": {"operator_action": "download_verify_migrate"},
    }
    answer_text = "BEGIN_PROMPTBRANCH_REPLY_JSON\n" + json.dumps(reply) + "\nEND_PROMPTBRANCH_REPLY_JSON"

    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

        def get_chat(self, conversation_url: str, **kwargs):
            return {
                "ok": True,
                "conversation_url": conversation_url,
                "conversation_id": "abc",
                "title": "Protocol chat",
                "turns": [
                    {"index": 1, "id": "u1", "role": "user", "text": "implement v0.0.206"},
                    {"index": 2, "id": "a1", "role": "assistant", "text": answer_text},
                ],
            }

    project_url = "https://chatgpt.com/g/g-p-demo-project/project"
    conversation_url = "https://chatgpt.com/g/g-p-demo-project/c/abc"
    store = ConversationStateStore(str(tmp_path))
    store.remember_project(project_url, project_name="demo-project")
    store.remember(project_url, conversation_url, project_name="demo-project")
    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(tmp_path),
        "artifact", "intake", "--from-last-answer",
        "--expect-artifact", artifact_name,
        "--expect-version", "v0.0.206",
        "--expect-repo", "chatgpt_claudecode_workflow",
        "--download",
        "--verify",
        "--migrate",
        "--repo-path", str(repo_root),
        "--json",
    ])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["status"] == "migrated_candidate"
    assert payload["download_performed"] is True
    assert payload["verification_performed"] is True
    assert "v0.0.225" not in payload["operator_instruction"]
    assert payload["migration_performed"] is True
    assert payload["adoption_performed"] is False
    assert payload["artifact_registry_updated"] is False
    assert payload["state_artifact_updated"] is False
    assert payload["state_source_updated"] is False
    assert (repo_root / artifact_name).is_file()


def test_artifact_intake_verifies_existing_inbox_candidate_without_download(monkeypatch, capsys, tmp_path) -> None:
    artifact_name = "chatgpt_claudecode_workflow_v0.0.205.zip"
    inbox_dir = tmp_path / "artifact_inbox" / "abc" / "a1" / "req-verify"
    inbox_dir.mkdir(parents=True)
    artifact_path = inbox_dir / artifact_name
    with zipfile.ZipFile(artifact_path, "w") as archive:
        archive.writestr("VERSION", "v0.0.205\n")
        archive.writestr("README.md", "# demo\n")

    reply = {
        "schema": "promptbranch.ask.reply",
        "schema_version": "1.0",
        "request_id": "req-verify",
        "correlation_id": "corr-verify",
        "status": "completed",
        "result_type": "release_candidate",
        "summary": "Built candidate.",
        "baseline": {
            "input_artifact": "chatgpt_claudecode_workflow_v0.0.205.zip",
            "input_version": "v0.0.205",
            "output_artifact": artifact_name,
            "output_version": "v0.0.205",
            "release_type": "normal",
        },
        "changes": [],
        "artifacts": [
            {
                "kind": "zip",
                "filename": artifact_name,
                "version": "v0.0.205",
                "role": "candidate_release",
                "download": {"available": True, "link_text": artifact_name, "url": None},
            }
        ],
        "validation": {"claimed": ["focused tests"], "not_claimed": ["full suite"]},
        "next_step": {"operator_action": "download_verify_test_adopt"},
    }
    answer_text = "BEGIN_PROMPTBRANCH_REPLY_JSON\n" + json.dumps(reply) + "\nEND_PROMPTBRANCH_REPLY_JSON"

    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

        def get_chat(self, conversation_url: str, **kwargs):
            return {
                "ok": True,
                "conversation_url": conversation_url,
                "conversation_id": "abc",
                "title": "Protocol chat",
                "turns": [
                    {"index": 1, "id": "u1", "role": "user", "text": "implement v0.0.205"},
                    {"index": 2, "id": "a1", "role": "assistant", "text": answer_text},
                ],
            }

    project_url = "https://chatgpt.com/g/g-p-demo-project/project"
    conversation_url = "https://chatgpt.com/g/g-p-demo-project/c/abc"
    store = ConversationStateStore(str(tmp_path))
    store.remember_project(project_url, project_name="demo-project")
    store.remember(project_url, conversation_url, project_name="demo-project")
    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(tmp_path),
        "artifact", "intake", "--from-last-answer",
        "--expect-artifact", artifact_name,
        "--expect-version", "v0.0.205",
        "--expect-repo", "chatgpt_claudecode_workflow",
        "--verify",
        "--json",
    ])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["action"] == "artifact_intake"
    assert payload["status"] == "verified_candidate"
    assert payload["verification_performed"] is True
    assert payload["download_performed"] is False
    assert payload["migration_performed"] is False
    assert payload["adoption_performed"] is False
    assert payload["verification"]["ok"] is True
    assert payload["zip_version"] == "v0.0.205"
    assert payload["filename_version"] == "v0.0.205"
    intake_record = json.loads(Path(payload["intake_record_path"]).read_text(encoding="utf-8"))
    assert intake_record["status"] == "verified_candidate"
    assert intake_record["verification_performed"] is True
    assert intake_record["migration_performed"] is False
    assert intake_record["adoption_performed"] is False



def test_artifact_intake_migrates_verified_candidate_to_repo_root_only(monkeypatch, capsys, tmp_path) -> None:
    artifact_name = "chatgpt_claudecode_workflow_v0.0.205.zip"
    inbox_dir = tmp_path / "artifact_inbox" / "abc" / "a1" / "req-migrate"
    inbox_dir.mkdir(parents=True)
    artifact_path = inbox_dir / artifact_name
    with zipfile.ZipFile(artifact_path, "w") as archive:
        archive.writestr("VERSION", "v0.0.205\n")
        archive.writestr("README.md", "# demo\n")
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    reply = {
        "schema": "promptbranch.ask.reply",
        "schema_version": "1.0",
        "request_id": "req-migrate",
        "correlation_id": "corr-migrate",
        "status": "completed",
        "result_type": "release_candidate",
        "summary": "Built candidate.",
        "baseline": {
            "input_artifact": "chatgpt_claudecode_workflow_v0.0.205.zip",
            "input_version": "v0.0.205",
            "output_artifact": artifact_name,
            "output_version": "v0.0.205",
            "release_type": "normal",
        },
        "changes": [],
        "artifacts": [
            {
                "kind": "zip",
                "filename": artifact_name,
                "version": "v0.0.205",
                "role": "candidate_release",
                "download": {"available": True, "link_text": artifact_name, "url": None},
            }
        ],
        "validation": {"claimed": ["focused tests"], "not_claimed": ["full suite"]},
        "next_step": {"operator_action": "download_verify_test_adopt"},
    }
    answer_text = "BEGIN_PROMPTBRANCH_REPLY_JSON\n" + json.dumps(reply) + "\nEND_PROMPTBRANCH_REPLY_JSON"

    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

        def get_chat(self, conversation_url: str, **kwargs):
            return {
                "ok": True,
                "conversation_url": conversation_url,
                "conversation_id": "abc",
                "title": "Protocol chat",
                "turns": [
                    {"index": 1, "id": "u1", "role": "user", "text": "implement v0.0.205"},
                    {"index": 2, "id": "a1", "role": "assistant", "text": answer_text},
                ],
            }

    project_url = "https://chatgpt.com/g/g-p-demo-project/project"
    conversation_url = "https://chatgpt.com/g/g-p-demo-project/c/abc"
    store = ConversationStateStore(str(tmp_path))
    store.remember_project(project_url, project_name="demo-project")
    store.remember(project_url, conversation_url, project_name="demo-project")
    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(tmp_path),
        "artifact", "intake", "--from-last-answer",
        "--expect-artifact", artifact_name,
        "--expect-version", "v0.0.205",
        "--expect-repo", "chatgpt_claudecode_workflow",
        "--verify",
        "--migrate",
        "--repo-path", str(repo_root),
        "--json",
    ])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["action"] == "artifact_intake"
    assert payload["status"] == "migrated_candidate"
    assert payload["verification_performed"] is True
    assert payload["migration_performed"] is True
    assert payload["adoption_performed"] is False
    assert payload["project_source_mutated"] is False
    assert payload["artifact_registry_updated"] is False
    assert payload["candidate_registry_updated"] is True
    assert payload["state_artifact_updated"] is False
    assert payload["state_source_updated"] is False
    target = repo_root / artifact_name
    assert target.is_file()
    assert payload["migration"]["target_path"] == str(target.resolve())
    assert payload["migration"]["copy_performed"] is True
    candidate_registry = json.loads((tmp_path / "artifact_candidates.json").read_text(encoding="utf-8"))
    assert candidate_registry["candidates"][0]["status"] == "candidate_release"
    assert candidate_registry["candidates"][0]["accepted"] is False
    intake_record = json.loads(Path(payload["intake_record_path"]).read_text(encoding="utf-8"))
    assert intake_record["status"] == "migrated_candidate"
    assert intake_record["migration_performed"] is True
    assert intake_record["adoption_performed"] is False

def test_artifact_intake_migrate_requires_verified_candidate(monkeypatch, capsys, tmp_path) -> None:
    artifact_name = "chatgpt_claudecode_workflow_v0.0.205.zip"
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    reply = {
        "schema": "promptbranch.ask.reply",
        "schema_version": "1.0",
        "request_id": "req-not-verified",
        "status": "completed",
        "result_type": "release_candidate",
        "summary": "Built candidate.",
        "baseline": {"input_artifact": "chatgpt_claudecode_workflow_v0.0.205.zip", "input_version": "v0.0.205", "output_artifact": artifact_name, "output_version": "v0.0.205", "release_type": "normal"},
        "changes": [],
        "artifacts": [{"kind": "zip", "filename": artifact_name, "version": "v0.0.205", "role": "candidate_release", "download": {"available": True, "link_text": artifact_name, "url": None}}],
        "validation": {"claimed": [], "not_claimed": ["full suite"]},
        "next_step": {"operator_action": "download_verify_test_adopt"},
    }
    answer_text = "BEGIN_PROMPTBRANCH_REPLY_JSON\n" + json.dumps(reply) + "\nEND_PROMPTBRANCH_REPLY_JSON"

    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

        def get_chat(self, conversation_url: str, **kwargs):
            return {"ok": True, "conversation_url": conversation_url, "conversation_id": "abc", "title": "Protocol chat", "turns": [{"index": 1, "id": "u1", "role": "user", "text": "implement"}, {"index": 2, "id": "a1", "role": "assistant", "text": answer_text}]}

    project_url = "https://chatgpt.com/g/g-p-demo-project/project"
    conversation_url = "https://chatgpt.com/g/g-p-demo-project/c/abc"
    store = ConversationStateStore(str(tmp_path))
    store.remember_project(project_url, project_name="demo-project")
    store.remember(project_url, conversation_url, project_name="demo-project")
    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(tmp_path),
        "artifact", "intake", "--from-last-answer",
        "--expect-artifact", artifact_name,
        "--expect-version", "v0.0.205",
        "--expect-repo", "chatgpt_claudecode_workflow",
        "--migrate",
        "--repo-path", str(repo_root),
        "--json",
    ])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert payload["status"] == "candidate_not_verified"
    assert payload["migration_performed"] is False
    assert payload["adoption_performed"] is False
    assert not (repo_root / artifact_name).exists()


def test_artifact_intake_verify_rejects_version_mismatch_without_migration(monkeypatch, capsys, tmp_path) -> None:
    artifact_name = "chatgpt_claudecode_workflow_v0.0.205.zip"
    inbox_dir = tmp_path / "artifact_inbox" / "abc" / "a1" / "req-mismatch"
    inbox_dir.mkdir(parents=True)
    artifact_path = inbox_dir / artifact_name
    with zipfile.ZipFile(artifact_path, "w") as archive:
        archive.writestr("VERSION", "v0.0.203.1\n")
        archive.writestr("README.md", "# demo\n")

    reply = {
        "schema": "promptbranch.ask.reply",
        "schema_version": "1.0",
        "request_id": "req-mismatch",
        "status": "completed",
        "result_type": "release_candidate",
        "summary": "Built candidate.",
        "baseline": {"input_artifact": "old.zip", "input_version": "v0.0.203.1", "output_artifact": artifact_name, "output_version": "v0.0.205"},
        "changes": [],
        "artifacts": [{"kind": "zip", "filename": artifact_name, "version": "v0.0.205", "role": "candidate_release", "download": {"available": True, "link_text": artifact_name, "url": None}}],
        "validation": {"claimed": [], "not_claimed": []},
        "next_step": {"operator_action": "download_verify_test_adopt"},
    }
    answer_text = "BEGIN_PROMPTBRANCH_REPLY_JSON\n" + json.dumps(reply) + "\nEND_PROMPTBRANCH_REPLY_JSON"

    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

        def get_chat(self, conversation_url: str, **kwargs):
            return {
                "ok": True,
                "conversation_url": conversation_url,
                "conversation_id": "abc",
                "title": "Protocol chat",
                "turns": [
                    {"index": 1, "id": "u1", "role": "user", "text": "implement"},
                    {"index": 2, "id": "a1", "role": "assistant", "text": answer_text},
                ],
            }

    project_url = "https://chatgpt.com/g/g-p-demo-project/project"
    conversation_url = "https://chatgpt.com/g/g-p-demo-project/c/abc"
    store = ConversationStateStore(str(tmp_path))
    store.remember_project(project_url, project_name="demo-project")
    store.remember(project_url, conversation_url, project_name="demo-project")
    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(tmp_path),
        "artifact", "intake", "--from-last-answer",
        "--expect-artifact", artifact_name,
        "--expect-version", "v0.0.205",
        "--expect-repo", "chatgpt_claudecode_workflow",
        "--verify",
        "--json",
    ])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert payload["action"] == "artifact_intake"
    assert payload["status"] == "artifact_version_mismatch"
    assert payload["verification_performed"] is True
    assert payload["migration_performed"] is False
    assert payload["adoption_performed"] is False
    assert "artifact_version_mismatch" in payload["verification_errors"]


def test_artifact_intake_download_requires_candidate_url(monkeypatch, capsys, tmp_path) -> None:
    reply = {
        "schema": "promptbranch.ask.reply",
        "schema_version": "1.0",
        "request_id": "req-missing-url",
        "status": "completed",
        "result_type": "release_candidate",
        "summary": "Built candidate.",
        "baseline": {"input_artifact": "old.zip", "input_version": "v0.0.205", "output_artifact": "repo_v0.0.205.zip", "output_version": "v0.0.205"},
        "changes": [],
        "artifacts": [{"kind": "zip", "filename": "repo_v0.0.205.zip", "version": "v0.0.205", "role": "candidate_release", "download": {"available": True, "link_text": "repo_v0.0.205.zip", "url": None}}],
        "validation": {"claimed": [], "not_claimed": []},
        "next_step": {"operator_action": "download_verify_test_adopt"},
    }
    answer_text = "BEGIN_PROMPTBRANCH_REPLY_JSON\n" + json.dumps(reply) + "\nEND_PROMPTBRANCH_REPLY_JSON"

    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

        def get_chat(self, conversation_url: str, **kwargs):
            return {
                "ok": True,
                "conversation_url": conversation_url,
                "conversation_id": "abc",
                "title": "Protocol chat",
                "turns": [
                    {"index": 1, "id": "u1", "role": "user", "text": "implement"},
                    {"index": 2, "id": "a1", "role": "assistant", "text": answer_text},
                ],
            }

    project_url = "https://chatgpt.com/g/g-p-demo-project/project"
    conversation_url = "https://chatgpt.com/g/g-p-demo-project/c/abc"
    store = ConversationStateStore(str(tmp_path))
    store.remember_project(project_url, project_name="demo-project")
    store.remember(project_url, conversation_url, project_name="demo-project")
    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(tmp_path),
        "artifact", "intake", "--from-last-answer", "--download", "--json",
    ])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert payload["action"] == "artifact_intake"
    assert payload["status"] == "artifact_download_url_missing"
    assert payload["download_performed"] is False
    assert payload["migration_performed"] is False
    assert payload["adoption_performed"] is False


def test_artifact_intake_rejects_wrong_expected_version(monkeypatch, capsys, tmp_path) -> None:
    reply = {
        "schema": "promptbranch.ask.reply",
        "schema_version": "1.0",
        "request_id": "req-test",
        "status": "completed",
        "result_type": "release_candidate",
        "summary": "Built candidate.",
        "baseline": {"input_artifact": "old.zip", "input_version": "v0.0.201.1", "output_artifact": "repo_v0.0.205.zip", "output_version": "v0.0.205"},
        "changes": [],
        "artifacts": [{"kind": "zip", "filename": "repo_v0.0.205.zip", "version": "v0.0.205", "role": "candidate_release", "download": {"available": True}}],
        "validation": {"claimed": [], "not_claimed": []},
        "next_step": {"operator_action": "download_verify_test_adopt"},
    }
    answer_text = "BEGIN_PROMPTBRANCH_REPLY_JSON\n" + json.dumps(reply) + "\nEND_PROMPTBRANCH_REPLY_JSON"

    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

        def get_chat(self, conversation_url: str, **kwargs):
            return {
                "ok": True,
                "conversation_url": conversation_url,
                "conversation_id": "abc",
                "title": "Protocol chat",
                "turns": [
                    {"index": 1, "id": "u1", "role": "user", "text": "implement"},
                    {"index": 2, "id": "a1", "role": "assistant", "text": answer_text},
                ],
            }

    project_url = "https://chatgpt.com/g/g-p-demo-project/project"
    conversation_url = "https://chatgpt.com/g/g-p-demo-project/c/abc"
    store = ConversationStateStore(str(tmp_path))
    store.remember_project(project_url, project_name="demo-project")
    store.remember(project_url, conversation_url, project_name="demo-project")
    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(tmp_path),
        "artifact", "intake", "--from-last-answer", "--expect-version", "v0.0.210", "--json",
    ])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert payload["action"] == "artifact_intake"
    assert payload["status"] == "artifact_wrong_version"
    assert payload["artifact_candidates"][0]["status"] == "artifact_wrong_version"
    assert payload["download_performed"] is False




def test_artifact_intake_dry_run_reads_latest_validated_protocol_run_without_backend(monkeypatch, capsys, tmp_path) -> None:
    reply = {
        "schema": "promptbranch.ask.reply",
        "schema_version": "1.0",
        "request_id": "req-no-artifact",
        "correlation_id": "req-no-artifact",
        "status": "no_artifact",
        "result_type": "no_change",
        "summary": "No artifact.",
        "baseline": {
            "input_artifact": "chatgpt_claudecode_workflow_v0.0.221.zip",
            "input_version": "v0.0.221",
            "source_ref": "chatgpt_claudecode_workflow_v0.0.221.zip",
            "source_version": "v0.0.221",
            "registry_current": "chatgpt_claudecode_workflow_v0.0.221.zip",
            "registry_current_version": "v0.0.221",
            "output_artifact": None,
            "output_version": "v0.0.222",
            "target_version": "v0.0.222",
            "release_type": "normal",
        },
        "changes": [],
        "artifacts": [],
        "validation": {"claimed": ["no artifact"], "not_claimed": ["test execution"]},
        "next_step": {"operator_action": "none"},
    }
    run = {
        "ok": True,
        "status": "reply_validated",
        "reply_validation_ok": True,
        "request_id": "req-no-artifact",
        "correlation_id": "req-no-artifact",
        "reply": reply,
        "artifact_candidate_count": 0,
        "request": {
            "workspace": {"project_home_url": "https://chatgpt.com/g/g-p-demo/project"},
            "task": {"conversation_url": "https://chatgpt.com/g/g-p-demo/c/abc", "conversation_id": "abc"},
            "artifact": {
                "repo": "chatgpt_claudecode_workflow",
                "current_baseline": "chatgpt_claudecode_workflow_v0.0.221.zip",
                "current_version": "v0.0.221",
                "source_ref": "chatgpt_claudecode_workflow_v0.0.221.zip",
                "source_version": "v0.0.221",
                "target_version": "v0.0.222",
                "release_type": "normal",
            },
        },
    }
    records = tmp_path / "ask_protocol_runs"
    records.mkdir()
    (records / "req-no-artifact.json").write_text(json.dumps(run), encoding="utf-8")

    class FailingServiceClient:
        def __init__(self, *args, **kwargs):
            pass
        def get_chat(self, *args, **kwargs):
            raise AssertionError("artifact intake dry-run should use protocol records, not live chat")

    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FailingServiceClient)
    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(tmp_path),
        "artifact", "intake", "--from-last-answer", "--dry-run", "--json",
    ])
    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["status"] == "no_artifact"
    assert payload["source"] == "last_validated_protocol_reply"
    assert payload["artifact_candidate_count"] == 0
    assert payload["candidates"] == []
    assert payload["next_action"] == "none"
    assert payload["download_performed"] is False
    assert payload["migration_performed"] is False
    assert payload["adoption_performed"] is False





def test_artifact_intake_accepts_recovered_protocol_run_after_service_timeout(monkeypatch, capsys, tmp_path) -> None:
    reply = {
        "schema": "promptbranch.ask.reply",
        "schema_version": "1.0",
        "request_id": "req-recovered-timeout",
        "correlation_id": "req-recovered-timeout",
        "status": "no_artifact",
        "result_type": "no_change",
        "summary": "Protocol smoke recovered after service read timeout.",
        "baseline": {
            "input_artifact": "chatgpt_claudecode_workflow_v0.0.247.zip",
            "input_version": "v0.0.247",
            "output_artifact": None,
            "output_version": "v0.0.247",
            "release_type": "normal",
        },
        "changes": [],
        "artifacts": [],
        "validation": {"claimed": ["protocol smoke"], "not_claimed": ["artifact creation"]},
        "next_step": {"operator_action": "none"},
    }
    run = {
        "ok": True,
        "status": "recovered_after_service_timeout",
        "reply_validation_ok": True,
        "reply_validation_errors": [],
        "request_id": "req-recovered-timeout",
        "correlation_id": "req-recovered-timeout",
        "reply": reply,
        "artifact_candidate_count": 0,
        "request": {
            "workspace": {"project_home_url": "https://chatgpt.com/g/g-p-demo/project"},
            "task": {"conversation_url": "https://chatgpt.com/g/g-p-demo/c/abc", "conversation_id": "abc"},
            "artifact": {
                "repo": "chatgpt_claudecode_workflow",
                "current_baseline": "chatgpt_claudecode_workflow_v0.0.247.zip",
                "current_version": "v0.0.247",
                "source_ref": "chatgpt_claudecode_workflow_v0.0.247.zip",
                "source_version": "v0.0.247",
                "target_version": "v0.0.247",
                "release_type": "normal",
            },
        },
        "service_timeout_recovery": {"attempted": True, "source": "task_transcript_reparse"},
    }
    records = tmp_path / "ask_protocol_runs"
    records.mkdir()
    (records / "req-recovered-timeout.json").write_text(json.dumps(run), encoding="utf-8")

    class FailingServiceClient:
        def __init__(self, *args, **kwargs):
            pass

    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FailingServiceClient)
    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(tmp_path),
        "artifact", "intake", "--from-last-answer", "--dry-run", "--json",
    ])
    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["ok"] is True
    assert payload["status"] == "no_artifact"
    assert payload["source"] == "last_validated_protocol_reply"
    assert payload["protocol_run_status"] == "recovered_after_service_timeout"
    assert payload["artifact_candidate_count"] == 0


def test_artifact_intake_no_artifact_no_change_allows_missing_source_baseline(monkeypatch, capsys, tmp_path) -> None:
    reply = {
        "schema": "promptbranch.ask.reply",
        "schema_version": "1.0",
        "request_id": "req-no-artifact-missing-source",
        "correlation_id": "req-no-artifact-missing-source",
        "status": "no_artifact",
        "result_type": "no_change",
        "summary": "Protocol smoke only; no artifact.",
        "baseline": {
            "input_artifact": "chatgpt_claudecode_workflow_v0.0.247.zip",
            "input_version": "v0.0.247",
            "output_artifact": None,
            "output_version": "v0.0.247",
            "release_type": "normal",
        },
        "changes": [],
        "artifacts": [],
        "validation": {"claimed": ["protocol smoke"], "not_claimed": ["artifact creation"]},
        "next_step": {"operator_action": "none"},
    }
    run = {
        "ok": True,
        "status": "reply_validated",
        "reply_validation_ok": True,
        "request_id": "req-no-artifact-missing-source",
        "correlation_id": "req-no-artifact-missing-source",
        "reply": reply,
        "artifact_candidate_count": 0,
        "request": {
            "workspace": {"project_home_url": "https://chatgpt.com/g/g-p-demo/project"},
            "task": {"conversation_url": "https://chatgpt.com/g/g-p-demo/c/abc", "conversation_id": "abc"},
            "artifact": {
                "repo": "chatgpt_claudecode_workflow",
                "current_baseline": "chatgpt_claudecode_workflow_v0.0.247.zip",
                "current_version": "v0.0.247",
                "source_ref": "chatgpt_claudecode_workflow_v0.0.247.zip",
                "source_version": "v0.0.247",
                "target_version": "v0.0.247",
                "release_type": "normal",
            },
        },
    }
    records = tmp_path / "ask_protocol_runs"
    records.mkdir()
    (records / "req-no-artifact-missing-source.json").write_text(json.dumps(run), encoding="utf-8")

    class FailingServiceClient:
        def __init__(self, *args, **kwargs):
            pass

    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FailingServiceClient)
    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(tmp_path),
        "artifact", "intake", "--from-last-protocol-run", "--dry-run", "--json",
    ])
    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["ok"] is True
    assert payload["status"] == "no_artifact"
    assert payload["reply_parse_status"] in {"valid", "no_artifact"}
    assert payload["artifact_candidate_count"] == 0
    assert payload["download_performed"] is False
    assert "baseline_source_ref_mismatch" not in payload.get("validation_errors", [])
    assert "baseline_source_version_mismatch" not in payload.get("validation_errors", [])


def test_artifact_intake_protocol_run_rejects_baseline_mismatch(monkeypatch, capsys, tmp_path) -> None:
    reply = {
        "schema": "promptbranch.ask.reply",
        "schema_version": "1.0",
        "request_id": "req-bad-baseline",
        "correlation_id": "req-bad-baseline",
        "status": "completed",
        "result_type": "release_candidate",
        "summary": "Built candidate.",
        "baseline": {
            "input_artifact": "chatgpt_claudecode_workflow_v0.0.220.zip",
            "input_version": "v0.0.220",
            "output_artifact": "chatgpt_claudecode_workflow_v0.0.222.zip",
            "output_version": "v0.0.222",
            "release_type": "normal",
        },
        "changes": [],
        "artifacts": [{"kind": "zip", "filename": "chatgpt_claudecode_workflow_v0.0.222.zip", "version": "v0.0.222", "role": "candidate_release", "download": {"available": True}}],
        "validation": {"claimed": [], "not_claimed": []},
        "next_step": {"operator_action": "download_verify"},
    }
    run = {
        "ok": True,
        "status": "reply_validated",
        "reply_validation_ok": True,
        "request_id": "req-bad-baseline",
        "correlation_id": "req-bad-baseline",
        "reply": reply,
        "request": {
            "workspace": {"project_home_url": "https://chatgpt.com/g/g-p-demo/project"},
            "task": {"conversation_url": "https://chatgpt.com/g/g-p-demo/c/abc", "conversation_id": "abc"},
            "artifact": {
                "repo": "chatgpt_claudecode_workflow",
                "current_baseline": "chatgpt_claudecode_workflow_v0.0.221.zip",
                "current_version": "v0.0.221",
                "target_version": "v0.0.222",
                "release_type": "normal",
            },
        },
    }
    records = tmp_path / "ask_protocol_runs"
    records.mkdir()
    (records / "req-bad-baseline.json").write_text(json.dumps(run), encoding="utf-8")

    class FailingServiceClient:
        def __init__(self, *args, **kwargs):
            pass

    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FailingServiceClient)
    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(tmp_path),
        "artifact", "intake", "--from-last-protocol-run", "--dry-run", "--json",
    ])
    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert payload["status"] == "baseline_mismatch"
    assert "baseline_artifact_mismatch" in payload["validation_errors"]
    assert payload["download_performed"] is False
    assert payload["migration_performed"] is False
    assert payload["adoption_performed"] is False

def test_artifact_intake_protocol_run_downloads_verifies_and_migrates_without_live_chat(monkeypatch, capsys, tmp_path) -> None:
    source_zip = tmp_path / "source-protocol.zip"
    artifact_name = "chatgpt_claudecode_workflow_v0.0.225.zip"
    with zipfile.ZipFile(source_zip, "w") as archive:
        archive.writestr("VERSION", "v0.0.225\n")
        archive.writestr("README.md", "# demo\n")
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    reply = {
        "schema": "promptbranch.ask.reply",
        "schema_version": "1.0",
        "request_id": "req-protocol-migrate",
        "correlation_id": "req-protocol-migrate",
        "status": "completed",
        "result_type": "release_candidate",
        "summary": "Built candidate.",
        "baseline": {
            "input_artifact": "chatgpt_claudecode_workflow_v0.0.223.zip",
            "input_version": "v0.0.223",
            "source_ref": "chatgpt_claudecode_workflow_v0.0.223.zip",
            "source_version": "v0.0.223",
            "registry_current": "chatgpt_claudecode_workflow_v0.0.223.zip",
            "registry_current_version": "v0.0.223",
            "output_artifact": artifact_name,
            "output_version": "v0.0.225",
            "target_version": "v0.0.225",
            "release_type": "normal",
        },
        "changes": [],
        "artifacts": [
            {
                "kind": "zip",
                "filename": artifact_name,
                "version": "v0.0.225",
                "role": "candidate_release",
                "download": {"available": True, "link_text": artifact_name, "url": source_zip.as_uri()},
            }
        ],
        "validation": {"claimed": ["focused tests"], "not_claimed": ["full suite"]},
        "next_step": {"operator_action": "download_verify_migrate"},
    }
    run = {
        "ok": True,
        "status": "reply_validated",
        "reply_validation_ok": True,
        "request_id": "req-protocol-migrate",
        "correlation_id": "req-protocol-migrate",
        "reply": reply,
        "artifact_candidate_count": 1,
        "conversation_id": "abc",
        "conversation_url": "https://chatgpt.com/g/g-p-demo/c/abc",
        "message": {"id": "u1", "index": 1, "role": "user"},
        "answer": {"id": "a1", "index": 2, "role": "assistant"},
        "answer_text_length": 1234,
        "request": {
            "workspace": {"project_home_url": "https://chatgpt.com/g/g-p-demo/project"},
            "task": {"conversation_url": "https://chatgpt.com/g/g-p-demo/c/abc", "conversation_id": "abc"},
            "artifact": {
                "repo": "chatgpt_claudecode_workflow",
                "current_baseline": "chatgpt_claudecode_workflow_v0.0.223.zip",
                "current_version": "v0.0.223",
                "source_ref": "chatgpt_claudecode_workflow_v0.0.223.zip",
                "source_version": "v0.0.223",
                "registry_current": "chatgpt_claudecode_workflow_v0.0.223.zip",
                "registry_current_version": "v0.0.223",
                "target_version": "v0.0.225",
                "release_type": "normal",
            },
        },
    }
    records = tmp_path / "ask_protocol_runs"
    records.mkdir()
    (records / "req-protocol-migrate.json").write_text(json.dumps(run), encoding="utf-8")

    class FailingServiceClient:
        def __init__(self, *args, **kwargs):
            pass

        def get_chat(self, *args, **kwargs):
            raise AssertionError("protocol-run intake must not fetch live chat")

    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FailingServiceClient)
    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(tmp_path),
        "artifact", "intake", "--from-last-protocol-run",
        "--download",
        "--verify",
        "--migrate",
        "--repo-path", str(repo_root),
        "--json",
    ])
    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["source"] == "last_validated_protocol_reply"
    assert payload["status"] == "migrated_candidate"
    assert payload["download_performed"] is True
    assert payload["verification_performed"] is True
    assert payload["migration_performed"] is True
    assert payload["adoption_performed"] is False
    assert payload["project_source_mutated"] is False
    assert payload["artifact_registry_updated"] is False
    assert payload["state_artifact_updated"] is False
    assert payload["state_source_updated"] is False
    assert (repo_root / artifact_name).is_file()



def test_artifact_intake_sandbox_download_fails_with_explicit_handoff(monkeypatch, capsys, tmp_path) -> None:
    artifact_name = "chatgpt_claudecode_workflow_v0.0.260.zip"
    reply = {
        "schema": "promptbranch.ask.reply",
        "schema_version": "1.0",
        "request_id": "req-sandbox-candidate",
        "correlation_id": "req-sandbox-candidate",
        "status": "completed",
        "result_type": "release_candidate",
        "summary": "Built candidate.",
        "baseline": {
            "input_artifact": "chatgpt_claudecode_workflow_v0.0.257.zip",
            "input_version": "v0.0.257",
            "source_ref": "chatgpt_claudecode_workflow_v0.0.257.zip",
            "source_version": "v0.0.257",
            "registry_current": "chatgpt_claudecode_workflow_v0.0.257.zip",
            "registry_current_version": "v0.0.257",
            "output_artifact": artifact_name,
            "output_version": "v0.0.260",
            "target_version": "v0.0.260",
            "release_type": "normal",
        },
        "changes": [],
        "artifacts": [
            {
                "kind": "zip",
                "filename": artifact_name,
                "version": "v0.0.260",
                "role": "candidate_release",
                "download": {"available": True, "link_text": artifact_name, "url": f"sandbox:/mnt/data/{artifact_name}"},
            }
        ],
        "validation": {"claimed": ["focused tests"], "not_claimed": ["full suite"]},
        "next_step": {"operator_action": "download_verify_migrate"},
    }
    run = {
        "ok": True,
        "status": "reply_validated",
        "reply_validation_ok": True,
        "request_id": "req-sandbox-candidate",
        "correlation_id": "req-sandbox-candidate",
        "reply": reply,
        "artifact_candidate_count": 1,
        "conversation_id": "abc",
        "conversation_url": "https://chatgpt.com/g/g-p-demo/c/abc",
        "answer": {"id": "a1", "index": 2, "role": "assistant"},
        "request": {
            "workspace": {"project_home_url": "https://chatgpt.com/g/g-p-demo/project"},
            "task": {"conversation_url": "https://chatgpt.com/g/g-p-demo/c/abc", "conversation_id": "abc"},
            "artifact": {
                "repo": "chatgpt_claudecode_workflow",
                "current_baseline": "chatgpt_claudecode_workflow_v0.0.257.zip",
                "current_version": "v0.0.257",
                "source_ref": "chatgpt_claudecode_workflow_v0.0.257.zip",
                "source_version": "v0.0.257",
                "registry_current": "chatgpt_claudecode_workflow_v0.0.257.zip",
                "registry_current_version": "v0.0.257",
                "target_version": "v0.0.260",
                "release_type": "normal",
            },
        },
    }
    records = tmp_path / "ask_protocol_runs"
    records.mkdir()
    (records / "req-sandbox-candidate.json").write_text(json.dumps(run), encoding="utf-8")

    class FailingServiceClient:
        def __init__(self, *args, **kwargs):
            pass

        def get_chat(self, *args, **kwargs):
            raise AssertionError("protocol-run intake must not fetch live chat")

    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FailingServiceClient)
    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(tmp_path),
        "artifact", "intake", "--from-last-protocol-run",
        "--download",
        "--json",
    ])
    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert payload["status"] == "artifact_download_url_unsupported"
    assert payload["download_url_scheme"] == "sandbox"
    assert payload["requires_browser_context"] is True
    assert payload["download_transport"]["direct_download_supported"] is False
    assert payload["download_transport"]["manual_import_supported"] is True
    assert payload["manual_import_supported"] is True
    assert "--local-file" in payload["manual_import_command"]
    assert artifact_name in payload["manual_import_command"]
    assert payload["download_performed"] is False
    assert payload["manual_import_performed"] is False
    assert payload["migration_performed"] is False
    assert payload["adoption_performed"] is False


def test_artifact_intake_manual_import_verifies_and_migrates_sandbox_candidate(monkeypatch, capsys, tmp_path) -> None:
    artifact_name = "chatgpt_claudecode_workflow_v0.0.260.zip"
    local_zip = tmp_path / "browser-downloaded.zip"
    with zipfile.ZipFile(local_zip, "w") as archive:
        archive.writestr("VERSION", "v0.0.260\n")
        archive.writestr("README.md", "# demo\n")
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    reply = {
        "schema": "promptbranch.ask.reply",
        "schema_version": "1.0",
        "request_id": "req-sandbox-manual-import",
        "correlation_id": "req-sandbox-manual-import",
        "status": "completed",
        "result_type": "release_candidate",
        "summary": "Built candidate.",
        "baseline": {
            "input_artifact": "chatgpt_claudecode_workflow_v0.0.257.zip",
            "input_version": "v0.0.257",
            "source_ref": "chatgpt_claudecode_workflow_v0.0.257.zip",
            "source_version": "v0.0.257",
            "registry_current": "chatgpt_claudecode_workflow_v0.0.257.zip",
            "registry_current_version": "v0.0.257",
            "output_artifact": artifact_name,
            "output_version": "v0.0.260",
            "target_version": "v0.0.260",
            "release_type": "normal",
        },
        "changes": [],
        "artifacts": [
            {
                "kind": "zip",
                "filename": artifact_name,
                "version": "v0.0.260",
                "role": "candidate_release",
                "download": {"available": True, "link_text": artifact_name, "url": f"sandbox:/mnt/data/{artifact_name}"},
            }
        ],
        "validation": {"claimed": ["focused tests"], "not_claimed": ["full suite"]},
        "next_step": {"operator_action": "download_verify_migrate"},
    }
    run = {
        "ok": True,
        "status": "reply_validated",
        "reply_validation_ok": True,
        "request_id": "req-sandbox-manual-import",
        "correlation_id": "req-sandbox-manual-import",
        "reply": reply,
        "artifact_candidate_count": 1,
        "conversation_id": "abc",
        "conversation_url": "https://chatgpt.com/g/g-p-demo/c/abc",
        "answer": {"id": "a1", "index": 2, "role": "assistant"},
        "request": {
            "workspace": {"project_home_url": "https://chatgpt.com/g/g-p-demo/project"},
            "task": {"conversation_url": "https://chatgpt.com/g/g-p-demo/c/abc", "conversation_id": "abc"},
            "artifact": {
                "repo": "chatgpt_claudecode_workflow",
                "current_baseline": "chatgpt_claudecode_workflow_v0.0.257.zip",
                "current_version": "v0.0.257",
                "source_ref": "chatgpt_claudecode_workflow_v0.0.257.zip",
                "source_version": "v0.0.257",
                "registry_current": "chatgpt_claudecode_workflow_v0.0.257.zip",
                "registry_current_version": "v0.0.257",
                "target_version": "v0.0.260",
                "release_type": "normal",
            },
        },
    }
    records = tmp_path / "ask_protocol_runs"
    records.mkdir()
    (records / "req-sandbox-manual-import.json").write_text(json.dumps(run), encoding="utf-8")

    class FailingServiceClient:
        def __init__(self, *args, **kwargs):
            pass

        def get_chat(self, *args, **kwargs):
            raise AssertionError("protocol-run intake must not fetch live chat")

    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FailingServiceClient)
    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(tmp_path),
        "artifact", "intake", "--from-last-protocol-run",
        "--local-file", str(local_zip),
        "--verify",
        "--migrate",
        "--repo-path", str(repo_root),
        "--json",
    ])
    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["status"] == "migrated_candidate"
    assert payload["manual_import_performed"] is True
    assert payload["download_performed"] is False
    assert payload["verification_performed"] is True
    assert payload["migration_performed"] is True
    assert payload["adoption_performed"] is False
    assert payload["download_transport"]["mode"] == "manual_import"
    assert payload["manual_import_filename_matches_candidate"] is False
    assert Path(payload["download"]["path"]).is_file()
    assert (repo_root / artifact_name).is_file()


def test_phase2_task_message_answer_accepts_latest_alias(monkeypatch, capsys, tmp_path) -> None:
    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

        def get_chat(self, conversation_url: str, **kwargs):
            return {
                "ok": True,
                "conversation_url": conversation_url,
                "conversation_id": "abc",
                "title": "Phase 2 chat",
                "turns": [
                    {"index": 1, "id": "u1", "role": "user", "text": "first question"},
                    {"index": 2, "id": "a1", "role": "assistant", "text": "first answer"},
                    {"index": 3, "id": "u2", "role": "user", "text": "second question"},
                    {"index": 4, "id": "a2", "role": "assistant", "text": "second answer"},
                ],
            }

    project_url = "https://chatgpt.com/g/g-p-demo-project/project"
    conversation_url = "https://chatgpt.com/g/g-p-demo-project/c/abc"
    store = ConversationStateStore(str(tmp_path))
    store.remember_project(project_url, project_name="demo-project")
    store.remember(project_url, conversation_url, project_name="demo-project")
    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(tmp_path),
        "task", "message", "answer", "latest", "--json",
    ])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["message"]["id"] == "u2"
    assert payload["answers"][0]["text"] == "second answer"


def test_chat_list_payload_includes_current_task_from_state_when_backend_empty() -> None:
    chats, payload = _chat_list_payload(
        {"ok": True, "count": 0, "chats": []},
        current_conversation_url="https://chatgpt.com/g/g-p-demo/c/chat-current-1",
    )

    assert payload["count"] == 1
    assert chats[0]["id"] == "chat-current-1"
    assert chats[0]["is_current"] is True
    assert chats[0]["source"] == "current_state"


def test_phase3_parser_accepts_src_sync_and_artifact_commands() -> None:
    parser = make_parser()

    sync_args = parser.parse_args(["src", "sync", ".", "--no-upload", "--dry-run", "--json"])
    assert sync_args.command == "src"
    assert sync_args.src_command == "sync"
    assert sync_args.path == "."
    assert sync_args.no_upload is True
    assert sync_args.dry_run is True

    upload_args = parser.parse_args(["src", "sync", ".", "--upload", "--confirm-upload", "--json"])
    assert upload_args.upload is True
    assert upload_args.confirm_upload is True

    plan_args = parser.parse_args(["src", "sync", ".", "--plan", "--json"])
    assert plan_args.dry_run is True

    current_args = parser.parse_args(["artifact", "current", "--json"])
    assert current_args.command == "artifact"
    assert current_args.artifact_command == "current"

    adopt_args = parser.parse_args(["artifact", "adopt", "chatgpt_claudecode_workflow_v1.2.3.zip", "--from-project-source", "--json"])
    assert adopt_args.command == "artifact"
    assert adopt_args.artifact_command == "adopt"
    assert adopt_args.artifact == "chatgpt_claudecode_workflow_v1.2.3.zip"
    assert adopt_args.from_project_source is True

    release_args = parser.parse_args(["artifact", "release", ".", "--filename", "demo.zip", "--json"])
    assert release_args.command == "artifact"
    assert release_args.artifact_command == "release"
    assert release_args.filename == "demo.zip"

    verify_args = parser.parse_args(["artifact", "verify", "demo.zip", "--json"])
    assert verify_args.command == "artifact"
    assert verify_args.artifact_command == "verify"
    assert verify_args.path == "demo.zip"




class _FakeArtifactAdoptBackend:
    def __init__(self, profile: Path, project_url: str, sources: list[dict[str, object]]) -> None:
        self.store = ConversationStateStore(profile)
        self.project_url = project_url
        self.sources = sources
        self.list_calls = 0
        self.store.remember_project(project_url, project_name="Demo")

    def state_snapshot(self) -> dict[str, object]:
        return self.store.snapshot(self.project_url)

    async def list_project_sources(self, *, keep_open: bool = False) -> dict[str, object]:
        self.list_calls += 1
        return {"ok": True, "status": "verified", "sources": self.sources}


def _write_test_release_zip(path: Path, version: str) -> None:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("VERSION", version + "\n")
        archive.writestr("README.md", "demo\n")


def test_artifact_adopt_existing_project_source_updates_registry_and_state(capsys, tmp_path) -> None:
    filename = "chatgpt_claudecode_workflow_v1.2.3.zip"
    zip_path = tmp_path / filename
    _write_test_release_zip(zip_path, "v1.2.3")
    profile = tmp_path / "profile"
    project_url = "https://chatgpt.com/g/g-p-demo/project"
    backend = _FakeArtifactAdoptBackend(profile, project_url, [{"title": filename, "id": "src_1"}])
    args = argparse.Namespace(
        artifact=filename,
        from_project_source=True,
        local_path=str(zip_path),
        keep_open=False,
        json=True,
        profile_dir=str(profile),
    )

    exit_code = asyncio.run(cmd_artifact_adopt(backend, args))
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["ok"] is True
    assert payload["status"] == "adopted"
    assert payload["source_verified"] is True
    assert payload["project_source_mutated"] is False
    assert payload["artifact_registry_updated"] is True
    assert payload["state_artifact_updated"] is True
    assert payload["state_source_updated"] is True
    assert payload["artifact_ref"] == filename
    assert payload["artifact_version"] == "v1.2.3"
    assert payload["source_ref"] == filename
    assert payload["source_version"] == "v1.2.3"
    assert payload["checks"]["registry_current_matches_artifact"] is True
    assert payload["after_snapshot"]["state"]["artifact_ref"] == filename
    registry_payload = json.loads((profile / "promptbranch_artifacts.json").read_text(encoding="utf-8"))
    assert registry_payload["artifacts"][0]["filename"] == filename


def test_artifact_adopt_requires_exactly_one_project_source(capsys, tmp_path) -> None:
    filename = "chatgpt_claudecode_workflow_v1.2.3.zip"
    zip_path = tmp_path / filename
    _write_test_release_zip(zip_path, "v1.2.3")
    profile = tmp_path / "profile"
    backend = _FakeArtifactAdoptBackend(profile, "https://chatgpt.com/g/g-p-demo/project", [])
    args = argparse.Namespace(
        artifact=filename,
        from_project_source=True,
        local_path=str(zip_path),
        keep_open=False,
        json=True,
        profile_dir=str(profile),
    )

    exit_code = asyncio.run(cmd_artifact_adopt(backend, args))
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert payload["ok"] is False
    assert payload["status"] == "project_source_match_count_invalid"
    assert payload["artifact_registry_updated"] if "artifact_registry_updated" in payload else True
    assert not (profile / "promptbranch_artifacts.json").exists()


def test_artifact_adopt_rejects_zip_version_mismatch(capsys, tmp_path) -> None:
    filename = "chatgpt_claudecode_workflow_v1.2.3.zip"
    zip_path = tmp_path / filename
    _write_test_release_zip(zip_path, "v1.2.4")
    profile = tmp_path / "profile"
    backend = _FakeArtifactAdoptBackend(profile, "https://chatgpt.com/g/g-p-demo/project", [{"title": filename}])
    args = argparse.Namespace(
        artifact=filename,
        from_project_source=True,
        local_path=str(zip_path),
        keep_open=False,
        json=True,
        profile_dir=str(profile),
    )

    exit_code = asyncio.run(cmd_artifact_adopt(backend, args))
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert payload["ok"] is False
    assert payload["status"] == "version_mismatch"
    assert payload["zip_version"] == "v1.2.4"
    assert not (profile / "promptbranch_artifacts.json").exists()



def _write_candidate_registry(profile: Path, *, filename: str, zip_path: Path, version: str, tested: bool = False) -> dict[str, object]:
    digest = hashlib.sha256(zip_path.read_bytes()).hexdigest()
    candidate = {
        "schema": "promptbranch.artifact.candidate",
        "schema_version": "1.0",
        "kind": "candidate_release",
        "status": "candidate_release",
        "accepted": False,
        "verified": True,
        "filename": filename,
        "version": version,
        "path": str(zip_path),
        "sha256": digest,
        "size_bytes": zip_path.stat().st_size,
        "source_inbox_path": str(profile / "artifact_inbox" / "abc" / "a1" / "req" / filename),
        "reply_request_id": "req",
        "conversation_id": "abc",
        "answer_id": "a1",
        "migration_performed": True,
        "adoption_performed": False,
    }
    profile.mkdir(parents=True, exist_ok=True)
    if tested:
        record_dir = profile / "artifact_candidate_tests" / version
        record_dir.mkdir(parents=True, exist_ok=True)
        record_path = record_dir / "candidate_test.fixture.json"
        record = {
            "schema": "promptbranch.artifact.candidate_test",
            "schema_version": "1.0",
            "candidate": candidate,
            "result": {
                "ok": True,
                "status": "candidate_test_passed",
                "returncode": 0,
                "adoption_performed": False,
            },
            "adoption_performed": False,
            "project_source_mutated": False,
            "artifact_registry_updated": False,
            "state_artifact_updated": False,
            "state_source_updated": False,
        }
        record_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
        candidate["latest_test"] = {
            "ok": True,
            "status": "candidate_test_passed",
            "record_path": str(record_path),
            "tested_at": "2026-05-17T00:00:00Z",
            "adoption_performed": False,
        }
        candidate["tested"] = True
        candidate["test_status"] = "candidate_test_passed"
    (profile / "artifact_candidates.json").write_text(json.dumps({"schema_version": 1, "candidates": [candidate]}, indent=2) + "\n", encoding="utf-8")
    return candidate


def test_artifact_candidate_test_preflight_requires_no_adoption(capsys, tmp_path) -> None:
    filename = "chatgpt_claudecode_workflow_v0.0.225.zip"
    repo = tmp_path / "repo"
    repo.mkdir()
    zip_path = repo / filename
    _write_test_release_zip(zip_path, "v0.0.225")
    script = repo / "chatgpt_claudecode_workflow_release_control.sh"
    script.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    script.chmod(0o755)
    profile = tmp_path / "profile"
    _write_candidate_registry(profile, filename=filename, zip_path=zip_path, version="v0.0.225")
    backend = _FakeArtifactAdoptBackend(profile, "https://chatgpt.com/g/g-p-demo/project", [])
    args = argparse.Namespace(
        artifact=filename,
        version=None,
        repo_path=str(repo),
        preflight_only=True,
        test_timeout=3600.0,
        release_log_keep=12,
        skip_docker_logs=True,
        prune_release_logs=True,
        json=True,
        profile_dir=str(profile),
    )

    exit_code = asyncio.run(cmd_artifact_candidate_test(backend, args))
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["ok"] is True
    assert payload["status"] == "candidate_test_preflight_verified"
    assert payload["verification_performed"] is True
    assert payload["project_source_mutated"] is False
    assert payload["adoption_performed"] is False
    assert payload["artifact_registry_updated"] is False
    assert payload["state_artifact_updated"] is False
    assert payload["state_source_updated"] is False
    assert not (profile / "promptbranch_artifacts.json").exists()
    assert not (profile / "artifact_candidate_tests").exists()


def test_artifact_candidate_test_runs_release_control_tests_only_and_records_result(monkeypatch, capsys, tmp_path) -> None:
    filename = "chatgpt_claudecode_workflow_v0.0.225.zip"
    repo = tmp_path / "repo"
    repo.mkdir()
    zip_path = repo / filename
    _write_test_release_zip(zip_path, "v0.0.225")
    script = repo / "chatgpt_claudecode_workflow_release_control.sh"
    script.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    script.chmod(0o755)
    profile = tmp_path / "profile"
    _write_candidate_registry(profile, filename=filename, zip_path=zip_path, version="v0.0.225")
    backend = _FakeArtifactAdoptBackend(profile, "https://chatgpt.com/g/g-p-demo/project", [])

    def fake_run(command, cwd, stdout, stderr, text, timeout, check):
        assert command[:4] == [str(script), "--version", "v0.0.225", "--tests-only"]
        assert "--adopt-if-green" not in command
        import subprocess

        return subprocess.CompletedProcess(command, 0, "tests passed\n", "")

    monkeypatch.setattr("promptbranch_cli.subprocess.run", fake_run)
    args = argparse.Namespace(
        artifact=None,
        version="v0.0.225",
        repo_path=str(repo),
        preflight_only=False,
        test_timeout=3600.0,
        release_log_keep=12,
        skip_docker_logs=True,
        prune_release_logs=True,
        json=True,
        profile_dir=str(profile),
    )

    exit_code = asyncio.run(cmd_artifact_candidate_test(backend, args))
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["ok"] is True
    assert payload["status"] == "candidate_test_passed"
    assert payload["candidate_test_status"] == "candidate_test_passed"
    assert payload["candidate_test"]["ok"] is True
    assert payload["candidate_registry_updated"] is True
    assert payload["artifact_registry_updated"] is False
    assert payload["state_artifact_updated"] is False
    assert payload["state_source_updated"] is False
    assert payload["project_source_mutated"] is False
    assert payload["adoption_performed"] is False
    assert not (profile / "promptbranch_artifacts.json").exists()
    record_path = Path(payload["candidate_test_record_path"])
    assert record_path.is_file()
    record = json.loads(record_path.read_text(encoding="utf-8"))
    assert record["result"]["status"] == "candidate_test_passed"
    assert record["adoption_performed"] is False
    registry = json.loads((profile / "artifact_candidates.json").read_text(encoding="utf-8"))
    assert registry["candidates"][0]["latest_test"]["status"] == "candidate_test_passed"
    assert registry["candidates"][0]["accepted"] is False


def test_artifact_candidate_test_rejects_accepted_candidate(capsys, tmp_path) -> None:
    filename = "chatgpt_claudecode_workflow_v0.0.225.zip"
    repo = tmp_path / "repo"
    repo.mkdir()
    zip_path = repo / filename
    _write_test_release_zip(zip_path, "v0.0.225")
    script = repo / "chatgpt_claudecode_workflow_release_control.sh"
    script.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    script.chmod(0o755)
    profile = tmp_path / "profile"
    _write_candidate_registry(profile, filename=filename, zip_path=zip_path, version="v0.0.225")
    registry = json.loads((profile / "artifact_candidates.json").read_text(encoding="utf-8"))
    registry["candidates"][0]["accepted"] = True
    registry["candidates"][0]["status"] = "accepted_candidate"
    (profile / "artifact_candidates.json").write_text(json.dumps(registry), encoding="utf-8")
    backend = _FakeArtifactAdoptBackend(profile, "https://chatgpt.com/g/g-p-demo/project", [])
    args = argparse.Namespace(
        artifact=filename,
        version=None,
        repo_path=str(repo),
        preflight_only=False,
        test_timeout=3600.0,
        release_log_keep=12,
        skip_docker_logs=True,
        prune_release_logs=True,
        json=True,
        profile_dir=str(profile),
    )

    exit_code = asyncio.run(cmd_artifact_candidate_test(backend, args))
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert payload["status"] == "candidate_not_release"
    assert payload["adoption_performed"] is False
    assert not (profile / "promptbranch_artifacts.json").exists()



def test_artifact_candidate_status_reports_ready_candidate_without_mutation(capsys, tmp_path) -> None:
    filename = "chatgpt_claudecode_workflow_v0.0.230.zip"
    repo = tmp_path / "repo"
    repo.mkdir()
    zip_path = repo / filename
    _write_test_release_zip(zip_path, "v0.0.230")
    profile = tmp_path / "profile"
    _write_candidate_registry(profile, filename=filename, zip_path=zip_path, version="v0.0.230", tested=True)
    backend = _FakeArtifactAdoptBackend(profile, "https://chatgpt.com/g/g-p-demo/project", [])
    args = argparse.Namespace(
        artifact=None,
        version="v0.0.230",
        repo_path=str(repo),
        json=True,
        profile_dir=str(profile),
    )

    exit_code = asyncio.run(cmd_artifact_candidate_status(backend, args))
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["ok"] is True
    assert payload["action"] == "artifact_candidate_status"
    assert payload["status"] == "candidate_ready_for_acceptance"
    assert payload["read_only"] is True
    assert payload["mutating_actions_executed"] is False
    assert payload["download_performed"] is False
    assert payload["candidate_test_performed"] is False
    assert payload["adoption_performed"] is False
    assert payload["artifact_registry_updated"] is False
    assert payload["state_artifact_updated"] is False
    assert payload["state_source_updated"] is False
    assert payload["project_source_mutated"] is False
    assert payload["lifecycle"]["candidate_verified"] is True
    assert payload["lifecycle"]["candidate_migrated"] is True
    assert payload["lifecycle"]["candidate_test_passed"] is True
    assert payload["lifecycle"]["adoption_eligible"] is True
    assert payload["recommended_next_command"]["kind"] == "accept_candidate"
    assert "accept-candidate --version v0.0.230 --adopt-if-green" in payload["recommended_next_command"]["command"]
    assert not (profile / "promptbranch_artifacts.json").exists()


def test_artifact_candidate_status_reports_missing_candidate_without_error(capsys, tmp_path) -> None:
    profile = tmp_path / "profile"
    repo = tmp_path / "repo"
    repo.mkdir()
    backend = _FakeArtifactAdoptBackend(profile, "https://chatgpt.com/g/g-p-demo/project", [])
    args = argparse.Namespace(
        artifact=None,
        version=None,
        repo_path=str(repo),
        json=True,
        profile_dir=str(profile),
    )

    exit_code = asyncio.run(cmd_artifact_candidate_status(backend, args))
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["ok"] is True
    assert payload["status"] == "candidate_not_found"
    assert payload["candidate"] is None
    assert payload["lifecycle"]["candidate_selected"] is False
    assert payload["recommended_next_command"]["kind"] == "intake_candidate"
    assert payload["adoption_performed"] is False
    assert payload["project_source_mutated"] is False
    assert not (profile / "promptbranch_artifacts.json").exists()


def test_artifact_candidate_status_all_reports_inventory_without_mutation(capsys, tmp_path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    profile = tmp_path / "profile"

    ready_filename = "chatgpt_claudecode_workflow_v0.0.230.zip"
    ready_zip = repo / ready_filename
    _write_test_release_zip(ready_zip, "v0.0.230")
    ready_candidate = _write_candidate_registry(profile, filename=ready_filename, zip_path=ready_zip, version="v0.0.230", tested=True)

    pending_filename = "chatgpt_claudecode_workflow_v0.0.230.zip"
    pending_zip = repo / pending_filename
    _write_test_release_zip(pending_zip, "v0.0.230")
    pending_candidate = {
        **ready_candidate,
        "filename": pending_filename,
        "version": "v0.0.230",
        "path": str(pending_zip),
        "sha256": hashlib.sha256(pending_zip.read_bytes()).hexdigest(),
        "tested": False,
        "test_status": None,
    }
    pending_candidate.pop("latest_test", None)
    (profile / "artifact_candidates.json").write_text(
        json.dumps({"schema_version": 1, "candidates": [ready_candidate, pending_candidate]}, indent=2) + "\n",
        encoding="utf-8",
    )

    backend = _FakeArtifactAdoptBackend(profile, "https://chatgpt.com/g/g-p-demo/project", [])
    args = argparse.Namespace(
        artifact=None,
        version=None,
        all=True,
        repo_path=str(repo),
        json=True,
        profile_dir=str(profile),
    )

    exit_code = asyncio.run(cmd_artifact_candidate_status(backend, args))
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["ok"] is True
    assert payload["status"] == "candidate_inventory_has_adoption_ready"
    assert payload["candidate_count"] == 2
    assert len(payload["candidates"]) == 2
    assert payload["lifecycle_counts"]["adoption_eligible"] == 1
    assert payload["lifecycle_counts"]["tested"] == 1
    assert payload["status_counts"]["candidate_ready_for_acceptance"] == 1
    assert payload["status_counts"]["candidate_verified_pending_test"] == 1
    assert payload["recommended_next_command"]["kind"] == "accept_candidate"
    assert "accept-candidate --version v0.0.230 --adopt-if-green" in payload["recommended_next_command"]["command"]
    assert payload["read_only"] is True
    assert payload["mutating_actions_executed"] is False
    assert payload["download_performed"] is False
    assert payload["candidate_test_performed"] is False
    assert payload["adoption_performed"] is False
    assert payload["artifact_registry_updated"] is False
    assert payload["state_artifact_updated"] is False
    assert payload["state_source_updated"] is False
    assert payload["project_source_mutated"] is False
    assert not (profile / "promptbranch_artifacts.json").exists()


def test_artifact_candidate_status_all_reports_empty_inventory(capsys, tmp_path) -> None:
    profile = tmp_path / "profile"
    repo = tmp_path / "repo"
    repo.mkdir()
    backend = _FakeArtifactAdoptBackend(profile, "https://chatgpt.com/g/g-p-demo/project", [])
    args = argparse.Namespace(
        artifact=None,
        version=None,
        all=True,
        repo_path=str(repo),
        json=True,
        profile_dir=str(profile),
    )

    exit_code = asyncio.run(cmd_artifact_candidate_status(backend, args))
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["ok"] is True
    assert payload["status"] == "candidate_registry_empty"
    assert payload["candidate_count"] == 0
    assert payload["candidates"] == []
    assert payload["recommended_next_command"]["kind"] == "intake_candidate"
    assert payload["adoption_performed"] is False
    assert payload["project_source_mutated"] is False




def test_artifact_candidate_next_selects_acceptance_ready_candidate_without_mutation(capsys, tmp_path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    profile = tmp_path / "profile"

    pending_filename = "chatgpt_claudecode_workflow_v0.0.230.zip"
    pending_zip = repo / pending_filename
    _write_test_release_zip(pending_zip, "v0.0.230")
    pending_candidate = _write_candidate_registry(profile, filename=pending_filename, zip_path=pending_zip, version="v0.0.230")

    ready_filename = "chatgpt_claudecode_workflow_v0.0.230.zip"
    ready_zip = repo / ready_filename
    _write_test_release_zip(ready_zip, "v0.0.230")
    ready_candidate = _write_candidate_registry(profile, filename=ready_filename, zip_path=ready_zip, version="v0.0.230", tested=True)

    (profile / "artifact_candidates.json").write_text(
        json.dumps({"schema_version": 1, "candidates": [pending_candidate, ready_candidate]}, indent=2) + "\n",
        encoding="utf-8",
    )
    backend = _FakeArtifactAdoptBackend(profile, "https://chatgpt.com/g/g-p-demo/project", [])
    args = argparse.Namespace(
        artifact=None,
        version=None,
        repo_path=str(repo),
        json=True,
        profile_dir=str(profile),
    )

    exit_code = asyncio.run(cmd_artifact_candidate_next(backend, args))
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["ok"] is True
    assert payload["action"] == "artifact_candidate_next"
    assert payload["status"] == "candidate_next_acceptance_ready"
    assert payload["selected_candidate"]["artifact_ref"] == ready_filename
    assert payload["selected_candidate"]["artifact_version"] == "v0.0.230"
    assert payload["recommended_next_command"]["kind"] == "accept_candidate"
    assert "accept-candidate --version v0.0.230 --adopt-if-green" in payload["recommended_next_command"]["command"]
    assert payload["read_only"] is True
    assert payload["mutating_actions_executed"] is False
    assert payload["download_performed"] is False
    assert payload["verification_performed"] is False
    assert payload["migration_performed"] is False
    assert payload["candidate_test_performed"] is False
    assert payload["adoption_performed"] is False
    assert payload["artifact_registry_updated"] is False
    assert payload["state_artifact_updated"] is False
    assert payload["state_source_updated"] is False
    assert payload["project_source_mutated"] is False
    assert not (profile / "promptbranch_artifacts.json").exists()


def test_artifact_candidate_next_reports_intake_when_inventory_empty(capsys, tmp_path) -> None:
    profile = tmp_path / "profile"
    repo = tmp_path / "repo"
    repo.mkdir()
    backend = _FakeArtifactAdoptBackend(profile, "https://chatgpt.com/g/g-p-demo/project", [])
    args = argparse.Namespace(
        artifact=None,
        version=None,
        repo_path=str(repo),
        json=True,
        profile_dir=str(profile),
    )

    exit_code = asyncio.run(cmd_artifact_candidate_next(backend, args))
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["ok"] is True
    assert payload["status"] == "candidate_next_intake_required"
    assert payload["selected_candidate"] is None
    assert payload["recommended_next_command"]["kind"] == "intake_candidate"
    assert payload["adoption_performed"] is False
    assert payload["project_source_mutated"] is False
    assert not (profile / "promptbranch_artifacts.json").exists()


def test_artifact_candidate_next_explicit_candidate_reuses_lifecycle_recommendation(capsys, tmp_path) -> None:
    filename = "chatgpt_claudecode_workflow_v0.0.230.zip"
    repo = tmp_path / "repo"
    repo.mkdir()
    zip_path = repo / filename
    _write_test_release_zip(zip_path, "v0.0.230")
    profile = tmp_path / "profile"
    _write_candidate_registry(profile, filename=filename, zip_path=zip_path, version="v0.0.230")
    backend = _FakeArtifactAdoptBackend(profile, "https://chatgpt.com/g/g-p-demo/project", [])
    args = argparse.Namespace(
        artifact=None,
        version="v0.0.230",
        repo_path=str(repo),
        json=True,
        profile_dir=str(profile),
    )

    exit_code = asyncio.run(cmd_artifact_candidate_next(backend, args))
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["status"] == "candidate_next_test_required"
    assert payload["selected_candidate"]["artifact_ref"] == filename
    assert payload["recommended_next_command"]["kind"] == "test_candidate"
    assert "candidate-test --version v0.0.230" in payload["recommended_next_command"]["command"]
    assert payload["adoption_performed"] is False
    assert payload["candidate_test_performed"] is False



def test_artifact_candidate_run_plans_one_allowlisted_next_step_without_mutation(capsys, tmp_path) -> None:
    filename = "chatgpt_claudecode_workflow_v0.0.230.zip"
    repo = tmp_path / "repo"
    repo.mkdir()
    zip_path = repo / filename
    _write_test_release_zip(zip_path, "v0.0.230")
    profile = tmp_path / "profile"
    _write_candidate_registry(profile, filename=filename, zip_path=zip_path, version="v0.0.230", tested=True)
    backend = _FakeArtifactAdoptBackend(profile, "https://chatgpt.com/g/g-p-demo/project", [])
    args = argparse.Namespace(
        artifact=None,
        version="v0.0.230",
        repo_path=str(repo),
        execute_next=False,
        step_timeout=3600.0,
        json=True,
        profile_dir=str(profile),
    )

    exit_code = asyncio.run(cmd_artifact_candidate_run(backend, args))
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["ok"] is True
    assert payload["action"] == "artifact_candidate_run"
    assert payload["mode"] == "plan_only"
    assert payload["status"] == "candidate_run_ready"
    assert payload["recommended_next_command"]["kind"] == "accept_candidate"
    assert payload["safe_command"][-6:] == ["--version", "v0.0.230", "--repo-path", str(repo), "--adopt-if-green", "--json"]
    assert payload["mutating_actions_executed"] is False
    assert payload["candidate_test_performed"] is False
    assert payload["adoption_performed"] is False
    assert payload["project_source_mutated"] is False
    assert not (profile / "promptbranch_artifacts.json").exists()


def test_artifact_candidate_run_execute_next_runs_one_allowlisted_step(monkeypatch, capsys, tmp_path) -> None:
    filename = "chatgpt_claudecode_workflow_v0.0.230.zip"
    repo = tmp_path / "repo"
    repo.mkdir()
    zip_path = repo / filename
    _write_test_release_zip(zip_path, "v0.0.230")
    profile = tmp_path / "profile"
    _write_candidate_registry(profile, filename=filename, zip_path=zip_path, version="v0.0.230")
    backend = _FakeArtifactAdoptBackend(profile, "https://chatgpt.com/g/g-p-demo/project", [])
    calls = []

    def fake_run(command, cwd, stdout, stderr, text, timeout, check):
        calls.append(command)
        assert command[2:5] == ["artifact", "candidate-test", "--version"]
        assert "--adopt-if-green" not in command
        import subprocess

        payload = {"ok": True, "action": "artifact_candidate_test", "status": "candidate_test_passed", "adoption_performed": False}
        return subprocess.CompletedProcess(command, 0, json.dumps(payload), "")

    monkeypatch.setattr("promptbranch_cli.subprocess.run", fake_run)
    args = argparse.Namespace(
        artifact=None,
        version="v0.0.230",
        repo_path=str(repo),
        execute_next=True,
        step_timeout=123.0,
        json=True,
        profile_dir=str(profile),
    )

    exit_code = asyncio.run(cmd_artifact_candidate_run(backend, args))
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert calls
    assert payload["ok"] is True
    assert payload["status"] == "candidate_run_step_completed"
    assert payload["step_kind"] == "test_candidate"
    assert payload["mutating_actions_executed"] is True
    assert payload["candidate_test_performed"] is True
    assert payload["adoption_performed"] is False
    assert payload["project_source_mutated"] is False
    assert payload["step_result"]["parsed_json"]["status"] == "candidate_test_passed"


def test_artifact_candidate_run_execute_until_blocked_runs_test_then_accept(monkeypatch, capsys, tmp_path) -> None:
    filename = "chatgpt_claudecode_workflow_v0.0.236.zip"
    repo = tmp_path / "repo"
    repo.mkdir()
    zip_path = repo / filename
    _write_test_release_zip(zip_path, "v0.0.236")
    profile = tmp_path / "profile"
    _write_candidate_registry(profile, filename=filename, zip_path=zip_path, version="v0.0.236")
    backend = _FakeArtifactAdoptBackend(profile, "https://chatgpt.com/g/g-p-demo/project", [])
    calls = []

    def mark_test_passed() -> None:
        registry_path = profile / "artifact_candidates.json"
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        candidate = registry["candidates"][0]
        record_dir = profile / "artifact_candidate_tests" / "v0.0.236"
        record_dir.mkdir(parents=True, exist_ok=True)
        record_path = record_dir / "candidate_test.fake.json"
        record = {
            "schema": "promptbranch.artifact.candidate_test",
            "schema_version": "1.0",
            "candidate": candidate,
            "result": {"ok": True, "status": "candidate_test_passed", "adoption_performed": False},
            "adoption_performed": False,
            "project_source_mutated": False,
        }
        record_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
        candidate["latest_test"] = {
            "ok": True,
            "status": "candidate_test_passed",
            "record_path": str(record_path),
            "tested_at": "2026-05-18T00:00:00Z",
            "adoption_performed": False,
        }
        candidate["tested"] = True
        candidate["test_status"] = "candidate_test_passed"
        registry_path.write_text(json.dumps(registry, indent=2) + "\n", encoding="utf-8")

    def fake_run(command, cwd, stdout, stderr, text, timeout, check):
        calls.append(command)
        import subprocess

        if command[2:5] == ["artifact", "candidate-test", "--version"]:
            mark_test_passed()
            payload = {
                "ok": True,
                "action": "artifact_candidate_test",
                "status": "candidate_test_passed",
                "adoption_performed": False,
                "project_source_mutated": False,
            }
            return subprocess.CompletedProcess(command, 0, json.dumps(payload), "")
        if command[2:5] == ["artifact", "accept-candidate", "--version"]:
            payload = {
                "ok": True,
                "action": "artifact_accept_candidate",
                "status": "accepted_candidate",
                "adoption_performed": True,
                "project_source_mutated": False,
                "artifact_registry_updated": True,
                "state_artifact_updated": True,
                "state_source_updated": True,
            }
            return subprocess.CompletedProcess(command, 0, json.dumps(payload), "")
        raise AssertionError(f"unexpected command: {command!r}")

    monkeypatch.setattr("promptbranch_cli.subprocess.run", fake_run)
    args = argparse.Namespace(
        artifact=None,
        version="v0.0.236",
        repo_path=str(repo),
        execute_next=False,
        execute_until_blocked=True,
        max_steps=4,
        step_timeout=123.0,
        json=True,
        profile_dir=str(profile),
    )

    exit_code = asyncio.run(cmd_artifact_candidate_run(backend, args))
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert len(calls) == 2
    assert payload["ok"] is True
    assert payload["status"] == "candidate_run_cycle_completed"
    assert payload["stopped_reason"] == "accepted_candidate"
    assert payload["cycle_step_count"] == 2
    assert [step["kind"] for step in payload["cycle_steps"]] == ["test_candidate", "accept_candidate"]
    assert payload["mutating_actions_executed"] is True
    assert payload["candidate_test_performed"] is True
    assert payload["adoption_performed"] is True
    assert payload["project_source_mutated"] is False
    assert payload["artifact_registry_updated"] is True
    assert payload["state_artifact_updated"] is True
    assert payload["state_source_updated"] is True




def _write_no_artifact_protocol_run(profile: Path, *, request_id: str = "req-no-artifact") -> Path:
    reply = {
        "schema": "promptbranch.ask.reply",
        "schema_version": "1.0",
        "request_id": request_id,
        "correlation_id": request_id,
        "status": "no_artifact",
        "result_type": "no_change",
        "summary": "Protocol smoke only; no artifact was produced.",
        "baseline": {
            "input_artifact": "chatgpt_claudecode_workflow_v0.0.236.zip",
            "input_version": "v0.0.236",
            "source_ref": "chatgpt_claudecode_workflow_v0.0.236.zip",
            "source_version": "v0.0.236",
            "output_artifact": None,
            "output_version": "v0.0.247",
            "target_version": "v0.0.247",
            "release_type": "normal",
        },
        "changes": [],
        "artifacts": [],
        "validation": {"claimed": ["protocol reply only"], "not_claimed": ["artifact creation"]},
        "next_step": {"operator_action": "none"},
    }
    run = {
        "ok": True,
        "status": "reply_validated",
        "reply_validation_ok": True,
        "request_id": request_id,
        "correlation_id": request_id,
        "reply": reply,
        "artifact_candidate_count": 0,
        "request": {
            "workspace": {"project_home_url": "https://chatgpt.com/g/g-p-demo/project"},
            "task": {"conversation_url": "https://chatgpt.com/g/g-p-demo/c/abc", "conversation_id": "abc"},
            "artifact": {
                "repo": "chatgpt_claudecode_workflow",
                "current_baseline": "chatgpt_claudecode_workflow_v0.0.236.zip",
                "current_version": "v0.0.236",
                "source_ref": "chatgpt_claudecode_workflow_v0.0.236.zip",
                "source_version": "v0.0.236",
                "target_version": "v0.0.247",
                "release_type": "normal",
            },
        },
    }
    records = profile / "ask_protocol_runs"
    records.mkdir(parents=True, exist_ok=True)
    path = records / f"{request_id}.json"
    path.write_text(json.dumps(run, indent=2) + "\n", encoding="utf-8")
    return path




def test_artifact_mvp_status_reports_no_artifact_protocol_precondition(capsys, tmp_path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    profile = tmp_path / "profile"
    _write_no_artifact_protocol_run(profile)
    backend = _FakeArtifactAdoptBackend(profile, "https://chatgpt.com/g/g-p-demo/project", [])
    args = argparse.Namespace(
        artifact=None,
        version=None,
        repo_path=str(repo),
        json=True,
        profile_dir=str(profile),
    )

    exit_code = asyncio.run(cmd_artifact_mvp_status(backend, args))
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["ok"] is True
    assert payload["action"] == "artifact_mvp_status"
    assert payload["read_only"] is True
    assert payload["mutating_actions_executed"] is False
    assert payload["mvp_complete"] is False
    assert payload["status"] == "candidate_mvp_no_artifact_candidate"
    assert payload["operator_verdict"] == "no_candidate_available"
    assert payload["severity"] == "warning"
    assert "no_artifact_candidate_available" in payload["warning_codes"]
    assert payload["lifecycle_classification"]["candidate_verdict"] == "no_candidate_available"
    assert payload["lifecycle_classification"]["versions"]["runtime_code_version"] == "v0.0.269"
    assert payload["candidate_next"]["status"] == "candidate_next_no_artifact_candidate"
    assert payload["candidate_next"]["recommended_next_command"]["kind"] == "no_artifact_candidate"
    assert payload["candidate_intake_precondition"]["blocks_intake"] is True
    assert payload["download_performed"] is False
    assert payload["candidate_test_performed"] is False
    assert payload["adoption_performed"] is False
    assert payload["project_source_mutated"] is False
    assert payload["remediation_plan"]["kind"] == "no_artifact_candidate_available"
    assert payload["remediation_plan"]["read_only"] is True
    assert payload["remediation_plan"]["mutating_actions_executed"] is False
    assert payload["remediation_plan"]["requires_operator_decision"] is True
    assert payload["next_safe_actions"] == payload["remediation_plan"]["next_safe_actions"]
    action_kinds = {item["kind"] for item in payload["next_safe_actions"]}
    assert "inspect_current_artifact_state" in action_kinds
    assert "inspect_candidate_inventory" in action_kinds
    assert "create_release_candidate_protocol_turn" in action_kinds
    assert all(item["mutates_state"] is False for item in payload["next_safe_actions"])


def test_artifact_mvp_status_warns_when_runtime_differs_from_adopted_source(capsys, tmp_path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    profile = tmp_path / "profile"
    _write_no_artifact_protocol_run(profile)
    project_url = "https://chatgpt.com/g/g-p-demo/project"
    backend = _FakeArtifactAdoptBackend(profile, project_url, [])
    backend.store.remember_artifact(
        artifact_ref="chatgpt_claudecode_workflow_v0.0.238.zip",
        artifact_version="v0.0.238",
        source_ref="chatgpt_claudecode_workflow_v0.0.238.zip",
        source_version="v0.0.238",
        project_url=project_url,
    )
    registry_path = profile / "promptbranch_artifacts.json"
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(json.dumps({
        "schema_version": 1,
        "artifacts": [{
            "path": str(repo / "chatgpt_claudecode_workflow_v0.0.238.zip"),
            "filename": "chatgpt_claudecode_workflow_v0.0.238.zip",
            "kind": "adopted_release",
            "version": "v0.0.238",
            "repo_path": None,
            "sha256": "demo",
            "size_bytes": 1,
            "file_count": 1,
            "created_at": "2026-05-20T00:00:00Z",
            "source_ref": "chatgpt_claudecode_workflow_v0.0.238.zip",
            "project_url": project_url,
        }],
    }), encoding="utf-8")
    args = argparse.Namespace(
        artifact=None,
        version=None,
        repo_path=str(repo),
        json=True,
        profile_dir=str(profile),
    )

    exit_code = asyncio.run(cmd_artifact_mvp_status(backend, args))
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["ok"] is True
    assert payload["operator_verdict"] == "runtime_source_baseline_mismatch"
    assert payload["severity"] == "warning"
    assert "runtime_source_baseline_mismatch" in payload["warning_codes"]
    assert "no_artifact_candidate_available" in payload["warning_codes"]
    classification = payload["lifecycle_classification"]
    assert classification["candidate_verdict"] == "no_candidate_available"
    assert classification["versions"]["runtime_code_version"] == "v0.0.269"
    assert classification["versions"]["adopted_project_source_version"] == "v0.0.238"
    assert classification["versions"]["runtime_vs_adopted_source"] == "left_newer"
    assert classification["checks"]["runtime_code_matches_adopted_source"] is False
    assert classification["checks"]["registry_current_matches_state_artifact"] is True
    assert classification["checks"]["state_source_matches_state_artifact"] is True
    assert payload["mutating_actions_executed"] is False
    plan = payload["remediation_plan"]
    assert plan["kind"] == "runtime_source_baseline_mismatch"
    assert plan["safe_action"] == "inspect_and_decide_reconciliation"
    assert plan["read_only"] is True
    assert plan["versions"]["runtime_code_version"] == "v0.0.269"
    assert plan["versions"]["adopted_project_source_version"] == "v0.0.238"
    action_kinds = {item["kind"] for item in plan["next_safe_actions"]}
    assert "inspect_project_sources" in action_kinds
    assert "decide_runtime_source_reconciliation" in action_kinds
    assert "create_release_candidate_protocol_turn" in action_kinds
    assert all(item["mutates_state"] is False for item in plan["next_safe_actions"])






def test_release_lifecycle_status_consolidates_local_state_and_finalizer_summary(capsys, tmp_path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "VERSION").write_text("v0.0.269\n", encoding="utf-8")
    profile = repo / ".pb_profile"
    summary_dir = profile / "release_logs" / "v0.0.269"
    summary_dir.mkdir(parents=True)
    summary_path = summary_dir / "post_release_validation.v0.0.269.summary.json"
    summary_path.write_text(json.dumps({
        "ok": True,
        "version": "v0.0.269",
        "target_version": "v0.0.269",
        "failure_count": 0,
        "validation_classification": {
            "status": "passed",
            "primary_category": "none",
            "blocking_categories": [],
        },
        "primary_failure_category": "none",
        "blocking_failure_categories": [],
    }), encoding="utf-8")

    artifact_name = "chatgpt_claudecode_workflow_v0.0.269.zip"
    registry = ArtifactRegistry(profile)
    registry.add(ArtifactRecord(
        filename=artifact_name,
        version="v0.0.269",
        path=str(tmp_path / artifact_name),
        sha256="abc",
        kind="release_zip",
        repo_path=str(repo),
        size_bytes=123,
        file_count=10,
        created_at="2026-05-24T00:00:00Z",
    ))
    store = ConversationStateStore(profile)
    store.remember_project("https://chatgpt.com/g/g-p-demo/project", project_name="Demo")
    store.remember_artifact(
        artifact_ref=artifact_name,
        artifact_version="v0.0.269",
        source_ref=artifact_name,
        source_version="v0.0.269",
        project_url="https://chatgpt.com/g/g-p-demo/project",
    )
    backend = _FakeArtifactAdoptBackend(profile, "https://chatgpt.com/g/g-p-demo/project", [])
    args = argparse.Namespace(
        artifact=None,
        version="v0.0.269",
        target_version="v0.0.269",
        repo_path=str(repo),
        health_url=None,
        health_timeout=3.0,
        source_timeout=60.0,
        include_service_health=False,
        include_project_sources=False,
        keep_open=False,
        json=True,
        profile_dir=str(profile),
    )

    exit_code = asyncio.run(cmd_release_lifecycle_status(backend, args))
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["action"] == "release_lifecycle_status"
    assert payload["read_only"] is True
    assert payload["local_first"] is True
    assert payload["mutating_actions_executed"] is False
    assert payload["runtime"]["runtime_code_version"] == "v0.0.269"
    assert payload["version_file"]["normalized_version"] == "v0.0.269"
    assert payload["artifact_current"]["baseline_roles"]["adopted_source_version"] == "v0.0.269"
    assert payload["service_health"]["status"] == "skipped"
    assert payload["project_sources"]["status"] == "skipped"
    assert payload["latest_post_release_validation"]["ok"] is True
    assert payload["latest_post_release_validation"]["failure_count"] == 0
    assert payload["latest_post_release_validation"]["summary_path"] == str(summary_path.resolve())
    assert payload["candidate_inventory_summary"]["candidate_count"] == 0
    assert payload["next_safe_action"]["kind"] == "continue_normal_development"
    assert payload["project_source_mutated"] is False
    assert payload["adoption_performed"] is False

def test_release_doctor_reports_runtime_source_mismatch_read_only(capsys, tmp_path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "VERSION").write_text("v0.0.269\n", encoding="utf-8")
    subprocess_run = __import__("subprocess").run
    subprocess_run(["git", "init"], cwd=repo, stdout=__import__("subprocess").DEVNULL, stderr=__import__("subprocess").DEVNULL, check=True)
    profile = tmp_path / "profile"
    project_url = "https://chatgpt.com/g/g-p-demo/project"
    backend = _FakeArtifactAdoptBackend(profile, project_url, [{"title": "chatgpt_claudecode_workflow_v0.0.238.zip", "identity": "src_1"}])
    backend.store.remember_artifact(
        artifact_ref="chatgpt_claudecode_workflow_v0.0.238.zip",
        artifact_version="v0.0.238",
        source_ref="chatgpt_claudecode_workflow_v0.0.238.zip",
        source_version="v0.0.238",
        project_url=project_url,
    )
    registry_path = profile / "promptbranch_artifacts.json"
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(json.dumps({
        "schema_version": 1,
        "artifacts": [{
            "path": str(repo / "chatgpt_claudecode_workflow_v0.0.238.zip"),
            "filename": "chatgpt_claudecode_workflow_v0.0.238.zip",
            "kind": "adopted_release",
            "version": "v0.0.238",
            "sha256": "demo",
            "size_bytes": 1,
            "file_count": 1,
            "created_at": "2026-05-20T00:00:00Z",
            "source_ref": "chatgpt_claudecode_workflow_v0.0.238.zip",
            "project_url": project_url,
        }],
    }), encoding="utf-8")
    args = argparse.Namespace(
        version="v0.0.269",
        target_version="v0.0.269",
        repo_path=str(repo),
        health_url="http://127.0.0.1:9/healthz",
        health_timeout=0.2,
        source_timeout=1.0,
        skip_service_health=True,
        skip_project_sources=False,
        keep_open=False,
        json=True,
        profile_dir=str(profile),
        service_base_url=None,
    )

    exit_code = asyncio.run(cmd_release_doctor(backend, args))
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["ok"] is True
    assert payload["action"] == "release_doctor"
    assert payload["read_only"] is True
    assert payload["mutating_actions_executed"] is False
    assert payload["runtime"]["runtime_code_version"] == "v0.0.269"
    assert payload["version_file"]["normalized_version"] == "v0.0.269"
    assert payload["project_sources"]["attempted"] is True
    assert payload["project_sources"]["detected_versions"][0]["normalized_version"] == "v0.0.238"
    assert "runtime_source_baseline_mismatch" in payload["warning_codes"]
    assert "runtime_version_not_visible_in_project_sources" in payload["warning_codes"]
    assert payload["blocker_codes"] == []
    assert payload["project_source_mutated"] is False
    assert payload["state_artifact_updated"] is False
    assert payload["git"]["is_git_repo"] is True
    action_kinds = {item["kind"] for item in payload["next_safe_actions"]}
    assert "inspect_artifact_current" in action_kinds
    assert "inspect_project_sources" in action_kinds
    assert all(item["mutates_state"] is False for item in payload["next_safe_actions"])



def test_release_doctor_artifact_zip_hardening_reports_candidate_phase(capsys, tmp_path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "VERSION").write_text("v0.0.269\n", encoding="utf-8")
    subprocess_run = __import__("subprocess").run
    subprocess_run(["git", "init"], cwd=repo, stdout=__import__("subprocess").DEVNULL, stderr=__import__("subprocess").DEVNULL, check=True)
    artifact_path = repo / "chatgpt_claudecode_workflow_v0.0.269.zip"
    _write_test_release_zip(artifact_path, "v0.0.269")
    profile = tmp_path / "profile"
    project_url = "https://chatgpt.com/g/g-p-demo/project"
    backend = _FakeArtifactAdoptBackend(profile, project_url, [{"title": artifact_path.name, "identity": "src_248"}])
    args = argparse.Namespace(
        version="v0.0.269",
        target_version="v0.0.269",
        artifact=str(artifact_path),
        repo_path=str(repo),
        health_url=None,
        health_timeout=0.2,
        source_timeout=1.0,
        skip_service_health=True,
        skip_project_sources=False,
        keep_open=False,
        json=True,
        profile_dir=str(profile),
        service_base_url=None,
    )

    exit_code = asyncio.run(cmd_release_doctor(backend, args))
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["ok"] is True
    assert payload["artifact_inspection"]["ok"] is True
    assert payload["artifact_inspection"]["normalized_version"] == "v0.0.269"
    assert payload["artifact_inspection"]["sha256"]
    assert payload["artifact_inspection"]["verification"]["wrapper_folder"] is None
    assert payload["artifact_consistency"]["checks"]["artifact_zip_verified"] is True
    assert payload["lifecycle_phase"] == "project_source_uploaded"
    assert payload["read_only"] is True
    assert payload["mutating_actions_executed"] is False
    assert payload["project_source_mutated"] is False
    assert payload["artifact_registry_updated"] is False


def test_release_doctor_blocks_runtime_version_file_mismatch(capsys, tmp_path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "VERSION").write_text("v0.0.999\n", encoding="utf-8")
    profile = tmp_path / "profile"
    backend = _FakeArtifactAdoptBackend(profile, "https://chatgpt.com/g/g-p-demo/project", [])
    args = argparse.Namespace(
        version="v0.0.257",
        target_version=None,
        repo_path=str(repo),
        health_url=None,
        health_timeout=0.2,
        source_timeout=1.0,
        skip_service_health=True,
        skip_project_sources=True,
        keep_open=False,
        json=True,
        profile_dir=str(profile),
        service_base_url=None,
    )

    exit_code = asyncio.run(cmd_release_doctor(backend, args))
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert payload["ok"] is False
    assert payload["status"] == "blocked"
    assert "runtime_version_file_mismatch" in payload["blocker_codes"]
    assert payload["download_performed"] is False
    assert payload["adoption_performed"] is False
    assert payload["project_source_mutated"] is False



def test_release_config_validates_lifecycle_config_read_only(capsys, tmp_path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    config = repo / ".promptbranch-release.yml"
    config.write_text("""
schema_version: 1
artifact:
  prefix: chatgpt_claudecode_workflow_
  suffix: .zip
  version_file: VERSION
  policy_file: .promptbranch-project.json
install:
  preserve:
    - .git/
    - .env
    - .pb_profile/
git:
  unsafe_paths:
    - .env
    - .pb_profile/
    - '*.zip'
hooks:
  doctor:
    command: pb release doctor --version {version} --artifact {artifact} --repo-path {repo_path} --json
""".lstrip(), encoding="utf-8")
    args = argparse.Namespace(
        config=str(config),
        repo_path=str(repo),
        json=True,
    )

    exit_code = asyncio.run(cmd_release_config(None, args))
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["ok"] is True
    assert payload["action"] == "release_config"
    assert payload["status"] == "verified"
    assert payload["read_only"] is True
    assert payload["mutating_actions_executed"] is False
    assert payload["project_source_mutated"] is False
    assert payload["git_commit_performed"] is False
    assert payload["config"]["artifact"]["prefix"] == "chatgpt_claudecode_workflow_"
    assert payload["config"]["install"]["preserve"] == [".git/", ".env", ".pb_profile/"]
    assert payload["blocker_codes"] == []


def test_release_config_rejects_unsafe_paths_and_unknown_hook_placeholder(capsys, tmp_path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    config = repo / ".promptbranch-release.yml"
    config.write_text("""
schema_version: 1
artifact:
  prefix: chatgpt_claudecode_workflow_
  suffix: .zip
  version_file: /VERSION
  policy_file: ../policy.json
install:
  preserve:
    - ../escape
git:
  unsafe_paths:
    - /tmp/secret
hooks:
  doctor:
    command: echo {unknown}
""".lstrip(), encoding="utf-8")
    args = argparse.Namespace(
        config=str(config),
        repo_path=str(repo),
        json=True,
    )

    exit_code = asyncio.run(cmd_release_config(None, args))
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert payload["ok"] is False
    assert payload["status"] == "blocked"
    assert "release_config_artifact_path_invalid" in payload["blocker_codes"]
    assert "release_config_install_preserve_path_invalid" in payload["blocker_codes"]
    assert "release_config_git_unsafe_path_invalid" in payload["blocker_codes"]
    assert "release_config_hook_placeholder_unsupported" in payload["blocker_codes"]
    assert payload["mutating_actions_executed"] is False




def test_release_install_plan_reports_read_only_install_contract(capsys, tmp_path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    config = repo / ".promptbranch-release.yml"
    config.write_text("""
schema_version: 1
artifact:
  prefix: chatgpt_claudecode_workflow_
  suffix: .zip
  version_file: VERSION
  policy_file: .promptbranch-project.json
install:
  preserve:
    - .git/
    - .env
    - .pb_profile/
git:
  unsafe_paths:
    - .env
    - .pb_profile/
    - '*.zip'
hooks:
  doctor:
    command: pb release doctor --version {version} --artifact {artifact} --repo-path {repo_path} --json
""".lstrip(), encoding="utf-8")
    (repo / "VERSION").write_text("v0.0.247.1\n", encoding="utf-8")
    artifact = repo / "chatgpt_claudecode_workflow_v0.0.257.zip"
    _write_test_release_zip(artifact, "v0.0.257")
    args = argparse.Namespace(
        artifact=str(artifact),
        version="v0.0.257",
        target_version="v0.0.257",
        config=str(config),
        repo_path=str(repo),
        plan=True,
        json=True,
    )

    exit_code = asyncio.run(cmd_release_install(None, args))
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["ok"] is True
    assert payload["action"] == "release_install"
    assert payload["status"] == "planned"
    assert payload["mode"] == "plan_only"
    assert payload["read_only"] is True
    assert payload["install_performed"] is False
    assert payload["project_source_mutated"] is False
    assert payload["artifact_registry_updated"] is False
    assert payload["git_commit_performed"] is False
    assert payload["git_push_performed"] is False
    assert payload["mutating_actions_executed"] is False
    assert payload["install_plan"]["mutation_allowed"] is False
    assert payload["install_plan"]["artifact_version"] == "v0.0.257"
    assert payload["install_plan"]["target_version"] == "v0.0.257"
    assert payload["install_plan"]["install_entry_count"] > 0
    assert payload["install_plan"]["preserved_conflict_count"] == 0
    assert payload["blocker_codes"] == []


def test_release_install_blocks_preserved_entries_before_mutation(capsys, tmp_path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    config = repo / ".promptbranch-release.yml"
    config.write_text("""
schema_version: 1
artifact:
  prefix: chatgpt_claudecode_workflow_
  suffix: .zip
  version_file: VERSION
  policy_file: .promptbranch-project.json
install:
  preserve:
    - .git/
    - .env
    - .pb_profile/
git:
  unsafe_paths:
    - .env
    - .pb_profile/
    - '*.zip'
hooks:
  doctor:
    command: pb release doctor --version {version} --artifact {artifact} --repo-path {repo_path} --json
""".lstrip(), encoding="utf-8")
    (repo / "VERSION").write_text("v0.0.247.1\n", encoding="utf-8")
    artifact = repo / "chatgpt_claudecode_workflow_v0.0.257.zip"
    with zipfile.ZipFile(artifact, "w") as archive:
        archive.writestr("VERSION", "v0.0.257\n")
        archive.writestr("promptbranch_cli.py", "# candidate\n")
        archive.writestr(".pb_profile/state.json", "{}")
    args = argparse.Namespace(
        artifact=str(artifact),
        version="v0.0.257",
        target_version=None,
        config=str(config),
        repo_path=str(repo),
        plan=False,
        json=True,
    )

    exit_code = asyncio.run(cmd_release_install(None, args))
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert payload["ok"] is False
    assert payload["status"] == "blocked"
    assert "release_install_artifact_contains_preserved_path" in payload["blocker_codes"]
    assert payload["install_performed"] is False
    assert payload["mutating_actions_executed"] is False


def test_release_install_executes_bounded_repo_extract_without_source_or_git_mutation(capsys, tmp_path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    config = repo / ".promptbranch-release.yml"
    config.write_text("""
schema_version: 1
artifact:
  prefix: chatgpt_claudecode_workflow_
  suffix: .zip
  version_file: VERSION
  policy_file: .promptbranch-project.json
install:
  preserve:
    - .git/
    - .env
    - .pb_profile/
git:
  unsafe_paths:
    - .env
    - .pb_profile/
    - '*.zip'
hooks:
  doctor:
    command: pb release doctor --version {version} --artifact {artifact} --repo-path {repo_path} --json
""".lstrip(), encoding="utf-8")
    (repo / "VERSION").write_text("v0.0.257-old\n", encoding="utf-8")
    (repo / "README.md").write_text("old readme\n", encoding="utf-8")
    (repo / "stale.txt").write_text("must remain\n", encoding="utf-8")
    (repo / ".env").write_text("SECRET=keep\n", encoding="utf-8")
    artifact = tmp_path / "chatgpt_claudecode_workflow_v0.0.257.zip"
    with zipfile.ZipFile(artifact, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("VERSION", "v0.0.257\n")
        archive.writestr("README.md", "new readme\n")
        archive.writestr("promptbranch_cli.py", "# candidate code\n")

    args = argparse.Namespace(
        artifact=str(artifact),
        version="v0.0.257",
        target_version="v0.0.257",
        config=str(config),
        repo_path=str(repo),
        plan=False,
        json=True,
    )

    exit_code = asyncio.run(cmd_release_install(None, args))
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["ok"] is True
    assert payload["status"] == "installed"
    assert payload["mode"] == "install"
    assert payload["read_only"] is False
    assert payload["install_performed"] is True
    assert payload["repo_install_performed"] is True
    assert payload["mutating_actions_executed"] is True
    assert payload["project_source_mutated"] is False
    assert payload["artifact_registry_updated"] is False
    assert payload["state_artifact_updated"] is False
    assert payload["state_source_updated"] is False
    assert payload["git_commit_performed"] is False
    assert payload["git_push_performed"] is False
    assert payload["execution"]["installed_entry_count"] == 3
    assert payload["execution"]["deleted_entry_count"] == 0
    assert payload["execution"]["installed_version"] == "v0.0.257"
    assert (repo / "VERSION").read_text(encoding="utf-8") == "v0.0.257\n"
    assert (repo / "README.md").read_text(encoding="utf-8") == "new readme\n"
    assert (repo / "promptbranch_cli.py").read_text(encoding="utf-8") == "# candidate code\n"
    assert (repo / "stale.txt").read_text(encoding="utf-8") == "must remain\n"
    assert (repo / ".env").read_text(encoding="utf-8") == "SECRET=keep\n"



def test_release_install_plan_reports_requested_source_upload_without_mutation(capsys, tmp_path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    config = repo / ".promptbranch-release.yml"
    config.write_text("""
schema_version: 1
artifact:
  prefix: chatgpt_claudecode_workflow_
  suffix: .zip
  version_file: VERSION
  policy_file: .promptbranch-project.json
install:
  preserve:
    - .git/
    - .env
    - .pb_profile/
git:
  unsafe_paths:
    - .env
    - .pb_profile/
    - '*.zip'
hooks:
  doctor:
    command: pb release doctor --version {version} --artifact {artifact} --repo-path {repo_path} --json
""".lstrip(), encoding="utf-8")
    (repo / "VERSION").write_text("v0.0.257\n", encoding="utf-8")
    artifact = repo / "chatgpt_claudecode_workflow_v0.0.257.zip"
    _write_test_release_zip(artifact, "v0.0.257")
    args = argparse.Namespace(
        artifact=str(artifact),
        version="v0.0.257",
        target_version="v0.0.257",
        config=str(config),
        repo_path=str(repo),
        plan=True,
        upload_source=True,
        keep_open=False,
        json=True,
    )

    exit_code = asyncio.run(cmd_release_install(None, args))
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["ok"] is True
    assert payload["status"] == "planned"
    assert payload["read_only"] is True
    assert payload["install_performed"] is False
    assert payload["project_source_mutated"] is False
    assert payload["upload_source_requested"] is True
    assert payload["install_plan"]["would_upload_project_source"] is True
    assert payload["install_plan"]["would_verify_project_source_visibility"] is True
    assert payload["source_upload_verification"] is None


def test_release_install_upload_source_verifies_before_after_without_state_advancement(capsys, tmp_path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    config = repo / ".promptbranch-release.yml"
    config.write_text("""
schema_version: 1
artifact:
  prefix: chatgpt_claudecode_workflow_
  suffix: .zip
  version_file: VERSION
  policy_file: .promptbranch-project.json
install:
  preserve:
    - .git/
    - .env
    - .pb_profile/
git:
  unsafe_paths:
    - .env
    - .pb_profile/
    - '*.zip'
hooks:
  doctor:
    command: pb release doctor --version {version} --artifact {artifact} --repo-path {repo_path} --json
""".lstrip(), encoding="utf-8")
    (repo / "VERSION").write_text("v0.0.257\n", encoding="utf-8")
    artifact = tmp_path / "chatgpt_claudecode_workflow_v0.0.257.zip"
    _write_test_release_zip(artifact, "v0.0.257")

    class FakeReleaseInstallBackend:
        def __init__(self) -> None:
            self.calls: list[dict[str, object]] = []

        async def list_project_sources(self, **kwargs):
            if not self.calls:
                return {"ok": True, "action": "source_list", "sources": [{"title": "keep-me.txt"}]}
            return {"ok": True, "action": "source_list", "sources": [{"title": "keep-me.txt"}, {"title": "chatgpt_claudecode_workflow_v0.0.257.zip"}]}

        async def add_project_source(self, **kwargs):
            self.calls.append(kwargs)
            return {"ok": True, "action": "source_add", "status": "verified"}

    backend = FakeReleaseInstallBackend()
    args = argparse.Namespace(
        artifact=str(artifact),
        version="v0.0.257",
        target_version="v0.0.257",
        config=str(config),
        repo_path=str(repo),
        plan=False,
        upload_source=True,
        keep_open=True,
        json=True,
    )

    exit_code = asyncio.run(cmd_release_install(backend, args))
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["ok"] is True
    assert payload["status"] == "installed_source_uploaded"
    assert payload["install_performed"] is True
    assert payload["repo_install_performed"] is True
    assert payload["project_source_mutated"] is True
    assert payload["project_source_mutation"] == "verified"
    assert payload["source_upload_verification"]["status"] == "verified"
    assert payload["source_upload_verification"]["checks"]["expected_source_present_after"] is True
    assert payload["source_upload_verification"]["checks"]["collateral_sources_removed"] is False
    assert payload["artifact_registry_updated"] is False
    assert payload["state_artifact_updated"] is False
    assert payload["state_source_updated"] is False
    assert payload["adoption_performed"] is False
    assert payload["git_commit_performed"] is False
    assert payload["git_push_performed"] is False
    assert backend.calls[0]["display_name"] == "chatgpt_claudecode_workflow_v0.0.257.zip"
    assert backend.calls[0]["overwrite_existing"] is True
    assert backend.calls[0]["keep_open"] is True


def test_release_install_upload_source_rejects_unverified_after_list(capsys, tmp_path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    config = repo / ".promptbranch-release.yml"
    config.write_text("""
schema_version: 1
artifact:
  prefix: chatgpt_claudecode_workflow_
  suffix: .zip
  version_file: VERSION
  policy_file: .promptbranch-project.json
install:
  preserve:
    - .git/
git:
  unsafe_paths:
    - '*.zip'
hooks:
  doctor:
    command: pb release doctor --version {version} --artifact {artifact} --repo-path {repo_path} --json
""".lstrip(), encoding="utf-8")
    (repo / "VERSION").write_text("v0.0.257\n", encoding="utf-8")
    artifact = tmp_path / "chatgpt_claudecode_workflow_v0.0.257.zip"
    _write_test_release_zip(artifact, "v0.0.257")

    class FakeReleaseInstallBackend:
        async def list_project_sources(self, **kwargs):
            return {"ok": True, "action": "source_list", "sources": []}

        async def add_project_source(self, **kwargs):
            return {"ok": True, "action": "source_add", "status": "verified"}

    args = argparse.Namespace(
        artifact=str(artifact),
        version="v0.0.257",
        target_version=None,
        config=str(config),
        repo_path=str(repo),
        plan=False,
        upload_source=True,
        keep_open=False,
        json=True,
    )

    exit_code = asyncio.run(cmd_release_install(FakeReleaseInstallBackend(), args))
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert payload["ok"] is False
    assert payload["status"] == "installed_source_upload_not_verified"
    assert payload["install_performed"] is True
    assert payload["project_source_mutated"] is False
    assert payload["artifact_registry_updated"] is False
    assert payload["state_source_updated"] is False
    assert "release_install_source_upload_not_verified" in payload["blocker_codes"]



def test_release_test_plan_reports_configured_hooks_without_execution(capsys, tmp_path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    config = repo / ".promptbranch-release.yml"
    config.write_text("""
schema_version: 1
artifact:
  prefix: chatgpt_claudecode_workflow_
  suffix: .zip
  version_file: VERSION
  policy_file: .promptbranch-project.json
install:
  preserve:
    - .git/
git:
  unsafe_paths:
    - '*.zip'
hooks:
  preflight:
    command: python -c "print('preflight {version}')"
  local_acceptance:
    command: python -c "print('local {artifact}')"
""".lstrip(), encoding="utf-8")
    artifact = repo / "chatgpt_claudecode_workflow_v0.0.257.zip"
    _write_test_release_zip(artifact, "v0.0.257")
    args = argparse.Namespace(
        artifact=str(artifact),
        version="v0.0.257",
        target_version="v0.0.257",
        config=str(config),
        repo_path=str(repo),
        hook=None,
        plan=True,
        hook_timeout=30.0,
        stop_on_failure=True,
        json=True,
    )

    exit_code = asyncio.run(cmd_release_test(None, args))
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["ok"] is True
    assert payload["action"] == "release_test"
    assert payload["status"] == "planned"
    assert payload["read_only"] is True
    assert payload["hook_count"] == 2
    assert [item["hook"] for item in payload["hook_plan"]] == ["preflight", "local_acceptance"]
    assert payload["acceptance_report_written"] is False
    assert payload["candidate_test_performed"] is False
    assert payload["adoption_performed"] is False
    assert payload["project_source_mutated"] is False
    assert payload["artifact_registry_updated"] is False


def test_release_test_runs_hooks_and_writes_structured_acceptance_report(capsys, tmp_path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    config = repo / ".promptbranch-release.yml"
    config.write_text("""
schema_version: 1
artifact:
  prefix: chatgpt_claudecode_workflow_
  suffix: .zip
  version_file: VERSION
  policy_file: .promptbranch-project.json
install:
  preserve:
    - .git/
git:
  unsafe_paths:
    - '*.zip'
hooks:
  preflight:
    command: python -c "print('preflight-ok')"
  local_acceptance:
    command: python -c "print('local-ok')"
""".lstrip(), encoding="utf-8")
    artifact = repo / "chatgpt_claudecode_workflow_v0.0.257.zip"
    _write_test_release_zip(artifact, "v0.0.257")
    args = argparse.Namespace(
        artifact=str(artifact),
        version="v0.0.257",
        target_version="v0.0.257",
        config=str(config),
        repo_path=str(repo),
        hook=None,
        plan=False,
        hook_timeout=30.0,
        stop_on_failure=True,
        json=True,
    )

    exit_code = asyncio.run(cmd_release_test(None, args))
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["ok"] is True
    assert payload["status"] == "release_acceptance_passed"
    assert payload["acceptance_status"] == "accepted"
    assert payload["candidate_test_performed"] is True
    assert payload["adoption_performed"] is False
    assert payload["state_artifact_updated"] is False
    assert payload["state_source_updated"] is False
    assert payload["git_commit_performed"] is False
    report_path = Path(payload["acceptance_report_path"])
    assert report_path.is_file()
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["schema"] == "promptbranch.release.acceptance_report"
    assert report["accepted"] is True
    assert [item["status"] for item in report["hook_results"]] == ["hook_passed", "hook_passed"]


def test_release_test_fails_closed_when_hook_fails(capsys, tmp_path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    config = repo / ".promptbranch-release.yml"
    config.write_text("""
schema_version: 1
artifact:
  prefix: chatgpt_claudecode_workflow_
  suffix: .zip
  version_file: VERSION
  policy_file: .promptbranch-project.json
install:
  preserve:
    - .git/
git:
  unsafe_paths:
    - '*.zip'
hooks:
  local_acceptance:
    command: python -c "import sys; print('bad'); sys.exit(7)"
  release_status:
    command: python -c "print('should-not-run')"
""".lstrip(), encoding="utf-8")
    artifact = repo / "chatgpt_claudecode_workflow_v0.0.257.zip"
    _write_test_release_zip(artifact, "v0.0.257")
    args = argparse.Namespace(
        artifact=str(artifact),
        version="v0.0.257",
        target_version="v0.0.257",
        config=str(config),
        repo_path=str(repo),
        hook=None,
        plan=False,
        hook_timeout=30.0,
        stop_on_failure=True,
        json=True,
    )

    exit_code = asyncio.run(cmd_release_test(None, args))
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert payload["ok"] is False
    assert payload["status"] == "release_acceptance_failed"
    assert payload["acceptance_status"] == "rejected"
    assert payload["hook_count"] == 1
    assert payload["hook_results"][0]["returncode"] == 7
    assert "release_acceptance_hooks_failed" in payload["blocker_codes"]
    assert payload["adoption_performed"] is False
    assert payload["state_artifact_updated"] is False


def test_release_adopt_requires_green_acceptance_report(capsys, tmp_path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    artifact = repo / "chatgpt_claudecode_workflow_v0.0.257.zip"
    _write_test_release_zip(artifact, "v0.0.257")
    profile = tmp_path / "profile"
    backend = _FakeArtifactAdoptBackend(profile, "https://chatgpt.com/g/g-p-demo/project", [{"title": artifact.name}])
    args = argparse.Namespace(
        artifact=str(artifact),
        version="v0.0.257",
        target_version="v0.0.257",
        acceptance_report=None,
        repo_path=str(repo),
        plan=False,
        keep_open=False,
        json=True,
        profile_dir=str(profile),
    )

    exit_code = asyncio.run(cmd_release_adopt(backend, args))
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert payload["ok"] is False
    assert payload["status"] == "release_adopt_blocked"
    assert "release_acceptance_report_missing" in payload["blocker_codes"]
    assert payload["adoption_performed"] is False
    assert payload["artifact_registry_updated"] is False
    assert payload["state_artifact_updated"] is False
    assert not (profile / "promptbranch_artifacts.json").exists()


def test_release_adopt_updates_current_only_after_green_acceptance_report_and_source_verification(capsys, tmp_path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    config = repo / ".promptbranch-release.yml"
    config.write_text("""
schema_version: 1
artifact:
  prefix: chatgpt_claudecode_workflow_
  suffix: .zip
  version_file: VERSION
  policy_file: .promptbranch-project.json
install:
  preserve:
    - .git/
git:
  unsafe_paths:
    - '*.zip'
hooks:
  local_acceptance:
    command: python -c "print('green')"
""".lstrip(), encoding="utf-8")
    artifact = repo / "chatgpt_claudecode_workflow_v0.0.257.zip"
    _write_test_release_zip(artifact, "v0.0.257")

    test_args = argparse.Namespace(
        artifact=str(artifact),
        version="v0.0.257",
        target_version="v0.0.257",
        config=str(config),
        repo_path=str(repo),
        hook=None,
        plan=False,
        hook_timeout=30.0,
        stop_on_failure=True,
        json=True,
    )
    assert asyncio.run(cmd_release_test(None, test_args)) == 0
    test_payload = json.loads(capsys.readouterr().out)
    assert test_payload["acceptance_status"] == "accepted"

    profile = tmp_path / "profile"
    backend = _FakeArtifactAdoptBackend(profile, "https://chatgpt.com/g/g-p-demo/project", [{"title": artifact.name, "id": "src_1"}])
    adopt_args = argparse.Namespace(
        artifact=str(artifact),
        version="v0.0.257",
        target_version="v0.0.257",
        acceptance_report=None,
        repo_path=str(repo),
        plan=False,
        keep_open=False,
        json=True,
        profile_dir=str(profile),
    )

    exit_code = asyncio.run(cmd_release_adopt(backend, adopt_args))
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["ok"] is True
    assert payload["status"] == "release_adopted"
    assert payload["source_verified"] is True
    assert payload["acceptance_report_gate"]["ok"] is True
    assert payload["adoption_performed"] is True
    assert payload["artifact_registry_updated"] is True
    assert payload["state_artifact_updated"] is True
    assert payload["state_source_updated"] is True
    assert payload["project_source_mutated"] is False
    assert payload["git_commit_performed"] is False
    assert payload["artifact_current"]["state"]["artifact_ref"] == artifact.name
    registry_payload = json.loads((profile / "promptbranch_artifacts.json").read_text(encoding="utf-8"))
    assert registry_payload["artifacts"][0]["filename"] == artifact.name




def test_release_policy_sync_writes_and_verifies_policy_without_git_commit(capsys, tmp_path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    config = repo / ".promptbranch-release.yml"
    config.write_text("""
schema_version: 1
artifact:
  prefix: chatgpt_claudecode_workflow_
  suffix: .zip
  version_file: VERSION
  policy_file: .promptbranch-project.json
install:
  preserve:
    - .git/
git:
  unsafe_paths:
    - '*.zip'
    - .pb_profile/
hooks:
  local_acceptance:
    command: python -c "print('ok')"
""".lstrip(), encoding="utf-8")
    artifact = repo / "chatgpt_claudecode_workflow_v0.0.257.zip"
    _write_test_release_zip(artifact, "v0.0.257")
    backend = _FakeArtifactAdoptBackend(tmp_path / "profile", "https://chatgpt.com/g/g-p-demo/project", [])
    args = argparse.Namespace(
        artifact=str(artifact),
        version="v0.0.257",
        target_version="v0.0.257",
        config=str(config),
        repo_path=str(repo),
        plan=False,
        json=True,
        profile_dir=str(tmp_path / "profile"),
    )

    exit_code = asyncio.run(cmd_release_policy_sync(backend, args))
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["ok"] is True
    assert payload["status"] == "release_policy_synced"
    assert payload["policy_sync_performed"] is True
    assert payload["policy_verified"] is True
    assert payload["git_commit_performed"] is False
    assert payload["git_push_performed"] is False
    policy = json.loads((repo / ".promptbranch-project.json").read_text(encoding="utf-8"))
    assert policy["accepted_baseline"]["artifact_ref"] == artifact.name
    assert policy["accepted_baseline"]["artifact_version"] == "v0.0.257"
    assert policy["source"]["ref"] == artifact.name


def test_release_policy_sync_plan_is_read_only(capsys, tmp_path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    config = repo / ".promptbranch-release.yml"
    config.write_text("""
schema_version: 1
artifact:
  prefix: chatgpt_claudecode_workflow_
  suffix: .zip
  version_file: VERSION
  policy_file: .promptbranch-project.json
install:
  preserve:
    - .git/
git:
  unsafe_paths:
    - '*.zip'
hooks:
  local_acceptance:
    command: python -c "print('ok')"
""".lstrip(), encoding="utf-8")
    artifact = repo / "chatgpt_claudecode_workflow_v0.0.257.zip"
    _write_test_release_zip(artifact, "v0.0.257")
    args = argparse.Namespace(
        artifact=str(artifact),
        version="v0.0.257",
        target_version="v0.0.257",
        config=str(config),
        repo_path=str(repo),
        plan=True,
        json=True,
        profile_dir=str(tmp_path / "profile"),
    )

    exit_code = asyncio.run(cmd_release_policy_sync(None, args))
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["ok"] is True
    assert payload["status"] == "planned"
    assert payload["read_only"] is True
    assert payload["policy_sync_performed"] is False
    assert not (repo / ".promptbranch-project.json").exists()


def test_release_lifecycle_plan_composes_phases_without_mutation(capsys, tmp_path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    config = repo / ".promptbranch-release.yml"
    config.write_text("""
schema_version: 1
artifact:
  prefix: chatgpt_claudecode_workflow_
  suffix: .zip
  version_file: VERSION
  policy_file: .promptbranch-project.json
install:
  preserve:
    - .git/
git:
  unsafe_paths:
    - '*.zip'
    - .pb_profile/
hooks:
  preflight:
    command: python -c "print('preflight')"
""".lstrip(), encoding="utf-8")
    artifact = repo / "chatgpt_claudecode_workflow_v0.0.257.zip"
    _write_test_release_zip(artifact, "v0.0.257")
    args = argparse.Namespace(
        artifact=str(artifact),
        version="v0.0.257",
        target_version="v0.0.257",
        config=str(config),
        repo_path=str(repo),
        plan=True,
        json=True,
    )

    exit_code = asyncio.run(cmd_release_lifecycle(None, args))
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["ok"] is True
    assert payload["status"] == "planned"
    assert payload["read_only"] is True
    assert payload["would_sync_policy"] is True
    assert payload["would_commit_git"] is False
    assert payload["would_push_git"] is False
    assert payload["mutating_actions_executed"] is False
    assert [item["phase"] for item in payload["phase_plan"]] == ["doctor", "install", "test", "adopt", "policy_sync", "git_sync"]
    assert not (repo / ".promptbranch-project.json").exists()



def test_release_lifecycle_executes_guarded_phases_through_policy_sync(capsys, tmp_path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    config = repo / ".promptbranch-release.yml"
    config.write_text("""
schema_version: 1
artifact:
  prefix: chatgpt_claudecode_workflow_
  suffix: .zip
  version_file: VERSION
  policy_file: .promptbranch-project.json
install:
  preserve:
    - .git/
git:
  unsafe_paths:
    - '*.zip'
    - .pb_profile/
hooks:
  preflight:
    command: python -c "print('preflight')"
  local_acceptance:
    command: python -c "print('local')"
""".lstrip(), encoding="utf-8")
    (repo / "VERSION").write_text("v0.0.269\n", encoding="utf-8")
    artifact = tmp_path / "chatgpt_claudecode_workflow_v0.0.269.zip"
    _write_test_release_zip(artifact, "v0.0.269")

    class FakeLifecycleBackend:
        def __init__(self) -> None:
            self.profile = tmp_path / "profile"
            self.store = ConversationStateStore(self.profile)
            self.project_url = "https://chatgpt.com/g/g-p-demo/project"
            self.store.remember_project(self.project_url, project_name="Demo")
            self.sources: list[dict[str, object]] = [{"title": "keep-me.txt"}]
            self.add_calls: list[dict[str, object]] = []

        def state_snapshot(self) -> dict[str, object]:
            return self.store.snapshot(self.project_url)

        async def list_project_sources(self, **kwargs):
            return {"ok": True, "action": "source_list", "sources": list(self.sources)}

        async def add_project_source(self, **kwargs):
            self.add_calls.append(kwargs)
            name = str(kwargs.get("display_name") or Path(str(kwargs.get("file_path") or "")).name)
            self.sources = [item for item in self.sources if item.get("title") != name]
            self.sources.append({"title": name, "id": "src-new"})
            return {"ok": True, "action": "source_add", "status": "verified", "persistence_verified": True}

    backend = FakeLifecycleBackend()
    args = argparse.Namespace(
        artifact=str(artifact),
        version="v0.0.269",
        target_version="v0.0.269",
        config=str(config),
        repo_path=str(repo),
        plan=False,
        keep_open=False,
        hook_timeout=30.0,
        health_url=None,
        health_timeout=1.0,
        source_timeout=30.0,
        skip_service_health=True,
        json=True,
        profile_dir=str(backend.profile),
    )

    exit_code = asyncio.run(cmd_release_lifecycle(backend, args))
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["ok"] is True
    assert payload["status"] == "release_lifecycle_completed"
    assert payload["executed_phase_count"] == 6
    assert [item["phase"] for item in payload["phase_results"]] == ["doctor", "install", "test", "adopt", "policy_sync", "git_sync"]
    assert payload["install_performed"] is True
    assert payload["project_source_mutated"] is True
    assert payload["candidate_test_performed"] is True
    assert payload["adoption_performed"] is True
    assert payload["policy_sync_performed"] is True
    assert payload["artifact_registry_updated"] is True
    assert payload["state_artifact_updated"] is True
    assert payload["state_source_updated"] is True
    assert payload["git_commit_performed"] is False
    assert payload["git_push_performed"] is False
    assert payload["final_summary"]["candidate"] == artifact.name
    policy = json.loads((repo / ".promptbranch-project.json").read_text(encoding="utf-8"))
    assert policy["accepted_baseline"]["artifact_ref"] == artifact.name
    assert policy["accepted_baseline"]["artifact_version"] == "v0.0.269"


def test_release_lifecycle_stops_on_failed_guarded_phase(capsys, tmp_path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    config = repo / ".promptbranch-release.yml"
    config.write_text("""
schema_version: 1
artifact:
  prefix: chatgpt_claudecode_workflow_
  suffix: .zip
  version_file: VERSION
  policy_file: .promptbranch-project.json
install:
  preserve:
    - .git/
git:
  unsafe_paths:
    - '*.zip'
hooks:
  preflight:
    command: python -c "import sys; sys.exit(9)"
""".lstrip(), encoding="utf-8")
    (repo / "VERSION").write_text("v0.0.269\n", encoding="utf-8")
    artifact = tmp_path / "chatgpt_claudecode_workflow_v0.0.269.zip"
    _write_test_release_zip(artifact, "v0.0.269")

    class FakeLifecycleBackend:
        def __init__(self) -> None:
            self.profile = tmp_path / "profile"
            self.store = ConversationStateStore(self.profile)
            self.project_url = "https://chatgpt.com/g/g-p-demo/project"
            self.store.remember_project(self.project_url, project_name="Demo")
            self.sources: list[dict[str, object]] = []

        def state_snapshot(self) -> dict[str, object]:
            return self.store.snapshot(self.project_url)

        async def list_project_sources(self, **kwargs):
            return {"ok": True, "action": "source_list", "sources": list(self.sources)}

        async def add_project_source(self, **kwargs):
            name = str(kwargs.get("display_name") or Path(str(kwargs.get("file_path") or "")).name)
            self.sources.append({"title": name, "id": "src-new"})
            return {"ok": True, "action": "source_add", "status": "verified"}

    backend = FakeLifecycleBackend()
    args = argparse.Namespace(
        artifact=str(artifact),
        version="v0.0.269",
        target_version="v0.0.269",
        config=str(config),
        repo_path=str(repo),
        plan=False,
        keep_open=False,
        hook_timeout=30.0,
        health_url=None,
        health_timeout=1.0,
        source_timeout=30.0,
        skip_service_health=True,
        json=True,
        profile_dir=str(backend.profile),
    )

    exit_code = asyncio.run(cmd_release_lifecycle(backend, args))
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert payload["ok"] is False
    assert payload["status"] == "release_lifecycle_failed"
    assert payload["stop_reason"] == "test_failed"
    assert [item["phase"] for item in payload["phase_results"]] == ["doctor", "install", "test"]
    assert payload["adoption_performed"] is False
    assert payload["policy_sync_performed"] is False
    assert payload["git_commit_performed"] is False


def test_release_git_sync_plan_blocks_unsafe_zip_and_does_not_mutate(capsys, tmp_path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo, check=True)
    config = repo / ".promptbranch-release.yml"
    config.write_text("""
schema_version: 1
artifact:
  prefix: chatgpt_claudecode_workflow_
  suffix: .zip
  version_file: VERSION
  policy_file: .promptbranch-project.json
install:
  preserve:
    - .git/
git:
  unsafe_paths:
    - '*.zip'
    - .pb_profile/
hooks:
  release_status:
    command: pb artifact current --json
""".lstrip(), encoding="utf-8")
    artifact = tmp_path / "chatgpt_claudecode_workflow_v0.0.257.zip"
    _write_test_release_zip(artifact, "v0.0.257")
    policy = {
        "schema": "promptbranch.release.policy",
        "schema_version": 1,
        "accepted_baseline": {
            "artifact_ref": artifact.name,
            "artifact_version": "v0.0.257",
            "source_ref": artifact.name,
            "source_version": "v0.0.257",
        },
        "artifact": {"ref": artifact.name, "version": "v0.0.257"},
        "source": {"ref": artifact.name, "version": "v0.0.257"},
    }
    (repo / ".promptbranch-project.json").write_text(json.dumps(policy), encoding="utf-8")
    (repo / "local.zip").write_text("unsafe", encoding="utf-8")
    args = argparse.Namespace(
        artifact=str(artifact),
        version="v0.0.257",
        target_version="v0.0.257",
        config=str(config),
        repo_path=str(repo),
        plan=True,
        commit=False,
        push=False,
        message=None,
        json=True,
    )

    exit_code = asyncio.run(cmd_release_git_sync(None, args))
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["ok"] is True
    assert payload["status"] == "planned"
    assert payload["read_only"] is True
    assert payload["git_sync_plan"]["unsafe_dirty_paths"] == ["local.zip"]
    assert payload["commit_performed"] is False
    assert payload["push_performed"] is False


def test_release_git_sync_commit_stages_only_allowed_release_files(capsys, tmp_path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo, check=True)
    (repo / "README.md").write_text("base\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "initial"], cwd=repo, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    config = repo / ".promptbranch-release.yml"
    config.write_text("""
schema_version: 1
artifact:
  prefix: chatgpt_claudecode_workflow_
  suffix: .zip
  version_file: VERSION
  policy_file: .promptbranch-project.json
install:
  preserve:
    - .git/
git:
  unsafe_paths:
    - '*.zip'
    - .pb_profile/
hooks:
  release_status:
    command: pb artifact current --json
""".lstrip(), encoding="utf-8")
    artifact = tmp_path / "chatgpt_claudecode_workflow_v0.0.257.zip"
    _write_test_release_zip(artifact, "v0.0.257")
    policy = {
        "schema": "promptbranch.release.policy",
        "schema_version": 1,
        "accepted_baseline": {
            "artifact_ref": artifact.name,
            "artifact_version": "v0.0.257",
            "source_ref": artifact.name,
            "source_version": "v0.0.257",
        },
        "artifact": {"ref": artifact.name, "version": "v0.0.257"},
        "source": {"ref": artifact.name, "version": "v0.0.257"},
    }
    (repo / ".promptbranch-project.json").write_text(json.dumps(policy), encoding="utf-8")
    args = argparse.Namespace(
        artifact=str(artifact),
        version="v0.0.257",
        target_version="v0.0.257",
        config=str(config),
        repo_path=str(repo),
        plan=False,
        commit=True,
        push=False,
        message="Release test",
        json=True,
    )

    exit_code = asyncio.run(cmd_release_git_sync(None, args))
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["ok"] is True
    assert payload["status"] == "git_sync_committed"
    assert payload["commit_performed"] is True
    assert payload["push_performed"] is False
    log = subprocess.run(["git", "log", "-1", "--pretty=%s"], cwd=repo, text=True, stdout=subprocess.PIPE, check=True)
    assert log.stdout.strip() == "Release test"
    status = subprocess.run(["git", "status", "--porcelain=v1"], cwd=repo, text=True, stdout=subprocess.PIPE, check=True)
    assert status.stdout == ""

def test_source_upload_verification_allows_expected_source_replacement_but_rejects_collateral_removal() -> None:
    replacement = _verify_project_source_upload_change(
        before_result={"ok": True, "action": "source_list", "sources": [{"title": "chatgpt_claudecode_workflow_v0.0.257.zip"}, {"title": "keep-me.txt"}]},
        after_result={"ok": True, "action": "source_list", "sources": [{"id": "new-id", "title": "chatgpt_claudecode_workflow_v0.0.257.zip"}, {"title": "keep-me.txt"}]},
        upload_result={"ok": True, "action": "source_add", "status": "verified", "overwritten": True},
        expected_filename="chatgpt_claudecode_workflow_v0.0.257.zip",
    )

    assert replacement["ok"] is True
    assert replacement["checks"]["expected_source_replaced"] is True
    assert replacement["checks"]["collateral_sources_removed"] is False
    assert replacement["expected_removed_source_keys"] == ["chatgpt_claudecode_workflow_v0.0.257.zip"]
    assert replacement["collateral_removed_source_keys"] == []

    collateral = _verify_project_source_upload_change(
        before_result={"ok": True, "action": "source_list", "sources": [{"title": "chatgpt_claudecode_workflow_v0.0.257.zip"}, {"title": "keep-me.txt"}]},
        after_result={"ok": True, "action": "source_list", "sources": [{"id": "new-id", "title": "chatgpt_claudecode_workflow_v0.0.257.zip"}]},
        upload_result={"ok": True, "action": "source_add", "status": "verified", "overwritten": True},
        expected_filename="chatgpt_claudecode_workflow_v0.0.257.zip",
    )

    assert collateral["ok"] is False
    assert collateral["checks"]["collateral_sources_removed"] is True
    assert collateral["collateral_removed_source_keys"] == ["keep-me.txt"]

def test_artifact_mvp_status_reports_completion_after_candidate_acceptance(capsys, tmp_path) -> None:
    filename = "chatgpt_claudecode_workflow_v0.0.269.zip"
    repo = tmp_path / "repo"
    repo.mkdir()
    zip_path = repo / filename
    _write_test_release_zip(zip_path, "v0.0.269")
    profile = tmp_path / "profile"
    _write_candidate_registry(profile, filename=filename, zip_path=zip_path, version="v0.0.269", tested=True)
    backend = _FakeArtifactAdoptBackend(profile, "https://chatgpt.com/g/g-p-demo/project", [])
    accept_args = argparse.Namespace(
        artifact=filename,
        version=None,
        repo_path=str(repo),
        from_project_source=False,
        run_release_control=False,
        adopt_if_green=True,
        test_timeout=3600.0,
        release_log_keep=12,
        skip_docker_logs=True,
        prune_release_logs=True,
        keep_open=False,
        json=True,
        profile_dir=str(profile),
    )
    assert asyncio.run(cmd_artifact_accept_candidate(backend, accept_args)) == 0
    capsys.readouterr()

    status_args = argparse.Namespace(
        artifact=None,
        version="v0.0.269",
        repo_path=str(repo),
        json=True,
        profile_dir=str(profile),
    )
    exit_code = asyncio.run(cmd_artifact_mvp_status(backend, status_args))
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["ok"] is True
    assert payload["mvp_complete"] is True
    assert payload["status"] == "candidate_mvp_complete"
    assert payload["operator_verdict"] == "candidate_mvp_complete"
    assert payload["severity"] == "ok"
    assert payload["lifecycle_classification"]["candidate_verdict"] == "candidate_mvp_complete"
    assert payload["lifecycle_classification"]["versions"]["accepted_candidate_version"] == "v0.0.269"
    assert payload["mvp_completion"]["accepted_candidate"]["artifact_version"] == "v0.0.269"
    assert payload["candidate_next"]["recommended_next_command"]["kind"] == "candidate_already_accepted"
    assert payload["commands"]["inspect_candidates"] == "pb artifact candidate-status --all --json"
    assert payload["mutating_actions_executed"] is False
    assert payload["remediation_plan"]["kind"] == "candidate_mvp_complete"
    assert payload["remediation_plan"]["safe_action"] == "continue_from_adopted_baseline"
    assert payload["remediation_plan"]["read_only"] is True
    assert all(item["mutates_state"] is False for item in payload["next_safe_actions"])

def test_artifact_candidate_run_no_artifact_protocol_reply_blocks_intake_precondition(monkeypatch, capsys, tmp_path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    profile = tmp_path / "profile"
    _write_no_artifact_protocol_run(profile)
    backend = _FakeArtifactAdoptBackend(profile, "https://chatgpt.com/g/g-p-demo/project", [])
    calls: list[list[str]] = []

    def fake_run(command, cwd, stdout, stderr, text, timeout, check):
        calls.append(command)
        raise AssertionError(f"candidate-run must not execute intake for no_artifact protocol replies: {command!r}")

    monkeypatch.setattr("promptbranch_cli.subprocess.run", fake_run)
    args = argparse.Namespace(
        artifact=None,
        version=None,
        repo_path=str(repo),
        execute_next=False,
        execute_until_blocked=True,
        max_steps=4,
        require_complete=True,
        step_timeout=123.0,
        json=True,
        profile_dir=str(profile),
    )

    exit_code = asyncio.run(cmd_artifact_candidate_run(backend, args))
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert calls == []
    assert payload["ok"] is False
    assert payload["status"] == "candidate_run_cycle_precondition_failed"
    assert payload["stopped_reason"] == "no_artifact_candidate"
    assert payload["cycle_step_count"] == 1
    assert payload["cycle_steps"][0]["kind"] == "no_artifact_candidate"
    assert payload["cycle_steps"][0]["executed"] is False
    assert payload["mutating_actions_executed"] is False
    assert payload["download_performed"] is False
    assert payload["verification_performed"] is False
    assert payload["migration_performed"] is False
    assert payload["adoption_performed"] is False
    assert payload["mvp_completion"]["status"] == "candidate_mvp_no_artifact_candidate"
    precondition = payload["mvp_completion"]["candidate_intake_precondition"]
    assert precondition["blocks_intake"] is True
    assert precondition["reply_status"] == "no_artifact"
    assert precondition["artifact_candidate_count"] == 0
    assert payload["recommended_next_command"]["kind"] == "no_artifact_candidate"
    assert payload["safe_command"] is None



def test_artifact_candidate_run_require_real_candidate_rejects_no_artifact_reply(monkeypatch, capsys, tmp_path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    profile = tmp_path / "profile"
    _write_no_artifact_protocol_run(profile)
    backend = _FakeArtifactAdoptBackend(profile, "https://chatgpt.com/g/g-p-demo/project", [])
    calls: list[list[str]] = []

    def fake_run(command, cwd, stdout, stderr, text, timeout, check):
        calls.append(command)
        raise AssertionError(f"candidate-run must not execute any step when real candidate is required and no artifact exists: {command!r}")

    monkeypatch.setattr("promptbranch_cli.subprocess.run", fake_run)
    args = argparse.Namespace(
        artifact=None,
        version=None,
        repo_path=str(repo),
        execute_next=False,
        execute_until_blocked=True,
        max_steps=4,
        require_complete=True,
        require_real_candidate=True,
        step_timeout=123.0,
        json=True,
        profile_dir=str(profile),
    )

    exit_code = asyncio.run(cmd_artifact_candidate_run(backend, args))
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert calls == []
    assert payload["ok"] is False
    assert payload["status"] == "candidate_run_real_candidate_required"
    assert payload["require_real_candidate"] is True
    assert payload["recommended_next_command"]["kind"] == "no_artifact_candidate"
    assert payload["safe_command"] is None
    assert payload["mutating_actions_executed"] is False
    assert payload["download_performed"] is False
    assert payload["verification_performed"] is False
    assert payload["migration_performed"] is False
    assert payload["adoption_performed"] is False

def test_artifact_candidate_run_require_real_candidate_accepts_scoped_adopted_current(capsys, tmp_path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    profile = tmp_path / "profile"
    _write_no_artifact_protocol_run(profile)
    project_url = "https://chatgpt.com/g/g-p-demo/project"
    backend = _FakeArtifactAdoptBackend(profile, project_url, [])
    artifact_name = "chatgpt_claudecode_workflow_v0.0.269.zip"
    backend.store.remember_artifact(
        artifact_ref=artifact_name,
        artifact_version="v0.0.269",
        source_ref=artifact_name,
        source_version="v0.0.269",
        project_url=project_url,
    )
    registry_path = profile / "promptbranch_artifacts.json"
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(json.dumps({
        "schema_version": 1,
        "artifacts": [{
            "path": str(repo / artifact_name),
            "filename": artifact_name,
            "kind": "adopted_release",
            "version": "v0.0.269",
            "sha256": "demo",
            "size_bytes": 1,
            "file_count": 1,
            "created_at": "2026-05-23T00:00:00Z",
            "source_ref": artifact_name,
            "project_url": project_url,
        }],
    }), encoding="utf-8")
    args = argparse.Namespace(
        artifact=None,
        version="v0.0.269",
        repo_path=str(repo),
        execute_next=False,
        execute_until_blocked=True,
        max_steps=4,
        require_complete=True,
        require_real_candidate=True,
        step_timeout=123.0,
        json=True,
        profile_dir=str(profile),
    )

    exit_code = asyncio.run(cmd_artifact_candidate_run(backend, args))
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["ok"] is True
    assert payload["status"] == "candidate_run_cycle_completed"
    assert payload["stopped_reason"] == "candidate_already_accepted"
    assert payload["mvp_complete"] is True
    assert payload["mvp_completion"]["proof_source"] == "adopted_current"
    assert payload["mvp_completion"]["recommended_next_command"]["kind"] == "continue_from_adopted_baseline"
    assert payload["selected_candidate"]["proof_source"] == "adopted_current"
    assert payload["mutating_actions_executed"] is False


def test_artifact_candidate_next_no_artifact_protocol_reply_reports_precondition(capsys, tmp_path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    profile = tmp_path / "profile"
    _write_no_artifact_protocol_run(profile)
    backend = _FakeArtifactAdoptBackend(profile, "https://chatgpt.com/g/g-p-demo/project", [])
    args = argparse.Namespace(
        artifact=None,
        version=None,
        repo_path=str(repo),
        all=False,
        json=True,
        profile_dir=str(profile),
    )

    exit_code = asyncio.run(cmd_artifact_candidate_next(backend, args))
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["status"] == "candidate_next_no_artifact_candidate"
    assert payload["candidate_count"] == 0
    assert payload["recommended_next_command"]["kind"] == "no_artifact_candidate"
    assert payload["recommended_next_command"]["command"] is None
    assert payload["candidate_intake_precondition"]["status"] == "candidate_mvp_no_artifact_candidate"
    assert payload["candidate_intake_precondition"]["blocks_intake"] is True
    assert payload["mutating_actions_executed"] is False


def test_artifact_candidate_run_require_complete_fails_when_lifecycle_incomplete(capsys, tmp_path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    profile = tmp_path / "profile"
    backend = _FakeArtifactAdoptBackend(profile, "https://chatgpt.com/g/g-p-demo/project", [])
    args = argparse.Namespace(
        artifact=None,
        version=None,
        repo_path=str(repo),
        execute_next=False,
        execute_until_blocked=False,
        max_steps=4,
        require_complete=True,
        step_timeout=123.0,
        json=True,
        profile_dir=str(profile),
    )

    exit_code = asyncio.run(cmd_artifact_candidate_run(backend, args))
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert payload["ok"] is False
    assert payload["status"] == "candidate_run_mvp_incomplete"
    assert payload["mvp_complete"] is False
    assert payload["mvp_completion"]["status"] == "candidate_mvp_intake_pending"
    assert payload["mvp_completion"]["checks"]["accepted_candidate_present"] is False
    assert payload["mutating_actions_executed"] is False


def test_artifact_candidate_run_require_complete_passes_after_acceptance(capsys, tmp_path) -> None:
    filename = "chatgpt_claudecode_workflow_v0.0.236.zip"
    repo = tmp_path / "repo"
    repo.mkdir()
    zip_path = repo / filename
    _write_test_release_zip(zip_path, "v0.0.236")
    profile = tmp_path / "profile"
    _write_candidate_registry(profile, filename=filename, zip_path=zip_path, version="v0.0.236", tested=True)
    backend = _FakeArtifactAdoptBackend(profile, "https://chatgpt.com/g/g-p-demo/project", [])
    accept_args = argparse.Namespace(
        artifact=filename,
        version=None,
        repo_path=str(repo),
        from_project_source=False,
        run_release_control=False,
        adopt_if_green=True,
        test_timeout=3600.0,
        release_log_keep=12,
        skip_docker_logs=True,
        prune_release_logs=True,
        keep_open=False,
        json=True,
        profile_dir=str(profile),
    )
    assert asyncio.run(cmd_artifact_accept_candidate(backend, accept_args)) == 0
    capsys.readouterr()

    run_args = argparse.Namespace(
        artifact=None,
        version="v0.0.236",
        repo_path=str(repo),
        execute_next=False,
        execute_until_blocked=False,
        max_steps=4,
        require_complete=True,
        step_timeout=123.0,
        json=True,
        profile_dir=str(profile),
    )

    exit_code = asyncio.run(cmd_artifact_candidate_run(backend, run_args))
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["ok"] is True
    assert payload["mvp_complete"] is True
    assert payload["mvp_completion"]["status"] == "candidate_mvp_complete"
    assert payload["mvp_completion"]["accepted_candidate"]["artifact_version"] == "v0.0.236"
    assert payload["mvp_completion"]["checks"]["accepted_candidate_matches_current"] is True
    assert payload["mutating_actions_executed"] is False

def test_artifact_candidate_run_rejects_two_execute_modes(capsys, tmp_path) -> None:
    filename = "chatgpt_claudecode_workflow_v0.0.236.zip"
    repo = tmp_path / "repo"
    repo.mkdir()
    zip_path = repo / filename
    _write_test_release_zip(zip_path, "v0.0.236")
    profile = tmp_path / "profile"
    _write_candidate_registry(profile, filename=filename, zip_path=zip_path, version="v0.0.236", tested=True)
    backend = _FakeArtifactAdoptBackend(profile, "https://chatgpt.com/g/g-p-demo/project", [])
    args = argparse.Namespace(
        artifact=None,
        version="v0.0.236",
        repo_path=str(repo),
        execute_next=True,
        execute_until_blocked=True,
        max_steps=4,
        step_timeout=123.0,
        json=True,
        profile_dir=str(profile),
    )

    exit_code = asyncio.run(cmd_artifact_candidate_run(backend, args))
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 2
    assert payload["ok"] is False
    assert payload["status"] == "candidate_run_invalid_mode"
    assert payload["mutating_actions_executed"] is False

def test_artifact_accept_candidate_preflight_requires_tested_candidate_and_no_adoption(capsys, tmp_path) -> None:
    filename = "chatgpt_claudecode_workflow_v0.0.225.zip"
    repo = tmp_path / "repo"
    repo.mkdir()
    zip_path = repo / filename
    _write_test_release_zip(zip_path, "v0.0.225")
    script = repo / "chatgpt_claudecode_workflow_release_control.sh"
    script.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    script.chmod(0o755)
    profile = tmp_path / "profile"
    _write_candidate_registry(profile, filename=filename, zip_path=zip_path, version="v0.0.225", tested=True)
    backend = _FakeArtifactAdoptBackend(profile, "https://chatgpt.com/g/g-p-demo/project", [{"title": filename, "id": "src_1"}])
    args = argparse.Namespace(
        artifact=filename,
        version=None,
        repo_path=str(repo),
        from_project_source=False,
        run_release_control=False,
        adopt_if_green=False,
        test_timeout=3600.0,
        release_log_keep=12,
        skip_docker_logs=True,
        prune_release_logs=True,
        keep_open=False,
        json=True,
        profile_dir=str(profile),
    )

    exit_code = asyncio.run(cmd_artifact_accept_candidate(backend, args))
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["ok"] is True
    assert payload["status"] == "candidate_acceptance_preflight_verified"
    assert payload["source_verified"] is False
    assert payload["candidate_test_gate"]["ok"] is True
    assert payload["checks"]["candidate_test_passed"] is True
    assert payload["project_source_mutated"] is False
    assert payload["release_control_performed"] is False
    assert payload["adoption_performed"] is False
    assert payload["artifact_registry_updated"] is False
    assert not (profile / "promptbranch_artifacts.json").exists()


def test_artifact_accept_candidate_rejects_untested_candidate(capsys, tmp_path) -> None:
    filename = "chatgpt_claudecode_workflow_v0.0.225.zip"
    repo = tmp_path / "repo"
    repo.mkdir()
    zip_path = repo / filename
    _write_test_release_zip(zip_path, "v0.0.225")
    profile = tmp_path / "profile"
    _write_candidate_registry(profile, filename=filename, zip_path=zip_path, version="v0.0.225")
    backend = _FakeArtifactAdoptBackend(profile, "https://chatgpt.com/g/g-p-demo/project", [{"title": filename, "id": "src_1"}])
    args = argparse.Namespace(
        artifact=filename,
        version=None,
        repo_path=str(repo),
        from_project_source=False,
        run_release_control=False,
        adopt_if_green=True,
        test_timeout=3600.0,
        release_log_keep=12,
        skip_docker_logs=True,
        prune_release_logs=True,
        keep_open=False,
        json=True,
        profile_dir=str(profile),
    )

    exit_code = asyncio.run(cmd_artifact_accept_candidate(backend, args))
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert payload["status"] == "candidate_not_tested"
    assert payload["candidate_test_gate"]["ok"] is False
    assert payload["adoption_performed"] is False
    assert not (profile / "promptbranch_artifacts.json").exists()


def test_artifact_accept_candidate_adopts_pretested_candidate_without_release_control(monkeypatch, capsys, tmp_path) -> None:
    filename = "chatgpt_claudecode_workflow_v0.0.225.zip"
    repo = tmp_path / "repo"
    repo.mkdir()
    zip_path = repo / filename
    _write_test_release_zip(zip_path, "v0.0.225")
    script = repo / "chatgpt_claudecode_workflow_release_control.sh"
    script.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    script.chmod(0o755)
    profile = tmp_path / "profile"
    _write_candidate_registry(profile, filename=filename, zip_path=zip_path, version="v0.0.225", tested=True)
    project_url = "https://chatgpt.com/g/g-p-demo/project"
    backend = _FakeArtifactAdoptBackend(profile, project_url, [{"title": filename, "id": "src_1"}])

    def fake_run(command, cwd, stdout, stderr, text, timeout, check):
        raise AssertionError("accept-candidate must not run release-control in v0.0.230")

    monkeypatch.setattr("promptbranch_cli.subprocess.run", fake_run)
    args = argparse.Namespace(
        artifact=None,
        version="v0.0.225",
        repo_path=str(repo),
        from_project_source=False,
        run_release_control=False,
        adopt_if_green=True,
        test_timeout=3600.0,
        release_log_keep=12,
        skip_docker_logs=True,
        prune_release_logs=True,
        keep_open=False,
        json=True,
        profile_dir=str(profile),
    )

    exit_code = asyncio.run(cmd_artifact_accept_candidate(backend, args))
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["ok"] is True
    assert payload["status"] == "accepted_candidate"
    assert payload["adoption_performed"] is True
    assert payload["release_control_performed"] is False
    assert payload["source_verified"] is False
    assert payload["project_source_mutated"] is False
    assert payload["artifact_current"]["state"]["artifact_ref"] == filename
    candidate_registry = json.loads((profile / "artifact_candidates.json").read_text(encoding="utf-8"))
    assert candidate_registry["candidates"][0]["status"] == "accepted_candidate"
    assert candidate_registry["candidates"][0]["accepted"] is True


def test_artifact_accept_candidate_rejects_release_control_runner(capsys, tmp_path) -> None:
    filename = "chatgpt_claudecode_workflow_v0.0.225.zip"
    repo = tmp_path / "repo"
    repo.mkdir()
    zip_path = repo / filename
    _write_test_release_zip(zip_path, "v0.0.225")
    profile = tmp_path / "profile"
    _write_candidate_registry(profile, filename=filename, zip_path=zip_path, version="v0.0.225", tested=True)
    backend = _FakeArtifactAdoptBackend(profile, "https://chatgpt.com/g/g-p-demo/project", [{"title": filename, "id": "src_1"}])
    args = argparse.Namespace(
        artifact=filename,
        version=None,
        repo_path=str(repo),
        from_project_source=False,
        run_release_control=True,
        adopt_if_green=True,
        test_timeout=3600.0,
        release_log_keep=12,
        skip_docker_logs=True,
        prune_release_logs=True,
        keep_open=False,
        json=True,
        profile_dir=str(profile),
    )

    exit_code = asyncio.run(cmd_artifact_accept_candidate(backend, args))
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 2
    assert payload["status"] == "candidate_acceptance_runner_not_allowed"
    assert payload["adoption_performed"] is False
    assert not (profile / "promptbranch_artifacts.json").exists()


def test_artifact_accept_candidate_rejects_sha_mismatch_before_adoption(capsys, tmp_path) -> None:
    filename = "chatgpt_claudecode_workflow_v0.0.225.zip"
    repo = tmp_path / "repo"
    repo.mkdir()
    zip_path = repo / filename
    _write_test_release_zip(zip_path, "v0.0.225")
    profile = tmp_path / "profile"
    _write_candidate_registry(profile, filename=filename, zip_path=zip_path, version="v0.0.225", tested=True)
    registry = json.loads((profile / "artifact_candidates.json").read_text(encoding="utf-8"))
    registry["candidates"][0]["sha256"] = "0" * 64
    (profile / "artifact_candidates.json").write_text(json.dumps(registry), encoding="utf-8")
    backend = _FakeArtifactAdoptBackend(profile, "https://chatgpt.com/g/g-p-demo/project", [{"title": filename, "id": "src_1"}])
    args = argparse.Namespace(
        artifact=filename,
        version=None,
        repo_path=str(repo),
        from_project_source=False,
        run_release_control=False,
        adopt_if_green=True,
        test_timeout=3600.0,
        release_log_keep=12,
        skip_docker_logs=True,
        prune_release_logs=True,
        keep_open=False,
        json=True,
        profile_dir=str(profile),
    )

    exit_code = asyncio.run(cmd_artifact_accept_candidate(backend, args))
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert payload["status"] == "candidate_sha_mismatch"
    assert payload["adoption_performed"] is False
    assert not (profile / "promptbranch_artifacts.json").exists()


def test_phase3_src_sync_dry_run_does_not_package_or_record_artifact(monkeypatch, capsys, tmp_path) -> None:
    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "VERSION").write_text("v1.2.3\n", encoding="utf-8")
    (repo / "main.py").write_text("print('ok')\n", encoding="utf-8")
    profile = tmp_path / "profile"

    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(profile),
        "src", "sync", str(repo), "--dry-run", "--json",
    ])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["status"] == "planned"
    assert payload["dry_run"] is True
    assert payload["mutating_actions_executed"] is False
    assert payload["artifact"]["filename"] == "repo_v1.2.3.zip"
    assert payload["included_count"] == 2
    assert payload["prechecks"]["repo_snapshot_plan_built"] is True
    assert payload["transaction_id"]
    assert payload["before_snapshot"]["repo"]["included_count"] == 2
    assert payload["before_snapshot"]["artifact_registry"]["exists"] is False
    assert payload["collateral_checks"]["would_overwrite_artifact_file"] is False
    assert payload["transaction_plan"]["verification_plan"]["after"]
    assert not Path(payload["artifact"]["path"]).exists()
    assert not (profile / "promptbranch_artifacts.json").exists()




def test_phase3_src_sync_requires_explicit_mode_before_mutation(monkeypatch, capsys, tmp_path) -> None:
    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "VERSION").write_text("v1.2.3\n", encoding="utf-8")
    (repo / "main.py").write_text("print('ok')\n", encoding="utf-8")
    profile = tmp_path / "profile"

    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(profile),
        "src", "sync", str(repo), "--json",
    ])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 2
    assert payload["status"] == "sync_mode_required"
    assert payload["mutating_actions_executed"] is False
    assert payload["project_source_mutated"] is False
    assert not (profile / "artifacts" / "repo_v1.2.3.zip").exists()
    assert "--no-upload" in payload["next_commands"]["local_package"]
    assert "--upload" in payload["next_commands"]["upload_preflight"]


def test_phase3_src_sync_upload_requires_confirmation(monkeypatch, capsys, tmp_path) -> None:
    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "VERSION").write_text("v1.2.3\n", encoding="utf-8")
    (repo / "main.py").write_text("print('ok')\n", encoding="utf-8")
    profile = tmp_path / "profile"

    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(profile),
        "src", "sync", str(repo), "--upload", "--json",
    ])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 2
    assert payload["status"] == "upload_confirmation_required"
    assert payload["upload_requested"] is True
    assert payload["confirm_upload"] is False
    assert payload["mutating_actions_executed"] is False
    assert payload["project_source_mutated"] is False
    assert payload["confirmation"]["required"] is True
    assert "--confirm-upload" in payload["confirmation"]["confirm_command"]
    assert not (profile / "artifacts" / "repo_v1.2.3.zip").exists()



def test_phase3_src_sync_confirm_upload_requires_transaction_id(monkeypatch, capsys, tmp_path) -> None:
    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "VERSION").write_text("v1.2.3\n", encoding="utf-8")
    (repo / "main.py").write_text("print('ok')\n", encoding="utf-8")
    profile = tmp_path / "profile"

    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(profile),
        "src", "sync", str(repo), "--upload", "--confirm-upload", "--json",
    ])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 2
    assert payload["status"] == "upload_transaction_id_required"
    assert payload["mutating_actions_executed"] is False
    assert payload["project_source_mutated"] is False
    assert payload["transaction_id"]
    assert "--confirm-transaction-id" in payload["confirmation"]["confirm_command"]
    assert not (profile / "artifacts" / "repo_v1.2.3.zip").exists()


def test_phase3_src_sync_confirm_upload_rejects_transaction_id_mismatch(monkeypatch, capsys, tmp_path) -> None:
    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "VERSION").write_text("v1.2.3\n", encoding="utf-8")
    (repo / "main.py").write_text("print('ok')\n", encoding="utf-8")
    profile = tmp_path / "profile"

    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(profile),
        "src", "sync", str(repo), "--upload", "--confirm-upload", "--confirm-transaction-id", "bad-token", "--json",
    ])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 2
    assert payload["status"] == "upload_transaction_id_mismatch"
    assert payload["provided_transaction_id"] == "bad-token"
    assert payload["mutating_actions_executed"] is False
    assert payload["project_source_mutated"] is False
    assert not (profile / "artifacts" / "repo_v1.2.3.zip").exists()




def test_phase3_src_sync_upload_transaction_id_changes_when_repo_content_changes(monkeypatch, capsys, tmp_path) -> None:
    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "VERSION").write_text("v1.2.3\n", encoding="utf-8")
    source = repo / "main.py"
    source.write_text("print('before')\n", encoding="utf-8")
    profile = tmp_path / "profile"
    project_url = "https://chatgpt.com/g/g-p-demo/project"

    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    first_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(profile),
        "--project-url", project_url,
        "src", "sync", str(repo), "--upload", "--json",
    ])
    first = json.loads(capsys.readouterr().out)
    assert first_code == 2
    first_transaction_id = first["transaction_id"]
    first_fingerprint = first["preflight"]["before_snapshot"]["repo"]["content_fingerprint"]["sha256"]

    source.write_text("print('after')\n", encoding="utf-8")

    second_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(profile),
        "--project-url", project_url,
        "src", "sync", str(repo), "--upload", "--json",
    ])
    second = json.loads(capsys.readouterr().out)
    assert second_code == 2
    assert second["transaction_id"] != first_transaction_id
    assert second["preflight"]["before_snapshot"]["repo"]["content_fingerprint"]["sha256"] != first_fingerprint

    stale_confirm_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(profile),
        "--project-url", project_url,
        "src", "sync", str(repo), "--upload", "--confirm-upload",
        "--confirm-transaction-id", first_transaction_id, "--json",
    ])
    stale = json.loads(capsys.readouterr().out)
    assert stale_confirm_code == 2
    assert stale["status"] == "upload_transaction_id_mismatch"
    assert stale["provided_transaction_id"] == first_transaction_id
    assert stale["transaction_id"] == second["transaction_id"]
    assert stale["mutating_actions_executed"] is False
    assert stale["project_source_mutated"] is False
    assert not (profile / "artifacts" / "repo_v1.2.3.zip").exists()

def test_phase3_src_sync_confirm_upload_with_transaction_id_executes_guarded_upload(monkeypatch, capsys, tmp_path) -> None:
    calls: list[dict[str, object]] = []

    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

        def list_project_sources(self, **kwargs):
            if calls:
                return {"ok": True, "action": "source_list", "sources": [{"title": "repo_v1.2.3.zip"}]}
            return {"ok": True, "action": "source_list", "sources": []}

        def add_project_source(self, **kwargs):
            calls.append(kwargs)
            return {"ok": True, "action": "source_add", "status": "verified"}

    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "VERSION").write_text("v1.2.3\n", encoding="utf-8")
    (repo / "main.py").write_text("print('ok')\n", encoding="utf-8")
    profile = tmp_path / "profile"
    project_url = "https://chatgpt.com/g/g-p-demo/project"

    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    preflight_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(profile),
        "--project-url", project_url,
        "src", "sync", str(repo), "--upload", "--json",
    ])
    preflight_payload = json.loads(capsys.readouterr().out)
    assert preflight_code == 2
    transaction_id = preflight_payload["transaction_id"]

    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(profile),
        "--project-url", project_url,
        "src", "sync", str(repo), "--upload", "--confirm-upload", "--confirm-transaction-id", transaction_id, "--json",
    ])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["status"] == "uploaded"
    assert payload["project_source_mutated"] is True
    assert payload["transaction_id"] == transaction_id
    assert calls[0]["source_kind"] == "file"
    assert calls[0]["display_name"] == "repo_v1.2.3.zip"




def test_phase3_source_upload_verification_marks_service_error_with_expected_source_as_ambiguous() -> None:
    payload = _verify_project_source_upload_change(
        before_result={"ok": True, "action": "source_list", "sources": []},
        after_result={"ok": True, "action": "source_list", "sources": [{"title": "repo_v1.2.8.zip"}]},
        upload_result={"ok": False, "action": "source_add", "status": "service_error", "error": "504 gateway timeout"},
        expected_filename="repo_v1.2.8.zip",
    )

    assert payload["ok"] is False
    assert payload["status"] == "upload_ambiguous"
    assert payload["operator_review_required"] is True
    assert payload["ambiguity_reason"] == "upload_result_failed_but_expected_source_present_after"
    assert payload["checks"]["upload_result_ok"] is False
    assert payload["checks"]["expected_source_present_after"] is True
    assert payload["collateral_change_detected"] is False

def test_phase3_src_sync_confirm_upload_failure_does_not_advance_registry_or_state(monkeypatch, capsys, tmp_path) -> None:
    calls: list[dict[str, object]] = []

    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

        def list_project_sources(self, **kwargs):
            return {"ok": True, "action": "source_list", "sources": []}

        def add_project_source(self, **kwargs):
            calls.append(kwargs)
            return {"ok": False, "action": "source_add", "status": "verification_failed"}

    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "VERSION").write_text("v1.2.4\n", encoding="utf-8")
    (repo / "main.py").write_text("print('ok')\n", encoding="utf-8")
    profile = tmp_path / "profile"
    project_url = "https://chatgpt.com/g/g-p-demo/project"

    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    preflight_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(profile),
        "--project-url", project_url,
        "src", "sync", str(repo), "--upload", "--json",
    ])
    preflight_payload = json.loads(capsys.readouterr().out)
    assert preflight_code == 2
    transaction_id = preflight_payload["transaction_id"]

    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(profile),
        "--project-url", project_url,
        "src", "sync", str(repo), "--upload", "--confirm-upload", "--confirm-transaction-id", transaction_id, "--json",
    ])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert payload["status"] == "upload_failed"
    assert payload["project_source_mutated"] is False
    assert payload["artifact_registry_updated"] is False
    assert payload["state_source_updated"] is False
    assert payload["upload_verification"]["registry_update_deferred_until_upload_verified"] is True
    assert Path(payload["artifact"]["path"]).is_file()
    assert not (profile / "promptbranch_artifacts.json").exists()
    assert calls[0]["display_name"] == "repo_v1.2.4.zip"


def test_phase3_src_sync_confirm_upload_requires_after_source_list_match(monkeypatch, capsys, tmp_path) -> None:
    calls: list[dict[str, object]] = []

    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

        def list_project_sources(self, **kwargs):
            return {"ok": True, "action": "source_list", "sources": []}

        def add_project_source(self, **kwargs):
            calls.append(kwargs)
            return {"ok": True, "action": "source_add", "status": "verified"}

    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "VERSION").write_text("v1.2.5\n", encoding="utf-8")
    (repo / "main.py").write_text("print('ok')\n", encoding="utf-8")
    profile = tmp_path / "profile"
    project_url = "https://chatgpt.com/g/g-p-demo/project"

    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    preflight_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(profile),
        "--project-url", project_url,
        "src", "sync", str(repo), "--upload", "--json",
    ])
    preflight_payload = json.loads(capsys.readouterr().out)
    assert preflight_code == 2
    transaction_id = preflight_payload["transaction_id"]

    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(profile),
        "--project-url", project_url,
        "src", "sync", str(repo), "--upload", "--confirm-upload", "--confirm-transaction-id", transaction_id, "--json",
    ])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert payload["status"] == "upload_failed"
    assert payload["upload_verification"]["source_list_verification"]["status"] == "source_upload_not_verified"
    assert payload["upload_verification"]["source_list_verification"]["checks"]["expected_source_present_after"] is False
    assert payload["artifact_registry_updated"] is False
    assert payload["state_source_updated"] is False
    assert calls[0]["display_name"] == "repo_v1.2.5.zip"


def test_phase3_src_sync_confirm_upload_rejects_collateral_source_removal(monkeypatch, capsys, tmp_path) -> None:
    calls: list[dict[str, object]] = []

    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

        def list_project_sources(self, **kwargs):
            if calls:
                return {"ok": True, "action": "source_list", "sources": [{"title": "repo_v1.2.6.zip"}]}
            return {"ok": True, "action": "source_list", "sources": [{"title": "keep-me.txt"}]}

        def add_project_source(self, **kwargs):
            calls.append(kwargs)
            return {"ok": True, "action": "source_add", "status": "verified"}

    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "VERSION").write_text("v1.2.6\n", encoding="utf-8")
    (repo / "main.py").write_text("print('ok')\n", encoding="utf-8")
    profile = tmp_path / "profile"
    project_url = "https://chatgpt.com/g/g-p-demo/project"

    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    preflight_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(profile),
        "--project-url", project_url,
        "src", "sync", str(repo), "--upload", "--json",
    ])
    preflight_payload = json.loads(capsys.readouterr().out)
    assert preflight_code == 2
    transaction_id = preflight_payload["transaction_id"]

    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(profile),
        "--project-url", project_url,
        "src", "sync", str(repo), "--upload", "--confirm-upload", "--confirm-transaction-id", transaction_id, "--json",
    ])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    verification = payload["upload_verification"]["source_list_verification"]
    assert verification["checks"]["expected_source_present_after"] is True
    assert verification["checks"]["collateral_sources_removed"] is True
    assert verification["collateral_change_detected"] is True
    assert payload["artifact_registry_updated"] is False
    assert payload["state_source_updated"] is False

def test_phase3_src_sync_rejects_conflicting_upload_modes(monkeypatch, capsys, tmp_path) -> None:
    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "VERSION").write_text("v1.2.3\n", encoding="utf-8")
    profile = tmp_path / "profile"

    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(profile),
        "src", "sync", str(repo), "--no-upload", "--upload", "--json",
    ])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 2
    assert payload["status"] == "conflicting_sync_modes"
    assert payload["mutating_actions_executed"] is False

def test_phase3_src_sync_dry_run_reports_artifact_collisions(monkeypatch, capsys, tmp_path) -> None:
    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "VERSION").write_text("v1.2.3\n", encoding="utf-8")
    (repo / "main.py").write_text("print('ok')\n", encoding="utf-8")
    profile = tmp_path / "profile"
    artifact_dir = profile / "artifacts"
    artifact_dir.mkdir(parents=True)
    existing = artifact_dir / "repo_v1.2.3.zip"
    existing.write_bytes(b"old")

    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(profile),
        "src", "sync", str(repo), "--dry-run", "--json",
    ])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["status"] == "planned"
    assert payload["collateral_checks"]["output_path_exists"] is True
    assert payload["collateral_checks"]["would_overwrite_artifact_file"] is True
    assert existing.read_bytes() == b"old"

def test_phase3_src_sync_no_upload_packages_and_records_artifact(monkeypatch, capsys, tmp_path) -> None:
    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "VERSION").write_text("v1.0.0\n", encoding="utf-8")
    (repo / "main.py").write_text("print('ok')\n", encoding="utf-8")

    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(tmp_path / "profile"),
        "src", "sync", str(repo), "--no-upload", "--json",
    ])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["status"] == "verified_packaged"
    assert payload["no_upload"] is True
    assert payload["project_source_mutated"] is False
    assert payload["artifact"]["filename"] == "repo_v1.0.0.zip"
    assert Path(payload["artifact"]["path"]).is_file()
    assert payload["local_verification"]["ok"] is True
    assert payload["local_verification"]["checks"]["zip_exists"] is True
    assert payload["local_verification"]["checks"]["registry_contains_artifact"] is True
    assert payload["local_verification"]["checks"]["project_source_mutated"] is False



def test_phase3_src_sync_no_upload_refuses_collision_without_force(monkeypatch, capsys, tmp_path) -> None:
    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "VERSION").write_text("v1.0.0\n", encoding="utf-8")
    (repo / "main.py").write_text("print('ok')\n", encoding="utf-8")
    profile = tmp_path / "profile"
    artifact_dir = profile / "artifacts"
    artifact_dir.mkdir(parents=True)
    existing = artifact_dir / "repo_v1.0.0.zip"
    existing.write_bytes(b"old")

    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(profile),
        "src", "sync", str(repo), "--no-upload", "--json",
    ])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 2
    assert payload["status"] == "local_artifact_collision"
    assert payload["mutating_actions_executed"] is False
    assert payload["collisions"]["output_path_exists"] is True
    assert existing.read_bytes() == b"old"



def test_phase3_src_sync_upload_preflight_collision_confirm_command_includes_force(monkeypatch, capsys, tmp_path) -> None:
    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "VERSION").write_text("v1.0.0\n", encoding="utf-8")
    (repo / "main.py").write_text("print('ok')\n", encoding="utf-8")
    profile = tmp_path / "profile"
    artifact_dir = profile / "artifacts"
    artifact_dir.mkdir(parents=True)
    existing = artifact_dir / "repo_v1.0.0.zip"
    existing.write_bytes(b"old")
    project_url = "https://chatgpt.com/g/g-p-demo/project"

    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(profile),
        "--project-url", project_url,
        "src", "sync", str(repo), "--upload", "--json",
    ])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 2
    assert payload["status"] == "upload_confirmation_required"
    assert payload["confirmation"]["force_required"] is True
    assert "--force" in payload["confirmation"]["confirm_command"]
    assert any("local artifact collision" in warning for warning in payload["warnings"])
    assert existing.read_bytes() == b"old"


def test_phase3_src_sync_confirm_upload_collision_returns_force_confirmation(monkeypatch, capsys, tmp_path) -> None:
    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "VERSION").write_text("v1.0.0\n", encoding="utf-8")
    (repo / "main.py").write_text("print('ok')\n", encoding="utf-8")
    profile = tmp_path / "profile"
    artifact_dir = profile / "artifacts"
    artifact_dir.mkdir(parents=True)
    existing = artifact_dir / "repo_v1.0.0.zip"
    existing.write_bytes(b"old")
    project_url = "https://chatgpt.com/g/g-p-demo/project"

    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    preflight_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(profile),
        "--project-url", project_url,
        "src", "sync", str(repo), "--upload", "--json",
    ])
    preflight_payload = json.loads(capsys.readouterr().out)
    assert preflight_code == 2
    transaction_id = preflight_payload["transaction_id"]

    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(profile),
        "--project-url", project_url,
        "src", "sync", str(repo), "--upload", "--confirm-upload", "--confirm-transaction-id", transaction_id, "--json",
    ])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 2
    assert payload["status"] == "local_artifact_collision"
    assert payload["mutating_actions_executed"] is False
    assert payload["confirmation"]["force_required"] is True
    assert "--force" in payload["confirmation"]["confirm_command"]
    assert existing.read_bytes() == b"old"

def test_phase3_src_sync_no_upload_force_overwrites_and_verifies(monkeypatch, capsys, tmp_path) -> None:
    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "VERSION").write_text("v1.0.0\n", encoding="utf-8")
    (repo / "main.py").write_text("print('ok')\n", encoding="utf-8")
    profile = tmp_path / "profile"
    artifact_dir = profile / "artifacts"
    artifact_dir.mkdir(parents=True)
    existing = artifact_dir / "repo_v1.0.0.zip"
    existing.write_bytes(b"old")

    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(profile),
        "src", "sync", str(repo), "--no-upload", "--force", "--json",
    ])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["status"] == "verified_packaged"
    assert payload["local_verification"]["ok"] is True
    assert existing.read_bytes() != b"old"

def test_phase3_artifact_release_current_and_verify(monkeypatch, capsys, tmp_path) -> None:
    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "VERSION").write_text("v1.0.0\n", encoding="utf-8")
    (repo / "README.md").write_text("# demo\n", encoding="utf-8")

    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)
    profile = tmp_path / "profile"

    release_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(profile),
        "artifact", "release", str(repo), "--json",
    ])
    release_payload = json.loads(capsys.readouterr().out)
    assert release_code == 0
    assert release_payload["ok"] is True
    artifact_path = release_payload["artifact"]["path"]

    current_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(profile),
        "artifact", "current", "--json",
    ])
    current_payload = json.loads(capsys.readouterr().out)
    assert current_code == 0
    assert current_payload["registry_current"]["path"] == artifact_path
    assert current_payload["runtime"]["version"].startswith("v0.0.")
    assert current_payload["baseline_roles"]["adopted_artifact_ref"] is None
    assert current_payload["baseline_roles"]["adopted_source_ref"] is None
    assert current_payload["baseline_roles"]["registry_current_ref"] == Path(artifact_path).name
    assert current_payload["baseline_roles"]["registry_current_version"] == "v1.0.0"
    assert current_payload["baseline_roles"]["code_matches_adopted_source"] is False
    assert current_payload["consistency"]["registry_current_matches_state_artifact"] is False
    assert current_payload["consistency"]["state_source_matches_state_artifact"] is False
    assert current_payload["consistency"]["code_version_matches_state_source"] is False

    verify_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(profile),
        "artifact", "verify", artifact_path, "--json",
    ])
    verify_payload = json.loads(capsys.readouterr().out)
    assert verify_code == 0
    assert verify_payload["ok"] is True
    assert verify_payload["wrapper_folder"] is None


def test_task_list_payload_reports_unique_indexed_task_count_not_source_observation_sum() -> None:
    chats, payload = _chat_list_payload(
        {
            "ok": True,
            "source_counts": {"snorlax": 20, "dom": 10, "current_page": 0, "history": 0, "history_detail": 0},
            "chats": [
                {"id": f"task-{idx}", "title": f"Task {idx}", "conversation_url": f"https://chatgpt.com/g/g-p-demo/c/task-{idx}"}
                for idx in range(20)
            ],
        }
    )

    assert len(chats) == 20
    assert payload["visibility_status"] == "indexed"
    assert payload["indexed_task_count"] == 20
    assert payload["indexed_observation_count"] == 30


def test_task_list_payload_recomputes_stale_service_visibility_diagnostics() -> None:
    chats, payload = _chat_list_payload(
        {
            "ok": True,
            "visibility_status": "missing",
            "indexed_observation_count": 20,
            "recent_state_count": 99,
            "source_counts": {"snorlax": 20, "project_endpoint": 25, "dom": 0, "current_page": 0, "history": 0, "history_detail": 0},
            "chats": [
                {
                    "id": f"task-{idx}",
                    "title": f"Task {idx}",
                    "conversation_url": f"https://chatgpt.com/g/g-p-demo/c/task-{idx}",
                    "source": "project_endpoint",
                }
                for idx in range(25)
            ],
        }
    )

    assert len(chats) == 25
    assert payload["visibility_status"] == "indexed"
    assert payload["indexed_task_count"] == 25
    assert payload["indexed_observation_count"] == 45
    assert payload["recent_state_count"] == 0


def test_main_ask_combines_prompt_file_and_repeatable_attachments(monkeypatch, capsys, tmp_path) -> None:
    prompt_file = tmp_path / "prompt.md"
    prompt_file.write_text("extra context", encoding="utf-8")
    first = tmp_path / "one.log"
    second = tmp_path / "two.log"
    first.write_text("one", encoding="utf-8")
    second.write_text("two", encoding="utf-8")
    captured_kwargs: dict[str, object] = {}

    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

        def ask_result(self, prompt: str, **kwargs):
            captured_kwargs.update(kwargs)
            assert prompt == "review\n\nextra context"
            return {"answer": "ok", "conversation_url": "https://chatgpt.com/g/demo/c/123"}

    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(tmp_path / "profile"),
        "--project-url", "https://chatgpt.com/g/demo/project",
        "ask", "review",
        "--prompt-file", str(prompt_file),
        "--attach", str(first),
        "--attachment", str(second),
    ])

    assert exit_code == 0
    assert capsys.readouterr().out.strip() == "ok"
    assert captured_kwargs["attachment_paths"] == [str(first), str(second)]
    assert captured_kwargs["file_path"] is None


def test_test_full_uses_rate_limit_safe_defaults(monkeypatch, capsys) -> None:
    async def fake_run_test_suite_async(**kwargs):
        assert kwargs["profile"] == "full"
        assert kwargs["rate_limit_safe"] is True
        assert kwargs["step_delay_seconds"] == 20.0
        assert kwargs["post_ask_delay_seconds"] == 60.0
        assert kwargs["task_list_visible_poll_min_seconds"] == 45.0
        assert kwargs["task_list_visible_poll_max_seconds"] == 90.0
        assert kwargs["task_list_visible_max_attempts"] == 2
        return {"ok": True, "action": "test_suite", "profile": "full"}

    monkeypatch.setattr("promptbranch_cli.run_test_suite_async", fake_run_test_suite_async)

    from promptbranch_cli import main

    rc = main(["test", "full", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["profile"] == "full"


def test_test_full_can_disable_rate_limit_safe_defaults(monkeypatch, capsys) -> None:
    async def fake_run_test_suite_async(**kwargs):
        assert kwargs["profile"] == "full"
        assert kwargs["rate_limit_safe"] is False
        assert kwargs["step_delay_seconds"] == 8.0
        assert kwargs["post_ask_delay_seconds"] == 20.0
        assert kwargs["task_list_visible_max_attempts"] == 4
        return {"ok": True, "action": "test_suite", "profile": "full"}

    monkeypatch.setattr("promptbranch_cli.run_test_suite_async", fake_run_test_suite_async)

    from promptbranch_cli import main

    rc = main(["test", "full", "--no-rate-limit-safe", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["profile"] == "full"



def test_test_status_command_dispatches(monkeypatch, capsys) -> None:
    def fake_status(**kwargs):
        assert kwargs["path"] == "."
        assert kwargs["log"] == "pb_test.full.log"
        assert kwargs["service_log"] == "service.log"
        return {"ok": True, "action": "test_status", "status": "verified"}

    monkeypatch.setattr("promptbranch_cli.build_test_status", fake_status)

    from promptbranch_cli import main

    rc = main(["test", "status", "--log", "pb_test.full.log", "--service-log", "service.log", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["action"] == "test_status"
    assert payload["status"] == "verified"

def test_test_import_smoke_command_dispatches(monkeypatch, capsys) -> None:
    def fake_import_smoke(**kwargs):
        assert kwargs["repo_path"] == "."
        return {"ok": True, "action": "package_import_smoke", "status": "verified"}

    monkeypatch.setattr("promptbranch_cli.package_import_smoke", fake_import_smoke)

    from promptbranch_cli import main

    rc = main(["test", "import-smoke", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["action"] == "package_import_smoke"
    assert payload["status"] == "verified"


def test_test_report_command_emits_summary(capsys, tmp_path) -> None:
    log_path = tmp_path / "pb_test.full.log"
    log_path.write_text(
        "noise before\n"
        + json.dumps({
            "ok": True,
            "action": "test_suite",
            "profile": "full",
            "browser": {"ok": True, "steps": [{"name": "login", "ok": True}]},
            "agent": {
                "ok": True,
                "version": "v0.0.205",
                "steps": [
                    {"name": "package_hygiene", "ok": True, "payload": {"status": "verified", "bad_entries": [], "wrapper_folder": False}}
                ],
            },
            "rate_limit_telemetry": {"rate_limit_modal_detected": False, "conversation_history_429_seen": False},
            "safety": {"write_tools_blocked": True, "model_has_execution_authority": False, "source_or_artifact_mutation_allowed": False},
        }, indent=2)
        + "\nnoise after\n",
        encoding="utf-8",
    )

    from promptbranch_cli import main

    rc = main(["test", "report", str(log_path), "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["action"] == "test_report"
    assert payload["ok"] is True
    assert payload["suite"]["profile"] == "full"
    assert payload["suite"]["browser"]["step_count"] == 1
    assert payload["suite"]["agent"]["step_count"] == 1
    assert payload["suite"]["package_hygiene"]["status"] == "verified"

def test_json_command_stdout_is_parseable_without_debug_noise(monkeypatch, capsys, tmp_path) -> None:
    def fake_status(**kwargs):
        return {"ok": True, "action": "test_status", "status": "verified"}

    monkeypatch.setattr("promptbranch_cli.build_test_status", fake_status)
    monkeypatch.setenv("CHATGPT_DEBUG", "1")

    from promptbranch_cli import main

    rc = main(["test", "status", "--json"])
    captured = capsys.readouterr()
    assert rc == 0
    payload = json.loads(captured.out)
    assert payload["action"] == "test_status"
    assert "Using selector" not in captured.out
    assert "Using selector" not in captured.err


def test_json_command_debug_flag_keeps_logging_on_stderr(monkeypatch, capsys) -> None:
    def fake_status(**kwargs):
        return {"ok": True, "action": "test_status", "status": "verified"}

    monkeypatch.setattr("promptbranch_cli.build_test_status", fake_status)

    from promptbranch_cli import main

    rc = main(["--debug", "test", "status", "--json"])
    captured = capsys.readouterr()
    assert rc == 0
    payload = json.loads(captured.out)
    assert payload["status"] == "verified"
    assert captured.out.lstrip().startswith("{")






def test_src_add_service_error_returns_structured_json_without_traceback(monkeypatch, capsys, tmp_path) -> None:
    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

        def add_project_source(self, **kwargs):
            raise RuntimeError("504 error for POST http://localhost:8000/v1/project-sources: Could not find the remove/delete action for the selected project source")

    file_path = tmp_path / "architecture-process_0.1.29.zip"
    file_path.write_bytes(b"zip")
    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    exit_code = main(["--service-base-url", "http://localhost:8000", "src", "add", str(file_path)])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 1
    assert payload["ok"] is False
    assert payload["status"] == "overwrite_remove_failed"
    assert payload["project_source_mutated"] is False
    assert payload["operator_review_required"] is True
    assert "Traceback" not in captured.out
    assert "Traceback" not in captured.err

def test_phase3_src_sync_confirm_upload_service_error_with_expected_source_is_ambiguous(monkeypatch, capsys, tmp_path) -> None:
    calls: list[dict[str, object]] = []

    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

        def list_project_sources(self, **kwargs):
            if calls:
                return {"ok": True, "action": "source_list", "sources": [{"title": "repo_v1.2.8.zip"}]}
            return {"ok": True, "action": "source_list", "sources": []}

        def add_project_source(self, **kwargs):
            calls.append(kwargs)
            raise RuntimeError("504 error for POST http://localhost:8000/v1/project-sources: Could not find the remove/delete action for the selected project source")

    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "VERSION").write_text("v1.2.8\n", encoding="utf-8")
    (repo / "main.py").write_text("print('ok')\n", encoding="utf-8")
    profile = tmp_path / "profile"
    project_url = "https://chatgpt.com/g/g-p-demo/project"

    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    preflight_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(profile),
        "--project-url", project_url,
        "src", "sync", str(repo), "--upload", "--json",
    ])
    preflight_payload = json.loads(capsys.readouterr().out)
    assert preflight_code == 2
    transaction_id = preflight_payload["transaction_id"]

    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(profile),
        "--project-url", project_url,
        "src", "sync", str(repo), "--upload", "--confirm-upload", "--confirm-transaction-id", transaction_id, "--json",
    ])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert payload["ok"] is False
    assert payload["status"] == "upload_ambiguous"
    assert payload["project_source_mutated"] is False
    assert payload["project_source_mutation"] == "ambiguous"
    assert payload["operator_review_required"] is True
    assert payload["artifact_registry_updated"] is False
    assert payload["state_artifact_updated"] is False
    assert payload["state_source_updated"] is False
    assert payload["upload_verification"]["status"] == "upload_ambiguous"
    assert payload["upload_verification"]["operator_review_required"] is True
    assert payload["upload_verification"]["source_list_verification"]["status"] == "upload_ambiguous"
    assert payload["upload_verification"]["source_list_verification"]["ambiguity_reason"] == "upload_result_failed_but_expected_source_present_after"
    assert payload["upload_verification"]["source_list_verification"]["checks"]["expected_source_present_after"] is True
    assert payload["upload_verification"]["source_list_verification"]["collateral_change_detected"] is False
    assert Path(payload["artifact"]["path"]).is_file()
    assert not (profile / "promptbranch_artifacts.json").exists()
    assert calls[0]["display_name"] == "repo_v1.2.8.zip"

def test_phase3_src_sync_confirm_upload_service_error_returns_structured_failure(monkeypatch, capsys, tmp_path) -> None:
    calls: list[dict[str, object]] = []

    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

        def list_project_sources(self, **kwargs):
            return {"ok": True, "action": "source_list", "sources": []}

        def add_project_source(self, **kwargs):
            calls.append(kwargs)
            raise RuntimeError("504 error for POST http://localhost:8000/v1/project-sources: Could not find the remove/delete action for the selected project source")

    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "VERSION").write_text("v1.2.7\n", encoding="utf-8")
    (repo / "main.py").write_text("print('ok')\n", encoding="utf-8")
    profile = tmp_path / "profile"
    project_url = "https://chatgpt.com/g/g-p-demo/project"

    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    preflight_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(profile),
        "--project-url", project_url,
        "src", "sync", str(repo), "--upload", "--json",
    ])
    preflight_payload = json.loads(capsys.readouterr().out)
    assert preflight_code == 2
    transaction_id = preflight_payload["transaction_id"]

    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(profile),
        "--project-url", project_url,
        "src", "sync", str(repo), "--upload", "--confirm-upload", "--confirm-transaction-id", transaction_id, "--json",
    ])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert payload["status"] == "upload_failed"
    assert payload["project_source_mutated"] is False
    assert payload["artifact_registry_updated"] is False
    assert payload["state_source_updated"] is False
    assert payload["upload_result"]["ok"] is False
    assert payload["upload_result"]["action"] == "source_add"
    assert payload["upload_result"]["status"] == "service_error"
    assert "remove/delete action" in payload["upload_result"]["error"]
    assert payload["upload_verification"]["registry_update_deferred_until_upload_verified"] is True
    assert Path(payload["artifact"]["path"]).is_file()
    assert not (profile / "promptbranch_artifacts.json").exists()
    assert calls[0]["display_name"] == "repo_v1.2.7.zip"


def test_v185_parser_accepts_artifact_release_source_sync_transaction_flags() -> None:
    parser = make_parser()
    args = parser.parse_args([
        "artifact", "release", ".", "--sync-source", "--upload", "--confirm-upload",
        "--confirm-transaction-id", "abc123", "--force", "--json",
    ])

    assert args.command == "artifact"
    assert args.artifact_command == "release"
    assert args.sync_source is True
    assert args.upload is True
    assert args.confirm_upload is True
    assert args.confirm_transaction_id == "abc123"
    assert args.force is True
    assert args.json is True


def test_v185_artifact_release_source_sync_upload_preflight_uses_artifact_confirm_command(monkeypatch, capsys, tmp_path) -> None:
    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "VERSION").write_text("v1.2.3\n", encoding="utf-8")
    (repo / "main.py").write_text("print('ok')\n", encoding="utf-8")
    profile = tmp_path / "profile"
    project_url = "https://chatgpt.com/g/g-p-demo/project"

    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(profile),
        "--project-url", project_url,
        "artifact", "release", str(repo), "--sync-source", "--upload", "--json",
    ])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 2
    assert payload["action"] == "artifact_release"
    assert payload["status"] == "planned"
    assert payload["source_sync_status"] == "upload_confirmation_required"
    assert payload["release_workflow"] == "artifact_release_source_sync_v1"
    assert payload["mutating_actions_executed"] is False
    assert payload["project_source_mutated"] is False
    assert payload["confirmation"]["required"] is True
    assert "pb artifact release" in payload["confirmation"]["confirm_command"]
    assert "--sync-source" in payload["confirmation"]["confirm_command"]
    assert "--confirm-upload" in payload["confirmation"]["confirm_command"]
    assert "source_sync_confirm_command" not in payload["confirmation"]
    assert payload["confirmation"]["operator_instruction"].startswith("Run this top-level artifact release")
    assert payload["operator_instruction"].startswith("Run confirmation.confirm_command exactly")
    assert "confirm_command" not in payload["source_sync"]["confirmation"]
    assert payload["source_sync"]["confirmation"]["confirm_command_redacted"] is True
    assert "pb src sync" not in json.dumps(payload["confirmation"])
    assert not (profile / "artifacts" / "repo_v1.2.3.zip").exists()


def test_v185_artifact_release_source_sync_no_upload_packages_with_clear_status(monkeypatch, capsys, tmp_path) -> None:
    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "VERSION").write_text("v1.2.4\n", encoding="utf-8")
    (repo / "main.py").write_text("print('ok')\n", encoding="utf-8")
    profile = tmp_path / "profile"

    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(profile),
        "artifact", "release", str(repo), "--sync-source", "--no-upload", "--json",
    ])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["action"] == "artifact_release"
    assert payload["status"] == "packaged"
    assert payload["source_sync_status"] == "verified_packaged"
    assert payload["artifact_registry_updated"] is True
    assert payload["state_source_updated"] is False
    assert payload["project_source_mutated"] is False
    assert Path(payload["artifact"]["path"]).is_file()
    assert payload["source_sync"]["local_verification"]["status"] == "verified"


def test_v185_artifact_release_source_sync_confirm_upload_advances_state_only_after_verified_upload(monkeypatch, capsys, tmp_path) -> None:
    calls: list[dict[str, object]] = []

    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

        def list_project_sources(self, **kwargs):
            if calls:
                return {"ok": True, "action": "source_list", "sources": [{"title": "repo_v1.2.5.zip"}]}
            return {"ok": True, "action": "source_list", "sources": []}

        def add_project_source(self, **kwargs):
            calls.append(kwargs)
            return {"ok": True, "action": "source_add", "status": "verified"}

    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "VERSION").write_text("v1.2.5\n", encoding="utf-8")
    (repo / "main.py").write_text("print('ok')\n", encoding="utf-8")
    profile = tmp_path / "profile"
    project_url = "https://chatgpt.com/g/g-p-demo/project"

    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    preflight_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(profile),
        "--project-url", project_url,
        "artifact", "release", str(repo), "--sync-source", "--upload", "--json",
    ])
    preflight = json.loads(capsys.readouterr().out)
    assert preflight_code == 2

    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(profile),
        "--project-url", project_url,
        "artifact", "release", str(repo), "--sync-source", "--upload", "--confirm-upload",
        "--confirm-transaction-id", preflight["transaction_id"], "--json",
    ])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["action"] == "artifact_release"
    assert payload["status"] == "uploaded"
    assert payload["source_sync_status"] == "uploaded"
    assert payload["project_source_mutated"] is True
    assert payload["artifact_registry_updated"] is True
    assert payload["state_artifact_updated"] is True
    assert payload["state_source_updated"] is True
    assert payload["upload_verification"]["status"] == "verified"
    assert calls[0]["display_name"] == "repo_v1.2.5.zip"



def test_v188_artifact_release_redacts_nested_source_sync_confirm_command() -> None:
    from promptbranch_cli import _rewrite_source_sync_payload_for_artifact_release

    payload = {
        "ok": False,
        "action": "src_sync",
        "status": "upload_confirmation_required",
        "transaction_id": "tx123",
        "confirmation": {
            "required": True,
            "confirm_command": "pb src sync /repo --upload --confirm-upload --confirm-transaction-id tx123 --json",
            "force_required": False,
        },
    }

    rewritten = _rewrite_source_sync_payload_for_artifact_release(payload, repo_path=Path("/repo"))

    assert rewritten["action"] == "artifact_release"
    assert rewritten["status"] == "planned"
    assert rewritten["confirmation"]["confirm_command"].startswith("pb artifact release")
    assert "pb src sync" not in rewritten["confirmation"]["confirm_command"]
    assert "source_sync_confirm_command" not in rewritten["confirmation"]
    assert "confirm_command" not in rewritten["source_sync"]["confirmation"]
    assert rewritten["source_sync"]["confirmation"]["confirm_command_redacted"] is True


def test_v188_artifact_release_confirm_command_includes_force_when_source_sync_requires_force() -> None:
    from promptbranch_cli import _rewrite_source_sync_payload_for_artifact_release

    payload = {
        "ok": False,
        "action": "src_sync",
        "status": "upload_confirmation_required",
        "transaction_id": "tx-force",
        "confirmation": {
            "required": True,
            "force_required": True,
            "confirm_command": "pb src sync /repo --upload --confirm-upload --confirm-transaction-id tx-force --force --json",
        },
    }

    rewritten = _rewrite_source_sync_payload_for_artifact_release(payload, repo_path=Path("/repo"))

    command = rewritten["confirmation"]["confirm_command"]
    assert command.startswith("pb artifact release")
    assert "--force" in command
    assert "pb src sync" not in command
    assert "confirm_command" not in rewritten["source_sync"]["confirmation"]
    assert rewritten["source_sync"]["confirmation"]["confirm_command_redacted"] is True


def test_v188_artifact_release_wrapper_maps_success_to_top_level_uploaded() -> None:
    from promptbranch_cli import _rewrite_source_sync_payload_for_artifact_release

    payload = {
        "ok": True,
        "action": "src_sync",
        "status": "uploaded",
        "project_source_mutated": True,
        "artifact_registry_updated": True,
        "state_artifact_updated": True,
        "state_source_updated": True,
        "upload_verification": {"ok": True, "status": "verified"},
    }

    rewritten = _rewrite_source_sync_payload_for_artifact_release(payload, repo_path=Path("/repo"))

    assert rewritten["action"] == "artifact_release"
    assert rewritten["status"] == "uploaded"
    assert rewritten["source_sync_status"] == "uploaded"
    assert rewritten["source_sync_action"] == "src_sync"
    assert rewritten["artifact_registry_updated"] is True
    assert rewritten["state_artifact_updated"] is True
    assert rewritten["state_source_updated"] is True
    assert rewritten["source_sync"]["status"] == "uploaded"


def test_v188_artifact_release_wrapper_maps_ambiguous_without_advancing_state() -> None:
    from promptbranch_cli import _rewrite_source_sync_payload_for_artifact_release

    payload = {
        "ok": False,
        "action": "src_sync",
        "status": "upload_ambiguous",
        "operator_review_required": True,
        "artifact_registry_updated": False,
        "state_artifact_updated": False,
        "state_source_updated": False,
        "upload_verification": {"ok": False, "status": "upload_ambiguous"},
    }

    rewritten = _rewrite_source_sync_payload_for_artifact_release(payload, repo_path=Path("/repo"))

    assert rewritten["action"] == "artifact_release"
    assert rewritten["status"] == "upload_ambiguous"
    assert rewritten["source_sync_status"] == "upload_ambiguous"
    assert rewritten["operator_review_required"] is True
    assert rewritten["artifact_registry_updated"] is False
    assert rewritten["state_source_updated"] is False


def test_v189_artifact_release_print_confirm_command_outputs_only_top_level_command(monkeypatch, capsys, tmp_path) -> None:
    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "VERSION").write_text("v1.2.9\n", encoding="utf-8")
    (repo / "main.py").write_text("print('ok')\n", encoding="utf-8")
    profile = tmp_path / "profile"
    project_url = "https://chatgpt.com/g/g-p-demo/project"

    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(profile),
        "--project-url", project_url,
        "artifact", "release", str(repo), "--sync-source", "--upload", "--print-confirm-command",
    ])

    output = capsys.readouterr().out.strip()
    assert exit_code == 0
    assert output.startswith("pb artifact release ")
    assert "--sync-source" in output
    assert "--confirm-upload" in output
    assert "--confirm-transaction-id" in output
    assert "pb src sync" not in output
    assert "{" not in output


def test_v189_artifact_release_print_confirm_command_includes_force_when_required(monkeypatch, capsys, tmp_path) -> None:
    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "VERSION").write_text("v1.2.10\n", encoding="utf-8")
    (repo / "main.py").write_text("print('ok')\n", encoding="utf-8")
    profile = tmp_path / "profile"
    project_url = "https://chatgpt.com/g/g-p-demo/project"

    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    first_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(profile),
        "--project-url", project_url,
        "artifact", "release", str(repo), "--sync-source", "--no-upload", "--json",
    ])
    _ = capsys.readouterr()
    assert first_code == 0

    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(profile),
        "--project-url", project_url,
        "artifact", "release", str(repo), "--sync-source", "--upload", "--print-confirm-command",
    ])

    output = capsys.readouterr().out.strip()
    assert exit_code == 0
    assert output.startswith("pb artifact release ")
    assert "--force" in output
    assert "pb src sync" not in output


def test_ask_release_print_request_json_requires_expected_candidate(monkeypatch, capsys, tmp_path) -> None:
    from promptbranch_artifacts import ArtifactRecord, utc_now

    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

    profile = tmp_path / "profile"
    registry = ArtifactRegistry(profile)
    registry.add(ArtifactRecord(
        path=str(tmp_path / "chatgpt_claudecode_workflow_v0.0.256.zip"),
        filename="chatgpt_claudecode_workflow_v0.0.256.zip",
        kind="adopted_release",
        version="v0.0.256",
        repo_path=None,
        sha256="abc",
        size_bytes=123,
        file_count=4,
        created_at=utc_now(),
        source_ref="chatgpt_claudecode_workflow_v0.0.256.zip",
        project_url="https://chatgpt.com/g/g-p-demo/project",
    ))
    ConversationStateStore(str(profile)).remember_project(
        "https://chatgpt.com/g/g-p-demo/project",
        project_name="demo",
    )
    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(profile),
        "ask-release",
        "Implement the next controlled proof.",
        "--target-version", "v0.0.257",
        "--print-request-json",
        "--json",
    ])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["action"] == "ask_release"
    assert payload["candidate_producing_protocol_flow"] is True
    assert payload["strict_real_candidate_required"] is True
    request = payload["request"]
    assert request["artifact"]["expected_output_artifact"] == "chatgpt_claudecode_workflow_v0.0.257.zip"
    assert request["artifact"]["no_artifact_reply_allowed"] is False
    assert request["constraints"]["exactly_one_zip_artifact_required"] is True
    assert request["expected_reply"]["artifact_policy"]["exact_count"] == 1


def test_ask_release_validation_rejects_no_artifact_reply() -> None:
    from promptbranch_cli import _validate_ask_release_candidate_result

    result = {
        "ok": True,
        "status": "reply_validated",
        "reply_validation_ok": True,
        "reply": {
            "status": "no_artifact",
            "result_type": "no_change",
            "artifacts": [],
        },
    }
    expected = {
        "expected_artifact": "chatgpt_claudecode_workflow_v0.0.257.zip",
        "expected_version": "v0.0.257",
        "expected_role": "candidate_release",
    }

    payload = _validate_ask_release_candidate_result(result, expected)

    assert payload["ok"] is False
    assert payload["status"] == "release_candidate_validation_failed"
    assert "ask_release:exact_artifact_count" in payload["reply_validation_errors"]
    assert "ask_release:status_release_candidate" in payload["reply_validation_errors"]


def test_ask_release_validation_accepts_one_expected_downloadable_zip() -> None:
    from promptbranch_cli import _validate_ask_release_candidate_result

    result = {
        "ok": True,
        "status": "reply_validated",
        "reply_validation_ok": True,
        "reply": {
            "status": "completed",
            "result_type": "release_candidate",
            "artifacts": [
                {
                    "kind": "zip",
                    "filename": "chatgpt_claudecode_workflow_v0.0.257.zip",
                    "version": "v0.0.257",
                    "role": "candidate_release",
                    "download": {"available": True, "link_text": "chatgpt_claudecode_workflow_v0.0.257.zip"},
                }
            ],
        },
    }
    expected = {
        "expected_artifact": "chatgpt_claudecode_workflow_v0.0.257.zip",
        "expected_version": "v0.0.257",
        "expected_role": "candidate_release",
    }

    payload = _validate_ask_release_candidate_result(result, expected)

    assert payload["ok"] is True
    assert payload["status"] == "reply_validated"
    assert payload["ask_release_validation"]["ok"] is True


def test_artifact_intake_explicit_message_answer_manual_import_promotes_and_migrates(monkeypatch, capsys, tmp_path) -> None:
    artifact_name = "chatgpt_claudecode_workflow_v0.0.260.zip"
    local_zip = tmp_path / "browser-downloaded.zip"
    with zipfile.ZipFile(local_zip, "w") as archive:
        archive.writestr("VERSION", "v0.0.260\n")
        archive.writestr("README.md", "# demo\n")
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    reply = {
        "schema": "promptbranch.ask.reply",
        "schema_version": "1.0",
        "request_id": "req-explicit-intake",
        "correlation_id": "req-explicit-intake",
        "status": "completed",
        "result_type": "release_candidate",
        "summary": "Built candidate.",
        "baseline": {
            "input_artifact": "chatgpt_claudecode_workflow_v0.0.259.zip",
            "input_version": "v0.0.259",
            "source_ref": "chatgpt_claudecode_workflow_v0.0.259.zip",
            "source_version": "v0.0.259",
            "registry_current": "chatgpt_claudecode_workflow_v0.0.259.zip",
            "registry_current_version": "v0.0.259",
            "output_artifact": artifact_name,
            "output_version": "v0.0.260",
            "target_version": "v0.0.260",
            "release_type": "normal",
        },
        "changes": [],
        "artifacts": [
            {
                "kind": "zip",
                "filename": artifact_name,
                "version": "v0.0.260",
                "role": "candidate_release",
                "download": {"available": True, "link_text": artifact_name, "url": f"sandbox:/mnt/data/{artifact_name}"},
            }
        ],
        "validation": {"claimed": ["focused tests"], "not_claimed": ["full suite"]},
        "next_step": {"operator_action": "download_verify_migrate"},
    }
    answer_text = "BEGIN_PROMPTBRANCH_REPLY_JSON\n" + json.dumps(reply) + "\nEND_PROMPTBRANCH_REPLY_JSON"

    class FakeServiceClient:
        def __init__(self, *args, **kwargs):
            pass

        def get_chat(self, conversation_url: str, **kwargs):
            return {
                "ok": True,
                "conversation_url": conversation_url,
                "conversation_id": "abc",
                "title": "Protocol chat",
                "turns": [
                    {"index": 1, "id": "u1", "role": "user", "text": "ordinary diagnostic"},
                    {"index": 2, "id": "a1", "role": "assistant", "text": "plain answer"},
                    {"index": 3, "id": "u-candidate", "role": "user", "text": "protocol request req-explicit-intake"},
                    {"index": 4, "id": "a-candidate", "role": "assistant", "text": answer_text},
                    {"index": 5, "id": "u-latest", "role": "user", "text": "check log"},
                    {"index": 6, "id": "a-latest", "role": "assistant", "text": "diagnostic without protocol"},
                ],
            }

    project_url = "https://chatgpt.com/g/g-p-demo-project/project"
    conversation_url = "https://chatgpt.com/g/g-p-demo-project/c/abc"
    store = ConversationStateStore(str(tmp_path))
    store.remember_project(project_url, project_name="demo-project")
    store.remember(project_url, conversation_url, project_name="demo-project")
    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(tmp_path),
        "artifact", "intake", "--from-last-answer",
        "--message-id", "u-candidate",
        "--answer-id", "a-candidate",
        "--local-file", str(local_zip),
        "--verify", "--migrate",
        "--repo-path", str(repo_root),
        "--json",
    ])
    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["status"] == "migrated_candidate"
    assert payload["source"] == "explicit_task_answer"
    assert payload["selected_request_id"] == "req-explicit-intake"
    assert payload["selected_message_id"] == "u-candidate"
    assert payload["selected_answer_id"] == "a-candidate"
    assert payload["protocol_run_promoted"] is True
    assert Path(payload["promoted_protocol_run_record_path"]).is_file()
    assert payload["candidate_registry_entry"]["reply_request_id"] == "req-explicit-intake"
    assert payload["candidate_registry_entry"]["message_id"] == "u-candidate"
    assert payload["candidate_registry_entry"]["answer_id"] == "a-candidate"
    assert (repo_root / artifact_name).is_file()


def test_task_answer_parse_resolves_unique_answer_id_globally(monkeypatch, capsys, tmp_path) -> None:
    project_url = "https://chatgpt.com/g/g-p-demo-claude-code/project"
    conversation_url = "https://chatgpt.com/g/g-p-demo-claude-code/c/globalanswer"
    reply = {
        "schema": "promptbranch.ask.reply",
        "schema_version": "1.0",
        "request_id": "req-global-answer",
        "correlation_id": "req-global-answer",
        "status": "completed",
        "result_type": "release_candidate",
        "summary": "candidate reply",
        "baseline": {
            "input_artifact": "chatgpt_claudecode_workflow_v0.0.269.zip",
            "input_version": "v0.0.269",
            "output_artifact": "chatgpt_claudecode_workflow_v0.0.269.zip",
            "output_version": "v0.0.269",
            "target_version": "v0.0.269",
            "release_type": "normal",
        },
        "changes": [],
        "artifacts": [
            {
                "kind": "zip",
                "filename": "chatgpt_claudecode_workflow_v0.0.269.zip",
                "version": "v0.0.269",
                "role": "candidate_release",
                "download": {"available": True, "url": "sandbox:/mnt/data/chatgpt_claudecode_workflow_v0.0.269.zip"},
            }
        ],
        "validation": {"claimed": ["focused tests"], "not_claimed": []},
        "next_step": {"operator_action": "download_verify_migrate"},
    }
    answer_text = "BEGIN_PROMPTBRANCH_REPLY_JSON\n" + json.dumps(reply) + "\nEND_PROMPTBRANCH_REPLY_JSON"

    class FakeServiceClient:
        def __init__(self, *args, **kwargs):
            pass

        def get_chat(self, conversation_url: str, **kwargs):
            return {
                "ok": True,
                "conversation_url": conversation_url,
                "conversation_id": "globalanswer",
                "title": "Global answer id parse",
                "turns": [
                    {"index": 1, "id": "u-old", "role": "user", "text": "previous ask"},
                    {"index": 2, "id": "a-old", "role": "assistant", "text": "previous answer"},
                    {"index": 3, "id": "u-candidate", "role": "user", "text": "protocol request req-global-answer"},
                    {"index": 4, "id": "a-candidate", "role": "assistant", "text": answer_text},
                    {"index": 5, "id": "u-latest", "role": "user", "text": "check log"},
                    {"index": 6, "id": "a-latest", "role": "assistant", "text": "diagnostic without protocol"},
                ],
            }

    store = ConversationStateStore(str(tmp_path))
    store.remember_project(project_url, project_name="demo-project")
    store.remember(project_url, conversation_url, project_name="demo-project")
    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(tmp_path),
        "task", "answer", "parse",
        "--answer-id", "a-candidate",
        "--json",
    ])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["status"] == "valid"
    assert payload["selected_message_id"] == "u-candidate"
    assert payload["selected_answer_id"] == "a-candidate"
    assert payload["answer_selection"]["policy"] == "global_answer_id"
    assert payload["answer_selection"]["global_answer_id_resolution"] is True
    assert payload["protocol_run_promoted"] is True


def test_task_answer_parse_explicit_message_id_keeps_answer_id_scoped(monkeypatch, capsys, tmp_path) -> None:
    project_url = "https://chatgpt.com/g/g-p-demo-claude-code/project"
    conversation_url = "https://chatgpt.com/g/g-p-demo-claude-code/c/scopedanswer"
    reply = {
        "schema": "promptbranch.ask.reply",
        "schema_version": "1.0",
        "request_id": "req-scoped-answer",
        "correlation_id": "req-scoped-answer",
        "status": "no_artifact",
        "result_type": "no_change",
        "summary": "smoke reply",
        "baseline": {
            "input_artifact": "chatgpt_claudecode_workflow_v0.0.269.zip",
            "input_version": "v0.0.269",
            "target_version": "v0.0.269",
            "release_type": "normal",
        },
        "changes": [],
        "artifacts": [],
        "validation": {"claimed": ["protocol smoke"], "not_claimed": []},
        "next_step": {"operator_action": "none"},
    }
    answer_text = "BEGIN_PROMPTBRANCH_REPLY_JSON\n" + json.dumps(reply) + "\nEND_PROMPTBRANCH_REPLY_JSON"

    class FakeServiceClient:
        def __init__(self, *args, **kwargs):
            pass

        def get_chat(self, conversation_url: str, **kwargs):
            return {
                "ok": True,
                "conversation_url": conversation_url,
                "conversation_id": "scopedanswer",
                "title": "Scoped answer id parse",
                "turns": [
                    {"index": 1, "id": "u1", "role": "user", "text": "first"},
                    {"index": 2, "id": "a1", "role": "assistant", "text": "plain"},
                    {"index": 3, "id": "u2", "role": "user", "text": "protocol request req-scoped-answer"},
                    {"index": 4, "id": "a2", "role": "assistant", "text": answer_text},
                ],
            }

    store = ConversationStateStore(str(tmp_path))
    store.remember_project(project_url, project_name="demo-project")
    store.remember(project_url, conversation_url, project_name="demo-project")
    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(tmp_path),
        "task", "answer", "parse",
        "--message-id", "u2",
        "--answer-id", "a2",
        "--json",
    ])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["status"] == "valid"
    assert payload["selected_message_id"] == "u2"
    assert payload["selected_answer_id"] == "a2"
    assert payload["answer_selection"]["policy"] == "explicit_message_selector"
    assert payload["answer_selection"]["global_answer_id_resolution"] is False
