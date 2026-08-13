# v0.1.128.2.6 — External-repository skill sync and publication-resume repair

Baseline authority: `v0.1.128.2.5`, SHA-256 `07c6e41d29e932e99d8eda20eeee35de92acdd567df6e529b51aee252fb70d58`.

## Scope

1. Add `pb skill sync` for external repositories.
2. Resolve skill source from the exact adopted/current Promptbranch artifact via tracked Project/repository identity.
3. Export and verify canonical portable bundles from accepted bytes before installation.
4. Stage and rollback-safe replace target `.promptbranch/skills/<skill>` directories.
5. Write deterministic `.promptbranch/promptbranch-skills.json` provenance and validate installed skills.
6. Report target Git status/diff without committing or pushing.
7. Convert publication subprocess timeout into structured retryable evidence and retry one bounded publication timeout inside the same canonical lifecycle wrapper invocation.

## Non-goals

- No external-application implementation scope.
- No implicit Git commit/push in target repositories.
- No skill-derived mutation/release/adoption authority.
- No compatibility shim for superseded Promptbranch skill mechanisms.

Next normal remains `v0.1.129 — External application pilot bootstrap`.

## Construction status

All 17 canonical release-validation groups pass. DOD-578 through DOD-581 are construction-proven. DOD-582 remains live-pending until the exact frozen artifact reaches FINAL_VERIFIED/current.
