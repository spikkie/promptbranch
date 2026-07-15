# Repair v0.1.103.10.111 — full-suite registry and overwrite alignment

## Problem

The v0.1.103.10.110 candidate made missing registries safe for read-only planning, but full validation exposed four contract mismatches: generic file overwrite still failed when ChatGPT exposed Download/Delete without Replace; smoke treated structured uninitialized read-only states as command failures; lifecycle planning could abort on unresolved project/registry authority; and mutation-oriented tests constructed invalid uninitialized registries.

## Repair

- Any file family falls back from unavailable in-place Replace to upload-new, exact backend-assigned verification, exact prior-family removal, and final singleton verification.
- The live fallback no longer falls through to the legacy test-double delete-before-upload path.
- Smoke accepts only the structured read-only statuses `project_scope_unresolved` and `artifact_registry_missing`, and only when all mutation flags are false.
- The release-status smoke probe uses JSON so the same structured uninitialized states can be accepted without weakening the normal guidance-field contract.
- Release lifecycle `--plan` remains read-only and returns a complete plan plus explicit execution blockers when project identity or registry current state is uninitialized.
- Candidate completion and current-state checks select the repository entry from the mandatory project repo-loop payload.
- Mutation test fixtures explicitly initialize project identity and the project-scoped artifact registry.
- Real artifact adoption and registry mutation remain fail-closed on missing, invalid, unreadable, or unresolved authority.

## Invariants

1. Existing source deletion never precedes verification of the new assigned source in live generic replacement.
2. Exactly one canonical/indexed file-family member remains after successful replacement.
3. Structured uninitialized read-only output is not treated as mutation authority.
4. Lifecycle planning may be available while execution is blocked.
5. Artifact mutations require valid initialized project-scoped authority.
6. Both direct and localhost full-test transports must pass before adoption.

## Focused acceptance

- Replace unavailable + existing generic file → upload once, verify assigned source, remove old family, final count one.
- Replace operation failure other than unsupported → fail closed without upload or deletion.
- structured read-only unresolved/missing status + no mutation flags → smoke pass.
- same status + mutation flag → smoke failure.
- lifecycle plan + missing project/registry current → planned with `execution_ready=false` and explicit blocker.
- initialized mutation fixtures → artifact JSON contract group passes.
- project-scoped candidate completion reads selected repo consistency.
