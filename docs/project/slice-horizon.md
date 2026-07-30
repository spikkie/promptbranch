# Slice Horizon

## Repair history

- `v0.1.114.1 — Candidate runtime resolution and FastAPI/Starlette compatibility repair` is repair-required after strict host validation exposed missing pytest in the exact candidate venv.

## Active repair

- `v0.1.114.2 — Deterministic candidate test-runner dependency repair` is the sole active repair.
- `v0.1.115 — PBAI-001 operational validation and lifecycle evidence` remains the next normal slice after repair acceptance.

## Current rolling horizon

| Version | Slice | Status | Release mode | Scope |
|---|---|---|---|---|
| v0.1.112 | PBAI-001 declaration and structural validation | superseded | normal | accepted structural proof superseded as current by v0.1.113 |
| v0.1.113 | PBAI-001 registry validation and reference resolution | accepted_current | normal | strict 10/10 validation, registry proof, adoption, and exact current identity verified |
| v0.1.114 | PBAI-001 executable validation and SkillRun evidence | repair_required | normal | executable implementation retained; host package import failed under an ambient shadow runtime |
| v0.1.114.1 | Candidate runtime resolution and FastAPI/Starlette compatibility repair | repair_required | repair | candidate runtime binding and import compatibility passed; exact candidate venv lacked pytest |
| v0.1.114.2 | Deterministic candidate test-runner dependency repair | active | repair | pin and verify pytest inside the exact candidate venv without changing PBAI scope |
| v0.1.115 | PBAI-001 operational validation and lifecycle evidence | planned_after_acceptance | normal | real lifecycle, publication, adoption/current, and recovery proof |

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
