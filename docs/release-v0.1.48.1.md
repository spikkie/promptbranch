# Repair release v0.1.48.1 — Parallel ask stale-baseline guard

Base release: `chatgpt_claudecode_workflow-2_v0.1.48.zip`
Repair version: `v0.1.48.1`

## Reason

`v0.1.48` introduced planning-only protocol-bound parallel ask envelopes. The command was mechanically green, but the live log showed that generic planning prompts could emit release-style envelopes using a stale artifact baseline (`v0.1.40`) while the installed runtime was `v0.1.48`.

That is semantically unsafe for later execution because stale `current_baseline` and inferred `target_version` fields could be treated as authoritative.

## Repair scope

- Default `pb parallel ask` intent is now `parallel_task_request`, not `software_release_request`.
- Non-release parallel ask plans do not infer `target_version` from artifact registry state.
- Release-like parallel ask plans fail closed when the protocol baseline version differs from installed runtime unless an explicit baseline override is supplied.
- The plan payload now includes `baseline_safety` metadata.
- Added stale-baseline regression tests.

## Files changed

- `VERSION`
- `pyproject.toml`
- `promptbranch_version.py`
- `docker-compose.chatgpt-service.yml`
- `promptbranch_ask_protocol.py`
- `promptbranch_parallel_ask.py`
- `promptbranch_cli.py`
- `docs/design/promptbranch-parallel-execution-architecture.md`
- `docs/release-v0.1.48.1.md`
- `tests/test_promptbranch_parallel_ask.py`
- `tests/test_promptbranch_cli.py`
- `tests/test_cli_parser.py`

## Validation performed

Recommended focused validation:

```bash
python3 -m pytest -q \
  tests/test_promptbranch_parallel_ask.py \
  tests/test_promptbranch_cli.py::test_parallel_ask_plan_builds_protocol_requests_and_serializes_same_conversation \
  tests/test_promptbranch_cli.py::test_parallel_ask_plan_blocks_release_request_when_baseline_is_stale \
  tests/test_promptbranch_cli.py::test_parallel_ask_plan_default_non_release_does_not_infer_target_from_stale_baseline \
  tests/test_cli_parser.py::test_parser_accepts_parallel_ask_plan_command

python3 -m compileall -q .
pb parallel ask "summarize status" --task 1 --task 2 --plan-only --protocol --json | python3 -m json.tool
pb test artifact-roundtrip --json --path . | python3 -m json.tool
```

## Slice continuity

No slice or line was advanced. This repair only fixes a defect in the intended `v0.1.48` planning-only protocol-bound parallel ask surface. `v0.1.49` remains the next normal release target.
