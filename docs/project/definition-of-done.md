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

| DOD-058 | Text Project Source add verifies the save trigger and applies bounded fallback triggers before persistence verification | done | `promptbranch_browser_auth/client.py`, `chatgpt_browser_auth/client.py`, `tests/test_project_source_capabilities.py`, `docs/repair-v0.1.78.2.12.md` | v0.1.78.2.12 |

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

| DOD-049 | Release-control live tests reuse a retained quarantine project while ChatGPT Project deletion is frozen | done | `chatgpt_claudecode_workflow_release_control.sh`, `tests/test_promptbranch_shell_scripts.py`, `docs/repair-v0.1.78.2.3.md` | v0.1.78.2.3 |


| DOD-050 | Delete-frozen live-test profiles default to the retained quarantine project and release-control can run all operator tests with continue-on-failure final GO/FIX reporting | done | `promptbranch_cli.py`, `chatgpt_claudecode_workflow_release_control.sh`, `tests/test_promptbranch_cli.py`, `tests/test_promptbranch_shell_scripts.py`, `docs/repair-v0.1.78.2.4.md` | v0.1.78.2.4 |

| DOD-051 | Release-control run-all verdict uses top-level step results, preflights live profile authentication, and reports full direct/localhost/live/import/guard rows | done | `chatgpt_claudecode_workflow_release_control.sh`, `promptbranch_cli.py`, `.gitignore`, `tests/test_promptbranch_shell_scripts.py`, `tests/test_cli_parser.py`, `docs/repair-v0.1.78.2.5.md` | v0.1.78.2.5 |

| DOD-052 | Release-control verifies Docker host build context, built image content, running container content, and service health version before tests | done | `Dockerfile`, `docker-compose.chatgpt-service.yml`, `chatgpt_claudecode_workflow_release_control.sh`, `tests/test_promptbranch_shell_scripts.py`, `docs/repair-v0.1.78.2.6.md` | v0.1.78.2.6 |

| DOD-053 | Docker provenance probe JSON writers are syntactically valid and write newline-terminated JSON evidence | done | `chatgpt_claudecode_workflow_release_control.sh`, `tests/test_promptbranch_shell_scripts.py`, `docs/repair-v0.1.78.2.7.md` | v0.1.78.2.7 |


## DOD-054 — Docker pyproject probe quoting repair

Status: done for v0.1.78.2.8 candidate.

Acceptance criteria:

- Docker image and container content probes must not use a malformed inline Python command that loses quotes around `/app/pyproject.toml` or `rb`.
- A focused regression test must reject the broken `tomllib.load(open(/app/pyproject.toml, rb))` form.
- Existing Docker provenance checks from DOD-052 and newline JSON writer fix from DOD-053 must remain present.
- ChatGPT Project deletion remains frozen.


## DOD-055 — Docker pyproject probes avoid shell positional parameters

Status: done for v0.1.78.2.9 candidate.

Acceptance criteria:

- Docker image-content and running-container content probes do not use an awk `$2` expression that can be expanded by the shell under `set -u`.
- The pyproject version reader remains shell-safe inside `docker run ... sh -lc` and `docker exec ... sh -lc`.
- A focused regression test rejects the old fragile awk-dollar probe form.
- Existing Docker provenance and delete-frozen live-test behavior is preserved.

## DOD-056 — Run-all rate-limit recovery policy

Status: done for v0.1.78.2.10 candidate.

Release-control `--run-all-tests` treats ChatGPT conversation-history 429 / "Too many requests" evidence as temporary backpressure. When a step exits non-zero with rate-limit evidence, release-control waits for the configured cooldown window and retries the same step once before declaring the all-tests verdict `FIX`. Browser-level modal acknowledgement remains in the Promptbranch client; the release path now makes that recovery first-class instead of immediately failing the candidate.

## DOD-057 — Run-all profile seed preservation and strict rate-limit detection

Status: done for v0.1.78.2.11 candidate.

Acceptance criteria:

- Release-control ZIP import preserves `.pb_profile_local_debug/` but not `.pb_profile_local_debug_pools/`.
- Live `--run-all-tests` preflight validates the actual seed profile directory before ask-live, visual-artifact-roundtrip, and release-live.
- Live seed profile hygiene removes Chromium singleton/DevTools runtime files before pool cloning.
- Rate-limit retry detection only triggers on strict ChatGPT 429 / "Too many requests" evidence, not generic "No rate-limit evidence" diagnostic text.
- Docker provenance checks and project deletion freeze remain preserved.

