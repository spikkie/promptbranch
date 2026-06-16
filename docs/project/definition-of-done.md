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

| DOD-035 | Temporary project cleanup retries sidebar-not-found when exact-name resolve proves the project is still present, and release-validation subprocesses are isolated from ambient pytest plugins | done | `promptbranch_full_integration_test.py`, `promptbranch_test_suite.py`, `tests/test_full_integration_harness.py`, `tests/test_promptbranch_test_suite.py`, `docs/repair-v0.1.77.2.md` | v0.1.77.2 |

| DOD-036 | Temporary project removal searches the More-projects surface before failing when the exact project is still resolvable but not visible in the normal sidebar | done | `promptbranch_browser_auth/client.py`, `tests/test_project_resolve.py`, `docs/repair-v0.1.77.3.md` | v0.1.77.3 |

| DOD-037 | Temporary project cleanup derives retry delay from nested rate-limit telemetry and uses extended attempts before failing when the exact project remains resolvable | done | `promptbranch_full_integration_test.py`, `promptbranch_browser_auth/client.py`, `chatgpt_browser_auth/client.py`, focused cleanup/remove tests, `docs/repair-v0.1.77.5.md` | v0.1.77.5 |
| DOD-042 | Project Source stale-inflight commit can proceed only into post-refresh persistence verification, and cleanup removal forwards project name plus exact URL through the service stack | done | `promptbranch_browser_auth/client.py`, `promptbranch_container_api.py`, `promptbranch_automation/service.py`, `promptbranch_full_integration_test.py`, `tests/test_project_source_capabilities.py`, `tests/test_promptbranch_service_client.py`, `docs/repair-v0.1.77.9.md` | v0.1.77.9 |

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

| DOD-038 | Repair ZIP includes required root `.gitignore` so release ZIP import plan can proceed | done | `.gitignore`, `docs/repair-v0.1.77.5.md`, ZIP import-plan root-file validation | v0.1.77.5 |
| DOD-039 | Temporary project cleanup can use generic project-page delete-menu selectors and release-validation scheduler timeout is bounded | done | `docs/repair-v0.1.77.6.md`, focused selector/timeout tests | v0.1.77.6 |
| DOD-040 | Temporary project cleanup retries with the resolved exact project URL passed as request data | done | `docs/repair-v0.1.77.7.md`, focused retarget cleanup tests | v0.1.77.7 |

| DOD-041 | Docker-service temporary project cleanup accepts and forwards explicit per-call project URLs during retargeted cleanup retry | done | `promptbranch_full_integration_test.py`, `tests/test_full_integration_harness.py`, `docs/repair-v0.1.77.8.md`, focused DockerServiceAdapter cleanup test | v0.1.77.8 |
| DOD-043 | Docker service recreation pins the Compose image to the release-derived service image by default | done | `chatgpt_claudecode_workflow_release_control.sh`, `run_chatgpt_service.sh`, `run_chatgpt_service_dev.sh`, `tests/test_promptbranch_shell_scripts.py`, `docs/repair-v0.1.77.10.md` | v0.1.77.10 |

| DOD-044 | Temporary project cleanup can locate name-matched non-anchor sidebar/menu project rows before failing | done | `promptbranch_browser_auth/client.py`, `tests/test_project_resolve.py`, `docs/repair-v0.1.77.11.md` | v0.1.77.11 |


| DOD-045 | Deterministic Artifact Guardian guard validates release ZIP structure before candidate handoff | done | `.artifact-guardian.yml`, `promptbranch_artifact_guardian.py`, `pb artifact guard`, `tests/test_artifact_guardian.py`, `docs/project/artifact-guardian-mvp.md` | v0.1.78 |

| DOD-046 | Project Source file mutation transaction failures are explicit, release-blocking, and reported in failed_steps | done | `promptbranch_browser_auth/client.py`, `promptbranch_full_integration_test.py`, `tests/test_project_source_capabilities.py`, `tests/test_full_integration_harness.py`, `docs/repair-v0.1.78.1.md` | v0.1.78.1 |

| DOD-047 | Public ChatGPT Project deletion paths are frozen until a secure delete protocol exists | done | `promptbranch_project_delete_safety.py`, `promptbranch_container_api.py`, `promptbranch_automation/service.py`, `promptbranch_automation/automation.py`, `promptbranch_browser_auth/client.py`, `promptbranch_full_integration_test.py`, `tests/test_project_delete_safety.py`, `docs/repair-v0.1.78.2.md` | v0.1.78.2 |

| DOD-048 | Release-control and post-release validation accept dotted numeric repair versions with at least three segments | done | `chatgpt_claudecode_workflow_release_control.sh`, `scripts/post-release-validation.sh`, `promptbranch_protocol/schemas/artifact.candidate.schema.json`, `tests/test_promptbranch_shell_scripts.py`, `docs/repair-v0.1.78.2.2.md` | v0.1.78.2.2 |
