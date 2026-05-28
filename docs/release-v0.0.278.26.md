# Release v0.0.278.26

Base release: v0.0.278.25
Release version: v0.0.278.26
Release type: normal diagnostic hardening release

## Reason

v0.0.278.25 proved that `/backend-api/f/conversation/prepare` returns HTTP 200 but no backend conversation commit appears for the submitted prompt marker. This release adds redacted diagnostics for the prepare response shape, stream status, conversation init, console/page errors, and post-prepare UI error state before fail-closed classification.

## Files changed

- `promptbranch_browser_auth/client.py`
- `VERSION`
- `pyproject.toml`
- `promptbranch_version.py`
- `docker-compose.chatgpt-service.yml`
- `tests/test_project_list_browser_client.py`
- version assertion tests
- `docs/release-v0.0.278.26.md`

## Validation performed

- Python compilation over repository Python files.
- Focused browser-client pytest suite.
- Version/container/compose focused pytest suite.
- ZIP hygiene verification before packaging.

## Scope confirmation

This release does not advance a product slice or broaden the release line. It preserves the fail-closed safety model and adds diagnostic evidence only.
