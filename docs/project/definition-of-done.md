# Definition of Done

## MVP DoD

| ID | DoD item | Status | Evidence | Last release |
|---|---|---:|---|---|
| DOD-001 | MVP goal is documented in the project control surface | done | `docs/project/mvp.md` | v0.1.67 |
| DOD-002 | Release plan is documented in the project control surface | done | `docs/project/plan.md` | v0.1.67 |
| DOD-003 | Current status page is documented in the project control surface | done | `docs/project/status.md` | v0.1.67 |
| DOD-004 | Release status table is initialized | done | `docs/project/release-status.md` | v0.1.67 |
| DOD-005 | Migration ledger maps existing planning/status documents | done | `docs/project/migration.md` | v0.1.67 |
| DOD-006 | Durable decisions are summarized | done | `docs/project/decisions.md` | v0.1.67 |
| DOD-007 | Focused project-control-surface validation passes | done | `tests/test_project_control_surface.py` | v0.1.67 |
| DOD-008 | Full tests pass when required | open | full test log not provided for this slice | - |
| DOD-009 | ZIP artifact has clean repository-root structure | done | final v0.1.68 ZIP hygiene check | v0.1.68 |
| DOD-010 | Accepted baseline is verified | done | user-provided `pb artifact current --json` for v0.1.66 | v0.1.66 |
| DOD-011 | New candidate is adopted/current | open | adoption evidence required after install/adopt | - |
| DOD-012 | Project Sources add performance/transactional diagnostics are covered by focused tests | done | `tests/test_project_source_capabilities.py` targeted v0.1.68 tests | v0.1.68 |

## Status values

Use only:

```text
open
in_progress
blocked
done
deferred
not_applicable
```

## Evidence rule

A DoD item may be marked `done` only when evidence is listed. A candidate ZIP does not satisfy adoption-related DoD rows until adoption evidence confirms alignment.
