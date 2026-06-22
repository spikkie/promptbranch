# Repair v0.1.84.5.1 — live-test Project identity and visual timing

## Base release

```text
base candidate: chatgpt_claudecode_workflow-2_v0.1.84.5.zip
repair version: v0.1.84.5.1
normal slice advanced: no
```

## Reason

ChatGPT Project display names are not unique, so resolving a mutation-capable live test Project by name is unsafe. The old default visual/ask live-test setup used `ensure_project(name)`, which can enumerate and select an existing Project with the same display name before creating a new one. That creates both latency and wrong-Project risk.

## Scope

- Change `ask-live` default/`--project-name` setup to call `create_project()` directly.
- Change `visual-artifact-roundtrip` default/`--project-name` setup to call `create_project()` directly.
- Keep `release-live` covered through the existing visual-roundtrip command path.
- Preserve `--conversation-url` as the explicit exact-target bypass.
- Add JSON evidence fields for Project setup strategy and identity source.
- Add `phase_timings` to `pb test visual-artifact-roundtrip --json`.
- Add regression coverage proving generated and explicit Project-name live tests do not call `ensure_project()`.

## Out of scope

- Re-enabling ChatGPT Project deletion.
- Changing `pb project ensure`, which remains an explicit command for testing/using ensure semantics.
- Rewriting full integration `project_ensure_*` characterization steps.
- Backend REST Project creation.
- Accepted-event ledger/write behavior.
- Project Source mutation behavior.
- Artifact adoption/current mutation.
- Deployment or model execution.

## Files changed

- `promptbranch_cli.py`
- `tests/test_promptbranch_cli.py`
- `VERSION`
- `pyproject.toml`
- `promptbranch_version.py`
- `docs/project/status.md`
- `docs/project/plan.md`
- `docs/project/release-status.md`
- `docs/project/definition-of-done.md`
- `docs/project/decisions.md`
- `docs/project/migration.md`
- `docs/repair-v0.1.84.5.1.md`

## Validation performed

```text
python -m py_compile promptbranch_cli.py
python -m py_compile tests/test_promptbranch_cli.py
pytest -q tests/test_promptbranch_cli.py::test_ask_live_profile_runs_visible_operator_steps_in_unique_delete_frozen_project \
  tests/test_promptbranch_cli.py::test_visual_artifact_roundtrip_wraps_ask_and_artifact_intake \
  tests/test_promptbranch_cli.py::test_visual_artifact_roundtrip_explicit_project_name_is_creation_label_not_lookup \
  tests/test_promptbranch_cli.py::test_visual_artifact_roundtrip_failure_payload_waits_for_temp_project_cleanup \
  tests/test_promptbranch_cli.py::test_visual_artifact_roundtrip_explicit_conversation_url_skips_temp_project \
  tests/test_promptbranch_version.py \
  tests/test_project_control_surface.py
python -m compileall -q .
```

Focused result: `13 passed`. Full release-control/all-tests and live browser validation were not run in this artifact build environment.

## No-scope-advance confirmation

This is a repair-only candidate. It does not advance the accepted-event ledger slice, does not open a new normal release line, does not mutate Project Source behavior, does not adopt an artifact/current baseline, and does not re-enable ChatGPT Project deletion.
