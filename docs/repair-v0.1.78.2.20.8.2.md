# Repair v0.1.78.2.20.8.2 — ephemeral project cleanup URL normalization repair

## Scope

This is a cleanup-only repair for `v0.1.78.2.20.8.1`.

## Base release

- Base candidate: `chatgpt_claudecode_workflow-2_v0.1.78.2.20.8.1.zip`
- Repair candidate: `chatgpt_claudecode_workflow-2_v0.1.78.2.20.8.2.zip`

## Reason

The `v0.1.78.2.20.8.1` focused fresh-project run proved that expected-missing classification and Project Source text-add persistence are working, but the new same-run ephemeral cleanup path failed in `/v1/projects/remove` with:

```text
AttributeError: 'ChatGPTBrowserClient' object has no attribute '_normalize_project_url'
```

This was an implementation defect in the cleanup remove path, not a source-add behavior defect.

## Files changed

- `VERSION`
- `pyproject.toml`
- `promptbranch_version.py`
- `promptbranch_browser_auth/client.py`
- `chatgpt_browser_auth/client.py`
- `tests/test_project_delete_safety.py`
- `tests/test_promptbranch_version.py`
- `docs/repair-v0.1.78.2.20.8.2.md`
- `docs/project/status.md`
- `docs/project/release-status.md`
- `docs/project/definition-of-done.md`
- `docs/project/decisions.md`
- `docs/project/migration.md`

## Behavior

- Adds `ChatGPTBrowserClient._normalize_project_url(...)` to normalize project cleanup targets to canonical Project home URLs.
- Supports project URLs with query/fragment state, slugged project routes, and project conversation URLs.
- Preserves strict same-run ephemeral cleanup validation.
- Preserves the public project-deletion freeze for all non-ephemeral cleanup requests.
- Does not change Project Source add behavior.
- Does not change prompt-file attachment/composer behavior.

## Validation performed

- Python compile check for touched runtime modules.
- Focused project delete/cleanup tests.
- Focused full-integration cleanup tests.
- Focused version/control-surface tests.
- ZIP integrity check.
- ZIP hygiene check.
- Required root-file check.

## Slice/line movement

No normal slice advanced. This repair only fixes the intended same-run ephemeral cleanup implementation defect in the `v0.1.78.2.20.8.x` repair line.
