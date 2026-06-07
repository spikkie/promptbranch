from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class OperationClass:
    """Declarative execution metadata for future Promptbranch parallel scheduling.

    This is intentionally policy data, not a scheduler yet. The first parallel
    architecture slice makes resource ownership explicit so later releases can
    add a queue/lease manager without guessing command semantics from argv.
    """

    operation: str
    command_group: str
    risk: str
    preferred_executor: str
    parallel_policy: str
    resource_templates: tuple[str, ...]
    transactional: bool
    json_stdout_strict: bool
    queue_required: bool
    notes: str

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["resource_templates"] = list(self.resource_templates)
        return payload


PARALLEL_ARCHITECTURE_VERSION = "1.0"

OPERATION_CLASSES: dict[str, OperationClass] = {
    "version": OperationClass(
        operation="version",
        command_group="version",
        risk="read_stateless",
        preferred_executor="local",
        parallel_policy="unlimited",
        resource_templates=(),
        transactional=False,
        json_stdout_strict=True,
        queue_required=False,
        notes="Pure local version read. No browser, workspace, task, source, artifact, or service lock required.",
    ),
    "agent_readonly": OperationClass(
        operation="agent_readonly",
        command_group="agent",
        risk="read_stateless",
        preferred_executor="mcp_local",
        parallel_policy="unlimited_per_repo_read_lock",
        resource_templates=("git_repo:{repo_path}:read",),
        transactional=False,
        json_stdout_strict=True,
        queue_required=False,
        notes="Read-only local MCP/agent operations may run concurrently as long as they do not request write/process tools.",
    ),
    "artifact_verify": OperationClass(
        operation="artifact_verify",
        command_group="artifact",
        risk="read_stateless",
        preferred_executor="local",
        parallel_policy="unlimited_per_file_read_lock",
        resource_templates=("artifact_file:{artifact_path}:read",),
        transactional=False,
        json_stdout_strict=True,
        queue_required=False,
        notes="ZIP verification is local and read-only; it should remain independent of ChatGPT/browser capacity.",
    ),
    "release_doctor": OperationClass(
        operation="release_doctor",
        command_group="release",
        risk="read_backend",
        preferred_executor="mixed_local_backend",
        parallel_policy="rate_limited_read",
        resource_templates=("git_repo:{repo_path}:read", "account:{account_id}:read", "workspace:{project_id}:read"),
        transactional=False,
        json_stdout_strict=True,
        queue_required=False,
        notes="Read-only status collection may use backend/browser fallbacks but must not mutate release, source, or artifact state.",
    ),
    "ws_list": OperationClass(
        operation="ws_list",
        command_group="ws",
        risk="read_backend",
        preferred_executor="backend_first",
        parallel_policy="rate_limited_read",
        resource_templates=("account:{account_id}:read",),
        transactional=False,
        json_stdout_strict=True,
        queue_required=False,
        notes="Workspace listing should prefer backend project payloads and only fall back to DOM scraping when necessary.",
    ),
    "task_list": OperationClass(
        operation="task_list",
        command_group="task",
        risk="read_backend_or_browser",
        preferred_executor="backend_first_then_local_browser_pool",
        parallel_policy="profile_pool_or_backend_read",
        resource_templates=("account:{account_id}:read", "workspace:{project_id}:read", "profile_pool:{profile_name}:{pool}:slot"),
        transactional=False,
        json_stdout_strict=True,
        queue_required=False,
        notes="Task listing can be parallel when backend-backed or when each browser fallback has a distinct leased profile slot.",
    ),
    "task_show": OperationClass(
        operation="task_show",
        command_group="task",
        risk="read_backend_or_browser",
        preferred_executor="backend_first_then_local_browser_pool",
        parallel_policy="profile_pool_or_backend_read",
        resource_templates=("account:{account_id}:read", "workspace:{project_id}:read", "task:{conversation_id}:read", "profile_pool:{profile_name}:{pool}:slot"),
        transactional=False,
        json_stdout_strict=True,
        queue_required=False,
        notes="Task transcript reads may run in parallel across tasks when output is strict JSON and browser fallbacks use separate profile slots.",
    ),
    "task_fanout": OperationClass(
        operation="task_fanout",
        command_group="parallel",
        risk="read_backend_or_browser",
        preferred_executor="backend_first_then_local_browser_pool",
        parallel_policy="parallel_read_only_across_distinct_task_read_locks",
        resource_templates=("account:{account_id}:read", "workspace:{project_id}:read", "task:{conversation_id}:read", "profile_pool:{profile_name}:{pool}:slot"),
        transactional=False,
        json_stdout_strict=True,
        queue_required=False,
        notes="Read-only task fan-out may fetch multiple task transcripts concurrently; same-conversation writes remain serialized by task exclusive locks and are not routed through this command.",
    ),
    "ask": OperationClass(
        operation="ask",
        command_group="ask",
        risk="write_conversation",
        preferred_executor="local_browser_pool_or_service_queue",
        parallel_policy="serialize_per_conversation_allow_different_tasks",
        resource_templates=("account:{account_id}:write", "workspace:{project_id}:write", "task:{conversation_id}:exclusive", "profile_pool:{profile_name}:ask:slot"),
        transactional=True,
        json_stdout_strict=True,
        queue_required=True,
        notes="Parallel asks are safe only across different conversations; the same conversation must serialize to avoid composer/answer races.",
    ),
    "parallel_ask_plan": OperationClass(
        operation="parallel_ask_plan",
        command_group="parallel",
        risk="write_conversation_plan_only",
        preferred_executor="scheduler_plan_only",
        parallel_policy="plan_parallel_across_distinct_conversations_serialize_same_conversation",
        resource_templates=("account:{account_id}:read", "workspace:{project_id}:read", "task:{conversation_id}:exclusive", "profile_pool:{profile_name}:ask:slot"),
        transactional=True,
        json_stdout_strict=True,
        queue_required=True,
        notes="Planning-only surface for protocol-bound asks. It emits per-target ask.request envelopes and conversation write locks but does not send prompts in this slice.",
    ),
    "src_list": OperationClass(
        operation="src_list",
        command_group="src",
        risk="read_backend_or_browser",
        preferred_executor="backend_first_then_service_browser",
        parallel_policy="rate_limited_read_or_service_queue",
        resource_templates=("account:{account_id}:read", "workspace:{project_id}:read", "sources:{project_id}:read"),
        transactional=False,
        json_stdout_strict=True,
        queue_required=False,
        notes="Source listing should become backend-first. Browser fallback must not block write operations indefinitely.",
    ),
    "src_add": OperationClass(
        operation="src_add",
        command_group="src",
        risk="write_project_sources",
        preferred_executor="service_browser_queue",
        parallel_policy="serialize_per_workspace_sources",
        resource_templates=("account:{account_id}:write", "workspace:{project_id}:write", "sources:{project_id}:exclusive", "service_profile:{service_id}:exclusive"),
        transactional=True,
        json_stdout_strict=True,
        queue_required=True,
        notes="Project Source mutation must queue per workspace and verify persistence before state changes.",
    ),
    "src_sync": OperationClass(
        operation="src_sync",
        command_group="src",
        risk="write_project_sources",
        preferred_executor="service_browser_queue",
        parallel_policy="serialize_per_workspace_sources",
        resource_templates=("account:{account_id}:write", "workspace:{project_id}:write", "sources:{project_id}:exclusive", "git_repo:{repo_path}:read", "service_profile:{service_id}:exclusive"),
        transactional=True,
        json_stdout_strict=True,
        queue_required=True,
        notes="Source sync packages local state and mutates Project Sources; it cannot run concurrently with source add/remove in the same workspace.",
    ),
    "src_remove": OperationClass(
        operation="src_remove",
        command_group="src",
        risk="write_project_sources",
        preferred_executor="service_browser_queue",
        parallel_policy="serialize_per_workspace_sources",
        resource_templates=("account:{account_id}:write", "workspace:{project_id}:write", "sources:{project_id}:exclusive", "service_profile:{service_id}:exclusive"),
        transactional=True,
        json_stdout_strict=True,
        queue_required=True,
        notes="Project Source removal must queue per workspace and verify the exact expected source delta without collateral removals.",
    ),
    "source_mutation_plan": OperationClass(
        operation="source_mutation_plan",
        command_group="src",
        risk="write_project_sources_plan_only",
        preferred_executor="scheduler_plan_only",
        parallel_policy="plan_serialize_per_workspace_sources",
        resource_templates=("account:{account_id}:read", "workspace:{project_id}:read", "sources:{project_id}:exclusive", "service_profile:{service_id}:exclusive"),
        transactional=True,
        json_stdout_strict=True,
        queue_required=True,
        notes="Planning-only source mutation queue surface. It renders per-workspace source locks and verification steps but does not mutate Project Sources.",
    ),
    "artifact_adopt": OperationClass(
        operation="artifact_adopt",
        command_group="artifact",
        risk="write_artifact_repo",
        preferred_executor="local_release_engine",
        parallel_policy="serialize_per_repo_artifact_line",
        resource_templates=("git_repo:{repo_path}:exclusive", "artifact:{repo_id}:exclusive"),
        transactional=True,
        json_stdout_strict=True,
        queue_required=True,
        notes="Artifact adoption changes accepted baseline state and must serialize per repository/artifact line.",
    ),
    "release_lifecycle": OperationClass(
        operation="release_lifecycle",
        command_group="release",
        risk="write_artifact_repo_and_project_sources",
        preferred_executor="release_engine_plus_service_queue",
        parallel_policy="serialize_per_repo_and_workspace_sources",
        resource_templates=("git_repo:{repo_path}:exclusive", "artifact:{repo_id}:exclusive", "workspace:{project_id}:write", "sources:{project_id}:exclusive", "service_profile:{service_id}:exclusive"),
        transactional=True,
        json_stdout_strict=True,
        queue_required=True,
        notes="Full lifecycle spans install, source upload, tests, adoption, policy sync, and Git state; do not overlap for the same repo or project.",
    ),
}


