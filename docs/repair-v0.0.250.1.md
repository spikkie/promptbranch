# Repair v0.0.250.1 — Restore packaged root .gitignore

## Base release

`chatgpt_claudecode_workflow_v0.0.250.zip`

## Repair version

`v0.0.250.1`

## Reason

`chatgpt_claudecode_workflow_v0.0.250.zip` omitted the repository-root `.gitignore` file even though earlier accepted artifacts included it. This is a packaging defect: the release artifact no longer carried the repository's ignore policy, which can affect local development hygiene after install or extraction.

## Files changed

- `.gitignore` restored from the accepted `v0.0.249` artifact.
- `VERSION` updated to `v0.0.250.1`.
- `promptbranch_version.py` updated to package version `0.0.250.1`.
- `pyproject.toml` updated to package version `0.0.250.1`.
- `promptbranch.egg-info/PKG-INFO` updated to package version `0.0.250.1`.
- `docker-compose.chatgpt-service.yml` updated to service image tag `0.0.250.1`.
- `docs/repair-v0.0.250.1.md` added.

## Validation performed

- Verified `.gitignore` exists in the repair artifact root.
- Verified `VERSION` is `v0.0.250.1`.
- Verified package/runtime version files agree on `0.0.250.1`.
- Verified ZIP opens successfully.
- Verified ZIP has no wrapper folder.
- Verified ZIP hygiene excludes generated/cache/local-state files.

## Slice / line advancement

No slice, lifecycle line, planned scope, source-add behavior, artifact intake behavior, adoption behavior, Git behavior, or Project Source semantics were advanced.

This repair fixes only a missing packaged file and version metadata consistency for the repair artifact.
