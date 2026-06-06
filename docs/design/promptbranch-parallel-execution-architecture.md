# Promptbranch Parallel Execution Architecture

Status: scheduler/resource lock inspection slice in `v0.1.43`  
Scope: Promptbranch / `chatgpt_claudecode_workflow-2`

## Goal

Make Promptbranch parallel by scheduling **resource ownership**, not by blindly opening more browsers.

The target is:

```text
pb command
  -> operation classifier
  -> resource planner
  -> scheduler / lease manager
  -> executor
       backend API
       local browser profile pool
       service browser profile queue/pool
       MCP/local read-only tools
       release engine
  -> verified strict JSON result
```

## Critical distinction

`v0.1.38` proved local profile-pool leases for browser-backed `pb task` reads, but that is only one part of the problem.

There are two different browser-profile domains:

```text
local browser profile
  host path such as ./.pb_profile_local_debug
  can be cloned into local profile-pool slots

service browser profile
  container path such as /app/.pb_profile
  currently serialized by the browser service lock
```

The observed `browser_profile_busy` error for `pb src add` came from the service browser profile. Local `--profile-pool` does not solve that path.

## Core model

Promptbranch keeps three independent scopes:

```text
Workspace = current ChatGPT Project
Task      = current chat/conversation inside the project
Artifact  = current source bundle, repo snapshot, or release ZIP
```

Parallel execution must respect this separation. A command that mutates one scope must not accidentally mutate or corrupt another.

## Resource classes

Every operation must declare its resource usage before execution.

Canonical resource identifiers:

```text
account:{account_id}
workspace:{project_id}
task:{conversation_id}
sources:{project_id}
artifact:{repo_id}
git_repo:{repo_path}
profile_pool:{profile_name}:{pool}:slot
service_profile:{service_id}
```

## Operation classes

### Read stateless

Examples:

```text
pb version
pb artifact verify
pb agent read-only operations
```

Policy:

```text
parallel: unlimited or local read-lock only
browser: no
mutation: no
queue: no
```

### Backend-first read

Examples:

```text
pb ws list
pb task list
pb task show
pb src list
```

Policy:

```text
parallel: yes, subject to account/rate-limit controls
preferred executor: backend JSON/network payload
fallback: DOM/browser only when backend is unavailable
```

### Browser fallback read

Examples:

```text
pb task list when backend data is unavailable
pb task show when transcript hydration needs browser fallback
```

Policy:

```text
parallel: yes only through profile-pool slots
same physical user-data-dir: never concurrently opened
```

### Conversation write

Examples:

```text
pb ask
pb task message answer
```

Policy:

```text
same conversation: serialize
different conversations: may parallelize when distinct profile slots and account limits allow
protocol envelope: required before automation consumes result
```

### Project source write

Examples:

```text
pb src add
pb src rm
pb src sync
```

Policy:

```text
serialize per workspace/source surface
queue when service profile is busy
verify persistence before state update
never treat UI transition as commit proof
```

### Artifact/release write

Examples:

```text
pb artifact adopt
pb release lifecycle
```

Policy:

```text
serialize per repository/artifact line
preserve baseline continuity
run acceptance before adoption
sync policy only after verified adoption
```

## JSON output invariant

All `--json` commands must emit strict JSON on stdout.

Logs and progress diagnostics must go to stderr or a log file.

Required test shape:

```bash
pb task list --json > out.json 2> out.log
python3 -m json.tool out.json
```

This is a prerequisite for any reliable parallel runner.


## Named profile registry (`v0.1.42`)

`v0.1.42` adds a read-only profile registry so later scheduler slices can refer to named profiles instead of ad-hoc paths.

Built-in profiles:

```text
local-debug
  kind: local_browser
  seed_dir: ./.pb_profile_local_debug or PROMPTBRANCH_LOCAL_DEBUG_PROFILE_DIR
  pools:
    tasks size=4
    ask   size=2

service-default
  kind: service_browser
  seed_dir: /app/.pb_profile or PROMPTBRANCH_SERVICE_PROFILE_DIR
  service_base_url: CHATGPT_SERVICE_BASE_URL / CHATGPT_API_BASE_URL / http://localhost:8000
  pools:
    sources size=1
    tasks   size=3
```

