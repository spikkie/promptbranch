# Issue #1 — Add a global release lifecycle engine with repository-specific lifecycle contracts

## Status

- ID: `ISSUE-001`
- External reference: `#1`
- Status: `pipeline_candidate`
- Implemented in: `v0.1.111`; evidence-bound end-to-end pipeline candidate in `v0.1.117`
- Priority: `1`
- Owner: Promptbranch
- Discovery result: No matching open issue existed before creation.

## Architectural invariant

> Promptbranch controls the release lifecycle. Each project defines what must be validated and how its artifact is built.

## Goal

Introduce a global Promptbranch release lifecycle engine that owns the generic lifecycle state machine, evidence model, publication, adoption, and accepted/current verification while delegating project-specific validation, testing, packaging, and domain gates to each repository through a strict tracked contract.

## Ownership boundary

### Promptbranch owns

- the generic lifecycle state machine;
- lifecycle planning and phase transitions;
- process execution and timeout enforcement;
- evidence collection and immutable execution records;
- artifact hashing, ZIP/package validation, and publication evidence;
- Project Source publication orchestration;
- artifact adoption orchestration;
- accepted/current verification;
- rollback and recovery decisions within explicitly granted authority;
- fail-closed aggregation and final lifecycle verdicts.

### Each repository owns

- project-specific validation commands;
- test selection and domain-specific gates;
- artifact build commands and packaging rules;
- repository-specific preconditions;
- release-specific environment requirements;
- explicit declarations of preserved paths and forbidden mutations;
- domain acceptance criteria.

Promptbranch must not infer repository-specific commands or silently replace them with generic defaults.

## Proposed tracked contract

Introduce a strict tracked `.promptbranch-release.json` file. The first contract version should define at least:

- schema and schema version;
- repository identity;
- sole version authority and version-file path;
- artifact filename pattern;
- planning command or planning declaration;
- validation commands and ordered gates;
- test commands and timeouts;
- artifact build command;
- artifact verification commands;
- publication policy;
- adoption policy;
- accepted/current verification commands;
- required environment variables by name only, never secret values;
- preserved repository paths;
- forbidden mutation paths;
- evidence requirements;
- lifecycle capabilities explicitly delegated to Promptbranch.

The contract must reject unknown fields, missing required fields, absolute repository paths, path traversal, ambiguous version authority, unbounded commands, unsupported shell constructs, and self-granted publication or adoption authority.

## Lifecycle operations

Planning, execution, publication, and adoption must be separate explicit operations.

### Planning

- Parse and validate `.promptbranch-release.json`.
- Resolve the accepted/current baseline.
- Produce a read-only lifecycle plan.
- Report missing prerequisites without mutation.
- Compute the exact ordered command graph and evidence requirements.

### Local execution

- Execute repository-defined validation, tests, and build commands.
- Enforce per-step and whole-run timeouts.
- Capture exit code, start/end timestamps, stdout/stderr references, hashes, and produced artifacts.
- Stop on the first release-blocking failure unless the contract explicitly defines safe independent continuation.
- Never publish or adopt implicitly.

### Publication

- Require successful local execution evidence.
- Verify the exact artifact hash and package structure again before publication.
- Publish only the artifact declared by the lifecycle evidence.
- Capture the exact backend-assigned Project Source identity and immutable backing identifiers.
- Leave adoption unchanged unless separately requested.

### Adoption

- Require successful local execution and publication evidence from the same lifecycle run or an explicitly imported equivalent evidence bundle.
- Adopt the exact verified artifact and exact Project Source identity.
- Verify runtime, state, registry, repository identity, artifact hash, and accepted/current agreement.
- Emit success only after final accepted/current verification.

## Process execution and evidence requirements

Every executed step must record:

- stable step ID;
- declared command and resolved executable;
- working directory;
- bounded environment allowlist;
- timeout;
- start and end timestamps;
- duration;
- exit code or timeout classification;
- stdout and stderr evidence references;
- input hashes where relevant;
- output hashes where relevant;
- mutation classification;
- validator result;
- release-blocking status.

Execution must fail closed on:

