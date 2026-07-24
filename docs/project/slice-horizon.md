# Slice Horizon

## Current rolling horizon

| Version | Slice | Status | Release mode | Scope |
|---|---|---|---|---|
| v0.1.107 | Controlled correction execution envelope design | completed | normal | accepted design-only envelope |
| v0.1.108 | Controlled correction execution envelope validation gate | repair_required | normal | historical failed normal candidate |
| v0.1.108.1 | Project Source staged-overwrite and removal-proof reliability | completed | repair | accepted/current reliability repair |
| v0.1.109 | PROJECT_SETTINGS.md, AGENTS.md and project authority-graph definition | active | normal | precedence-free authority ownership and read-only drift validation |
| v0.1.110 | Authority-backed project snapshot and drift report | planned_after_acceptance | normal | structured read-only snapshot; no automatic repair |

## Repair horizon rule

Repair releases must not advance normal scope. A normal slice may advance only after the accepted/current baseline and project control surface agree.
