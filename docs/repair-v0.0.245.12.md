# Repair v0.0.245.12 — No-artifact artifact-intake baseline validation consistency

Base release: v0.0.245.11
Repair version: v0.0.245.12

## Reason

The final Artifact Intake MVP finalizer reached a validated no-artifact/no-change protocol smoke reply, but `pb artifact intake --from-last-answer --dry-run` rejected the same reply with `baseline_source_ref_mismatch` and `baseline_source_version_mismatch`.

This was inconsistent: protocol smoke accepted the reply, but artifact intake required `source_ref` and `source_version` fields that the no-artifact/no-change reply did not need to echo.

## Files changed

- `promptbranch_cli.py`
- `tests/test_promptbranch_cli.py`
- version metadata files
- `docs/repair-v0.0.245.12.md`

## Validation intent

For protocol replies with:

```text
status = no_artifact
result_type = no_change
artifacts = []
```

artifact intake now validates request/correlation identity, input artifact/version, release type, and absence of artifacts, but it does not require `source_ref` / `source_version` to be echoed in the reply baseline.

## Explicit scope control

No normal v0.0.246 scope was advanced.
No release lifecycle scope was advanced.
No source-add, login, browser, project-source, adoption, or ZIP packaging behavior was intentionally changed.

The optional v0.0.245.10 post-Google callback diagnostics were not rebased into this repair because that candidate was not installed/accepted and its automation wrapper changes were not cleanly self-contained.
