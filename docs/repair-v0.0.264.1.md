# Repair v0.0.264.1

Base release: v0.0.264

Repair version: v0.0.264.1

Reason: strict final Artifact Intake MVP validation for v0.0.264 failed in the browser full-suite step `project_source_add_text`. The browser service returned a 500 after Playwright/Patchright failed to launch a persistent browser context with `TargetClosedError` / `Opening in existing browser session`. The v0.0.264 release-readiness changes, ZIP hygiene, install path, source overwrite, service version, and post-install checks were not the failing surface.

Files changed:

- `VERSION`
- `promptbranch_version.py`
- `pyproject.toml`
- `promptbranch.egg-info/PKG-INFO`
- `promptbranch_browser_auth/exceptions.py`
- `promptbranch_browser_auth/client.py`
- `chatgpt_browser_auth/client.py`
- `promptbranch_container_api.py`
- `tests/test_response_completion.py`
- `docs/repair-v0.0.264.1.md`

Repair details:

- Added `BrowserContextUnavailableError` for failed persistent-context startup after recovery.
- Added one controlled persistent-context launch retry when the first launch fails with recoverable browser profile/session markers such as `TargetClosedError`, closed context/browser text, singleton lock hints, or `Opening in existing browser session`.
- Clears profile singleton artifacts before retrying.
- Maps unrecovered browser-context startup failure to HTTP 503 instead of a generic HTTP 500.
- Added focused regression coverage for successful retry and unrecovered classification.

Validation performed by builder:

- `python3 -m compileall -q .`
- focused regression tests for persistent-context retry/classification
- focused parser/version smoke
- extracted ZIP smoke
- ZIP hygiene check

No slice, line, target normal version, Project Source mutation, adoption, Git commit, or Git push was advanced by this repair.
