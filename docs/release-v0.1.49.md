# Release v0.1.49 — Source mutation queue planning per workspace

Base: `chatgpt_claudecode_workflow-2_v0.1.48.1.zip`

## Scope

`v0.1.49` adds a planning-only source mutation queue surface for Project Source writes.

Implemented:

- `promptbranch_source_queue.py`
- `pb src queue-plan --operation add|sync|remove --json`
- per-workspace `sources:{project_id}:exclusive` resource planning
- explicit source mutation verification plan
- `src_remove` and `source_mutation_plan` operation classifications
- focused tests for source queue planning and CLI/parser contract

## Boundary

This release does not execute source mutations.

Unchanged:

- `pb src add`
- `pb src sync`
- `pb src rm`
- source upload persistence behavior
- artifact adoption
- release lifecycle execution

The command emits a queue and verification plan only:

```bash
pb src queue-plan --operation add --file candidate.zip --json
```

## Safety policy

All source mutations remain serialized per workspace/source surface:

```text
sources:{project_id}:exclusive
service_profile:{service_id}:exclusive
```

The plan requires:

1. before source-list snapshot
2. queued service-browser source mutation
3. settled UI/backend state
4. after source-list snapshot
5. expected source delta verification
6. collateral-change detection
7. state update only after verified readback

## Validation

Recommended focused tests:

```bash
python3 -m pytest -q \
  tests/test_promptbranch_source_mutation_queue.py \
  tests/test_promptbranch_scheduler.py \
  tests/test_cli_parser.py::test_parser_accepts_src_queue_plan_command \
  tests/test_promptbranch_cli.py::test_src_queue_plan_command_emits_workspace_serialization_json \
  tests/test_promptbranch_cli.py::test_src_queue_plan_command_fails_closed_without_workspace
```

Recommended smokes:

```bash
python3 -m compileall -q .

pb --version
pb src queue-plan --operation add --workspace-url https://chatgpt.com/g/g-p-demo/project --file demo.zip --json | python3 -m json.tool
pb queue plan --operation src_remove --context account_id=default --context project_id=demo --context service_id=default --json | python3 -m json.tool
pb test artifact-roundtrip --json --path . | python3 -m json.tool
```
