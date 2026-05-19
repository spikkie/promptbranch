# Release repair v0.0.240.1

Base release: `v0.0.240`
Repair version: `v0.0.240.1`

## Reason

`chatgpt_claudecode_workflow_release_control.sh --version v0.0.240` failed during automatic ZIP import when repo-local generated debug artifacts were owned by `root`. The import step attempted to delete `debug_artifacts/` and hit `Permission denied` before it could install the candidate ZIP.

## Files changed

- `chatgpt_claudecode_workflow_release_control.sh`
- `docker-compose.chatgpt-service.yml`
- `run_chatgpt_service.sh`
- `run_chatgpt_service_dev.sh`
- `docker/run-chatgpt-service-in-container.sh`
- `tests/test_promptbranch_shell_scripts.py`
- version metadata files

## Behavior

- `debug_artifacts/` is treated as generated repo-local state and is preserved during automatic ZIP import.
- Release control normalizes ownership for `.pb_profile/` and `debug_artifacts/` before import and after release steps unless `--skip-chown` is used.
- Docker Compose runs the service as the invoking host UID/GID by default, so new bind-mounted files are created as the current user instead of `root`.
- Container cache/home paths are redirected to `/tmp` and bytecode generation is disabled to reduce root-owned generated surfaces.

## Validation performed

- `bash -n` for changed shell scripts.
- Focused release-control shell-script tests.
- Version metadata smoke checks.
- ZIP hygiene verification.

## Scope confirmation

No slice, line, protocol, artifact-intake, browser automation, or source-upload scope was advanced. This repair only fixes ownership/import hygiene defects in the intended `v0.0.240` release.
