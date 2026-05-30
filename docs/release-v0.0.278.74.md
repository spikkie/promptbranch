# Release v0.0.278.74

Packaging-only repair after v0.0.278.73.

## Base release

- Input candidate: v0.0.278.73
- Output candidate: v0.0.278.74

## Reason

v0.0.278.73 restored `.gitignore`, but the manually created ZIP accidentally included local browser/debug profile state under `.pb_profile_local_debug/`. That made the artifact unsuitable as an accepted baseline.

## Scope

- Preserve the v0.0.278.73 code surface, including the v0.0.278.72 attachment submit-readiness repair.
- Repackage from the candidate content with local profile/cache/debug state excluded.
- Keep `.gitignore` at ZIP root.
- Remove accidental root file `0` if present.
- Advance only package metadata to v0.0.278.74.

## Files changed

- `VERSION`
- `pyproject.toml`
- `promptbranch_version.py`
- `docker-compose.chatgpt-service.yml`
- `promptbranch.egg-info/PKG-INFO`
- `promptbranch.egg-info/SOURCES.txt`
- version expectation tests
- `docs/release-v0.0.278.74.md`

## Validation performed

- Python compile check.
- Focused version and packaging checks.
- ZIP reopened and verified.

## Slice/line statement

No functional scope, slice, or line was advanced. This release only repairs package hygiene for the intended v0.0.278.73 candidate line.
