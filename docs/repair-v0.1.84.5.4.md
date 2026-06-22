# Repair v0.1.84.5.4 — Recovered 429 live-test continuation policy

## Base release

`v0.1.84.5.3` repair candidate context. Accepted/current baseline remains `chatgpt_claudecode_workflow-2_v0.1.84.5.zip` until adoption evidence proves a newer artifact.

## Repair version

`v0.1.84.5.4`

## Reason

The v0.1.84.5.3 run-all log showed otherwise functional `ask_live` and `visual_artifact_roundtrip` results being marked `rate_limited_contaminated` with `ok=false` after ChatGPT 429 telemetry had already been acknowledged and waited through in the active browser operation. Release-control then retried the whole step. That does not match the intended operator workflow: click `Got it`, wait, keep the browser open, and continue the same validated operation.

## Files changed

- `VERSION`
- `pyproject.toml`
- `promptbranch_version.py`
- `promptbranch_cli.py`
- `tests/test_promptbranch_cli.py`
- `docs/repair-v0.1.84.5.4.md`
- `docs/project/status.md`
- `docs/project/plan.md`
- `docs/project/definition-of-done.md`
- `docs/project/release-status.md`
- `docs/project/decisions.md`
- `docs/project/migration.md`

## Behavior change

- Functional live-test success plus recovered 429 telemetry now reports `ok=true` and `status=verified_with_recovered_rate_limit`.
- Recovered means the telemetry includes a cooldown wait or modal acknowledgement with cooldown satisfaction evidence.
- Unrecovered 429 evidence remains `ok=false` / `rate_limited_contaminated`.
- Release-control no longer retries a live-test step merely because recovered 429 telemetry was observed after functional success.

## Boundaries preserved

- No project deletion re-enable.
- No ledger creation or append.
- No `accept-event --write`.
- No Project Source mutation behavior change.
- No artifact adoption/current behavior change.
- No deployment or model-execution behavior change.

## Validation

Focused validation before handoff:

- Recovered visual artifact 429 test passes as `verified_with_recovered_rate_limit`.
- Unrecovered ask-live 429 test remains `rate_limited_contaminated` and fails closed.
- Rate-limit recovery predicate tests cover cooldown and modal-ack satisfaction.
- Version and project-control tests pass.
- Compileall, shell syntax, orchestration validate-ledger, Artifact Guardian, and ZIP hygiene pass.

## Slice advancement

No slice or line advanced. This is a repair-only candidate.
