# Repair v0.1.103.10.110 — missing-registry-safe read-only validation

## Problem

`pb test agent` and `pb test full` reached the read-only source-sync planning steps while the clean-break project registry had not been initialized. The planning path called `ArtifactRegistry.current()` / `list()`, which promoted the expected uninitialized state into a top-level `artifact_registry_missing` exception. The CLI therefore exited before emitting the normal `test_suite` JSON, and `pb test report` could only return `json_not_found`.

## Repair

- `build_source_sync_preflight()` now inspects registry state without mutation.
- A missing registry is represented as `registry_status: missing`, `artifact_count: 0`, and `current: null` for read-only planning.
- Invalid or unreadable registries remain fail-closed.
- Dry-run and upload-preflight helpers convert invalid registry state into structured failed test steps instead of aborting the complete suite.
- `pb test agent` and `pb test full` always emit a top-level `test_suite` JSON, including an explicit `pre_suite_failure` object if dispatch itself raises.
- `pb test report` recognizes a structured pre-suite failure and returns `test_command_failed_before_suite` instead of `json_not_found`.
- Artifact mutations still require a valid initialized registry; no registry is created implicitly.

## Invariants

1. Read-only planning may observe an uninitialized registry.
2. Read-only planning must not create the registry or artifact directory.
3. Artifact adoption, release, and registry mutation remain blocked on missing, invalid, or unreadable registry authority.
4. Test commands always produce one machine-readable terminal suite object.
5. Invalid registry state is visible as a failed step, never silently treated as empty.

## Focused acceptance

- missing registry + dry-run plan → planned, `registry_status=missing`
- missing registry + upload preflight → confirmation plan, no mutation
- missing registry + artifact mutation → blocked
- invalid registry + authority-dependent operation → blocked
- `pb test agent` with no registry → complete suite JSON
- `pb test full` → complete suite JSON
- `pb test report` over a pre-suite failure → structured failure summary
