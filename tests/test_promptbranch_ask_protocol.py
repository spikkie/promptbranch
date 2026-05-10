from __future__ import annotations

import json
from pathlib import Path

from promptbranch_ask_protocol import (
    BEGIN_REPLY_MARKER,
    END_REPLY_MARKER,
    extract_reply_blocks,
    parse_promptbranch_reply,
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
