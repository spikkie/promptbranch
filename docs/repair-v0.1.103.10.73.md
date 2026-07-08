# v0.1.103.10.73 — make version_surface tests derive expected version from release metadata

## Scope

- Keep the v0.1.103.10.69 `install.sh` strict all-all release gate.
- Keep the v0.1.103.10.71 `live_bootstrap_guardrail` cascade normalization.
- Keep the v0.1.103.10.72 final verdict precedence: product failures remain `FIX`; clean product validation with external-live blockage remains `LIVE_BLOCKED`.
- Fix `tests/test_promptbranch_version.py` so the expected package version is derived from `VERSION`, `pyproject.toml`, and `promptbranch_version.py` instead of a stale literal.
- Preserve the real version test intent: no double `v` prefix in `VERSION_TAG`.
- Add a stale repair-version literal guard for future version-surface tests.

## Out of scope

- No Cloudflare/rate-limit bypass.
- No host-CDP/session-manager.
- No copied-profile trust.
- No adoption behavior relaxation.
