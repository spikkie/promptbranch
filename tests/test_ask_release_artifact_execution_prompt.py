from __future__ import annotations

import promptbranch_cli as cli


BASELINE = "chatgpt_claudecode_workflow-2_v0.1.123.2.3.zip"
BASELINE_VERSION = "v0.1.123.2.3"
TARGET_VERSION = "v0.1.124"
EXPECTED = "chatgpt_claudecode_workflow-2_v0.1.124.zip"
REQUEST_ID = "req_20260804T194110060130Z"


def _prompt() -> str:
    envelope = {
        "request_id": REQUEST_ID,
        "artifact": {
            "current_baseline": BASELINE,
            "current_version": BASELINE_VERSION,
            "target_version": TARGET_VERSION,
        },
    }
    expected = {
        "expected_artifact": EXPECTED,
        "expected_version": TARGET_VERSION,
        "expected_role": "candidate_release",
    }
    return cli._build_ask_release_user_prompt(
        "Create the requested normal release from accepted/current.",
        expected,
        envelope,
    )


def test_ask_release_prompt_requires_fresh_baseline_derived_physical_zip() -> None:
    prompt = _prompt()

    assert f"Use the exact accepted/current release artifact {BASELINE}" in prompt
    assert f"(version {BASELINE_VERSION}) as the actual source baseline" in prompt
    assert f"create a brand-new release ZIP named {EXPECTED}" in prompt
    assert f"for target version {TARGET_VERSION}" in prompt
    assert "complete repository contents derived from the accepted/current baseline" in prompt
    assert "Before writing the Promptbranch reply envelope, create the physical ZIP artifact" in prompt


def test_ask_release_prompt_requires_real_attachment_before_completed_envelope() -> None:
    prompt = _prompt()

    assert "Attach the created ZIP to this exact assistant answer as a real ChatGPT downloadable attachment" in prompt
    assert "A filename in JSON, a sandbox path written as text, or a claim that the file exists is not sufficient" in prompt
    assert "Do not set status=completed unless the attachment is visibly materialized" in prompt
    assert f"its filename is exactly {EXPECTED}" in prompt
    assert "Only after the attachment exists, calculate its actual SHA-256, byte size, and ZIP entry count" in prompt
    assert "return status=failed, result_type=release_candidate, artifacts=[]" in prompt


def test_ask_release_prompt_binds_fresh_artifact_to_exact_request_id() -> None:
    prompt = _prompt()

    assert "Do not reuse, rename, or reference a ZIP created by an earlier answer or failed request" in prompt
    assert f"Create a fresh artifact for this exact request_id: {REQUEST_ID}" in prompt
    assert (
        "Create a brand-new ZIP from the exact accepted/current release artifact, attach that physical ZIP "
        "to this exact answer, and only then construct the reply envelope from the actual created file."
    ) in prompt


def test_hard_execution_contract_precedes_requested_implementation_scope() -> None:
    prompt = _prompt()

    assert prompt.index("Hard artifact-execution requirements:") < prompt.index("Requested implementation scope:")


def test_shared_zip_prompt_without_hard_requirements_keeps_existing_header() -> None:
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
