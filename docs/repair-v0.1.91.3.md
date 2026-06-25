# Repair v0.1.91.3 — Docker service clean-system recreate/version verification hardening

## Base release

```text
accepted/current baseline before this repair: chatgpt_claudecode_workflow-2_v0.1.91.1.zip
repair candidate preserved: chatgpt_claudecode_workflow-2_v0.1.91.2.zip
repair version: v0.1.91.3
```

## Reason

`v0.1.91.2` preserved the run-all final summary aggregation repair, but release-control failed before validation because Docker service recreate/version verification reported a running-container content mismatch while the diagnostic payload was actually `container_not_found`.

That failure class must be handled as a Docker lifecycle/bootstrap issue, not as a content-version mismatch. It can happen on a dirty developer machine and on a clean new system if Compose is missing, the service identity changes, the service exits before inspection, Docker is not ready, or verification races ahead of container creation.

## Scope

This repair changes only Docker service recreate/version verification in release-control:

- add Docker/Compose preflight diagnostics;
- resolve the service container by explicit Compose service name, default `chatgpt-service`;
- wait for a running/healthy-or-healthless container before content version probing;
- classify missing container as `docker_service_container_missing_after_recreate`;
- classify non-running container as `docker_service_container_not_running_after_recreate`;
- collect Compose ps/logs/config and Docker context/info diagnostics on missing/non-running containers;
- preserve the no-cache fallback but make the post-fallback missing-container failure explicit.

## Out of scope

- no live/browser behavior change;
- no ask-live retry behavior change;
- no run-all evidence reuse semantic change;
- no localhost cooldown audit semantic change;
- no Project Source mutation behavior change;
- no artifact adoption/current behavior change;
- no ChatGPT Project deletion behavior change.

## Files changed

```text
VERSION
pyproject.toml
promptbranch_version.py
chatgpt_claudecode_workflow_release_control.sh
tests/test_promptbranch_shell_scripts.py
tests/test_promptbranch_version.py
docs/repair-v0.1.91.3.md
docs/project/status.md
docs/project/release-status.md
docs/project/definition-of-done.md
docs/project/plan.md
docs/project/decisions.md
docs/project/migration.md
```

## Validation performed

Focused validation for this candidate should include:

```bash
python3 -m pytest -q \
  tests/test_promptbranch_shell_scripts.py::test_release_control_docker_service_lookup_is_clean_system_safe \
  tests/test_promptbranch_shell_scripts.py::test_release_control_docker_preflight_and_diagnostics_are_declared \
  tests/test_promptbranch_shell_scripts.py::test_release_control_recreates_docker_service_and_verifies_version \
  tests/test_promptbranch_shell_scripts.py::test_release_control_pins_compose_service_image_to_release_version \
  tests/test_promptbranch_shell_scripts.py::test_docker_build_context_version_guard_declared \
  tests/test_promptbranch_version.py \
  tests/test_project_control_surface.py

python3 -m compileall -q promptbranch_browser_auth promptbranch_test_report.py promptbranch_full_integration_test.py promptbranch_cli.py promptbranch_version.py promptbranch_loop.py promptbranch_container_api.py promptbranch_automation promptbranch_service_client.py
bash -n chatgpt_claudecode_workflow_release_control.sh
python3 promptbranch_cli.py artifact guard --zip chatgpt_claudecode_workflow-2_v0.1.91.3.zip --version v0.1.91.3 --json
python3 promptbranch_cli.py artifact verify chatgpt_claudecode_workflow-2_v0.1.91.3.zip --json
```

## Slice movement

No slice or line advanced. This is a repair-only release that preserves `v0.1.91` run-all evidence reuse and localhost cooldown audit scope while retaining `v0.1.91.2` run-all aggregation repair.
