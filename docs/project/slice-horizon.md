# Slice Horizon

## Current rolling horizon

| Version | Slice | Status | Release mode | Scope |
|---|---|---|---|---|
| v0.1.108.1 | Project Source staged-overwrite and removal-proof reliability | completed | repair | accepted reliability repair before v0.1.109 |
| v0.1.109 | PROJECT_SETTINGS.md, AGENTS.md and project authority-graph definition | completed | normal | accepted/current authority graph |
| v0.1.109.1 | Behavioral surface inventory and runtime authority resolver alignment | repair_required | normal | original normal candidate not adopted |
| v0.1.109.1.1 | Tracked repository Project binding and runtime evidence separation | completed | repair | accepted tracked binding and evidence separation |
| v0.1.110 | Tracked backlog and architecture ticket intake | active | normal | tracked backlog with ISSUE-001 and PBAI-001; no runtime implementation |
| v0.1.111 | Global release lifecycle contract and read-only planner | planned_after_acceptance | normal | first ISSUE-001 implementation phase |

## Repair horizon rule

Repair releases must not advance normal scope. A normal slice may advance only after the accepted/current baseline and project control surface agree.

| v0.1.110 | Tracked backlog and architecture ticket intake | superseded | normal | carried into v0.1.111 |
| v0.1.111 | Global release lifecycle contract and read-only planner | repair_required | normal | installed module packaging failed |
| v0.1.111.1 | Package and verify the release-contract engine | superseded | repair | retained in v0.1.111.2 |
| v0.1.111.2 | Full-test progress, ETA, and fail-fast reporting | repair_required | repair | false expected-missing failure accounting; browser fail-fast was only phase-level |
| v0.1.111.3 | Normalised browser progress and genuine step-level fail-fast | repair_required | repair | product transport proof passed; strict logs exposed idle-handoff and ETA defects |
| v0.1.111.4 | Deterministic external-live idle handoff | repair_required | repair | idle-handoff retained; strict retry exposed false full-capacity final-count verification |
| v0.1.111.4.1 | Capacity-aware Project Source family replacement verification | active | repair | exact prune/upload/delete-old deltas and final identity multiset; fail closed on drift |
| v0.1.111.5 | Named-step ETA planning and stable countdown | planned_after_acceptance | repair | ETA-only observability correction; validation evidence remains independent |
| v0.1.112 | PBAI-001 declaration and structural validation | planned_after_repair_sequence | normal | starts only after v0.1.111.4.1 and v0.1.111.5 acceptance |
