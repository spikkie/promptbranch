from __future__ import annotations

from promptbranch_cli import _project_source_add_exception_payload


def test_source_add_gate_closed_payload_preserves_safe_validation_command() -> None:
    service_payload = {
        "ok": False,
        "status": "project_source_mutation_gate_closed",
        "release_blocking": True,
        "runtime": {
            "docker_browser_profile": "standard-browser",
            "standard_browser_mode": True,
            "project_source_mutation_allowed": False,
        },
    }

    payload = _project_source_add_exception_payload(
        RuntimeError("403 error for POST http://localhost:8000/v1/project-sources"),
        source_kind="file",
        file_path="chatgpt_claudecode_workflow-2_v0.1.103.10.7.zip",
        display_name="chatgpt_claudecode_workflow-2_v0.1.103.10.7.zip",
        overwrite_existing=True,
        service_payload=service_payload,
    )

    assert payload["ok"] is False
    assert payload["status"] == "project_source_mutation_gate_closed"
    assert payload["classification"] == "expected_safety_gate"
    assert payload["project_source_mutated"] is False
    assert payload["project_source_required_for_standard_browser_validation"] is False
    assert payload["runtime"]["project_source_mutation_allowed"] is False
    assert payload["next_safe_commands"][0] == (
        "./scripts/pb-browser-cloudflare-validation.sh "
        "--install-artifact chatgpt_claudecode_workflow-2_v0.1.103.10.7.zip "
        "--install-version v0.1.103.10.7"
    )


def test_source_add_gate_closed_payload_handles_non_candidate_names() -> None:
    payload = _project_source_add_exception_payload(
        RuntimeError("403 error for POST http://localhost:8000/v1/project-sources"),
        source_kind="file",
        file_path="notes.zip",
        display_name="notes.zip",
        overwrite_existing=True,
        service_payload={"status": "project_source_mutation_gate_closed"},
    )

    assert payload["status"] == "project_source_mutation_gate_closed"
    assert all("--install-version" not in command for command in payload["next_safe_commands"])
    assert payload["next_safe_commands"][0] == "./scripts/pb-browser-cloudflare-validation.sh --skip-bootstrap"
