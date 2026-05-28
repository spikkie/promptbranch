# Repair release v0.0.278.16

Base release: v0.0.278.15
Repair version: v0.0.278.16

## Reason

Reduce old-task hydration overhead by reusing an already-warm target conversation when the browser is already on the requested task and the composer is usable. The previous path could still force same-task reload/transcript hydration, causing very large `hydration_seconds` on long conversations.

## Files changed

- `promptbranch_browser_auth/client.py`
- `tests/test_project_list_browser_client.py`
- `VERSION`
- `pyproject.toml`
- `promptbranch_version.py`
- `docker-compose.chatgpt-service.yml`
- current-version test expectations
- `docs/repair-v0.0.278.16.md`

## Validation performed

- Python compile validation for packaged Python files.
- Focused pytest for browser-client hydration/submit/response regressions and version/container checks.
- ZIP hygiene verification.

## Slice advancement

No slice or line was advanced. This release only repairs and instruments ask-flow hydration behavior for the intended v0.0.278 performance line.
