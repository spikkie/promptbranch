# Repair v0.1.91.5 — Run-all live_project_ensure aggregation terminal-line repair

## Base

- Accepted/current baseline before repair stack: `chatgpt_claudecode_workflow-2_v0.1.91.1.zip`
- Repair stack base: `v0.1.91.4` candidate state
- Repair version: `v0.1.91.5`

## Reason

The `v0.1.91.4 --run-all-tests` proof showed the `live_project_ensure` command itself returned valid `ok=true` / `action=ensure_project` JSON and a concrete `project_url`, but the final all-tests summary still listed `live_project_ensure` as failed. The log shape included the valid JSON payload followed by a human-readable terminal line:

```text
shared_live_project_url: https://chatgpt.com/g/.../project
```

The aggregation ranking still required a `status` field for command-result payloads. `ensure_project` does not emit `status`, so nested schema/helper JSON could outrank the real command payload.

## Files changed

- `chatgpt_claudecode_workflow_release_control.sh`
- `tests/test_promptbranch_shell_scripts.py`
- `VERSION`
- `pyproject.toml`
- `promptbranch_version.py`
- `tests/test_promptbranch_version.py`
- `docs/repair-v0.1.91.5.md`
- `docs/project/status.md`
- `docs/project/release-status.md`
- `docs/project/definition-of-done.md`
- `docs/project/plan.md`
- `docs/project/decisions.md`
- `docs/project/migration.md`

## Change

The all-tests summary JSON extractor now gives highest priority to `project_ensure` / `ensure_project` payloads that prove:

- `ok=true`
- a concrete `project_url`

This remains limited to payload selection. It does not change Project ensure behavior, live browser behavior, Project Source mutation, adoption/current semantics, Docker lifecycle behavior, or Project deletion behavior.

## Validation

Focused validation was run before packaging. Full operator release-control and all-tests proof are still required before adoption/current.

## Slice advancement

No normal slice advanced. This repair preserves the `v0.1.91` run-all evidence reuse proof line and the `v0.1.91.1`–`v0.1.91.4` repair stack.
