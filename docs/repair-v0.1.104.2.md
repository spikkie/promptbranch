# Repair v0.1.104.2 — project ensure create/reuse browser timeout repair

## Base release

- Accepted/current baseline before repair: `chatgpt_claudecode_workflow-2_v0.1.103.zip`
- Failed normal candidate: `chatgpt_claudecode_workflow-2_v0.1.104.zip`
- Failed repair candidate: `chatgpt_claudecode_workflow-2_v0.1.104.1.zip`
- Repair candidate: `chatgpt_claudecode_workflow-2_v0.1.104.2.zip`

## Reason

The `v0.1.104.1` full release-control run proved that the project-remove frozen scheduler timeout repair held, but the run then failed in live browser project ensure/reuse:

```text
project_ensure_create_or_reuse: ReadTimeout after 300 seconds
```

The failure occurred before the sandbox mutation verification slice was exercised by adoption. The browser service may still complete the Project ensure action after the client timeout, so the release harness must avoid an immediate ambiguous failure when exact project identity can be recovered.

## Repair

- The Docker service adapter now gives Project ensure/create/reuse its own extended request timeout, defaulting to `PROMPTBRANCH_PROJECT_ENSURE_SERVICE_TIMEOUT_SECONDS` / `CHATGPT_PROJECT_ENSURE_SERVICE_TIMEOUT_SECONDS` / `900.0`.
- If Project ensure still raises `ReadTimeout`, the harness waits a bounded recovery delay and resolves the requested project by name.
- Recovery succeeds only when exactly one matching project with a concrete Project URL is verified.
- If post-timeout resolve cannot prove exact identity, the result remains release-blocking and operator review is required.
- The repair also adds a pre-adoption isolated release test mode for targeted local validation. This mode is explicitly not an adoption/current gate and cannot be combined with `--adopt-after-validation`.

## Isolated release tests

Developers can run focused local checks for the active slice/repair without running the full browser/live matrix:

```bash
./chatgpt_claudecode_workflow_release_control.sh \
  --install-from-zip ~/Downloads/chatgpt_claudecode_workflow-2_v0.1.104.2.zip \
  --version v0.1.104.2 \
  --run-isolated-release-tests \
  --skip-docker-logs \
  --prune-release-logs \
  --release-log-keep 12
```

This validates focused loop/CLI/control/version tests, the Project ensure timeout repair tests, sandbox mutation verification, and Artifact Guardian. It does not prove live browser readiness, Project Source persistence, or artifact adoption/current alignment.

## Scope confirmation

This repair does not advance the normal slice. `v0.1.104` remains the active normal slice: Sandbox mutation verification and rollback evidence gate. `v0.1.105` remains deferred.

No ChatGPT Project deletion is enabled. The no-delete invariant remains active.

## Files changed

- `VERSION`
- `pyproject.toml`
- `promptbranch_version.py`
- `promptbranch_service_client.py`
- `promptbranch_full_integration_test.py`
- `chatgpt_claudecode_workflow_release_control.sh`
- `tests/test_full_integration_harness.py`
- `tests/test_project_control_surface.py`
- project control-surface docs under `docs/project/`

## Validation

Focused validation must include the Project ensure timeout recovery tests and the isolated release-test mode. Full release-control/adoption remains required before this repair can be called accepted/current.
