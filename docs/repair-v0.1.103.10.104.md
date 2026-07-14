# v0.1.103.10.104 — bounded Library UI recovery after backend presence

## Scope

- Keep accepted/current at `v0.1.103.10.68`.
- Preserve both processing-stream watchers, bounded Fetch/XHR settlement, immutable request phases, sequence-bound deletion discovery, and the `v0.1.103.10.103` confirmation logic unchanged.
- After exact backend inventory presence is stable but the active Library UI is non-authoritative, perform exactly one bounded recovery cycle.
- Clear and reapply the exact filename search.
- If still non-authoritative, perform at most one controlled page reload, reapply the exact search, and continue bounded polling.
- Require exact UI row binding before any deletion action.
- Return `library_surface_not_authoritative_after_bounded_recovery` with detailed final UI evidence if recovery fails.
- Do not run canonical release `pbsa`, adoption, or ChatGPT Project deletion.

## Validation intent

The repair is proven by deterministic tests for recovery after search reapplication, recovery after one reload, fail-closed behavior after one unsuccessful reload, caller ordering before the delete sequence boundary, packaged-byte tests, Artifact Guardian, and release import-plan validation.
