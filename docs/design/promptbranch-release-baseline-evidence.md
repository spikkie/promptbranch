# Promptbranch Release Baseline Evidence

Release: `v0.1.60`

## Purpose

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

After `v0.1.60` is adopted, the same rule moves the next normal release target to `v0.1.61`.

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