SLICE_TEST_PLAN: list[dict[str, Any]] = [
    {
        "slice": "v0.1.41",
        "goal": "Document parallel architecture, add command classification metadata, and restore browser log stderr behavior for strict JSON stdout.",
        "tests": [
            "python3 -m pytest -q tests/test_promptbranch_parallel.py tests/test_cli_parser.py::test_parser_accepts_debug_parallel_plan_command tests/test_promptbranch_cli.py::test_debug_parallel_plan_emits_command_metadata_json tests/test_promptbranch_cli.py::test_browser_client_log_writes_to_stderr",
            "python3 -m compileall -q .",
            "pb debug parallel-plan --json | python3 -m json.tool",
        ],
    },
    {
        "slice": "v0.1.42",
        "goal": "Add named profile registry for local browser profiles and future service profile queues.",
        "tests": [
            "python3 -m pytest -q tests/test_promptbranch_parallel.py tests/test_promptbranch_profile_registry.py tests/test_cli_parser.py::test_parser_accepts_debug_parallel_plan_command tests/test_cli_parser.py::test_parser_accepts_profile_registry_commands tests/test_promptbranch_cli.py::test_debug_parallel_plan_emits_command_metadata_json tests/test_promptbranch_cli.py::test_profile_list_command_emits_profile_registry_json tests/test_promptbranch_cli.py::test_profile_pools_command_emits_flattened_pool_json tests/test_promptbranch_cli.py::test_browser_client_log_writes_to_stderr",
            "python3 -m compileall -q .",
            "pb debug parallel-plan --json | python3 -m json.tool",
            "pb profile list --json | python3 -m json.tool",
            "pb profile pools --json | python3 -m json.tool",
        ],
    },
    {
        "slice": "v0.1.43",
        "goal": "Add scheduler/resource lock planner and read-only queue inspection commands.",
        "tests": [
            "python3 -m pytest -q tests/test_promptbranch_parallel.py tests/test_promptbranch_profile_registry.py tests/test_promptbranch_scheduler.py tests/test_cli_parser.py::test_parser_accepts_debug_parallel_plan_command tests/test_cli_parser.py::test_parser_accepts_profile_registry_commands tests/test_cli_parser.py::test_parser_accepts_queue_inspection_commands tests/test_promptbranch_cli.py::test_debug_parallel_plan_emits_command_metadata_json tests/test_promptbranch_cli.py::test_profile_list_command_emits_profile_registry_json tests/test_promptbranch_cli.py::test_profile_pools_command_emits_flattened_pool_json tests/test_promptbranch_cli.py::test_queue_status_command_emits_scheduler_json tests/test_promptbranch_cli.py::test_queue_plan_command_emits_resource_plan_json tests/test_promptbranch_cli.py::test_browser_client_log_writes_to_stderr",
            "python3 -m compileall -q .",
            "pb debug parallel-plan --json | python3 -m json.tool",
            "pb profile list --json | python3 -m json.tool",
            "pb profile pools --json | python3 -m json.tool",
            "pb queue status --json | python3 -m json.tool",
            "pb queue plan --operation src_add --context account_id=default --context project_id=demo --context service_id=default --json | python3 -m json.tool",
        ],
    },
    {
        "slice": "v0.1.44",
        "goal": "Route service-backed browser operations through queue/wait semantics instead of immediate browser_profile_busy failure.",
        "tests": [
            "pb browser status --json | python3 -m json.tool",
            "pytest -q tests/test_promptbranch_service_queue.py",
        ],
    },
    {
        "slice": "v0.1.45",
        "goal": "Move task/source reads backend-first with DOM fallback only when required.",
        "tests": [
            "pb task list --json > /tmp/pb_task_list.json 2> /tmp/pb_task_list.log && python3 -m json.tool /tmp/pb_task_list.json",
            "pytest -q tests/test_promptbranch_backend_first_reads.py",
        ],
    },
    {
        "slice": "v0.1.46",
        "goal": "Use backend-read diagnostics for actual backend-first task list routing while keeping source reads explicit-fallback on provenance gaps.",
        "tests": [
            "python3 -m pytest -q tests/test_promptbranch_backend_reads.py tests/test_promptbranch_cli.py::test_chat_list_deep_history_skips_history_when_backend_indexed tests/test_promptbranch_cli.py::test_chat_list_deep_history_uses_fallback_when_backend_missing tests/test_promptbranch_cli.py::test_project_source_list_json_marks_metadata_gap_routing",
            "python3 -m compileall -q .",
            "pb task list --json | python3 -m json.tool",
            "pb src list --json | python3 -m json.tool",
            "pb debug backend-reads --json | python3 -m json.tool",
        ],
    },
    {
        "slice": "v0.1.47",
        "goal": "Add read-only parallel task fan-out while preserving same-conversation write serialization policy.",
        "tests": [
            "python3 -m pytest -q tests/test_promptbranch_task_fanout.py tests/test_cli_parser.py::test_parser_accepts_parallel_task_show_command tests/test_promptbranch_cli.py::test_parallel_task_show_plan_only_emits_read_only_policy tests/test_promptbranch_cli.py::test_parallel_task_show_fetches_targets_without_mutating_current_state",
            "python3 -m compileall -q .",
            "pb parallel policy --json | python3 -m json.tool",
            "pb parallel task show --task 1 --plan-only --json | python3 -m json.tool",
        ],
    },
    {
        "slice": "v0.1.48",
        "goal": "Add protocol-bound parallel ask planning across different conversations while serializing same-conversation writes.",
        "tests": [
            "python3 -m pytest -q tests/test_promptbranch_parallel_ask.py tests/test_cli_parser.py::test_parser_accepts_parallel_ask_plan_command tests/test_promptbranch_cli.py::test_parallel_ask_plan_builds_protocol_requests_and_serializes_same_conversation",
            "python3 -m compileall -q .",
            "pb parallel ask --task 1 --task 2 --plan-only --protocol --json 'summarize status' | python3 -m json.tool",
        ],
    },
    {
        "slice": "v0.1.49",
        "goal": "Queue source mutations per workspace with transactional verification.",
        "tests": [
            "pytest -q tests/test_promptbranch_source_mutation_queue.py",
            "pb src add --dry-run --queue --json <artifact> | python3 -m json.tool",
        ],
    },
    {
        "slice": "v0.1.50",
        "goal": "Integrate release lifecycle with scheduler locks and source upload queue.",
        "tests": [
            "pytest -q tests/test_promptbranch_release_lifecycle_scheduler.py",
            "pb release lifecycle --dry-run --json --artifact <zip> --version <version> | python3 -m json.tool",
        ],
    },
]