| DOD-059 | Default run-all release validation isolates text-source add/remove as source-kind compatibility unless strict matrix is requested | done | `chatgpt_claudecode_workflow_release_control.sh`, focused shell-script tests | v0.1.78.2.13 |

## DOD-060 — Project Source remove containment guard

Status: done for v0.1.78.2.14 candidate.

Acceptance criteria:

- Project Source card snapshots are scoped to visible Project Sources surfaces.
- Project Source container/action-button lookup does not fall back to broad `main`/`body` DOM queries.
- Source remove/overwrite verification fails closed instead of treating sidebar, recents, project navigation, or conversation history rows as source cards.
- Docker provenance, live seed profile handling, strict rate-limit detection, text-source compatibility isolation, and project deletion freeze remain preserved.


| DOD-061 | Project Source add verification does not false-fail by waiting on conversation-history cooldown | done | `promptbranch_browser_auth/client.py`, `tests/test_project_source_capabilities.py`, `tests/test_project_resolve.py`, `docs/repair-v0.1.78.2.15.md` | v0.1.78.2.15 |
| DOD-062 | File-source overwrite recovers only the specific post-commit stale-inflight verification false-negative state with bounded refreshed proof | done | `promptbranch_browser_auth/client.py`, `tests/test_project_source_capabilities.py`, `docs/repair-v0.1.78.2.16.md` | v0.1.78.2.16 |

## DOD-061 — Project Source add timeout false-negative containment

Status: done for v0.1.78.2.15 candidate.

Acceptance criteria:

- Project Source add/list/remove/capability operations skip the persisted conversation-history cooldown at context start.
- Project Source persistence refresh navigation can clear rate-limit modals without sleeping on the persisted conversation-history cooldown.
- Conversation-history cooldown telemetry and persisted cooldown state are still recorded for history-reading operations.
- Docker provenance, live seed profile handling, strict rate-limit detection, text-source compatibility isolation, Project Source remove containment, and project deletion freeze remain preserved.

| DOD-063 | `pb ask --prompt-file` preserves prompt-file origin through CLI/service/browser submit policy, uses button-first dispatch when the send button is available, keeps prepare-token-only fail-closed, and exposes submit-causality diagnostics | done | `promptbranch_cli.py`, `promptbranch_service_client.py`, `promptbranch_container_api.py`, `promptbranch_automation/service.py`, `promptbranch_browser_auth/client.py`, `scripts/smoke-pb-ask-prompt-file.sh`, focused prompt-file submit tests, `docs/repair-v0.1.78.2.17.md` | v0.1.78.2.17 |

| DOD-064 | Prompt-file smoke failures preserve causal diagnostics and prompt-file button-first submit does not press keyboard Enter after a successful button dispatch | done | `scripts/smoke-pb-ask-prompt-file.sh`, `promptbranch_browser_auth/client.py`, focused prompt-file submit/smoke tests, `docs/repair-v0.1.78.2.18.md` | v0.1.78.2.18 |
| DOD-065 | `pb ask --prompt-file` submit-policy flag is accepted and forwarded by the intermediate automation wrapper before reaching the browser client | done | `promptbranch_automation/automation.py`, focused automation wrapper test, `docs/repair-v0.1.78.2.19.md` | v0.1.78.2.19 |
| DOD-066 | Prompt-file live smoke accepts the structured `pb ask --json` answer contract and successful ask JSON exposes top-level submit-causality evidence | done | `scripts/smoke-pb-ask-prompt-file.sh`, `promptbranch_browser_auth/client.py`, focused smoke/source contract tests, `docs/repair-v0.1.78.2.20.md` | v0.1.78.2.20 |
| DOD-067 | Release-control supports guarded full-workflow adoption through `--adopt-after-validation` after successful validation | done | `chatgpt_claudecode_workflow_release_control.sh`, `tests/test_promptbranch_shell_scripts.py`, `docs/repair-v0.1.78.2.20.1.md` | v0.1.78.2.20.1 |

