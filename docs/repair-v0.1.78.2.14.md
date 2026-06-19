# Repair v0.1.78.2.14 — Project Source remove containment guard

## Reason

`v0.1.78.2.13 --run-all-tests` no longer blocked on text-source compatibility, but `full_direct` failed at `project_source_overwrite_file` because the source-remove guard reported collateral rows that were not Project Source cards, including sidebar/project/history labels.

## Scope

This repair constrains Project Source snapshotting, source-container lookup, and source action-button lookup to visible Project Sources surfaces only. It removes the broad body/main fallback that could treat sidebar, recents, project navigation, or global page chrome rows as source cards during overwrite/remove verification.

## Files changed

- `promptbranch_browser_auth/client.py`
- `chatgpt_browser_auth/client.py`
- `tests/test_project_source_capabilities.py`
- project control-surface documentation
- version metadata

## Validation performed

Focused static regression tests assert that source-card snapshots and remove lookups no longer fall back to broad `main/body` queries and require a sources-surface predicate.

## Boundary confirmation

This is a repair-only release. It does not advance the normal slice, does not change Project deletion policy, and does not alter adoption/current semantics.
