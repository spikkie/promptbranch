# Repair v0.0.245.8

Base release: v0.0.245.5
Repair version: v0.0.245.8

## Reason

The unsafe local v0.0.245.6/v0.0.245.7 attempts exposed two release-control defects:

1. ZIP import could delete or fail to preserve required repository control files such as `.gitignore` and `.not_to_zip` when processing a candidate ZIP.
2. The commit step used broad `git add .` without a fail-closed staging guard, allowing `.env`, `.pb_profile/`, `debug_artifacts/`, ZIPs, logs, and other generated/local state to be staged if `.gitignore` was missing or changed.

A second observed issue was that candidate ZIP contents such as `ollama_mcp_verification_harness/`, `ollama_mcp_verification_harness_v2/`, and `promptbranch.egg-info/` were present in the ZIP but not reliably staged/tracked after import because `.gitignore` still ignored those paths.

## Files changed

- `.gitignore`
- `chatgpt_claudecode_workflow_release_control.sh`
- `docker-compose.chatgpt-service.yml`
- `promptbranch_browser_auth/client.py`
- `chatgpt_browser_auth/client.py`
- `tests/test_project_source_capabilities.py`
- `tests/test_promptbranch_shell_scripts.py`
- version metadata files

## Repair details

- Require candidate ZIPs to contain required repo-control files:
  - `VERSION`
  - `pyproject.toml`
  - `.gitignore`
  - `.not_to_zip`
  - `chatgpt_claudecode_workflow_release_control.sh`
- Reject candidate ZIPs that contain protected local/runtime state:
  - `.env`
  - `.generated/`
  - `.pb_profile/`
  - `profile/`
  - `debug_artifacts/`
- Verify after import that candidate ZIP entries were actually copied into the working tree.
- Add a staging safety guard that refuses to commit protected/generated/local files or deletion of `.gitignore` / `.not_to_zip`.
- Force-add intentional, previously ignored, candidate ZIP repo paths when present:
  - `ollama_mcp_verification_harness/`
  - `ollama_mcp_verification_harness_v2/`
  - `promptbranch.egg-info/`
- Update `.gitignore` so those intentional release harness/package metadata paths are not ignored.
- Re-apply the file-source overwrite before-state classification repair from v0.0.245.6.
- Fix the compose image tag to match v0.0.245.8.

## Validation

- Shell syntax validation.
- Python bytecode compilation.
- Focused release-control shell-script regression tests.
- Focused project-source capability regression tests.
- Focused version/container/MCP tests.
- ZIP hygiene checks.

## Scope confirmation

No normal release scope was advanced. This is a repair of the intended v0.0.245 line only.