| DOD-068 | Large prompt-file packages use automated attachment-mode transport by default while small prompt files remain inline | done | `promptbranch_cli.py`, `scripts/smoke-pb-ask-large-prompt-file.sh`, focused CLI transport tests, `docs/repair-v0.1.78.2.20.2.md` | v0.1.78.2.20.2 |
| DOD-069 | Large prompt-file attachment mode exposes stable top-level attachment/upload/submit/response causality diagnostics without changing transport behavior | done | `promptbranch_cli.py`, `promptbranch_container_api.py`, `promptbranch_browser_auth/client.py`, `scripts/smoke-pb-ask-large-prompt-file.sh`, focused attachment-diagnostics tests, `docs/repair-v0.1.78.2.20.3.md` | v0.1.78.2.20.3 |

| DOD-070 | Project Source text add treats large pasted text/document conversion as success only with current-run content proof, and prunes only safe retained-test sources at the observed source-capacity boundary | done | `promptbranch_browser_auth/client.py`, `promptbranch_full_integration_test.py`, `tests/test_project_source_capabilities.py`, `docs/repair-v0.1.78.2.20.4.md` | v0.1.78.2.20.4 |

| DOD-071 | Generic document-converted text sources cannot satisfy Project Source text-add unless current-run content proof succeeds | done | `promptbranch_browser_auth/client.py`, `tests/test_project_source_capabilities.py`, `docs/repair-v0.1.78.2.20.5.md` | v0.1.78.2.20.5 |

| DOD-072 | Project Source large text-document conversion requires a dedicated/generated document name; legacy `pasted.txt` identities are cleanup noise only | done | `promptbranch_browser_auth/client.py`, `tests/test_project_source_capabilities.py`, `docs/repair-v0.1.78.2.20.6.md` | v0.1.78.2.20.6 |

| DOD-073 | Project Source text-add release gate is split from large-paste document-conversion characterization | done | `promptbranch_full_integration_test.py`, `promptbranch_browser_auth/client.py`, `tests/test_project_source_capabilities.py`, `docs/repair-v0.1.78.2.20.7.md` | v0.1.78.2.20.7 |

| DOD-074 | Fresh Project Source integration runs classify pre-create missing projects as expected, remove only same-run ephemeral test projects, and use a sufficient scheduler/source lifecycle validation timeout | done | `promptbranch_full_integration_test.py`, `promptbranch_project_delete_safety.py`, `promptbranch_container_api.py`, `promptbranch_test_suite.py`, focused cleanup/classification tests, `docs/repair-v0.1.78.2.20.8.1.md` | v0.1.78.2.20.8 |
| DOD-075 | Same-run ephemeral project cleanup normalizes project URL shapes before removal without changing Project Source add behavior | done | `promptbranch_browser_auth/client.py`, `tests/test_project_delete_safety.py`, focused cleanup/normalization tests, `docs/repair-v0.1.78.2.20.8.2.md` | v0.1.78.2.20.8.2 |

| DOD-076 | Same-run ephemeral cleanup compares canonical Project ids and text-source save commits receive bounded post-commit source-surface recovery | done | `promptbranch_project_delete_safety.py`, `promptbranch_browser_auth/client.py`, focused cleanup/source tests, `docs/repair-v0.1.78.2.20.8.3.md` | v0.1.78.2.20.8.3 |

| DOD-077 | ChatGPT Project deletion is immutable-frozen with no same-run, ephemeral, focused-test, or command-line exception | done | `promptbranch_project_delete_safety.py`, `promptbranch_container_api.py`, `promptbranch_automation/service.py`, `promptbranch_browser_auth/client.py`, `promptbranch_full_integration_test.py`, focused delete-safety/cleanup tests, `docs/repair-v0.1.78.2.20.8.4.md` | v0.1.78.2.20.8.4 |
| DOD-078 | Project deletion cleanup-policy evidence labels consistently report `no_project_delete_until_secure_protocol` | done | `promptbranch_full_integration_test.py`, `tests/test_full_integration_harness.py`, stale-label grep, `docs/repair-v0.1.78.2.20.8.5.md` | v0.1.78.2.20.8.5 |
| DOD-079 | Joined repos use one project-scoped Promptbranch workflow state authority by default for backend state reads and task/workspace/artifact state writes | done | `promptbranch_cli.py`, `tests/test_promptbranch_repos.py`, `docs/repair-v0.1.78.2.20.8.6.md` | v0.1.78.2.20.8.6 |
| DOD-080 | Plain-text response wait initializes diagnostic breakdown before deadline/debug bookkeeping | done | `promptbranch_browser_auth/client.py`, `tests/test_project_list_browser_client.py`, `docs/repair-v0.1.78.2.20.8.7.md` | v0.1.78.2.20.8.7 |
| DOD-081 | Localhost Project Source add returns structured stale-inflight diagnostics before client timeout and records a post-failure source-list diagnostic | done | `promptbranch_service_client.py`, `promptbranch_full_integration_test.py`, `tests/test_promptbranch_service_client.py`, `tests/test_full_integration_harness.py`, `tests/test_project_source_capabilities.py`, `docs/repair-v0.1.78.2.20.8.8.md` | v0.1.78.2.20.8.8 |

