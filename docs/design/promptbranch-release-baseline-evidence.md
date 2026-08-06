# Promptbranch Release Baseline Evidence

Release: `v0.1.66`

## Purpose

Introduced in `v0.1.60`; refreshed in `v0.1.61` for the living-design HTML overview, in `v0.1.62` for the documentation site scaffold, in `v0.1.63` for docs-site link-integrity validation, in `v0.1.64` for docs-site build-readiness validation, in `v0.1.65` for read-only release lifecycle config validation, and in `v0.1.66` for config-aware release doctor candidate ZIP prechecks.


This document defines the release/adoption evidence model used by Promptbranch after a candidate ZIP has been created, installed, validated, and adopted.

The goal is to prevent baseline ambiguity after adoption, especially when a transient sandbox ZIP checksum differs from the ZIP that becomes the locally accepted Promptbranch artifact.

## Core rule

After adoption, the locally accepted Promptbranch artifact is authoritative.

That means the authoritative baseline is the artifact reported by Promptbranch current-state reads, not a prior generated candidate checksum, not a transient sandbox ZIP checksum, and not assistant prose.

## Evidence commands

Use these read-only commands to reason about accepted release state:

```bash
pb artifact current --json
pb release baseline-status --json
```

`pb artifact current --json` answers what Promptbranch currently considers active across runtime, state artifact, state source, and artifact registry.

`pb release baseline-status --json` is the stricter post-adoption verifier. It answers whether runtime, adopted source, adopted artifact, registry current, and optional local accepted ZIP are aligned for an expected version.

## Artifact roles

The release flow must keep these roles separate:

| Role | Meaning | Authority |
|---|---|---|
| candidate ZIP | ZIP produced for review or local installation | Not authoritative until verified/adopted |
| transient sandbox ZIP | Artifact generated in a ChatGPT execution sandbox | Transport artifact only; its checksum is not authoritative after local adoption |
| installed ZIP | Candidate installed into the local working tree | Development state, not proof of accepted baseline |
| locally accepted artifact | ZIP recorded by Promptbranch as `registry_current.kind = adopted_release` | Authoritative after adoption |
| Project Source baseline | Artifact/source reference attached to the ChatGPT Project | Must align with accepted state after adoption |
| runtime package version | Installed package/runtime version | Must match adopted source for a clean accepted baseline |

## Post-adoption success indicators

A clean accepted baseline normally requires these fields:

```text
registry_current.kind = adopted_release
code_matches_adopted_source = true
registry_current_matches_state_artifact = true
state_source_matches_state_artifact = true
code_version_matches_state_source = true
project_home_url_present = true
```

When these fields are true, future releases should continue from the locally accepted artifact reported by Promptbranch.

## Validation evidence classes

Promptbranch must distinguish full-test evidence from focused-validation evidence.

full-test evidence may be stale. For example, a later focused documentation release may be adopted while the newest structured full-test evidence still points to an older release. That does not automatically invalidate adoption, but the operator must describe the release honestly as focused-validation accepted rather than full-test-green.

Focused-validation evidence is acceptable for narrow documentation, schema, fixture, and docs-status guard slices when the changed surface is small and targeted tests plus `compileall` pass.

## Continuation rule

The next normal release must build from the accepted baseline reported by Promptbranch current state.

If `pb artifact current --json` reports:

```text
artifact_version = v0.1.59
source_version = v0.1.59
registry_current.kind = adopted_release
code_matches_adopted_source = true
```

then the next normal release is:

```text
base:   chatgpt_claudecode_workflow-2_v0.1.59.zip
target: chatgpt_claudecode_workflow-2_v0.1.60.zip
```

After `v0.1.61` is adopted, the same rule moves the next normal release target to `v0.1.62`.

## Non-authoritative signals

Do not use these alone as accepted-baseline proof:

- assistant text saying a ZIP was built;
- a sandbox download checksum;
- a candidate ZIP path;
- an installed runtime version without registry/source alignment;
- stale full-test evidence from a different release;
- manually remembered baseline names.

## Release-checkable invariant

The accepted baseline is the ZIP that Promptbranch reports as the current adopted release after adoption. If there is a checksum conflict between a transient sandbox ZIP and the local accepted artifact, the local accepted artifact checksum wins for future continuation.


## v0.1.62 documentation-site evidence

The documentation site scaffold is source evidence only. `mkdocs.yml` and the docs index pages help humans find the authoritative design and release documents, but rendered `site/` output is generated material and is not an accepted baseline signal.


## v0.1.63 documentation link-integrity evidence

The accepted-baseline evidence model now also protects documentation navigation. A candidate release must not merely contain the right docs; its `mkdocs.yml` navigation and Markdown entrypoint links must resolve to repo-local files before the candidate is considered documentation-fresh. This remains read-only validation and does not alter artifact adoption authority.


## v0.1.64 documentation build-readiness evidence

Documentation build readiness is source evidence only. `docs/site.md` documents local preview/build commands and the generated-output exclusion rule. `docs_site.build_readiness.ok=true` confirms that the source tree is operationally understandable without treating rendered `site/` output as an accepted artifact or Project Source baseline.


## v0.1.65 release lifecycle config evidence

`pb release config --json` is a read-only evidence command. It can help an operator verify lifecycle policy before a future install/test/adopt workflow, but it is not adoption evidence by itself. Authoritative accepted-baseline evidence remains `pb artifact current --json` with `registry_current.kind = adopted_release` and `code_matches_adopted_source = true`.


## v0.1.66 release doctor candidate evidence

`pb release doctor --artifact ZIP --version VERSION --json` now produces read-only candidate evidence before any lifecycle mutation. The `candidate_artifact` section records filename/config agreement, VERSION consistency, ZIP readability, root layout, hygiene, nested ZIP checks, and accepted-baseline continuity. This evidence can block unsafe candidates, but it is not adoption evidence by itself. Authoritative accepted-baseline evidence still comes from `pb artifact current --json` after adoption.

## v0.1.125 baseline evidence scope

For release `v0.1.125`, candidate construction evidence remains distinct from candidate verification, candidate testing, explicit acceptance, Project Source publication, and accepted/current evidence. The accepted baseline entering the proof cycle is `v0.1.124`; `v0.1.125` must not be described as accepted/current until the native candidate lifecycle proves it.
