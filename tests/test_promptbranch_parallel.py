from __future__ import annotations

from promptbranch_parallel import OPERATION_CLASSES, command_classification, parallel_architecture_payload


def test_parallel_operation_registry_covers_core_command_classes() -> None:
    required = {
        "version",
        "agent_readonly",
        "artifact_verify",
        "release_doctor",
        "ws_list",
        "task_list",
        "task_show",
        "ask",
        "src_list",
        "src_add",
        "src_sync",
        "artifact_adopt",
        "release_lifecycle",
    }

    assert required.issubset(OPERATION_CLASSES)

    for operation in required:
        payload = OPERATION_CLASSES[operation].to_dict()
        assert payload["operation"] == operation
        assert payload["risk"]
        assert payload["preferred_executor"]
        assert payload["parallel_policy"]
        assert isinstance(payload["resource_templates"], list)
        assert payload["json_stdout_strict"] is True


def test_parallel_classification_marks_mutating_operations_transactional_and_queued() -> None:
    for operation in ["ask", "src_add", "src_sync", "artifact_adopt", "release_lifecycle"]:
        payload = command_classification(operation)
        assert payload["ok"] is True
        classified = payload["operation"]
        assert classified["transactional"] is True
        assert classified["queue_required"] is True


def test_parallel_classification_rejects_unknown_operation() -> None:
    payload = command_classification("does_not_exist")

    assert payload["ok"] is False
    assert payload["status"] == "unknown_operation"
    assert "task_list" in payload["known_operations"]


def test_parallel_architecture_payload_includes_cumulative_slice_tests() -> None:
    payload = parallel_architecture_payload("src_add")

    assert payload["ok"] is True
    assert payload["action"] == "debug_parallel_plan"
    assert payload["classification"]["operation"]["operation"] == "src_add"
    assert payload["classification"]["operation"]["parallel_policy"] == "serialize_per_workspace_sources"
    assert payload["slice_test_plan"]
    assert payload["slice_test_plan"][0]["slice"] == "v0.1.41"
    assert any("pytest" in item for item in payload["slice_test_plan"][0]["tests"])
