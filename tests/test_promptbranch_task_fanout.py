from __future__ import annotations

from promptbranch_task_fanout import (
    MAX_TASK_FANOUT_CONCURRENCY,
    TaskFanoutTarget,
    normalize_task_fanout_concurrency,
    split_task_fanout_targets,
    task_fanout_plan_payload,
    task_fanout_policy_payload,
)


def test_split_task_fanout_targets_accepts_repeated_and_comma_values() -> None:
    assert split_task_fanout_targets(["1, 2", "abc", "", " title "]) == ["1", "2", "abc", "title"]


def test_task_fanout_concurrency_is_bounded_by_targets_and_cap() -> None:
    assert normalize_task_fanout_concurrency(99, target_count=2) == 2
    assert normalize_task_fanout_concurrency(99) == MAX_TASK_FANOUT_CONCURRENCY
    assert normalize_task_fanout_concurrency(0, target_count=4) == 1


def test_task_fanout_plan_declares_read_only_policy_and_write_serialization() -> None:
    target = TaskFanoutTarget(
        target="1",
        id="abc",
        title="Demo",
        conversation_url="https://chatgpt.com/g/demo/c/abc",
        source="project_endpoint",
    )
    payload = task_fanout_plan_payload(
        targets=[target],
        requested_targets=["1"],
        concurrency=4,
        task_list_routing={"selected_path": "backend_first"},
    )

    assert payload["ok"] is True
    assert payload["status"] == "planned"
    assert payload["policy"]["read_only"] is True
    assert payload["policy"]["same_conversation_writes_serialized"] is True
    assert payload["resource_policy"]["same_conversation_write_lock"] == "task:{conversation_id}:exclusive"
    assert payload["task_list_routing"]["selected_path"] == "backend_first"


def test_task_fanout_policy_payload_rejects_mutating_overlap() -> None:
    payload = task_fanout_policy_payload()
    assert payload["ok"] is True
    assert payload["read_only"] is True
    assert "ask" in payload["mutating_operations_rejected"]
    assert payload["same_conversation_writes_serialized"] is True