def command_classification(operation: str | None = None) -> dict[str, Any]:
    if operation:
        if operation not in OPERATION_CLASSES:
            return {
                "ok": False,
                "status": "unknown_operation",
                "operation": operation,
                "known_operations": sorted(OPERATION_CLASSES),
            }
        return {
            "ok": True,
            "schema": "promptbranch.parallel.operation_classification",
            "schema_version": PARALLEL_ARCHITECTURE_VERSION,
            "status": "classified",
            "operation": OPERATION_CLASSES[operation].to_dict(),
        }
    return {
        "ok": True,
        "schema": "promptbranch.parallel.operation_registry",
        "schema_version": PARALLEL_ARCHITECTURE_VERSION,
        "status": "classified",
        "operation_count": len(OPERATION_CLASSES),
        "operations": {key: value.to_dict() for key, value in sorted(OPERATION_CLASSES.items())},
    }


def parallel_architecture_payload(operation: str | None = None) -> dict[str, Any]:
    classification = command_classification(operation)
    return {
        "ok": bool(classification.get("ok")),
        "action": "debug_parallel_plan",
        "status": classification.get("status"),
        "schema": "promptbranch.parallel.plan",
        "schema_version": PARALLEL_ARCHITECTURE_VERSION,
        "architecture": {
            "goal": "Make Promptbranch parallel by scheduling resource ownership, not by blindly opening more browsers.",
            "principles": [
                "strict JSON stdout for --json commands",
                "backend-first reads before DOM scaling",
                "resource locks for every command class",
                "profile pools only for browser fallbacks that can safely use cloned slots",
                "serialize mutations by task, workspace, source surface, repo, and artifact line",
                "transactional writes with verified re-read before state update",
                "queue service-backed browser operations instead of failing immediately with browser_profile_busy",
            ],
            "resource_model": [
                "account:{account_id}",
                "workspace:{project_id}",
                "task:{conversation_id}",
                "sources:{project_id}",
                "artifact:{repo_id}",
                "git_repo:{repo_path}",
                "profile_pool:{profile_name}:{pool}:slot",
                "service_profile:{service_id}",
            ],
        },
        "classification": classification,
        "test_policy": {
            "default_cadence": "lightweight_cumulative_slice_tests",
            "full_test_required_when": [
                "scheduler or queue behavior changes",
                "service-backed browser profile behavior changes",
                "Project Source mutations change",
                "artifact adoption or release lifecycle behavior changes",
                "a focused regression is unexplained",
                "operator wants to accept a major stable baseline",
            ],
            "required_every_slice": [
                "new slice focused tests",
                "all prior parallel-line focused tests",
                "python3 -m compileall -q .",
                "strict JSON smoke for new/changed --json commands",
                "pb test artifact-roundtrip --json --path .",
            ],
        },
        "slice_test_plan": SLICE_TEST_PLAN,
    }
