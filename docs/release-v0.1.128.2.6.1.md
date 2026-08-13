# v0.1.128.2.6.1 — Immutable successor for external-repository skill sync and publication-resume repair

Baseline authority: `v0.1.128.2.5`, SHA-256 `07c6e41d29e932e99d8eda20eeee35de92acdd567df6e529b51aee252fb70d58`.

Historical predecessor: `v0.1.128.2.6`, immutably bound to SHA-256 `4ac66b37cba7b3676d487f082e9fe64239fd97b71f53b10f66b28b67fe1cf026`. That attempt is preserved and must not be deleted or rebound.

Construction input: finalized `v0.1.128.2.6` source ZIP at SHA-256 `a7af8a5e61ff7ec41e8cc51d8931b1abf251e42652bfbdea819d792fa419afce`. Because `v0.1.128.2.6` was already bound to different bytes, this successor advances VERSION/control-surface identity to `v0.1.128.2.6.1`; the final `v0.1.128.2.6.1` ZIP will necessarily have a new SHA-256.

## Preserved scope

1. `pb skill sync` for external repositories.
2. Skill source authority only from exact adopted/current Promptbranch artifact via tracked Project/repository identity.
3. Export/verify canonical portable bundles before install.
4. Stage and atomically replace target `.promptbranch/skills/<skill>` directories with rollback.
5. Deterministic `.promptbranch/promptbranch-skills.json` provenance plus target validation.
6. Report target Git status/diff without implicit commit or push.
7. Structured retryable publication-timeout evidence and bounded same-invocation publication retry.

## Identity repair

- Preserve `(repo_id, target_version) -> exactly one immutable artifact SHA-256`.
- Never delete or mutate historical `v0.1.128.2.6` release attempt to reuse its version.
- Treat `a7af8a5e61ff7ec41e8cc51d8931b1abf251e42652bfbdea819d792fa419afce` only as construction input for this successor.
- No normal product scope advances.

## Closure

Construction requires focused tests, all canonical deterministic release-validation groups, byte-identical rebuild, ZIP integrity, and Artifact Guardian. Acceptance/current requires the fresh canonical live lifecycle through `FINAL_VERIFIED`, independent all-state verification, and fresh scoped artifact-current alignment.

Next normal remains `v0.1.129 — External application pilot bootstrap`.

## Construction evidence

- Focused repair/control tests: 134 passed.
- Release-validation runner preflight: verified, pytest 9.0.2.
- Required deterministic validation: all 17 canonical constituent groups passed.
- State-machine group: 123 passed, 1 intentional Docker-integration skip reserved for canonical exact-candidate transition.
- Release-pipeline group: 72 passed.
- Deterministic package build: byte-identical independent builds.
- Artifact Guardian: canonical-name pass, zero failures.
- Full live lifecycle: not run in the artifact-construction environment; remains required on the operator host.
