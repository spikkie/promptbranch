from __future__ import annotations

import json

from promptbranch_ask_protocol import (
    BEGIN_REPLY_MARKER,
    END_REPLY_MARKER,
    render_release_candidate_artifact_prompt,
)


def test_renderer_emits_request_json_and_dynamic_failure_envelope() -> None:
    envelope = {
        "schema": "promptbranch.ask.request",
        "schema_version": "1.0",
        "request_id": "req_dynamic",
        "correlation_id": "corr_dynamic",
        "artifact": {
            "current_baseline": "repo_v1.2.3.zip",
            "current_version": "v1.2.3",
            "target_version": "v1.2.4",
            "expected_output_artifact": "repo_v1.2.4.zip",
            "expected_output_version": "v1.2.4",
            "release_type": "normal",
        },
    }

    prompt = render_release_candidate_artifact_prompt(envelope, user_prompt="Apply the requested release scope.")

    assert "BEGIN_PROMPTBRANCH_REQUEST_JSON" in prompt
    assert json.dumps(envelope, indent=2, ensure_ascii=False) in prompt
    assert prompt.count(BEGIN_REPLY_MARKER) >= 3
    assert prompt.count(END_REPLY_MARKER) >= 3
    assert '"request_id": "req_dynamic"' in prompt
    assert '"correlation_id": "corr_dynamic"' in prompt
    assert '"input_baseline": "repo_v1.2.3.zip"' in prompt
    assert "Apply the requested release scope." in prompt