| DOD-082 | JSON orchestration event-intake proposals have a repo-relative read-only schema, validator, CLI command, committed example, and fail-closed tests | done | `promptbranch_orchestration.py`, `scripts/orchestration/validate_event_intake.py`, `pb orchestration validate-event`, `tests/orchestration/test_event_intake_foundation.py` | v0.1.79 |

| DOD-083 | Accepted-event fixtures have a dedicated read-only CLI validator, committed G0-G6 examples, explicit accepted-current baseline binding, fail-closed zero-default behavior, and no state/source/artifact/deployment mutation authority | done | `promptbranch_orchestration.py`, `pb orchestration validate-accepted-event`, `scripts/orchestration/validate_accepted_event.py` compatibility wrapper, `tests/orchestration/test_orchestration_accepted_event_schema.py`, `docs/design/orchestration/examples/accepted_events/*.json` | v0.1.80 |
| DOD-084 | Accepted-event dry-run promotion previews validated accepted-event records without writing accepted state or mutating source/artifacts/deployment/runtime | focused | `promptbranch_orchestration.py`, `pb orchestration accept-event --dry-run`, `tests/orchestration/test_orchestration_accepted_event_schema.py`, `tests/test_cli_parser.py` | v0.1.81 |
| DOD-085 | Accepted-event dry-run supports explicit repo-local input files and fails closed for unsafe/missing/invalid explicit paths without writing state or mutating source/artifacts/deployment/runtime | focused | `promptbranch_orchestration.py`, `pb orchestration accept-event --dry-run --json <accepted-event-file>`, `tests/orchestration/test_orchestration_accepted_event_schema.py`, `tests/test_cli_parser.py` | v0.1.82 |

| DOD-085a | Accepted-event dry-run explicit input works from installed runtime/worktree path resolution and does not fall back to `site-packages/docs/...` | focused_candidate | `tests/orchestration/test_orchestration_accepted_event_schema.py`; `pb orchestration accept-event --dry-run --json docs/design/orchestration/examples/accepted_events/G0_intent.accepted_event.example.json` expected after install | v0.1.82 candidate |

## DOD-086 — Accepted-event ledger scaffold remains read-only

Status: done for v0.1.83 focused candidate.

Acceptance criteria:

- `pb orchestration ledger-status --json` reports the future accepted-event ledger path and record schema path.
- The ledger scaffold reports `write_command_available=false` and `accept_event_write_supported=false`.
- No accepted state, runtime state, Project Source, artifact adoption, deployment, or model-execution authority is introduced.
- The command works from installed-runtime/worktree path resolution and does not rely on `site-packages/docs/...`.
- The actual append-only ledger write remains out of scope.
| DOD-087 | Accepted-event ledger validation command validates the pre-write ledger scaffold read-only, treats absent ledger as valid when scaffold exists, fails closed for malformed existing JSONL, and introduces no ledger write or mutation authority | focused | `promptbranch_orchestration.py`, `pb orchestration validate-ledger --json`, `tests/orchestration/test_orchestration_accepted_event_schema.py`, `tests/test_cli_parser.py` | v0.1.84 |


