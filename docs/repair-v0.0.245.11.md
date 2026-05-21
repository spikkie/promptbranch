# Repair v0.0.245.11 — Protocol reply parse state-store API repair

Base release: v0.0.245.9
Repair version: v0.0.245.11

## Reason

`scripts/finalize-artifact-intake-mvp.sh --version v0.0.245.9 --target-version v0.0.246` reached protocol smoke after login, full tests, ZIP hygiene, adoption, and after-adopt semantic checks, but failed while parsing the protocol reply.

The protocol parse path called `ConversationStateStore.load().conversation_url`, but `ConversationStateStore` exposes `snapshot(...)` and not a public `load()` method. This caused a raw `AttributeError` before reply validation could run.

## Scope

Narrow repair only:

- Replace the stale `ConversationStateStore.load().conversation_url` usage in the protocol reply parse path.
- Resolve conversation URL from `ConversationStateStore.snapshot(...)` and its `task.conversation_url` fallback.
- Add a regression test for a parser-shaped no-artifact protocol reply where the service ask response omits `conversation_url`; the parser must use stored task state instead of crashing.

No normal release scope was advanced.

## Files changed

- `promptbranch_cli.py`
- `tests/test_promptbranch_cli.py`
- version/package metadata
- `docker-compose.chatgpt-service.yml`
- `docs/repair-v0.0.245.11.md`

## Validation

Performed during artifact construction:

- Python compile checks
- focused protocol parser regression tests
- focused container/API/MCP/version parser tests
- ZIP CRC check
- ZIP hygiene check

