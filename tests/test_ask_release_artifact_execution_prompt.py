from __future__ import annotations

import promptbranch_cli as cli
from promptbranch_ask_protocol import render_release_candidate_artifact_prompt


BASELINE = "chatgpt_claudecode_workflow-2_v0.1.123.2.4.zip"
BASELINE_VERSION = "v0.1.123.2.4"
TARGET_VERSION = "v0.1.124"
EXPECTED = "chatgpt_claudecode_workflow-2_v0.1.124.zip"
REQUEST_ID = "req_20260805T090213580863Z"


def _envelope() -> dict:
    base = {
        "schema": "promptbranch.ask.request",
        "schema_version": "1.0",
        "request_id": REQUEST_ID,
        "correlation_id": REQUEST_ID,
        "task": {
            "conversation_id": "conversation",
            "turn_policy": "assistant_may_return_one_protocol_reply",
        },
        "artifact": {
            "repo": "chatgpt_claudecode_workflow-2",
            "current_baseline": BASELINE,
            "current_version": BASELINE_VERSION,
            "target_version": TARGET_VERSION,
            "release_type": "normal",
        },
        "constraints": {},
        "expected_reply": {},
        "protocol_decisions": {},
    }
    expected = {
        "expected_repo": "chatgpt_claudecode_workflow-2",
        "expected_artifact": EXPECTED,
        "expected_version": TARGET_VERSION,
        "expected_role": "candidate_release",
    }
    return cli._augment_release_candidate_request(base, expected)


def _prompt() -> str:
    envelope = _envelope()
    expected = {
        "expected_artifact": EXPECTED,
        "expected_version": TARGET_VERSION,
        "expected_role": "candidate_release",
    }
    implementation = cli._build_ask_release_user_prompt(
        "Create normal release v0.1.124 from accepted/current v0.1.123.2.4.",
        expected,
        envelope,
    )
    return render_release_candidate_artifact_prompt(envelope, user_prompt=implementation)


def test_ask_release_prompt_defines_two_ordered_output_components() -> None:
    prompt = _prompt()

    assert prompt.startswith("Promptbranch release-candidate artifact request.")
    assert "A successful final response MUST contain exactly two output components" in prompt
    assert prompt.index("COMPONENT 1 — REAL DOWNLOADABLE ZIP OUTPUT") < prompt.index(
        "COMPONENT 2 — EXACTLY ONE PROMPTBRANCH REPLY ENVELOPE"
    )
    assert f"[Download {EXPECTED}](actual-created-file-reference)" in prompt
    assert "The ZIP output must appear as a separate rendered attachment or clickable download link" in prompt


def test_ask_release_prompt_rejects_json_only_sandbox_declaration() -> None:
    prompt = _prompt()

    assert "A sandbox path written only inside JSON is not an attachment" in prompt
    assert f'"download_url": "sandbox:/mnt/data/{EXPECTED}"' in prompt
    assert "The required successful output is not “one JSON envelope containing a ZIP path.”" in prompt
    assert "ONE REAL DOWNLOADABLE ZIP FILE\n+\nONE BEGIN_PROMPTBRANCH_REPLY_JSON" in prompt


def test_ask_release_prompt_binds_fresh_physical_zip_to_exact_request() -> None:
    prompt = _prompt()

    assert f"Use the exact accepted/current release ZIP {BASELINE} as the actual source baseline" in prompt
    assert f"Create a brand-new physical ZIP specifically for request:\n\n{REQUEST_ID}" in prompt
    assert "Do not reuse, rename, copy, or reference" in prompt
    assert "Create the physical ZIP before beginning the final response" in prompt
    assert "Only after Component 1 is present, construct Component 2" in prompt


def test_ask_release_prompt_contains_fail_closed_dynamic_envelope() -> None:
    prompt = _prompt()

    assert f'"request_id": "{REQUEST_ID}"' in prompt
    assert f'"correlation_id": "{REQUEST_ID}"' in prompt
    assert '"status": "failed"' in prompt
    assert '"result_type": "release_candidate"' in prompt
    assert '"artifacts": []' in prompt
    assert '"physical_artifact_created": false' in prompt
    assert '"attachment_rendered": false' in prompt


def test_release_candidate_request_schema_declares_two_component_contract() -> None:
    envelope = _envelope()

    assert envelope["task"]["turn_policy"] == "assistant_must_return_one_zip_attachment_and_one_protocol_reply"
    assert envelope["artifact"]["download_policy"] == "rendered_chatgpt_attachment_or_clickable_download_link_required"
    assert envelope["constraints"]["attachment_outside_envelope_required"] is True
    assert envelope["constraints"]["json_only_artifact_declaration_forbidden"] is True
    assert envelope["expected_output"]["success_component_count"] == 2
    assert envelope["expected_output"]["success_components_in_order"][0]["type"] == "rendered_chatgpt_downloadable_zip"
    assert envelope["expected_output"]["success_components_in_order"][1]["type"] == "promptbranch_reply_envelope"
    assert envelope["protocol_decisions"]["zip_attachment_outside_envelope"] is True
    assert envelope["expected_reply"]["artifact_policy"]["json_only_declaration_forbidden"] is True


def test_release_prompt_avoids_generic_json_only_lead_in() -> None:
    prompt = _prompt()

    assert "You MUST answer the current request with exactly one machine-readable reply envelope" not in prompt
    assert prompt.index("MANDATORY FINAL RESPONSE FORMAT") < prompt.index("PROMPTBRANCH REQUEST")
    assert prompt.index("PROMPTBRANCH REQUEST") < prompt.index("RELEASE-CANDIDATE IMPLEMENTATION REQUEST")


def test_shared_zip_prompt_without_release_renderer_keeps_existing_header() -> None:
    prompt = cli._build_zip_artifact_user_prompt(
        request_label="Visual artifact roundtrip request",
        expected_artifact="visual.zip",
        baseline=None,
        current_version=None,
        target_version=None,
        result_type="test_report",
        expected_role="visual_artifact_roundtrip_output",
        prompt_text="Create the visual artifact.",
        artifact_version_required=False,
        no_change_disallowed=True,
    )

    assert prompt.startswith("Visual artifact roundtrip request. Create exactly one ZIP artifact named visual.zip.")
    assert "Requested implementation scope:\nCreate the visual artifact." in prompt
