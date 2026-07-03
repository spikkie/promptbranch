# Promptbranch Native Release Lifecycle — Current State Update

Updated: 2026-05-24 for documentation release v0.0.265.

## Current state

The native release lifecycle is partially implemented. The older TODO that described doctor/install/test/adopt/lifecycle as future-only is now stale. The current line has delivered these surfaces in stages:

```text
pb release doctor
pb release install planning / controlled install
acceptance hook runner
release adopt + verify mechanics
policy/Git sync safety work
pb release lifecycle orchestration surface
strict final Artifact Intake MVP validation
```

The lifecycle is not yet fully consolidated. Repo-local scripts such as `scripts/finalize-artifact-intake-mvp.sh` and project release-control wrappers still remain part of the operating path.

## Remaining priority

The next lifecycle work should focus on classification and consolidation, not new mutation capability.

Required failure classes:

```text
product_validation_failure
artifact_state_failure
browser_environment_failure
service_network_failure
operator_precondition_failure
```

A browser/session failure must be distinguishable from a source-code or artifact-baseline failure.

## Updated lifecycle target

A mature native lifecycle command should report each proof independently:

```text
doctor proof
install proof
Project Source visibility proof
acceptance hook proof
adopt/current proof
Artifact Intake MVP proof
protocol smoke proof
Git/policy sync proof
```

Post-adoption current proof and protocol-smoke proof must not share ambiguous “latest protocol reply” state. A no-artifact protocol smoke is valid and must not overwrite the real-candidate proof required for strict MVP validation.
