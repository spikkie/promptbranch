# Release v0.0.278.23

Base release: v0.0.278.22
Release version: v0.0.278.23
Release type: normal diagnostic repair on the v0.0.278 line

## Reason

v0.0.278.22 proved that the stale-answer path is fail-closed and that browser network observation is active, but the old warm task still did not emit a marker-bearing submit request. The composer appeared filled through `locator_fill` and cleared after submit, yet submit causality was not proven.

v0.0.278.23 changes prompt entry to a trusted-input-first strategy and expands post-click backend write diagnostics.

## Changes

- Default ChatGPT composer fill mode is now `trusted_paste`.
- Prompt fill sequence tries clipboard paste, then keyboard insertion, then `locator_fill` as last fallback.
- Prompt fill evidence now records trusted input usage, fallback chain, and composer-state verification.
- Submit network diagnostics now preserve all observed backend mutating write URLs, not only marker-matching requests.
- `/backend-api/f/conversation/prepare` is classified as diagnostic prepare traffic, not submit proof.
- Network snapshots report backend write event count, marker event count, prepare request observation, and message request candidates.
- Network request body previews are redacted while preserving body length and marker-match booleans.

## Files changed

- `VERSION`
- `pyproject.toml`
- `promptbranch_version.py`
- `docker-compose.chatgpt-service.yml`
- `promptbranch_browser_auth/client.py`
- `tests/test_project_list_browser_client.py`
- version assertion tests
- `docs/release-v0.0.278.23.md`

## Validation performed

- Python compile check over Promptbranch package and tests.
- Focused browser-client pytest suite.
- Focused version/container/compose pytest suite.
- ZIP hygiene and root-layout verification.

## Scope control

No baseline was adopted. No slice or project line was advanced. This release preserves v0.0.278.22 fail-closed semantics while improving submit input and network diagnostics.