The service profile is metadata-only in this slice. It documents the future queue target for `/app/.pb_profile`, but does not yet clone service-side profiles or change `pb src add` execution.

Commands:

```bash
pb profile list --json
pb profile pools --json
pb profile pools --profile local-debug --json
pb profile show service-default --json
```

The registry intentionally treats a missing local seed profile as a structured `seed_missing` status, not as a command failure. This keeps profile discovery safe across repositories where `.pb_profile_local_debug` has not yet been created.

## Scheduler/resource lock planner (`v0.1.43`)

`v0.1.43` adds the first scheduler surface without yet routing command execution through it.

Implemented commands:

```bash
pb queue status --json
pb queue list --json
pb queue plan --operation src_add --context account_id=default --context project_id=demo --context service_id=default --json
pb queue conflicts --left-operation src_add --right-operation src_sync --context account_id=default --context project_id=demo --context service_id=default --context repo_path=. --json
```

Boundary of this slice:

```text
implemented:
  - render resource templates from command classification metadata
  - identify missing context instead of guessing
  - classify read/write/exclusive lock scopes
  - detect direct resource conflicts
  - expose queue status/list as strict JSON

not implemented yet:
  - no command execution is routed through the scheduler
  - no service browser queue is active yet
  - no source mutation behavior changes yet
```

This keeps `v0.1.43` safe and testable. Runtime source/upload behavior still changes later in the service-queue slice.

## Scheduler target

The future scheduler should do this:

```text
1. classify command
2. calculate required resources
3. acquire locks or queue operation
4. execute only after resources are available
5. release resources
6. emit strict JSON with operation_id and resource evidence
```

Example operation envelope:

```json
{
  "operation_id": "op_20260605_150901_abc123",
  "command": "src_add",
  "resources_requested": [
    "workspace:candlecast2",
    "sources:candlecast2",
    "service_profile:default"
  ],
  "resources_acquired": true,
  "queued": false,
  "status": "verified"
}
```

## Slice plan and cumulative tests

Every slice must add tests. Later slices keep prior tests and add their own focused tests. The eventual full test is the union of all slice tests plus release-control.

| Slice | Goal | Required tests |
|---|---|---|
| `v0.1.41` | Document architecture, add operation classification metadata, add `pb debug parallel-plan`, route browser `_log` output to stderr. | `pytest -q tests/test_promptbranch_parallel.py tests/test_cli_parser.py::test_parser_accepts_debug_parallel_plan_command tests/test_promptbranch_cli.py::test_debug_parallel_plan_emits_command_metadata_json tests/test_promptbranch_cli.py::test_browser_client_log_writes_to_stderr`; `python3 -m compileall -q .`; `pb debug parallel-plan --json \| python3 -m json.tool` |
| `v0.1.42` | Add named profile registry for local browser profiles and future service profile queues. | prior tests + `pytest -q tests/test_promptbranch_profile_registry.py`; `pb profile list --json \| python3 -m json.tool`; `pb profile pools --json \| python3 -m json.tool`; `pb profile show service-default --json \| python3 -m json.tool` |
| `v0.1.43` | Add scheduler/resource lock planner and read-only queue inspection commands. | prior tests + `pytest -q tests/test_promptbranch_scheduler.py`; `pb queue status --json \| python3 -m json.tool`; `pb queue plan --operation src_add --context account_id=default --context project_id=demo --context service_id=default --json \| python3 -m json.tool` |
| `v0.1.44` | Queue service-backed browser operations instead of immediate `browser_profile_busy` failure. | prior tests + `pytest -q tests/test_promptbranch_service_queue.py`; `pb browser status --json \| python3 -m json.tool` |
| `v0.1.45` | Add backend-first task/source read diagnostics before changing live read routing. | prior tests + `pytest -q tests/test_promptbranch_backend_reads.py`; strict JSON smoke for `pb debug backend-reads --plan-only --json` |
| `v0.1.46` | Use backend-read diagnostics for actual task-list routing; keep source-list backend-first blocked when provenance is missing. | prior tests + focused routing tests; strict JSON smoke for `pb task list --json`, `pb src list --json`, and `pb debug backend-reads --json` |
| `v0.1.46` | Add read-only parallel task runner. | prior tests + `pytest -q tests/test_promptbranch_parallel_runner.py`; `pb parallel task show --tasks 1,2 --concurrency 2 --json \| python3 -m json.tool` |
| `v0.1.47` | Add protocol-bound parallel asks across different conversations while serializing same-conversation writes. | prior tests + `pytest -q tests/test_promptbranch_parallel_ask.py`; `pb parallel ask --dry-run --tasks 1,2 --protocol --json \| python3 -m json.tool` |
| `v0.1.48` | Queue source mutations per workspace with transactional verification. | prior tests + `pytest -q tests/test_promptbranch_source_mutation_queue.py`; source mutation dry-run JSON smoke |
| `v0.1.49` | Integrate release lifecycle with scheduler locks and source upload queue. | prior tests + `pytest -q tests/test_promptbranch_release_lifecycle_scheduler.py`; release lifecycle dry-run JSON smoke |

