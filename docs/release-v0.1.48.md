# Release v0.1.48 — Protocol-bound parallel ask planning

Base: `chatgpt_claudecode_workflow-2_v0.1.47.1.zip`

## Scope

This release adds a planning-only surface for future parallel asks:

```bash
pb parallel ask "summarize status" --task 1 --task 2 --plan-only --protocol --json
```

The command resolves target tasks, builds one Promptbranch `ask.request` protocol envelope per target conversation, and emits resource policy metadata for future scheduler execution.

## Safety boundary

- No prompt is sent in this release.
- No conversation is mutated.
- `pb ask` behavior is unchanged.
- Same-conversation writes remain serialized by `task:{conversation_id}:exclusive`.
- Different conversations are only marked as future parallel-eligible when distinct conversation write locks are present.

## Files changed

- `VERSION`
- `pyproject.toml`
- `promptbranch_version.py`
- `docker-compose.chatgpt-service.yml`
- `promptbranch_parallel.py`
- `promptbranch_parallel_ask.py`
- `promptbranch_cli.py`
- `docs/design/promptbranch-parallel-execution-architecture.md`
- `tests/test_promptbranch_parallel_ask.py`
- `tests/test_promptbranch_cli.py`
- `tests/test_cli_parser.py`

## Validation

Focused tests and strict JSON smokes should cover:

```bash
python3 -m pytest -q \
  tests/test_promptbranch_parallel.py \
  tests/test_promptbranch_task_fanout.py \
  tests/test_promptbranch_parallel_ask.py \
  tests/test_cli_parser.py::test_parser_accepts_parallel_ask_plan_command \
  tests/test_promptbranch_cli.py::test_parallel_ask_plan_builds_protocol_requests_and_serializes_same_conversation

python3 -m compileall -q .
pb parallel ask "summarize status" --task 1 --task 2 --plan-only --protocol --json | python3 -m json.tool
pb test artifact-roundtrip --json --path . | python3 -m json.tool
```
