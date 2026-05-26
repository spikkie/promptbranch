# Repair v0.0.276.9 — Browser download staging path

Base release: v0.0.276.8
Repair version: v0.0.276.9
Reason: browser-assisted artifact download attempted to write the CLI host artifact inbox path from inside the Dockerized ChatGPT service, causing `PermissionError: /home/spikkie` before the UI link click could be tested.

Files changed:
- `promptbranch_cli.py`
- `promptbranch_browser_auth/client.py`
- version metadata and version-current tests

Change summary:
- Service-backed browser artifact downloads now use a container-writable staging path under `/tmp/promptbranch-artifact-downloads/...`.
- The browser service returns downloaded bytes as base64 in the JSON result.
- The CLI decodes those bytes and imports the ZIP into the host-owned `.pb_profile/artifact_inbox/...` path.
- Direct/non-service backends continue to write directly to the local artifact inbox.

Validation performed:
- `bash -n` for shell scripts.
- Python compilation for project Python files.
- Focused parser/version tests.
- ZIP hygiene verification.

No slice, line, or feature scope was advanced. This is a repair-only transport/path-mapping fix.