## Definition of done for the architecture line

The architecture line is complete when:

```text
- all JSON commands used by automation are strict JSON on stdout
- every command has operation classification metadata
- local and service profiles are represented in one registry
- scheduler locks account/workspace/task/source/artifact/profile resources
- backend-first reads reduce browser contention
- mutations are queued and transactional
- parallel task reads are supported
- parallel asks are supported only across different conversations
- source/artifact/release mutations serialize safely
- full release-control passes with the accumulated test set
```

## Scheduler/resource lock inspection (`v0.1.43`)

`v0.1.43` adds an executable resource planning surface before live queue mutation:

```bash
pb queue status --json
pb queue list --json
pb queue plan --operation src_add --context account_id=default --context project_id=<id> --context service_id=default --json
pb queue conflicts --left-operation src_add --right-operation src_sync --context account_id=default --context project_id=<id> --context repo_path=. --context service_id=default --json
```

The scheduler slice is intentionally inspection-only. It proves command/resource classification and conflict planning before any browser-backed operation is routed through a queue.

## Backend-first read diagnostics (`v0.1.45`)

`v0.1.45` adds a read-only diagnostic surface before rerouting live task/source reads.

```bash
pb debug backend-reads --json
pb debug backend-reads --plan-only --json
pb debug backend-reads --operation task_list --json
pb debug backend-reads --operation source_list --json
```

The diagnostic classifies task-list payloads as `backend_indexed`, `fallback_only`, `recent_state_only`, `undifferentiated`, or `missing`.

For Project Source lists, the diagnostic intentionally flags `metadata_gap` when the payload does not expose whether the source list came from a backend/network source or DOM fallback. That keeps the backend-first migration honest: no read path is claimed backend-first without explicit evidence.

Boundary: this slice does not change `pb task list`, `pb task show`, `pb src list`, or source mutation behavior. It only exposes the evidence needed for the next read-routing slice.

## Service-profile bounded wait queue (`v0.1.44`)

`v0.1.44` starts the first live service-profile queue behavior for Project Source upload.

Scope:

```text
pb src add / project-source-add
  default service profile wait: 600 seconds
  queue mode: bounded_wait_for_single_service_profile
  opt-out: --no-queue
  override: --profile-wait-timeout-seconds <seconds>
```

This is not multi-profile service cloning yet. It is a single-owner bounded wait queue around `/app/.pb_profile`, so source upload waits for an active operation such as `get_chat` before failing with `browser_profile_busy`.

The implementation remains fail-closed:

```text
project_source_mutated=false when timeout occurs
persistence_verified=false when timeout occurs
queue_wait_timeout_seconds is reported in the JSON payload
```

Acceptance smoke:

```bash
pb browser status --json | python3 -m json.tool
pb queue plan --operation src_add --context account_id=default --context project_id=demo --context service_id=default --json | python3 -m json.tool
pb src add --file <zip> --profile-wait-timeout-seconds 600 --json | python3 -m json.tool
```


## Backend-first read routing (`v0.1.46`)

`v0.1.46` turns the read-only diagnostics from `v0.1.45` into runtime routing for the safe part of the read surface. `pb task list` now reads the lightweight backend/indexed project task list first. If `--deep-history` is requested, global history is used only when backend/indexed evidence is missing.

`pb src list` remains intentionally conservative. The live `v0.1.45` diagnostic showed source-list payloads can contain sources without reliable backend-vs-DOM provenance. `v0.1.46` therefore adds `read_routing.mode=backend_first_blocked` and keeps the source path explicit-fallback until the service exposes source provenance.