| DOD-088 | Delete-frozen live/browser tests use a fresh run-scoped ChatGPT Project by default for each validation run while still enforcing keep-project and preserving the project-deletion freeze | focused | `promptbranch_cli.py`, `chatgpt_claudecode_workflow_release_control.sh`, focused parser/CLI/release-control shell tests, `docs/repair-v0.1.84.1.md` | v0.1.84.1 |
| DOD-089 | Mutation-capable delete-frozen live tests create fresh Projects directly and do not resolve target Projects by non-unique display name | focused | `promptbranch_cli.py`, `tests/test_promptbranch_cli.py`, `docs/repair-v0.1.84.5.1.md` | v0.1.84.5.1 |
| DOD-090 | Live-test backend/history `429` and rate-limit modal telemetry is propagated through `/v1/ask` and classified as non-clean validation for ask-live and visual artifact roundtrip | focused | `promptbranch_container_api.py`, `promptbranch_cli.py`, `tests/test_promptbranch_container_api.py`, `tests/test_promptbranch_cli.py`, `docs/repair-v0.1.84.5.2.md` | v0.1.84.5.2 |
| DOD-091 | Live-test rate-limit telemetry aggregation deduplicates carried browser download snapshots without weakening non-clean 429 classification | focused | `promptbranch_cli.py`, `tests/test_promptbranch_cli.py`, `docs/repair-v0.1.84.5.3.md` | v0.1.84.5.3 |


## v0.1.84.2 repair note

`v0.1.84.2` is a repair-only candidate on top of focused `v0.1.84.1`. It changes live/browser 429 modal handling so history-sensitive operations click `Got it`, wait the configured acknowledgement cooldown, and continue polling instead of failing on a short modal timeout. It does not advance ledger/write/orchestration scope and does not re-enable ChatGPT Project deletion. Accepted/current remains `v0.1.79` until later adoption/current evidence exists.


## v0.1.84.3 repair status

Uploaded `release_control.v0.1.84.2.run_all_tests.log` ended after the release-control rate-limit retry wait line, so it did not prove a second retry failure. It did prove a release-blocking first-attempt failure in `project_ensure_create_or_reuse`: after 429 modal acknowledgement and cooldown, the ChatGPT create-project submit button stayed disabled after the project name was filled. `v0.1.84.3` repairs only that browser recovery path by adding bounded create-project disabled-submit recovery: check/acknowledge rate-limit modal again, wait configured cooldown, clear/refill the project name, dispatch input/change/keyup/blur events, tab out, reacquire the submit button, and retry enablement before failing closed with structured disabled-state logs. Project deletion remains frozen; ledger/write/orchestration scope does not advance.


## v0.1.84.4 repair status

ChatGPT Project names are limited to 50 characters. `v0.1.84.4` repairs generated test Project naming only: release-control and live-test generated names are capped at 50 characters while preserving run-scoped uniqueness through a stable hash suffix when truncation is required. Explicit `PROMPTBRANCH_RELEASE_TEST_PROJECT_NAME` values longer than 50 characters now fail fast. Project deletion remains frozen; ledger/write/orchestration scope does not advance.


## v0.1.84.5 repair status

The v0.1.84.4 full all-tests/adoption gate returned `FIX` because `visual_artifact_roundtrip` failed with `artifact_candidate_not_selected`: the ChatGPT reply envelope was near-complete but invalid JSON in one attempt due raw nested quotes inside a validation string, and another attempt had a balanced JSON object followed by a truncated `END_PROMPTBRANCH_REPLY_JSON` marker fragment. `v0.1.84.5` repairs only the visual artifact reply-envelope surface: the prompt now asks for simple validation strings without arrays/raw quotes/Markdown links, and the reply parser accepts a balanced JSON object followed only by a truncated end-marker fragment while still rejecting genuinely malformed JSON. Project deletion, ledger/write/orchestration, Project Source, artifact adoption/current, deployment, and model-execution scope do not advance.

## v0.1.84.5.1 repair status

`v0.1.84.5.1` repairs live-test Project identity and visual-roundtrip timing evidence only. `ask-live`, `visual-artifact-roundtrip`, and `release-live` now create a fresh Project with `create_project()` for mutation-capable default/`--project-name` test setup and carry the returned Project URL/id forward; they do not resolve by non-unique ChatGPT Project display name. `--conversation-url` remains the exact existing-target bypass. `pb test visual-artifact-roundtrip --json` now includes `phase_timings` for input ZIP creation, Project setup, ask, reply parse, artifact download, smoke verification, cleanup when applicable, and total elapsed time. Project deletion remains frozen; ledger/write/orchestration, Project Source, artifact adoption/current, deployment, and model-execution scope do not advance.

