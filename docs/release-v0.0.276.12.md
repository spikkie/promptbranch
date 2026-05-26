# Release v0.0.276.12

## Scope

Narrow MVP Definition-of-Done repair on top of `v0.0.276.11`.

This release does **not** weaken strict release artifact verification. It adds visibility for the now-proven ChatGPT UI attachment smoke path so the MVP cockpit can distinguish:

- attachment transport proof: `--verify-smoke-zip`
- real release candidate proof: `--verify --migrate`
- guarded adoption proof: candidate test + accept/adopt

## Changes

- Updated `docs/mvp-definition-of-done.md` to include the explicit ChatGPT UI attachment smoke gate.
- Added read-only smoke ZIP evidence discovery for `.pb_profile/artifact_inbox/**/intake.json` records.
- Extended `pb artifact mvp-dod --json` with `smoke_zip_verification`.
- Extended `pb artifact mvp-status --json` with `smoke_zip_verification` and a ready-to-run smoke verification command.
- Updated required DoD workflow markers to include `--verify-smoke-zip`, `--expect-entry`, and `--expect-content`.

## Validation

Focused validation performed for this release:

```bash
python3 -m py_compile promptbranch_cli.py promptbranch_version.py tests/test_promptbranch_cli.py
pytest -q tests/test_promptbranch_cli.py -k "smoke_zip or mvp_dod_reports or mvp_status_includes_smoke" 
python3 promptbranch_cli.py version
```

## Non-goals

- No browser download repair; `v0.0.276.10` already proved button-based UI attachment download.
- No release ZIP verification weakening.
- No automatic migration/adoption from smoke artifacts.
- No Project Source mutation.
