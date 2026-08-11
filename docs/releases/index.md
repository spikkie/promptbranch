- [v0.1.127.1.1.1.1](../release-v0.1.127.1.1.1.1.md) — acceptance-path conversation provenance validator repair
- [v0.1.127.1.1.1](../release-v0.1.127.1.1.1.md) — successor ask pin propagation and executed-route verification repair
- [v0.1.127.1.1](../release-v0.1.127.1.1.md) — canonical ChatGPT project identity repair for artifact conversation provenance
- [v0.1.127.1](../release-v0.1.127.1.md) — artifact-bound conversation provenance and successor ask routing repair
- [`v0.1.126.1.1.1.1.3`](../release-v0.1.126.1.1.1.1.3.md) — preserve candidate validation-Python authority through sanitized publication validation.
- [`v0.1.126.1.1.1.1.2`](../release-v0.1.126.1.1.1.1.2.md) — accepted-runtime precondition and immutable production preservation before TESTED_GREEN.
- [`v0.1.126.1.1.1.1.1`](../release-v0.1.126.1.1.1.1.1.md) — runtime-checkpoint fingerprint authority, exact RUNTIME_PREPARED projection, and publication identity convergence.
- [`v0.1.126.1.1.1.1`](../release-v0.1.126.1.1.1.1.md) — Docker-service ask deadline propagation, structured timeout evidence, and non-duplicating fail-closed ask handling.
- [`v0.1.126.1.1.1`](../release-v0.1.126.1.1.1.md) — Project Source text-add body authority, disabled-save readiness stabilization, and bounded zero-request recovery.
- [`v0.1.126`](../release-v0.1.126.md) — persistent whole-release ETA, expected-finish, confidence/provenance, and advisory timeout-risk diagnostics.
- [`v0.1.125.3.4.2`](../release-v0.1.125.3.4.2.md) — lifecycle-aware historical candidate verification after adoption and exact tested-image final convergence.
- [`v0.1.125.3.4.1`](../release-v0.1.125.3.4.1.md) — authoritative runtime promotion, rollback, isolated candidate cleanup, and live final convergence.
# Promptbranch release documentation
- [`v0.1.125.3.3`](../release-v0.1.125.3.3.md) — acceptance/adoption transactional reconciliation and idempotent post-side-effect recovery.

- [`v0.1.125.3.2`](../release-v0.1.125.3.2.md) — deterministic schema-bound candidate-test evidence and genuine full-gate repair.
- [`v0.1.125.3.1`](../release-v0.1.125.3.1.md) — isolated, observable and resumable candidate runtime preparation.
Release: `v0.1.126`

This index provides a compact path into the current documentation-governance release line.

## Current documentation-governance releases

- [v0.1.125 — canonical PB environment proof cycle 2](../release-v0.1.125.md)
- [v0.1.124 — accepted PB candidate lifecycle checkpoint](../release-v0.1.124.md)

- [v0.1.66 — release doctor config-aware candidate ZIP precheck](../release-v0.1.66.md)
- [v0.1.65 — release lifecycle config contract guard](../release-v0.1.65.md)
- [v0.1.64 — docs-site build-readiness guard](../release-v0.1.64.md)
- [v0.1.63 — docs-site link-integrity / navigation validation guard](../release-v0.1.63.md)
- [v0.1.62 — documentation site scaffold / navigation guard](../release-v0.1.62.md)
- [v0.1.61 — living-design HTML overview integration](../release-v0.1.61.md)
- [v0.1.60 — release baseline evidence semantics](../release-v0.1.60.md)
- [v0.1.59 — PB application design docs-status guard](../release-v0.1.59.md)

- [v0.1.127 — Portable Promptbranch tool-authoring skill and export bundle](../release-v0.1.127.md)

## Release rules

Every normal release continues from the latest accepted Promptbranch baseline. Candidate ZIPs, transient sandbox ZIPs, installed ZIPs, locally accepted artifacts, Project Source baselines, and runtime package versions must remain distinguishable in the release evidence model.


## Link-integrity policy

Release documentation referenced from the MkDocs navigation or release index must resolve to repo-local Markdown files. Rendered `site/` output remains generated output and must not be committed.


## Build-readiness policy

Release documentation now links to the [documentation site operation](../site.md) page, which defines local preview/build commands and the rule that generated `site/` output remains outside committed source.


## Lifecycle-config policy

Release documentation includes the repo-local lifecycle config contract. `pb release config --json` validates `.promptbranch-release.yml` as data and explicitly reports that no hooks, installs, source uploads, artifact adoption, Git commits, or pushes were performed.


## Release doctor candidate precheck policy

`pb release doctor --artifact ZIP --version VERSION --json` now consumes `.promptbranch-release.yml` when inspecting candidate ZIPs. It reports `candidate_artifact` and `release_config` sections, checks filename/config agreement, VERSION consistency, ZIP layout and hygiene, and accepted-baseline continuity without mutating release state.

- [`v0.1.125.1`](../release-v0.1.125.1.md) — isolated compileall and repeatable template-snapshot validation repair.
- [`v0.1.125.2`](../release-v0.1.125.2.md) — version-independent authority projection-drift fixture repair.

- `v0.1.126.1` — whole-release publication convergence repair (superseded by `v0.1.126.1.1`; never accepted).

- `v0.1.127.2.1` — construction-proof repair for consolidated v0.1.127 closure (`docs/release-v0.1.127.2.1.md`).
- `v0.1.127.2` — consolidated v0.1.127 closure and single-Python lifecycle repair (`docs/release-v0.1.127.2.md`).
