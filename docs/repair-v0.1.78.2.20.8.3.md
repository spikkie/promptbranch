# Repair v0.1.78.2.20.8.3 — Slugged cleanup identity and text-source post-commit recovery

## Base release

`v0.1.78.2.20.8.2`

## Repair version

`v0.1.78.2.20.8.3`

## Reason

A live focused fresh-project run on `v0.1.78.2.20.8.2` proved that the missing `_normalize_project_url` cleanup crash was fixed, but exposed two remaining repair-only defects:

1. Same-run ephemeral cleanup retargeted from a bare create URL to a slugged Project URL, then the safety guard compared the slugged route id literally against the base created id and blocked with `project_id_mismatch`.
2. Text-source add could observe a save commit with stale inflight request state, but did not run the bounded post-commit Project Sources refresh recovery that already existed for file sources.

## Scope

In scope:

- Normalize slugged Project route ids such as `g-p-<id>-itest-promptbranch-*` to the stable created Project id before same-run ephemeral cleanup comparison.
- Keep cleanup allowed only for same-run `itest-promptbranch-*` projects whose created name and canonical Project id match.
- Extend bounded post-commit Project Source recovery to text-source saves when the transaction is `commit_seen_with_stale_inflight_not_verified_present`.
- Widen post-commit readback policy for committed text-source saves in the same way as file-source saves.
- Report `post_commit_source_surface_not_refreshed` when post-commit recovery is attempted but refreshed proof still does not appear.

Out of scope:

- Broad Project deletion.
- Project Source text-add semantics or `pasted.txt Document` success rules.
- Prompt-file attachment transport.
- Artifact adoption/current mutation.
- Normal `v0.1.79` scope.

## Files changed

- `promptbranch_project_delete_safety.py`
- `promptbranch_browser_auth/client.py`
- `tests/test_project_delete_safety.py`
- `tests/test_project_source_capabilities.py`
- `tests/test_promptbranch_version.py`
- `VERSION`
- `pyproject.toml`
- `promptbranch_version.py`
- `docs/project/definition-of-done.md`
- `docs/project/status.md`
- `docs/project/release-status.md`
- `docs/project/decisions.md`
- `docs/project/migration.md`
- `docs/project/plan.md`

## Validation performed

- Python compile checks for changed runtime modules.
- Focused cleanup, Project Source, full-integration harness, project-resolution, version, control-surface, and test-suite regression tests.
- ZIP integrity, root-layout, required root file, and hygiene checks before handoff.

## Explicit no-advance statement

This is a repair release only. It does not advance the active MVP slice, open normal `v0.1.79`, alter artifact current/adoption state, or enable broad Project deletion.
