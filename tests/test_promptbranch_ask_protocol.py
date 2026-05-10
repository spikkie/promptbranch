from __future__ import annotations

import json
from pathlib import Path

from promptbranch_ask_protocol import (
    BEGIN_REPLY_MARKER,
    END_REPLY_MARKER,
    classify_artifact_candidates,
    extract_reply_blocks,
    parse_promptbranch_reply,
    repo_prefix_from_artifact_filename,
    version_from_artifact_filename,
)


def _valid_reply_text() -> str:
    reply = json.loads(Path("promptbranch_protocol/examples/ask.release.reply.example.json").read_text())
    return f"Human intro\n{BEGIN_REPLY_MARKER}\n{json.dumps(reply)}\n{END_REPLY_MARKER}\nHuman outro"


def test_extract_reply_blocks_finds_one_marked_block() -> None:
    blocks = extract_reply_blocks(_valid_reply_text())

    assert len(blocks) == 1
    assert blocks[0].index == 1
    assert "promptbranch.ask.reply" in blocks[0].text


def test_parse_promptbranch_reply_returns_artifact_candidates() -> None:
    payload = parse_promptbranch_reply(_valid_reply_text())

    assert payload["ok"] is True
    assert payload["status"] == "valid"
    assert payload["request_id"] == "req_20260510_001"
    assert payload["artifact_candidate_count"] == 1
    candidate = payload["artifact_candidates"][0]
    assert candidate["status"] == "candidate_found"
    assert candidate["filename"] == "chatgpt_claudecode_workflow_v0.0.201.zip"
    assert candidate["download"]["available"] is True




def test_version_and_repo_prefix_are_extracted_from_artifact_filename() -> None:
    filename = "chatgpt_claudecode_workflow_v0.0.202.zip"

    assert version_from_artifact_filename(filename) == "v0.0.202"
    assert repo_prefix_from_artifact_filename(filename) == "chatgpt_claudecode_workflow"


def test_classify_artifact_candidates_selects_expected_zip() -> None:
    parsed = parse_promptbranch_reply(_valid_reply_text())

    payload = classify_artifact_candidates(
        parsed["artifact_candidates"],
        expected_filename="chatgpt_claudecode_workflow_v0.0.201.zip",
        expected_version="v0.0.201",
        expected_repo="chatgpt_claudecode_workflow",
    )

    assert payload["ok"] is True
    assert payload["status"] == "candidate_selected"
    assert payload["selected_candidate"]["filename"] == "chatgpt_claudecode_workflow_v0.0.201.zip"
    assert payload["download_performed"] is False
    assert payload["migration_performed"] is False
    assert payload["adoption_performed"] is False


def test_classify_artifact_candidates_reports_missing_ambiguous_and_wrong_version() -> None:
    assert classify_artifact_candidates([])["status"] == "artifact_candidate_missing"

    ambiguous = classify_artifact_candidates([
        {"filename": "repo_v0.0.1.zip", "version": "v0.0.1"},
        {"filename": "repo_v0.0.2.zip", "version": "v0.0.2"},
    ])
    assert ambiguous["ok"] is False
    assert ambiguous["status"] == "artifact_candidate_ambiguous"

    wrong = classify_artifact_candidates(
        [{"filename": "repo_v0.0.1.zip", "version": "v0.0.1"}],
        expected_version="v0.0.2",
    )
    assert wrong["ok"] is False
    assert wrong["status"] == "artifact_wrong_version"
    assert wrong["artifact_candidates"][0]["status"] == "artifact_wrong_version"


def test_parse_promptbranch_reply_reports_missing_block() -> None:
    payload = parse_promptbranch_reply("plain answer with no protocol envelope")

    assert payload["ok"] is False
    assert payload["status"] == "reply_schema_missing"
    assert payload["artifact_candidate_count"] == 0


def test_parse_promptbranch_reply_reports_invalid_json() -> None:
    payload = parse_promptbranch_reply(f"{BEGIN_REPLY_MARKER}\n{{bad json\n{END_REPLY_MARKER}")

    assert payload["ok"] is False
    assert payload["status"] == "reply_schema_invalid"
    assert "json_error" in payload


def test_parse_promptbranch_reply_reports_ambiguous_blocks() -> None:
    text = _valid_reply_text() + "\n" + _valid_reply_text()

    payload = parse_promptbranch_reply(text)

    assert payload["ok"] is False
    assert payload["status"] == "reply_schema_ambiguous"
    assert payload["block_count"] == 2


def test_protocol_schema_and_examples_are_valid_json() -> None:
    paths = [
        "promptbranch_protocol/schemas/ask.request.schema.json",
        "promptbranch_protocol/schemas/ask.reply.schema.json",
        "promptbranch_protocol/schemas/artifact.candidate.schema.json",
        "promptbranch_protocol/examples/ask.release.request.example.json",
        "promptbranch_protocol/examples/ask.release.reply.example.json",
    ]
    for rel in paths:
        parsed = json.loads(Path(rel).read_text())
        assert isinstance(parsed, dict)


def test_ask_protocol_module_is_declared_for_setuptools_install() -> None:
    import tomllib

    data = tomllib.loads(Path("pyproject.toml").read_text())
    modules = data["tool"]["setuptools"]["py-modules"]
    assert "promptbranch_ask_protocol" in modules
    package_data = data["tool"]["setuptools"]["package-data"]
    assert "promptbranch_protocol" in package_data