## v0.1.84.5.2 repair status

`v0.1.84.5.2` repairs live-test 429 telemetry propagation and non-clean validation classification only. `/v1/ask` now preserves browser-service `rate_limit_telemetry`; `pb test ask-live --json` and `pb test visual-artifact-roundtrip --json` surface rate-limit telemetry; otherwise functional live-test runs that observe backend/history `429` or ChatGPT rate-limit modal telemetry now report `status=rate_limited_contaminated` and `ok=false` instead of clean `verified`. Functional artifact evidence remains visible through `functional_status`, `verification_status`, and artifact-intake details. Project deletion remains frozen; ledger/write/orchestration, Project Source, artifact adoption/current, deployment, and model-execution scope do not advance.


## v0.1.84.5.3 repair status

`v0.1.84.5.3` repairs rate-limit telemetry aggregation evidence only. It deduplicates event-backed telemetry snapshots so browser download telemetry carried into smoke-verification results is not counted twice. The `rate_limited_contaminated` non-clean classification from `v0.1.84.5.2` is preserved.


## v0.1.84.5.4 repair DoD note

`v0.1.84.5.4` adds the recovered-rate-limit continuation invariant: when ChatGPT 429 telemetry is acknowledged and cooldown-waited inside the live browser operation and the sentinel/artifact verification succeeds, the test reports `verified_with_recovered_rate_limit` with `ok=true`; unrecovered 429 evidence remains non-clean.


## DOD-092 — Recovered 429 does not replay whole release-control step

A run-all step that functionally passes after ChatGPT rate-limit modal acknowledgement and cooldown wait is treated as `verified_with_recovered_rate_limit` by release-control and is not replayed solely because 429 telemetry remains in the log. Unrecovered 429 evidence remains retryable/failing.

## v0.1.84.5.6 repair note

`v0.1.84.5.6` repairs release-control `--run-all-tests` live Project reuse on top of `v0.1.84.5.5`. The run-all live phase now ensures one run-scoped ChatGPT Project once after live profile preflight and passes the returned Project URL to `ask-live`, `visual-artifact-roundtrip`, and `release-live` with `--conversation-url`. This prevents every live subtest from creating a separate retained Project while preserving delete-frozen safety, 50-character Project name caps, project-create recovery, recovered 429 retry suppression, and visual artifact reply-envelope hardening. No ledger/write/orchestration, Project Source mutation, artifact adoption/current, deployment, or model-execution scope advances.

## v0.1.84.5.7 repair note

`v0.1.84.5.7` repairs the shared live Project ensure command introduced in `v0.1.84.5.6`. Release-control `--run-all-tests` now uses the supported top-level `pb project-ensure` command to create or resolve one run-scoped ChatGPT Project, extracts the returned Project URL, and passes that exact URL to `ask-live`, `visual-artifact-roundtrip`, and `release-live` with `--conversation-url`. This preserves the one-Project-per-full-test-run policy without calling the unsupported nested `pb project ensure` surface. No project deletion, ledger/write/orchestration, Project Source mutation, artifact adoption/current, deployment, or model-execution scope advances.

| DOD-093 | Release-control shared live Project ensure uses the supported `pb project-ensure` CLI surface | done | `chatgpt_claudecode_workflow_release_control.sh`, focused shell tests, `docs/repair-v0.1.84.5.7.md` | v0.1.84.5.7 |
| DOD-094 | Release-control detects browser-service ReadTimeout evidence during run-all, recovers the service before the next browser-backed phase, retries live profile preflight at most once after recovery, and does not mask original full-test failures | done | `chatgpt_claudecode_workflow_release_control.sh`, focused shell tests, `docs/repair-v0.1.84.5.8.md` | v0.1.84.5.8 |
| DOD-095 | Release-control robustly extracts the shared live Project URL from `pb project-ensure` and treats recovered 429 with `ok=true` plus `project_url` as a warning, not a live-phase blocker | done | `chatgpt_claudecode_workflow_release_control.sh`, `tests/test_promptbranch_shell_scripts.py::test_release_control_live_project_ensure_accepts_recovered_rate_limit_with_project_url`, `docs/repair-v0.1.84.5.9.md` | v0.1.84.5.9 |
| DOD-096 | Release-control isolates offline release-validation groups from live browser/service transport, skips duplicate local groups after primary direct proof, ignores absent selector-probe modal text as rate-limit evidence, and accepts ask-live streaming-timeout sentinel evidence only when the expected sentinel is visibly present in the expected Project | done | `chatgpt_claudecode_workflow_release_control.sh`, `promptbranch_test_suite.py`, `promptbranch_browser_auth/client.py`, `promptbranch_cli.py`, focused CLI/test-suite/shell tests, `docs/repair-v0.1.84.5.10.md` | v0.1.84.5.10 |

