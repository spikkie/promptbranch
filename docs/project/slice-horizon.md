# Slice Horizon

## Current rolling horizon

| Version | Slice | Status | Release mode | Scope |
|---|---|---|---|---|
| v0.1.111.5.2 | Null-safe previous active-step ETA state | superseded | repair | accepted ETA corrective superseded as current by v0.1.112 |
| v0.1.112 | PBAI-001 declaration and structural validation | accepted_current | normal | strict 10/10 validation, structural PBAI gate, adoption, and exact current identity verified |
| v0.1.113 | PBAI-001 registry validation and reference resolution | active | normal | tracked registry, exact reference resolution, implementation binding, capability coverage, and bounded authority proof |
| v0.1.114 | PBAI-001 executable validation and SkillRun evidence | planned_after_acceptance | normal | ordered bounded execution and valid SkillRun evidence without operational proof |

## Repair horizon rule

Repair releases must not advance normal scope. A normal slice may advance only after the accepted/current baseline and project control surface agree.

## Historical repair chain

| Version | Slice | Status | Release mode | Scope |
|---|---|---|---|---|
| v0.1.111 | Global release lifecycle contract and read-only planner | repair_required | normal | installed module packaging failed |
| v0.1.111.1 | Package and verify the release-contract engine | superseded | repair | retained in v0.1.111.2 |
| v0.1.111.2 | Full-test progress, ETA, and fail-fast reporting | repair_required | repair | false expected-missing failure accounting; browser fail-fast was only phase-level |
| v0.1.111.3 | Normalised browser progress and genuine step-level fail-fast | repair_required | repair | product transport proof passed; strict logs exposed idle-handoff and ETA defects |
| v0.1.111.4 | Deterministic external-live idle handoff | repair_required | repair | strict retry exposed false full-capacity final-count verification |
| v0.1.111.4.1 | Capacity-aware Project Source family replacement verification | accepted | repair | strict 10/10 validation and evidence-bound adoption passed |
| v0.1.111.5 | Named-step ETA planning and stable countdown | accepted | repair | strict 10/10 validation passed; informational defects queued for correction |
| v0.1.111.5.1 | Empty-step-safe ETA progress and stable range countdown | repair_required | repair | strict run exposed null previous active-step TypeError; not adopted |
| v0.1.111.5.2 | Null-safe previous active-step ETA state | accepted_current | repair | corrected null prior state and closed ETA exception diagnostics |
