from __future__ import annotations

from promptbranch_ask_protocol import REQUEST_SCHEMA
from promptbranch_parallel_ask import (
    MAX_PARALLEL_ASK_CONCURRENCY,
    ParallelAskRequestPlan,
    build_parallel_ask_serial_groups,
    normalize_parallel_ask_concurrency,
    parallel_ask_baseline_safety,
    parallel_ask_is_release_like,
    parallel_ask_plan_payload,
    parallel_ask_policy_payload,
)
from promptbranch_task_fanout import TaskFanoutTarget


def _target(identifier: str, *, url: str | None = None) -> TaskFanoutTarget:
    return TaskFanoutTarget(
        target=identifier,
        id=identifier,
        title=f"Task {identifier}",
        conversation_url=url or f"https://chatgpt.com/g/demo/c/{identifier}",
        source="project_endpoint",
    )


def _request(identifier: str, *, url: str | None = None) -> ParallelAskRequestPlan:
    target = _target(identifier, url=url)
    return ParallelAskRequestPlan(
        target=target,
        request_id=f"req_{identifier}",
        correlation_id=f"req_{identifier}",
        request={
            "schema": REQUEST_SCHEMA,
            "request_id": f"req_{identifier}",
            "correlation_id": f"req_{identifier}",
            "task": {"conversation_id": identifier, "conversation_url": target.conversation_url},
        },
    )


def test_parallel_ask_concurrency_is_bounded_by_distinct_groups() -> None:
    assert normalize_parallel_ask_concurrency(99) == MAX_PARALLEL_ASK_CONCURRENCY
    assert normalize_parallel_ask_concurrency(99, group_count=2) == 2
    assert normalize_parallel_ask_concurrency(0, group_count=3) == 1


def test_parallel_ask_policy_is_protocol_bound_and_planning_only() -> None:
    payload = parallel_ask_policy_payload()

    assert payload["ok"] is True
    assert payload["protocol_required"] is True
    assert payload["planning_only"] is True
    assert payload["automation_performed"] is False
    assert payload["same_conversation_writes_serialized"] is True


def test_parallel_ask_serial_groups_detect_same_conversation_overlap() -> None:
    duplicate_a = _request("abc")
    duplicate_b = _request("abc")
    other = _request("def")

    groups = build_parallel_ask_serial_groups([duplicate_a, duplicate_b, other])

    assert len(groups) == 2
    assert groups[0]["conversation_key"] == "abc"
    assert groups[0]["serialization_required"] is True
    assert groups[0]["request_count"] == 2
    assert groups[1]["conversation_key"] == "def"
    assert groups[1]["parallel_eligible"] is True


def test_parallel_ask_plan_emits_protocol_requests_and_conversation_locks() -> None:
    requests = [_request("abc"), _request("def")]

    payload = parallel_ask_plan_payload(
        requests=requests,
        requested_targets=["abc", "def"],
        concurrency=4,
        prompt="Summarize the current status",
        task_list_routing={"selected_path": "backend_first"},
    )

    assert payload["ok"] is True
    assert payload["status"] == "planned"
    assert payload["automation_performed"] is False
    assert payload["request_count"] == 2
    assert payload["conversation_group_count"] == 2
    assert payload["concurrency"] == 2
    assert payload["policy"]["protocol_required"] is True
    assert payload["resource_policy"]["same_conversation_overlap_allowed"] is False
    assert payload["resource_policy"]["different_conversation_parallel_allowed"] is True
    assert payload["protocol_requests"][0]["request"]["schema"] == REQUEST_SCHEMA
    assert payload["task_list_routing"]["selected_path"] == "backend_first"


def test_parallel_ask_module_is_declared_for_setuptools_install() -> None:
    import tomllib
    from pathlib import Path

    data = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    modules = data["tool"]["setuptools"]["py-modules"]
    assert "promptbranch_parallel_ask" in modules


def test_parallel_ask_release_like_detection() -> None:
    assert parallel_ask_is_release_like(intent_kind="software_release_request") is True
    assert parallel_ask_is_release_like(intent_kind="parallel_task_request") is False
    assert parallel_ask_is_release_like(intent_kind="parallel_task_request", target_version="v0.1.49") is True
    assert parallel_ask_is_release_like(intent_kind="parallel_task_request", baseline_version="v0.1.48.1") is True


def test_parallel_ask_baseline_safety_blocks_stale_release_without_override() -> None:
    request = {"artifact": {"current_baseline": "demo_v0.1.40.zip", "current_version": "v0.1.40"}}
    artifact_current = {
        "runtime": {"version": "v0.1.48.1"},
        "consistency": {"code_version_matches_state_source": False, "state_source_matches_state_artifact": True},
    }

    safety = parallel_ask_baseline_safety(request=request, artifact_current=artifact_current, release_like=True)

    assert safety["ok"] is False
    assert safety["blocking"] is True
    assert safety["status"] == "stale_release_baseline_blocked"


def test_parallel_ask_baseline_safety_allows_explicit_override() -> None:
    request = {"artifact": {"current_baseline": "demo_v0.1.40.zip", "current_version": "v0.1.40", "baseline_override": True}}
    artifact_current = {"runtime": {"version": "v0.1.48.1"}, "consistency": {}}

    safety = parallel_ask_baseline_safety(request=request, artifact_current=artifact_current, release_like=True)

    assert safety["ok"] is True
    assert safety["status"] == "explicit_baseline_override"