| DOD-097 | Release-control denies browser rate-limit cooldown sleep/retry for localhost/offline validation step names before parsing cooldown seconds or printing the generic waiting warning | focused | `chatgpt_claudecode_workflow_release_control.sh`, `tests/test_promptbranch_shell_scripts.py`, `docs/repair-v0.1.84.5.10.1.md` | v0.1.84.5.10.1 |
| DOD-098 | Release-control keeps localhost/offline cooldown denial while allowing direct transport retry policy and selecting top-level recovered live-test payloads in all-tests summary | focused | `chatgpt_claudecode_workflow_release_control.sh`, `tests/test_promptbranch_shell_scripts.py`, `docs/repair-v0.1.84.5.10.2.md` | v0.1.84.5.10.2 |
| DOD-099 | All-tests summary treats recovered ask-live `ok=false` bookkeeping as green only when acknowledged cooldown telemetry and complete functional sentinel proof are present; failed functional proof remains red | focused | `chatgpt_claudecode_workflow_release_control.sh`, `tests/test_promptbranch_shell_scripts.py`, `docs/repair-v0.1.84.5.10.3.md` | v0.1.84.5.10.3 |

| DOD-100 | Release-control all-tests and full-transport summaries expose live validation diagnostics for source-add timeouts, browser ReadTimeouts, rate-limit evidence, retry policy, retry denial, transport class, likely failure phase, and next operator action without masking failures | focused | `chatgpt_claudecode_workflow_release_control.sh`, `tests/test_promptbranch_shell_scripts.py`, `docs/release-v0.1.84.5.11.md` | v0.1.84.5.11 |

| DOD-101 | `pb ask --new-task` / `--new-conversation` starts a fresh Project task from remembered Project home, preserves default remembered-conversation behavior, fails closed for conflicting or missing target state, preserves no-fill composer safety, and guards state updates behind successful fresh-task binding/submission evidence | focused | `promptbranch_cli.py`, `promptbranch_browser_auth/client.py`, `promptbranch_container_api.py`, `tests/test_ask_cli_new_task.py`, `tests/test_ask_busy_conversation.py`, `docs/release-v0.1.84.5.12.md` | v0.1.84.5.12 |

## DOD-102 — deterministic scheduler/source release-validation group

A release candidate satisfies this DoD when the required `browser_scheduler_source_lifecycle` release-validation group uses explicit fast pytest nodeids for scheduler/source lifecycle invariants and does not rely on broad generic selectors such as `cleanup`. Focused validation must include a regression test that rejects reintroduction of the broad selector and proves at least one source-remove and one browser-profile-busy nodeid remain in the group.

| DOD-103 | Ask state observability exposes schema-v2 `.current.conversation_url` proof path and prevents stale top-level conversation proof assumptions | done | `pb state --proof`, `scripts/smoke-pb-ask-new-task.sh`, `tests/test_cli_state.py`, `tests/test_promptbranch_shell_scripts.py` | v0.1.85 |

| DOD-104 | K8s-game orchestration plan is reconciled to accepted/current v0.1.85 baseline before game implementation starts | focused | `docs/project/*`, `docs/design/orchestration/docs/current_status.md`, `global_mvp_plan.md`, `detailed_mvp_setup_plan.md`, `k8s_game_mvp_contract.md`, `tests/test_project_control_surface.py` | v0.1.86 |

| DOD-105 | Loop target schema and dry-run planner validate bounded problem definitions without side effects | focused | `promptbranch_loop.py`, `pb loop validate`, `pb loop plan`, `pb loop run --dry-run`, `tests/test_promptbranch_loop.py`, `tests/test_cli_loop.py`, `examples/loop-targets/static-game-dry-run-target.json` | v0.1.87 |

