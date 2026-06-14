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
| DOD-008 | Full tests pass when required | open | full test log required per release | - |
| DOD-009 | ZIP artifact has clean repository-root structure | done | ZIP hygiene checks | v0.1.68+ |
| DOD-010 | Accepted baseline is verified | done | `pb artifact current --all --json` evidence for v0.1.73.4 | v0.1.73.4 |
| DOD-011 | New candidate is adopted/current | open | adoption evidence required after install/adopt | - |
| DOD-012 | Project Sources add performance/transactional diagnostics are covered by focused tests | done | `tests/test_project_source_capabilities.py` targeted v0.1.68 tests | v0.1.68 |
| DOD-013 | Browser-profile busy source/adoption sequencing is guarded by wait-idle and structured retry guidance | done | `tests/test_promptbranch_cli.py` and `tests/test_cli_parser.py` focused v0.1.69 tests | v0.1.69 |
| DOD-014 | Multi-repo artifact current state is repo-scoped and adoption cannot overwrite another repo baseline | done | artifact/current repo-focused tests and v0.1.70 adoption evidence | v0.1.70 |
| DOD-015 | Explicit missing repo artifact-current lookup fails closed without leaking another repo state | done | missing-repo focused tests and v0.1.70.1 adoption evidence | v0.1.70.1 |
| DOD-016 | Project-scoped multi-repo registry resolution works from any joined repo without remembering a coordinator profile | done | project/repo focused tests and control-surface validation | v0.1.71 |
| DOD-017 | Project join/list/doctor and artifact-current all use the same project-scoped registry unless `--profile-dir` is explicitly supplied | done | project/repo/artifact-current focused tests | v0.1.71.1 |
| DOD-018 | Repair ZIP includes required root `.gitignore` and passes root-file completeness guard | done | required root-file check and ZIP hygiene | v0.1.71.2 |
| DOD-019 | Release-control Docker service health gate normalizes canonical `v` versions and bare package versions | done | shell-script health-probe regression tests | v0.1.71.4 |
| DOD-020 | `promptbranch_version.VERSION_TAG` is canonical and cannot double-prefix `v` | done | `tests/test_promptbranch_version.py` | v0.1.71.5 |
| DOD-021 | Explicit project registry import ergonomics safely migrate legacy repo-local current records | done | project import dry-run/import/conflict tests | v0.1.72 |
| DOD-022 | Canonical artifact naming and adopt compatibility are release-gated | done | artifact/adopt focused tests and naming docs | v0.1.73 |
| DOD-023 | Canonical adoption diagnostics and external-repo current-state reporting are repair-gated | done | focused artifact/adopt/current/hygiene tests | v0.1.73.1 |
| DOD-024 | v0.1.73.1 validation/reporting regressions were repaired in candidate v0.1.73.2 | not_applicable | v0.1.73.2 focused tests passed but release-control failed with browser_profile_busy | v0.1.73.2 |
| DOD-025 | All browser-touching source/project lifecycle operations are scheduler-mediated with same-profile serialization | done | focused scheduler tests and `docs/repair-v0.1.73.3.md` | v0.1.73.3 |
| DOD-026 | Focused scheduler lifecycle-plan tests are isolated from ambient `.pb_profile` state | done | `tests/test_promptbranch_cli.py::test_release_lifecycle_plan_includes_scheduler_and_source_queue`; `docs/repair-v0.1.73.4.md` | v0.1.73.4 |
| DOD-027 | Release-control/full-test validation declares and runs required focused regression groups | done | `docs/project/validation-matrix.md`, `promptbranch_test_suite.py`, `promptbranch_test_report.py`, focused validation tests | v0.1.74 |
| DOD-028 | Release-validation pytest groups use the repo/operator Python instead of the installed Promptbranch runtime interpreter | done | `promptbranch_test_suite.py`, `tests/test_promptbranch_test_suite.py`, `docs/repair-v0.1.74.1.md` | v0.1.74.1 |
| DOD-029 | Release-lifecycle plan tests are isolated from ambient operator artifact registry state | done | `tests/test_promptbranch_cli.py`, `docs/repair-v0.1.74.2.md`, focused release-validation tests | v0.1.74.2 |
| DOD-030 | Full integration source-mutation waits align with the universal browser-operation scheduler wait budget | done | `promptbranch_full_integration_test.py`, `tests/test_full_integration_harness.py`, `docs/repair-v0.1.74.3.md` | v0.1.74.3 |
| DOD-031 | Project/repo management commands use one repo-loop model for one repo or many repos | done | `promptbranch_cli.py`, `tests/test_promptbranch_repos.py`, focused project/repo validation | v0.1.75 |

| DOD-032 | Operator/release consumers of `pb artifact current --json` use the repo-loop payload model for one repo and many repos | done | `chatgpt_claudecode_workflow_release_control.sh`, `scripts/post-release-validation.sh`, `tests/test_promptbranch_shell_scripts.py`, focused artifact-current regression tests; accepted/current evidence for v0.1.76 | v0.1.76 |
| DOD-033 | Artifact-current compatibility surface is hardened: normal operator/release logic consumes repo-loop entries, and legacy top-level parsing is confined to explicit compatibility fallback paths | done | `_artifact_current_selected_sections`, `promptbranch_parallel_ask.py`, repo-loop/legacy fallback tests, parallel ask baseline-safety test | v0.1.77 |
| DOD-034 | Temporary project create/remove lifecycle is release-blocking unless create-submit is enabled and cleanup proves absence after sidebar-not-found | done | `promptbranch_browser_auth/client.py`, `promptbranch_full_integration_test.py`, `tests/test_full_integration_harness.py`, `tests/test_project_list_browser_client.py`, `docs/repair-v0.1.77.1.md` | v0.1.77.1 |

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
