# Repair v0.1.91.4 — Pre-source-add service bootstrap for clean-system release-control

## Classification

```text
base accepted/current: chatgpt_claudecode_workflow-2_v0.1.91.1.zip
repair lineage: v0.1.91.2 candidate + v0.1.91.3 candidate
repair version: v0.1.91.4
normal slice advanced: false
```

## Reason

A clean-system validation attempt started with no running Docker containers and failed before Project Source add because release-control tried `promptbranch src add` against `localhost:8000` before starting or verifying the candidate service.

The previous `v0.1.91.3` repair hardened post-release Docker recreate/version verification, but the clean host failed earlier in the pre-source-add phase. Dirty developer machines could mask this because an older Promptbranch service was already running.

## Scope

This repair is limited to pre-source-add service bootstrap ordering:

- reinstall the candidate CLI before service-mediated source mutation;
- verify the pre-source-add service health/version before `promptbranch src add`;
- when the service is missing or stale and `--skip-service` is not set, bootstrap the candidate Docker service before Project Source add;
- emit `pre_source_add_service_unavailable` and pre-source-add Docker diagnostics instead of a generic connection-refused source-add failure.

## Preserved behavior

- v0.1.91.1 ask-live first-turn retry recovery is preserved.
- v0.1.91.2 run-all final summary aggregation repair is preserved.
- v0.1.91.3 Docker recreate/version verification hardening is preserved.
- No live/browser behavior changed.
- No adoption/current semantics changed.
- No Project deletion behavior changed.
- No Project Source mutation semantics changed beyond ensuring the required service exists before source-add.

## Files changed

```text
VERSION
pyproject.toml
promptbranch_version.py
chatgpt_claudecode_workflow_release_control.sh
tests/test_promptbranch_shell_scripts.py
tests/test_promptbranch_version.py
docs/repair-v0.1.91.4.md
docs/project/status.md
docs/project/release-status.md
docs/project/definition-of-done.md
docs/project/plan.md
docs/project/decisions.md
docs/project/migration.md
```

## Validation performed

```text
python3 -m pytest -q \
  tests/test_promptbranch_shell_scripts.py::test_release_control_pre_source_add_service_bootstrap_is_clean_system_safe \
  tests/test_promptbranch_shell_scripts.py::test_release_control_installs_candidate_before_source_add_bootstrap \
  tests/test_promptbranch_shell_scripts.py::test_release_control_docker_service_lookup_is_clean_system_safe \
  tests/test_promptbranch_shell_scripts.py::test_release_control_docker_preflight_and_diagnostics_are_declared \
  tests/test_promptbranch_version.py

bash -n chatgpt_claudecode_workflow_release_control.sh
```

Candidate packaging also requires Artifact Guardian, artifact verify, and ZIP hygiene before handoff.

## No slice advancement confirmation

`v0.1.91.4` does not advance the `v0.1.91` validation-control slice. It only repairs clean-system release bootstrap so the existing run-all evidence reuse / localhost cooldown audit line can be validated.
