# Slice Horizon

## Repair history

- `v0.1.112` and `v0.1.113` are superseded historical PBAI structural and registry slices.
- `v0.1.114.2 — Deterministic candidate test-runner dependency repair` is accepted/current.
- `v0.1.115 — PBAI-001 operational validation, lifecycle evidence, and impact-based fast testing` is repair-required after cross-process browser-profile handoff failed before external-live execution.

## Active repair

- `v0.1.115.1 — Release-live profile ownership handoff repair` is the sole active repair candidate.
- `v0.1.116 — PBAI-001 templates, migration reports, and first domain-module proof` is planned after repair acceptance.

## Current rolling horizon

| Version | Slice | Status | Release mode | Scope |
|---|---|---|---|---|
| v0.1.114 | PBAI-001 executable validation and SkillRun evidence | repair_required | normal | executable implementation retained through accepted repairs |
| v0.1.114.1 | Candidate runtime resolution and compatibility repair | repair_required | repair | exact candidate runtime worked; missing pytest required another repair |
| v0.1.114.2 | Deterministic candidate test-runner dependency repair | accepted_current | repair | strict 10/10 validation and exact adoption verified |
| v0.1.115 | PBAI-001 operational validation, lifecycle evidence, and impact-based fast testing | repair_required | normal | primary transports passed; external-live profile handoff failed and adoption was refused |
| v0.1.115.1 | Release-live profile ownership handoff repair | active | repair | bounded cross-process flock queue plus explicit service/host release barrier |
| v0.1.116 | PBAI-001 templates, migration reports, and first domain-module proof | planned_after_acceptance | normal | complete template migration and domain-module proof |

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
## Current horizon — v0.1.116

- `v0.1.115.1` — accepted/current repair with operational PBAI proof.
- `v0.1.116` — active normal slice: v0.1.116 — PBAI-001 templates, migration reports, differential validation, and first promptbranch-method domain-module proof.
- `v0.1.117` — planned after acceptance: v0.1.117 — PBAI compliance inventory and multi-repository rollout.

Repair horizon rule remains unchanged: repairs do not advance normal scope.

