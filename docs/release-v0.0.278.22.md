# Release v0.0.278.22

Base release: v0.0.278.21
Release version: v0.0.278.22
Release type: normal diagnostic/safety release

## Reason

v0.0.278.21 proved that backend conversation detail could be fetched, but the live old-task ask still failed closed because the newly submitted prompt was not visible in backend conversation state. The failure path also spent too long probing backend/DOM causality after the composer cleared.

v0.0.278.22 adds a pre-click browser network observer so submit causality is checked at the dispatch layer before relying on DOM turn selectors or backend conversation commit state.

## Changes

- Added browser network request/response observer around submit.
- Captures post-click ChatGPT backend-like requests.
- Requires the outbound request body or URL to contain the current prompt marker/sentinel.
- Accepts submit causality via `network_submit_request` when the current marker is observed in a post-click network request.
- Fails closed as `network_submit_request_not_observed` before backend/DOM causality fallback when network proof is required.
- Preserves URL-only rejection, request-marker response freshness guard, warm hydration reuse, and stale-output fail-closed behavior.

## Files changed

- `promptbranch_browser_auth/client.py`
- `tests/test_project_list_browser_client.py`
- `VERSION`
- `pyproject.toml`
- `promptbranch_version.py`
- `docker-compose.chatgpt-service.yml`
- version assertion tests
- `docs/release-v0.0.278.22.md`

## Validation performed

- `python3 -m py_compile promptbranch_browser_auth/client.py`
- `pytest -q tests/test_project_list_browser_client.py`

## Scope confirmation

No slice or line was advanced. This release only hardens live ask submit causality diagnostics and fail-closed behavior.