- missing executables;
- non-zero exit codes unless explicitly defined as an accepted result;
- timeout;
- missing output artifact;
- hash mismatch;
- invalid archive structure;
- unsafe archive entries;
- missing evidence;
- stale baseline identity;
- ambiguous Project Source identity;
- adoption-state mismatch.

## Preservation requirements

Lifecycle import, execution, and packaging must preserve:

- `.pb_profile/` as user-local runtime/profile evidence outside release artifacts;
- tracked `.promptbranch-repo.json` as authoritative repository-to-Project binding;
- Git metadata and operator-owned local configuration unless an explicit operation requires otherwise.

`.pb_profile/` must not be copied into release ZIPs. `.promptbranch-repo.json` must remain tracked and included in release ZIPs.

## Staged migration

1. Add read-only contract parsing and lifecycle planning.
2. Add local execution with evidence capture while retaining project-local lifecycle scripts as the invoked implementation.
3. Add differential validation between Promptbranch lifecycle results and existing project-local scripts.
4. Add artifact publication as a separate explicit operation.
5. Add evidence-bound adoption and accepted/current verification.
6. Migrate repositories one at a time after equivalence or stronger behaviour is proven.
7. Retire project-local orchestration only after Promptbranch owns the equivalent generic lifecycle behaviour; project-specific commands and domain gates remain repository-owned.

## First proving project

`promptbranch-method` is the first differential-validation project.

Its existing project-local lifecycle remains authoritative during the comparison period. Promptbranch must prove equivalent or stronger planning, command execution, evidence, packaging, publication, adoption, and final verification before the local orchestration layer can be retired.

## Safety requirements

- Read-only planning must not execute commands or mutate state.
- Local execution must not publish or adopt.
- Publication must not adopt.
- Adoption must require explicit operator intent.
- Commands must run with bounded timeouts and explicit working directories.
- Secrets must never be written into the tracked contract or evidence logs.
- Absolute paths and path traversal in tracked contracts are forbidden.
- Artifact hashes must bind execution, publication, and adoption to the same bytes.
- Project Source publication must preserve exact backend-assigned identity evidence.
- Missing repository or Project authority must block before mutation.
- Failed or ambiguous validation must never advance accepted/current state.
- `.pb_profile/` and tracked `.promptbranch-repo.json` must be handled according to their distinct authority roles.
- Existing project-local lifecycle scripts must remain available during staged migration and rollback.

## Non-goals

- No single universal project test suite.
- No requirement that repositories use the same build system.
- No implicit Git commit or push.
- No implicit deployment.
- No automatic Project Source mutation during planning or local execution.
- No adoption based only on a successful command exit code.
- No silent migration of existing repository contracts.
- No storage of secrets in `.promptbranch-release.json`.
- No replacement of repository-owned domain gates with Promptbranch guesses.

## Acceptance criteria

- [x] Strict `.promptbranch-release.json` schema and parser exist.
- [x] Unknown, missing, ambiguous, absolute, traversal, and unbounded contract values fail closed.
- [x] `pb release contract-plan` is read-only and returns the complete ordered lifecycle plan.
- [x] Local execution runs repository-defined gates with bounded timeouts and complete step evidence.
- [x] Artifact build output is hash-bound and structurally validated.
- [x] Publication is a separate explicit operation; exact Project Source identity is captured by the declared `pb src add --json` step evidence.
- [x] Same-run pipeline adoption is bound to exact Project Source evidence; resumable cross-invocation import is planned for v0.1.118.
- [x] Final accepted/current verification is a separately declared required operation using the existing strict verifier.
- [x] `.pb_profile/` is preserved locally and excluded from release artifacts.
- [x] `.promptbranch-repo.json` is preserved as tracked repository authority and included in release artifacts.
- [x] Existing project-local lifecycle scripts remain during migration.
- [x] `promptbranch-method` actual-repository executable proof is 6/6 equivalent-or-stronger; operational pipeline rollout remains separate.
- [x] The v0.1.117 pipeline skips every dependent later phase after a failed or ambiguous step.
- [x] Same-run pipeline evidence records every phase and exact source/adoption/current payload; resumable evidence import is planned for v0.1.118.