| DOD-106 | Installed Promptbranch CLI can import the loop module after package installation, so `pb loop` does not fail with `ModuleNotFoundError: No module named 'promptbranch_loop'` | focused | `pyproject.toml`, `promptbranch_loop.py`, `tests/test_promptbranch_loop_packaging.py`, isolated pip install smoke | v0.1.87.1 |

| DOD-107 | Release-control run-all can reuse already-passed identical direct run-tests evidence only when artifact hash and validation dimensions match, and otherwise fails closed by rerunning | focused_candidate | `chatgpt_claudecode_workflow_release_control.sh`, `tests/test_promptbranch_shell_scripts.py` static fail-closed contract tests | v0.1.88 |

| DOD-108 | Project-source-add-text timeout diagnostics/recovery uses an extended source-mutation timeout and fails closed with source-list diagnostics if the service still times out | focused_candidate | `promptbranch_full_integration_test.py`, `tests/test_full_integration_harness.py`, `docs/repair-v0.1.88.1.md` | v0.1.88.1 |
| DOD-109 | Live validation exposes reviewable timing and browser-action/click audit so redundant clicks can be treated as cooldown risk | focused | `promptbranch_browser_auth/client.py`, `promptbranch_test_report.py`, focused browser-action/test-report tests, `docs/release-v0.1.89.md` | v0.1.89 |


| DOD-110 | Live validation shields non-essential global conversation-history auto-requests while preserving explicit Promptbranch history fetches | focused | `promptbranch_browser_auth/client.py`, `promptbranch_browser_auth/config.py`, `promptbranch_automation/automation.py`, `tests/test_project_list_browser_client.py`, `tests/test_promptbranch_test_report.py` | v0.1.90 |

| DOD-111 | File-source uploads/overwrites do not treat stale inflight after commit as quiet, and post-commit recovery distinguishes visible-source false negatives from true absence | done | `promptbranch_browser_auth/client.py`, `tests/test_project_source_capabilities.py`, `docs/repair-v0.1.90.1.md` | v0.1.90.1 |

| DOD-112 | Run-all validation exposes proof-based direct evidence reuse and localhost/offline cooldown audit so repeated broad validation does not rerun identical direct groups or hide localhost cooldown policy violations | focused_candidate | `chatgpt_claudecode_workflow_release_control.sh`, `tests/test_promptbranch_shell_scripts.py`, `docs/release-v0.1.91.md` | v0.1.91 |

| DOD-113 | Ask-live first-turn null-project Retry responses are bounded-retried without hiding real wrong-Project failures, and run-all summary aggregation prefers live command results over nested helper objects | done_with_followup | `promptbranch_cli.py`, `chatgpt_claudecode_workflow_release_control.sh`, focused tests, `docs/repair-v0.1.91.1.md` | v0.1.91.1 |
| DOD-114 | Run-all final summary extracts pretty-printed live command JSON from noisy logs and does not mark verified live steps failed because of payload parsing/selection | focused_candidate | `chatgpt_claudecode_workflow_release_control.sh`, `tests/test_promptbranch_shell_scripts.py`, `docs/repair-v0.1.91.2.md` | v0.1.91.2 |

## DOD-115 — Docker service clean-system recreate/version verification

Status: in_progress in `v0.1.91.3` repair candidate.

The release-control Docker lifecycle must be deterministic from clean, dirty, and broken host states. It must check Docker/Compose availability before build, resolve the running container by explicit Compose service ID, wait for running/healthy state before content-version probing, and emit diagnostics that distinguish missing containers from version mismatches.

| DOD-116 | Release-control does not require a pre-existing Promptbranch service before Project Source add; it installs the candidate CLI, verifies or bootstraps the candidate service, and reports `pre_source_add_service_unavailable` diagnostics if bootstrap fails | focused_candidate | `chatgpt_claudecode_workflow_release_control.sh`, `tests/test_promptbranch_shell_scripts.py`, `docs/repair-v0.1.91.4.md` | v0.1.91.4 |


## DOD-117 — Run-all live_project_ensure terminal-line aggregation

Done when run-all summary aggregation selects valid `ok=true` `ensure_project` / `project_ensure` payloads with a concrete `project_url`, even when the JSON is followed by a human-readable `shared_live_project_url:` line, and does not mark the step failed solely due to nested schema/helper payloads.
