# v0.1.128.2.7 — deterministic offline wheel-build authority corrective

Status: construction candidate; not accepted/current.

Accepted/current baseline: `v0.1.128.2.6.1.1.1` (`chatgpt_claudecode_workflow-2_v0.1.128.2.6.1.1.1.zip`), SHA-256 `90c36f8065d0d343f7a7d6f8e6a11577f8e02ba683d24a026ccb48a755fc5926`.

Active candidate: `v0.1.128.2.7` (`chatgpt_claudecode_workflow-2_v0.1.128.2.7.zip`).

Immutable predecessor `v0.1.128.2.6.1.1.2.1.1` (`chatgpt_claudecode_workflow-2_v0.1.128.2.6.1.1.2.1.1.zip`) passed exact SHA and authority/control gates but failed live `RUNTIME_PREPARED` deterministically while building the candidate Docker image because its Dockerfile still parsed hard-coded version literals from `promptbranch_version.py` and `pyproject.toml`.

Immutable predecessor `v0.1.128.2.6.1.1.2.1.1.1` (`chatgpt_claudecode_workflow-2_v0.1.128.2.6.1.1.2.1.1.1.zip`) is repair-required: its host exact-final-ZIP Docker gate exposed two remaining build-boundary defects—Python 3.10 lacks stdlib `tomllib`, and extracted release contexts must not trigger Git/VCS probing.

This repair keeps `VERSION` as the sole mutable version authority, adds a Python 3.10 `tomli` fallback to the Docker build contract, disables Buildx Git info/labels/dirty probing for extracted release builds, and requires regression proof that the exact-ZIP Docker gate itself never invokes Git from a non-Git directory.

`v0.1.129 — External application pilot bootstrap` remains blocked until this repair is accepted/current.

## v0.1.128.2.6.1.1.1 VERSION-derived structural-contract corrective

Accepted/current remains `v0.1.128.2.5` at SHA-256 `07c6e41d29e932e99d8eda20eeee35de92acdd567df6e529b51aee252fb70d58`. Immutable `v0.1.128.2.6.1.1` at SHA-256 `f23253e99d985906e7a24b61594efb6d3d39a011f2acda78e2c4bc7a49001553` reached independently verified `RUNTIME_PREPARED`; its exact package metadata/import smoke passed, then `TESTED_GREEN` failed deterministically in `validation.application_architecture_structural` because four portable-skill tests pinned `v0.1.128.2.6.1` instead of deriving the current release from `VERSION`. This repair removes those duplicate mutable version authorities and applies the same `VERSION` derivation to current project-control assertions. External-application scope remains blocked; `v0.1.129` is still next normal after acceptance.

## v0.1.128.2.6.1.1 packaging/import-surface corrective

Active repair from accepted/current `v0.1.128.2.5`. `v0.1.128.2.6` (`4ac66b37…`) and distributed `v0.1.128.2.6.1` are preserved as historical failed candidates. This corrective declares `promptbranch_skill_sync` in setuptools package metadata and binds canonical candidate testing to the exact release ZIP through `--package-zip`, closing the source-tree-masking validation gap. Live lifecycle/adoption remains open.
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

| DOD-310 | Full-capacity Project Source replacement derives its authoritative final count and identity multiset from one verified prune, one upload, and verified previous-family removals; exact assigned singleton, pruned absence, previous-family absence, and no unexpected disappearance are release-gated | focused_candidate | `promptbranch_browser_auth/client.py`, `tests/test_project_source_capabilities.py`, `docs/repair-v0.1.111.4.1.md` | v0.1.111.4.1 |

| DOD-342 | PBAI compliance inventory reports migration, proof level and release-contract rollout readiness for one or more repositories without mutation | focused_candidate | `promptbranch_release_pipeline.py`, `tests/test_promptbranch_release_pipeline.py` | v0.1.117 |
| DOD-343 | Generic release-pipeline planning is read-only and declares local, Git, publication, adoption and current-verification phases in authority order | focused_candidate | `pb release pipeline plan`, focused tests | v0.1.117 |
| DOD-344 | Pipeline apply requires canonical version confirmation and explicit mutation dependencies | focused_candidate | pipeline dependency tests | v0.1.117 |
| DOD-345 | Project Source publication evidence is bound into adoption and final accepted/current verification | focused_candidate | fake transport pipeline test and strict release validation pending | v0.1.117 |
| DOD-346 | Candidate artifact is rebuilt and reverified after the guarded release commit before publication | focused_candidate | pipeline phase-order tests; strict release validation pending | v0.1.117 |

| DOD-422 | Generated ask-release prompt names the exact accepted/current artifact and version as the actual source baseline | done | `tests/test_ask_release_artifact_execution_prompt.py` | v0.1.123.2.4 |
| DOD-423 | Generated ask-release prompt requires a fresh physical ZIP bound to the exact request ID before envelope construction | done | `tests/test_ask_release_artifact_execution_prompt.py` | v0.1.123.2.4 |
| DOD-424 | Generated ask-release prompt requires a real attachment and rejects JSON-only sandbox declarations as sufficient evidence | done | `tests/test_ask_release_artifact_execution_prompt.py` | v0.1.123.2.4 |
| DOD-425 | Generated ask-release prompt requires observed artifact metadata and a failed envelope with `artifacts=[]` when materialization fails | done | `tests/test_ask_release_artifact_execution_prompt.py` | v0.1.123.2.4 |

| DOD-426 | Ask-release prompt declares exactly two ordered success components | done | `tests/test_ask_release_artifact_execution_prompt.py` | v0.1.123.2.5 |
| DOD-427 | ZIP output is rendered outside the envelope and JSON-only sandbox declarations are invalid | done | `tests/test_ask_release_artifact_execution_prompt.py` | v0.1.123.2.5 |
| DOD-428 | Failure format is one dynamic failed envelope with `artifacts=[]` | done | `tests/test_ask_release_artifact_execution_prompt.py` | v0.1.123.2.5 |
| DOD-429 | Request schema declares the two-component output and matching attachment policy | done | `tests/test_ask_release_artifact_execution_prompt.py` | v0.1.123.2.5 |
| DOD-430 | Generic exactly-one-envelope lead-in is excluded from release-candidate asks | done | `tests/test_ask_release_two_component_renderer.py` | v0.1.123.2.5 |

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


## DOD-118 — Adopt-after-validation accepts reused direct evidence report path

Done when `--run-all-tests --adopt-after-validation` does not require `pb_test.full.direct.<version>.report.json` if direct validation was reused. The adoption verifier must accept a green `pb_test.all.<version>.summary.json` plus matching `validation_evidence/full_direct.<version>.json`, and must still fail closed when both the direct report and valid reused evidence are absent.

| DOD-119 | Pre-source-add candidate Docker bootstrap uses explicit repo-root Compose invocation and a no-cache build, records build-context version surfaces, and classifies Docker build-context version mismatches before health probing | done | `chatgpt_claudecode_workflow_release_control.sh`, focused shell contract tests, `docs/repair-v0.1.91.7.md` | v0.1.91.7 |


## DOD-120 — Run-all reuses one live browser/source lifecycle for localhost matrix

Done when `--run-all-tests` executes one authoritative direct browser/source lifecycle proof and reuses it for `full_localhost` only when direct validation evidence matches artifact SHA256, version, artifact ref, service base, runtime mode, strict source-kind matrix mode, command signature, and green test/report status. The localhost matrix remains visible through the all-tests summary and cooldown audit, and release-control fails closed if matching direct evidence is missing or stale.

| DOD-121 | Adopt-after-validation accepts reused `full_localhost` lifecycle proof without requiring a missing localhost report file, and run-all emits incremental progress percentages | done | `chatgpt_claudecode_workflow_release_control.sh`, `tests/test_promptbranch_shell_scripts.py`, `docs/repair-v0.1.91.9.md`, accepted/current proof in v0.1.91.10 | v0.1.91.10 |

| DOD-122 | Run-all progress writer emits valid JSON without embedded-Python newline syntax errors, and `browser_scheduler_source_lifecycle` timeout diagnostics expose active/completed/failed/timed-out pytest nodeids without changing required validation semantics | done | `chatgpt_claudecode_workflow_release_control.sh`, `promptbranch_test_suite.py`, focused shell/test-suite regressions, `docs/repair-v0.1.91.10.md`, all-tests/adopt-current proof | v0.1.91.10 |


| DOD-123 | MVP-1 state-only loop walkthrough prints only planned loop states while preserving dry-run/no-side-effect semantics | done | accepted/current `v0.1.92`; `promptbranch_loop.py`, `promptbranch_cli.py`, `tests/test_promptbranch_loop.py`, `tests/test_cli_loop.py`, `docs/release-v0.1.92.md` | v0.1.92 |

| DOD-124 | MVP-1 planned-action walkthrough prints one planned action and validation gate per state while preserving no-execution semantics | focused_candidate | `promptbranch_loop.py`, `promptbranch_cli.py`, `tests/test_promptbranch_loop.py`, `tests/test_cli_loop.py`, `docs/release-v0.1.93.md` | v0.1.93 |

| DOD-125 | Direct release-validation scheduler/source nodeids are isolated from ambient live browser/service/profile state while preserving the v0.1.93 planned-action feature | focused_candidate | `promptbranch_test_suite.py`, `tests/test_promptbranch_test_suite.py`, `docs/repair-v0.1.93.1.md` | v0.1.93.1 |

| DOD-127 | Project Source capacity-prune identity drift fails closed before looser retry | done | `v0.1.94.1` accepted/current evidence showed full release-control/adoption passed after the repair; focused tests cover exact-remove drift no-retry behavior | v0.1.94.1 |

| DOD-128 | Read-only loop execution produces an explicit evidence report with no-side-effect assertions | focused | `promptbranch_loop.py`, `promptbranch_cli.py`, `tests/test_promptbranch_loop.py`, `tests/test_cli_loop.py`, `docs/release-v0.1.95.md` | v0.1.95 |

| DOD-129 | Project Source capacity pruning keeps at most five generated release ZIP sources per repository family and never auto-selects documentation or other-repository sources | focused_candidate | `promptbranch_browser_auth/client.py`, `tests/test_project_source_capabilities.py`, `docs/release-v0.1.96.md` | v0.1.96 |

| DOD-130 | Read-only loop evidence gate converts the read-only evidence report into a deterministic pass/block decision before real command execution is introduced | focused_candidate | `promptbranch_loop.py`, `promptbranch_cli.py`, `tests/test_promptbranch_loop.py`, `tests/test_cli_loop.py`, `docs/release-v0.1.97.md` | v0.1.97 |


## DOD-131 — Text-source post-commit reconciliation requires exact text proof

Done when `project_source_add_text` can recover a committed-but-stale-inflight text-source add only after the Project Sources surface is re-read and the expected text-source identity or content anchor is visible. Recovery must reject nearby/different text sources and must not accept release ZIP source visibility as text-source proof. Ambiguous stale-inflight states remain release-blocking when exact text proof is missing.
| DOD-132 | Plan authority and anti-drift control-surface gate is machine-readable and validated | done | `docs/project/plan-state.json`, `pb project validate-control-surface --json`, `tests/test_project_control_surface.py` | v0.1.98 |
| DOD-133 | Rolling slice horizon and architecture-decision protocol are documented, machine-readable, and validated before first command execution | focused_candidate | `docs/project/architecture.md`, `docs/project/slice-horizon.md`, `docs/project/plan-state.json`, `pb project next-slice --json`, `tests/test_project_control_surface.py` | v0.1.99 |

| DOD-134 | Docker build-context freshness is repaired without advancing v0.1.99 scope | focused_candidate | `chatgpt_claudecode_workflow_release_control.sh`, `Dockerfile`, `docker-compose.chatgpt-service.yml`, `tests/test_promptbranch_shell_scripts.py`, `docs/repair-v0.1.99.1.md` | v0.1.99.1 |


| DOD-135 | First controlled read-only validation command execution runs exactly one allowlisted JSON syntax command after evidence gate approval and proves no file mutation | focused_candidate | `promptbranch_loop.py`, `promptbranch_cli.py`, `examples/loop-targets/read-only-validation-command-target.json`, `tests/test_promptbranch_loop.py`, `tests/test_cli_loop.py`, `docs/release-v0.1.100.md` | v0.1.100 |


## DOD-136 — v0.1.100.1 text-source stale-inflight recovery diagnostics repair

Status: focused candidate done; full release-control pending.

Criteria:
- `v0.1.100` read-only validation command execution behavior is preserved.
- Repair release does not advance scope or move `v0.1.101` forward.
- Text-source post-commit recovery explicitly re-opens/re-reads the Project Sources surface.
- Empty or unreadable source surfaces are recorded as diagnostics and remain release-blocking unless exact text proof appears.
- Exact text identity/content proof remains mandatory; ZIP/source-card visibility alone cannot satisfy text-source recovery.
- Focused regression tests cover recovery with re-opened source surface and not-recovered empty-surface diagnostics.


## DOD-137 — v0.1.100.2 browser scheduler source-lifecycle timeout repair

Status: focused candidate done; full release-control pending.

Criteria:
- `v0.1.100` read-only validation command execution behavior is preserved.
- `v0.1.100.1` text-source stale-inflight diagnostics are preserved.
- Repair release does not advance scope or move `v0.1.101` forward.
- `tests/test_promptbranch_automation_service.py::test_source_remove_waits_behind_source_list_with_same_profile` uses a bounded explicit start signal instead of an unbounded active-operation polling loop.
- The same-profile source-remove test still proves source remove waits until source list releases the shared profile lock.
- Focused validation includes the hanging nodeid and the release-validation group manifest.

## DOD-138 — v0.1.100.3 ZIP hygiene repair for packaged debug artifacts

Status: candidate

Evidence required: `chatgpt_claudecode_workflow-2_v0.1.100.3.zip` contains no `debug_artifacts/` entries; Artifact Guardian policy forbids `debug_artifacts/`; focused artifact guardian test proves packaged debug artifacts fail before handoff; release-control install verification accepts the cleaned ZIP.

Last release: v0.1.100.3



## DOD-139 — v0.1.101 read-only command result diagnosis

Status: focused_candidate.

Done when `pb loop run --read-only-execution --evidence-gate --execute-read-only-validation --diagnose-read-only-result --json` emits `promptbranch.loop.read_only_command_diagnosis`, classifies read-only command evidence as `passed`, `blocked`, or `failed`, preserves reason codes for blocked/failed outcomes, and proves no correction plan, file mutation, deployment, Project Source mutation, artifact adoption, or ChatGPT Project deletion occurred.

Evidence: `promptbranch_loop.py`, `promptbranch_cli.py`, `tests/test_promptbranch_loop.py`, `tests/test_cli_loop.py`, `docs/release-v0.1.101.md`.

Last release: v0.1.101

## DOD-140 — v0.1.102 correction-plan generation without file mutation

Status: done for focused v0.1.102 candidate validation; adoption remains pending full release-control.

Acceptance criteria:

- A machine-readable correction-plan schema is generated from read-only command diagnosis evidence.
- Blocked and failed diagnosis results produce bounded operator-review plan entries.
- Passed diagnosis results produce `no_correction_required` evidence.
- Generated plans include no file changes, no write actions, no immediate command retries, no Project Source mutation, no artifact adoption, no deployment, and no ChatGPT Project deletion.
- File mutation remains deferred to `v0.1.103.1` sandbox-only execution.

Evidence: `promptbranch_loop.py`, `promptbranch_cli.py`, `tests/test_promptbranch_loop.py`, `tests/test_cli_loop.py`, `docs/release-v0.1.102.md`.

Last release: v0.1.102

| DOD-141 | First controlled sandbox-only file mutation is gated and evidenced | done | `pb loop run --execute-sandbox-mutation` fixture and focused loop/CLI tests | v0.1.103.1 |

| DOD-136 | Docker browser parity diagnostic envelope is explicit and non-mutating | in_progress | `scripts/docker-browser-parity-auth-readiness.sh`; `/v1/docker/browser-runtime`; no Project Source mutation in script | v0.1.103.1 |

| DOD-142 | Docker browser parity auth readiness is passive and fail-fast | in_progress | `/v1/auth-readiness`; `scripts/docker-browser-parity-auth-readiness.sh`; `scripts/docker-browser-profile-bootstrap-host-chrome.sh` | v0.1.103.2 |

| DOD-143 | Docker passive auth-readiness is implemented on the runtime browser client | in_progress | `promptbranch_browser_auth/client.py`; `tests/test_promptbranch_container_api.py`; `/v1/auth-readiness` must not return AttributeError | v0.1.103.3 |

| DOD-144 | Docker parity Project Source mutation is guarded by passive auth readiness and explicit operator opt-in | in_progress | `promptbranch_container_api.py`; `scripts/docker-browser-parity-guarded-project-source-test.sh`; focused API tests | v0.1.103.5 |
| DOD-145 | Docker parity challenge artifacts are exported safely without recursive debug tree copies | in_progress | `scripts/docker-browser-parity-export-challenge-artifacts.sh`; focused shell-script test | v0.1.103.6 |
| DOD-146 | Docker parity Cloudflare challenge settling is isolated from downstream mutation | in_progress | `scripts/docker-browser-parity-cloudflare-check.sh`; same-session `/v1/auth-readiness/session/status` polling; bounded evidence export; no Project Source mutation | v0.1.103.8 |

| DOD-147 | Bonnetjes Cloudflare parity profile hygiene is documented and build-context safe | in_progress | `.dockerignore`; `scripts/docker-bonnetjes-clean-login-profile-bootstrap.sh`; `docs/bonnetjes-cloudflare-parity-test-procedure.md`; safe no-artifact export | v0.1.103.9 |
| DOD-148 | standard browser Cloudflare validation can be run as one operator workflow | in_progress | `scripts/docker-bonnetjes-cloudflare-validation.sh`; `docs/bonnetjes-cloudflare-one-shot-validation.md` | v0.1.103.10.4 |
| DOD-149 | standard browser profile bootstrap repairs empty Docker-created root-owned placeholders and fails fast on non-empty non-writable profiles | in_progress | `scripts/pb-browser-profile-bootstrap.sh`; `scripts/docker-browser-parity-cloudflare-check.sh`; focused shell-script tests | v0.1.103.10.6 |
| DOD-150 | source-add mutation gate failure preserves operator-safe auth-only validation guidance | in_progress | `promptbranch_cli.py`; `tests/test_standard_browser_source_add_gate.py` | v0.1.103.10.6 |

| DOD-151 | standard browser auth-only release candidate ZIP is clean of generated cache entries before import | in_progress | release import plan rejects `.pytest_cache/`; `v0.1.103.10.8` clean candidate packaging evidence | v0.1.103.10.8 |
| DOD-152 | successful auth-readiness evidence export does not require a challenge manifest | in_progress | Docker standard-browser validation may clear Cloudflare immediately; missing staged challenge manifest is normalized only when readiness status is already cloudflare_cleared_* | v0.1.103.10.8 |

| DOD-153 | pb ask reuses a held auth-ready browser session instead of launching a competing profile context | in_progress | `promptbranch_browser_auth/client.py`; `tests/test_held_auth_session_reuse.py`; ask preflight probes held auth-readiness and refuses Singleton* cleanup while held session is active | v0.1.103.10.9 |

| DOD-154 | pb ask sends through the held auth-ready current page without target conversation navigation | in_progress | `promptbranch_browser_auth/client.py`; `tests/test_held_auth_session_reuse.py`; held auth-ready ask sets `navigation_mode=held_auth_ready_current_page` and skips direct project conversation URL navigation | v0.1.103.10.10 |

| DOD-155 | standard profile can be bootstrapped by a visible Docker-launched Chrome fingerprint | in_progress | `scripts/pb-docker-browser-profile-bootstrap.sh`; `scripts/pb-browser-cloudflare-validation.sh`; validation defaults to Docker visual bootstrap and preserves host bootstrap as compatibility mode | v0.1.103.10.11 |

| DOD-156 | `pb ask` preserves current Promptbranch project/conversation scope while reusing held auth-ready browser sessions | in_progress | `promptbranch_browser_auth/client.py`, `scripts/pb-docker-browser-profile-bootstrap.sh`, `scripts/pb-browser-cloudflare-validation.sh`, `tests/test_held_auth_session_reuse.py`, `tests/test_promptbranch_shell_scripts.py`; live project-scoped `pb ask` validation pending | v0.1.103.10.12 |

| DOD-157 | `pbsa` / `promptbranch src add` can perform Project Source mutation through an explicit per-request operator intent after Docker browser auth/profile preflight passes, while direct API calls without intent remain gate-closed | in_progress | `promptbranch_container_api.py`, `promptbranch_service_client.py`, `tests/test_promptbranch_container_api.py`, `tests/test_promptbranch_service_client.py`; live project-source add validation pending | v0.1.103.10.13 |

| DOD-158 | `pbsa` reuses an active held auth-ready browser session for Project Source mutation preflight and source upload, avoiding a second persistent context and returning structured preflight errors instead of HTTP 500 | in_progress | `promptbranch_browser_auth/client.py`, `promptbranch_container_api.py`, `tests/test_held_auth_session_reuse.py`, `tests/test_promptbranch_container_api.py`; live `pbsa` validation pending | v0.1.103.10.15 |

| DOD-159 | `pbsa` preserves the Project Sources route before Add source lookup and does not wait on a generic conversation after Sources navigation escapes project scope | in_progress | `promptbranch_browser_auth/client.py`, `tests/test_project_source_capabilities.py`; live `pbsa` validation pending | v0.1.103.10.15 |

| DOD-160 | Docker visible browser bootstrap uses a stable bootstrap URL while auth-readiness keeps the project-scoped target URL, preventing bootstrap URL instability from blocking project validation | in_progress | `scripts/pb-browser-cloudflare-validation.sh`, `scripts/pb-docker-browser-profile-bootstrap.sh`, `tests/test_promptbranch_shell_scripts.py`; live auth-only validation pending | v0.1.103.10.17 |

| DOD-161 | pbsa remembered overwrite removal reuses the active held auth-readiness browser session, and Project Source add/remove reuse accepts authenticated Project Source pages without requiring a chat composer | in_progress | `promptbranch_browser_auth/client.py`, `promptbranch_container_api.py`, `tests/test_held_auth_session_reuse.py`, `tests/test_promptbranch_container_api.py`; live pbsa retry pending | v0.1.103.10.17 |


## DOD-162 — pb test api sequential API coverage runner

`pb test api` provides a rerunnable sequential API coverage test runner for the Promptbranch container API. It records a JSON report, exercises safe/status/browser/read endpoints, skips destructive endpoints by default, and only performs Project Source mutation when explicit source-add flags are supplied.

## DOD-163 — Install-safe API coverage command

`pb test api` must invoke the API coverage runner as an installed Promptbranch package module, not as a top-level source-tree script path, so the command works after pipx/wheel installation and remains rerunnable after every release.

| DOD-164 | `pb test api` avoids held-session self-conflicts | in_progress | Default serial-browser mode keeps auth-readiness from holding `/app/profile` before unrelated endpoint checks; `browser_context_unavailable_held_auth_session_active` is classified as `browser_profile_busy`. | v0.1.103.10.21 |
| DOD-165 | `pb test api` classification cleanup | in_progress | Successful clear API coverage steps do not receive misleading failure classifications; browser/profile busy, rate-limit, and auth challenge labels are emitted only when the endpoint response actually indicates those conditions. | v0.1.103.10.21 |

| DOD-166 | Docker Chrome shared-memory sizing is explicit for service and visual bootstrap paths | in_progress | `docker-compose.chatgpt-service.yml` sets `shm_size`; `scripts/pb-docker-browser-profile-bootstrap.sh` passes `--shm-size`; default can be overridden with `PROMPTBRANCH_DOCKER_SHM_SIZE`. | v0.1.103.10.22 |

| DOD-167 | full/browser validation skips generic-root login check | in_progress | HTTP 200 alone is not enough; ask requires token, source add requires persistence, auth readiness requires logged-in/no-challenge, debug rate-limit requires clear status, and project/chat/source read endpoints require ok=true. | v0.1.103.10.42 |

| DOD-168 | full/browser validation skips generic-root login check | in_progress | API coverage ask targets the current Promptbranch conversation from state.current.conversation_url before legacy top-level conversation_url, preserving query parameters while keeping strict API_ASK_OK semantic checks. | v0.1.103.10.42 |
| DOD-169 | full/browser validation skips generic-root login check | in_progress | API coverage preserves normal Promptbranch CLI service config for base URL/token defaults, keeps .env out of scope, and never prints the token in JSON reports, logs, or summaries. | v0.1.103.10.42 |
| DOD-170 | full/browser validation skips generic-root login check | in_progress | Browser/full validation no longer forces login_check by default; login_check remains available as an explicit diagnostic via --only login or PROMPTBRANCH_TEST_ENABLE_LOGIN_CHECK=1. | v0.1.103.10.42 |

| DOD-171 | release-control clears auth bootstrap held session explicitly | in_progress | Release-control runs the existing auth-only/browser validation method before Project Source add and before tests, using current conversation/project state first and preserving no browser/session architecture changes. | v0.1.103.10.42 |

| DOD-172 | missing `.pb_profile_local_debug` live seed profile is non-blocking for live-only run-all steps | superseded_by_DOD-176 | preserved as v0.1.103.10.38 behavior; v0.1.103.10.42 makes live profiles release-blocking for --run-all-tests | v0.1.103.10.38 |

| DOD-173 | release-control pre_source_add auth bootstrap accepts logged-in `/project` page readiness without requiring a composer, while composer remains required outside that phase | in_progress | `chatgpt_claudecode_workflow_release_control.sh`; `scripts/pb-browser-cloudflare-validation.sh`; focused shell-script tests | v0.1.103.10.42 |
| DOD-174 | release-control pre_tests auth bootstrap targets current conversation URL before requiring composer | in_progress | `chatgpt_claudecode_workflow_release_control.sh`; `tests/test_promptbranch_shell_scripts.py` | v0.1.103.10.42 |

| DOD-176 | run-all live tests use explicitly bootstrapped Docker live profiles and do not trust copied live pool slots | in_progress | `scripts/pb-docker-live-profile-bootstrap.sh`; `chatgpt_claudecode_workflow_release_control.sh`; focused shell-script tests | v0.1.103.10.42 |
| DOD-177 | release ZIP import preserves explicitly bootstrapped Docker live profile pool state | in_progress | `chatgpt_claudecode_workflow_release_control.sh`; `tests/test_promptbranch_shell_scripts.py` | v0.1.103.10.42 |
| DOD-178 | run-all live ask uses a conversation URL and refuses `/project` ask/live execution | in_progress | `chatgpt_claudecode_workflow_release_control.sh`; focused shell-script tests | v0.1.103.10.42 |
| DOD-179 | release-live Cloudflare challenge fails fast without manual-login wait | in_progress | `promptbranch_browser_auth/client.py`; `chatgpt_claudecode_workflow_release_control.sh`; focused shell-script tests | v0.1.103.10.43 |

| DOD-180 | release-live challenge fail-fast logging is structured and does not cascade live steps | in_progress | `promptbranch_browser_auth/client.py`; `chatgpt_browser_auth/client.py`; `chatgpt_claudecode_workflow_release_control.sh`; focused shell-script tests | v0.1.103.10.45 |

| DOD-181 | Package version surface is coherent across VERSION, promptbranch_version.py, and pyproject.toml | in_progress | `tests/test_promptbranch_version.py`; Docker build-context version guard | v0.1.103.10.45 |
| DOD-182 | `docker_live_profile_challenged` is terminal for the ask-live matrix and release-control live cascade | in_progress | `promptbranch_cli.py`; `chatgpt_claudecode_workflow_release_control.sh`; focused CLI/shell tests | v0.1.103.10.48 |
| DOD-183 | Mid-run Cloudflare/backend-403 challenge during response wait is terminal `docker_live_profile_challenged` and does not persist cooldown | in_progress | `promptbranch_browser_auth/client.py`; `chatgpt_browser_auth/client.py`; `tests/test_project_resolve.py` | v0.1.103.10.48 |

| DOD-184 | Backend-api 403 guardrail is terminal browser challenge across full/direct, localhost, and live validation paths | in_progress | `promptbranch_browser_auth/client.py`; `chatgpt_browser_auth/client.py`; `chatgpt_claudecode_workflow_release_control.sh`; focused client/shell tests | v0.1.103.10.48 |

| DOD-185 | Release-live project setup, conversation bootstrap, ask-live, visual artifact, and release-live use the same explicit live slot profile; Docker bootstrap image defaults no longer depend on unset service image tag | in_progress | `chatgpt_claudecode_workflow_release_control.sh`; `docker-compose.chatgpt-service.yml`; `scripts/pb-docker-browser-profile-bootstrap.sh`; focused shell tests | v0.1.103.10.49 |

| DOD-186 | Backend-api 403 guardrail during auth bootstrap is release-blocking and clears held browser owner before stopping | in_progress | `scripts/pb-browser-cloudflare-validation.sh`; `chatgpt_claudecode_workflow_release_control.sh`; focused shell tests | v0.1.103.10.53 |

| DOD-187 | Docker parity/check compose paths propagate versioned service image tags and refuse silent local/unknown candidate validation fallbacks | in_progress | docker-compose.chatgpt-service.yml; scripts/docker-browser-parity-cloudflare-check.sh; focused shell tests | v0.1.103.10.53 |

| DOD-188 | Release-live bootstrap 429/rate-limit/backend-api guardrail telemetry is terminal before ask_live | in_progress | `chatgpt_claudecode_workflow_release_control.sh`; focused shell tests | v0.1.103.10.53 |

| DOD-189 | Fast release-control replay harness covers run-all success and terminal live bootstrap guardrail before ask_live | in_progress | tests/test_release_control_replay_harness.py; tests/fixtures/release_control_replay/bin/pb | v0.1.103.10.55 |

## v0.1.103.10.59

- Added trusted conversation warmup for `release-live-continuous`: the continuous live session starts from the conversation URL proven by `live_profile_preflight` instead of bare `https://chatgpt.com/`.
- Preserves all-in-Docker, explicit slot profile, no host-CDP/session-manager, and no copied-profile trust.


## v0.1.103.10.59

DOD-192: release-live-continuous extracts the trusted warmup conversation URL from `pb login-check` top-level `url` and refuses to fall back to ChatGPT root when it is missing.


## v0.1.103.10.61

Active candidate: `v0.1.128.2.7` (`chatgpt_claudecode_workflow-2_v0.1.128.2.7.zip`).

Artifact: chatgpt_claudecode_workflow-2_v0.1.103.10.61.zip

Slice: v0.1.103.10.61 — classify Docker live preflight challenge as external live challenge and stop browser-repair loop

## v0.1.103.10.65

DOD-193: default `--run-all-tests` performs deterministic product release validation without invoking Cloudflare-gated external ChatGPT live probes. `live_profile_preflight`, `live_project_ensure`, `ask_live`, `visual_artifact_roundtrip`, and `release_live` are reported as `external_live_not_requested` unless explicitly enabled with `--run-external-live-tests` or `--require-chatgpt-live-validation`.

| DOD-236 | `release-live-continuous` with a trusted project conversation warmup URL skips root project discovery and keeps bootstrap/ask in that conversation/session | in_progress | `promptbranch_browser_auth/client.py`; `tests/test_release_live_continuous_direct_conversation.py` | v0.1.103.10.65 |


## v0.1.103.10.65

| ID | DoD item | Status | Evidence | Last release |
| --- | --- | --- | --- | --- |
| DOD-237 | `release-live-continuous` trusted conversation direct mode explicitly navigates to the trusted `/g/.../c/...` URL and verifies current URL scope, composer visibility, logged-in state, and no challenge before the held-page send guard | in_progress | `promptbranch_browser_auth/client.py`; `tests/test_release_live_continuous_direct_conversation.py` | v0.1.103.10.65 |


## v0.1.103.10.66

| ID | DoD item | Status | Evidence | Last release |
| --- | --- | --- | --- | --- |
| DOD-238 | `release-live-continuous` trusted conversation direct mode returns structured `browser_context_closed_during_submit` when the page/context closes after readiness but before/during composer submit, and click fallbacks stop immediately on target-close evidence | in_progress | `promptbranch_browser_auth/client.py`; `tests/test_release_live_continuous_direct_conversation.py` | v0.1.103.10.66 |

## v0.1.103.10.67

| ID | DoD item | Status | Evidence | Last release |
| --- | --- | --- | --- | --- |
| DOD-239 | `release-live-continuous` returns structured `browser_context_closed_during_submit` with `submit_subphase=composer_wait` when the browser target closes during chat input selector wait, and does not downgrade that evidence to `ResponseTimeoutError` | in_progress | `promptbranch_browser_auth/client.py`; `tests/test_release_live_continuous_direct_conversation.py` | v0.1.103.10.67 |

| DOD-240 | release-live-continuous completed sentinel aggregation | in_progress | A trusted direct-conversation release-live-continuous run with successful project evidence, completed bootstrap result matching the bootstrap sentinel, and completed ask result matching the ask sentinel must emit top-level `ok=true`, `contains_expected_sentinel=true`, and no `failed_phase`, even when sub-results do not include `ok=true`. | v0.1.103.10.68 |

## v0.1.103.10.69

| ID | DoD item | Status | Evidence | Last release |
| --- | --- | --- | --- | --- |
| DOD-241 | strict all-all release gate script | in_progress | Repo-root `install.sh` must install an exact candidate ZIP, run `--run-all-tests`, `--run-external-live-tests`, `--require-chatgpt-live-validation`, and `--adopt-after-validation`, then emit `pb artifact current --all --json` evidence. | v0.1.103.10.69 |


## v0.1.103.10.70

| ID | Requirement | Status | Evidence | Slice |
| --- | --- | --- | --- | --- |
| DOD-242 | live bootstrap guardrail classification | in_progress | Release-control must classify `live_bootstrap_guardrail` and `skipped_blocked_by_live_bootstrap_guardrail` as external-live blockage evidence, preserving failed live steps and adoption refusal while avoiding product `FIX` when artifact/product validation passed. | v0.1.103.10.70 |


## v0.1.103.10.71

| ID | Requirement | Status | Evidence | Slice |
| --- | --- | --- | --- | --- |
| DOD-243 | final all-tests aggregation maps live bootstrap guardrail cascades to LIVE_BLOCKED | in_progress | Release-control must normalize mixed `live_project_ensure` logs containing terminal `live_bootstrap_guardrail` evidence before product failure counting, preserving failed downstream live steps and passed artifact guard evidence. | v0.1.103.10.71 |


## v0.1.103.10.72

| ID | Requirement | Status | Evidence | Slice |
| --- | --- | --- | --- | --- |
| DOD-244 | project control-surface candidate metadata and final verdict precedence | in_progress | `docs/project/plan-state.json`, `docs/project/status.md`, `docs/project/plan.md`, `docs/project/slice-horizon.md`, `tests/test_project_control_surface.py`, and `tests/test_release_control_replay_harness.py` must keep active candidate metadata aligned and prove that product failures produce `FIX` even when external-live is also blocked. | v0.1.103.10.72 |


## v0.1.103.10.73

| ID | DoD item | Status | Evidence | Last release |
|---|---|---|---|---|
| DOD-245 | version_surface tests derive expected version from release metadata | in_progress | `tests/test_promptbranch_version.py` must derive expected package/version-tag values from `VERSION`, `pyproject.toml`, and `promptbranch_version.py`, and must reject stale hardcoded repair-version literals. | v0.1.103.10.73 |

## v0.1.103.10.76

| ID | DoD item | Status | Evidence | Last release |
|---|---|---|---|---|
| DOD-246 | release-live bootstrap guardrail bounded retry | in_progress | `release-live-continuous` must perform at most one safe cooldown/re-readiness retry after bootstrap guardrail telemetry, without bypassing Cloudflare/rate limits or trusting copied profiles. | v0.1.103.10.76 |

## v0.1.103.10.76

| ID | Capability | Status | Evidence | Version |
|---|---|---|---|---|
| DOD-247 | precise release-live bootstrap sentinel status | in_progress | `release-live-continuous` must distinguish `bootstrap_sentinel_missing_after_ask_success` from explicit backend/rate-limit bootstrap guardrail, retry only the missing bootstrap phase once when readiness is clean, and preserve product-clean `LIVE_BLOCKED` classification. | v0.1.103.10.76 |

## v0.1.103.10.76

| ID | Item | Status | Evidence | Version |
| --- | --- | --- | --- | --- |
| DOD-248 | release-live visible thinking preamble normalization | in_progress | `release-live-continuous` must accept only known visible thinking preambles before an exact expected sentinel line and reject arbitrary extra text. | v0.1.103.10.76 |

## v0.1.103.10.78

| ID | Capability | Status | Done means | Version |
| --- | --- | --- | --- | --- |
| DOD-249 | exact-name Project Source upsert guard | in_progress | `pb src add` / `pbsa` require exact canonical file names; visible suffix-renamed sources block before upload, and backend-created suffixes after upload fail as `backend_renamed_source`. | v0.1.103.10.78 |


## v0.1.103.10.79

| ID | DoD item | Status | Evidence | Last release |
|---|---|---|---|---|
| DOD-250 | authoritative Project Sources preflight and early suffix rollback | in_progress | File uploads require explicit empty state or stable non-empty snapshots; non-authoritative surfaces block before upload, and backend-assigned suffix names are rolled back before exact-name persistence retries. | v0.1.103.10.79 |

## v0.1.103.10.80

| ID | DoD item | Status | Evidence | Last release |
|---|---|---|---|---|
| DOD-251 | verified candidate image reuse and stable Docker dependency cache | in_progress | Pre-source auth bootstrap uses `--no-recreate`; Docker metadata is consumed after pinned stable dependencies; transport retry exhaustion maps to `docker_browser_dependency_download_failed`. | v0.1.103.10.80 |

## v0.1.103.10.81

| ID | DoD item | Status | Evidence | Last release |
|---|---|---|---|---|
| DOD-252 | Candidate transport identity is separate from canonical Project Source identity | in_progress | Unique transport basename `chatgpt_claudecode_workflow-2_transport_v0.1.103.10.81_b7c1de9f28.zip` is accepted only after internal VERSION/CRC validation; canonical `chatgpt_claudecode_workflow-2_v0.1.103.10.81.zip` is derived from version and is the only source/adoption identity. | v0.1.103.10.81 |


## v0.1.103.10.82

| ID | DoD item | Status | Evidence | Last release |
|---|---|---|---|---|
| DOD-253 | Library-backed exact-name Project Source overwrite | in_progress | `pbsa <file>` remains an alias for `promptbranch src add <file>`; same-name overwrite removes the exact Project Source association, reconciles exact attributable Library file IDs and Recently deleted entries, uploads the canonical basename, and succeeds only with one exact canonical source and zero numeric suffix variants. Ambiguous cross-project ownership fails closed. | v0.1.103.10.82 |

## v0.1.103.10.83

| ID | Requirement | Status | Evidence | Version |
|---|---|---|---|---|
| DOD-254 | Authoritative Library reconciliation and exact live upload identity capture | in_progress | Stable Library/Recently deleted authority, JSON/NDJSON/SSE/header file-ID capture, exact-ID suffix cleanup, missing-ID fail-closed status, direct/localhost release validation, and unchanged `pbsa` command surface. | v0.1.103.10.83 |

## v0.1.103.10.84

| ID | Requirement | Status | Evidence | Release |
|---|---|---|---|---|
| DOD-255 | Fresh Project Source file add bypasses Library and Recently deleted | in_progress | Project Source regression tests and live release-control validation | v0.1.103.10.84 |
| DOD-256 | Same-name overwrite uses exact-source replace/update when exposed and never falls back to live remove-and-reupload | in_progress | Replace capability diagnostics and live integration overwrite test | v0.1.103.10.84 |
| DOD-257 | Library cleanup is invoked only after concrete suffix collision evidence | in_progress | Visible/backend suffix regression tests | v0.1.103.10.84 |


## v0.1.103.10.86

| ID | DoD item | Status | Evidence | Last release |
|---|---|---|---|---|
| DOD-258 | Deterministic legacy-vs-current Project Source A/B diagnostic | in_progress | Two disposable projects, unique filenames, exact upload/remove/source/Library identities, and explicit conclusion without release upload or adoption. | v0.1.103.10.86 |

## v0.1.103.10.87

| ID | Requirement | Status | Evidence | Release |
|---|---|---|---|---|
| DOD-259 | Diagnostic runner uses standard service bearer-token configuration | in_progress | External-CWD subprocess test with standard Promptbranch config and protected diagnostic endpoint | v0.1.103.10.87 |

## v0.1.103.10.89

| ID | Requirement | Status | Evidence | Release |
|---|---|---|---|---|
| DOD-260 | Exact backing Library object is deleted and proven absent before canonical reupload | in_progress | Captured `file_...` and `libfile_...` identities, exact-ID-only active/Recently deleted removal, two stable authoritative absence observations, distinct replacement identities, canonical backend filename classification, and live diagnostic JSON | v0.1.103.10.89 |


## v0.1.103.10.90

| ID | Requirement | Status | Evidence | Release |
|---|---|---|---|---|
| DOD-261 | Exact backing-file backend inventory and deletion protocol discovery | in_progress | Full redacted fetch/XHR phase trace, disposable visible Library-file inventory and soft/hard-delete capture, exact-ID protocol replay, backend inventory presence/absence verification, canonical reupload classification, history-request shielding, and live diagnostic JSON | v0.1.103.10.90 |


## v0.1.103.10.91

| ID | Requirement | Status | Evidence | Release |
|---|---|---|---|---|
| DOD-262 | ID-driven active Library inventory discovery and safely auditable complete protocol trace | in_progress | Dual `file_...`/`libfile_...` node extraction, empty-search `/backend-api/files/library/nodes` discovery, stable exact-`libfile_...` polling, corrected inconclusive classifications, protocol-only sanitized body export, all fetch/XHR events retained, and fail-closed deletion/reupload gates | v0.1.103.10.91 |


## v0.1.103.10.92

| ID | DoD item | Status | Evidence | Last release |
|---|---|---|---|---|
| DOD-263 | Private authenticated Library inventory replay with fail-fast authorization classification | in_progress | Private in-memory raw headers, sanitized public protocol, captured exact-ID `200` counted as observation one, one additional authenticated observation required, immediate `401`/`403` stop, and deletion/reupload gates remain closed | v0.1.103.10.92 |


## v0.1.103.10.93

| ID | DoD item | Status | Evidence | Last release |
|---|---|---|---|---|
| DOD-264 | Exact Library filename reconstruction and safe backend-to-UI card binding | in_progress | Wrapped filename regression, exact contiguous-token reconstruction, suffix/partial rejection, one exact UI record, zero suffix siblings, unique backend `libfile_...` proof, unique marked card locator, and fail-closed mutation gate | v0.1.103.10.93 |

| DOD-263 | Exact Library UI binding rejects ancestor/header containers and requires one row-scoped action menu | in_progress | `v0.1.103.10.94` focused tests; live diagnostic pending | v0.1.103.10.94 |

| DOD-264 | Exact Library filename leaf binds to one local file row before a hover-revealed row-owned menu; repeated backend observations deduplicate by `libfile_...`; non-authoritative surfaces fail before row absence | in_progress | `v0.1.103.10.95` focused deterministic tests; live diagnostic pending | v0.1.103.10.95 |
| DOD-265 | Disposable Library soft deletion is proven by a successful exact-ID mutation plus stable active absence/trashed state; Recently deleted navigation and exact deleted-inventory presence are independently proven before permanent deletion | in_progress | `v0.1.103.10.96` focused deterministic tests; live diagnostic pending | v0.1.103.10.96 |


| DOD-266 | Long-lived Project Source processing streams do not block ordinary save quietness; terminal completion requires exact file/libfile/filename identity and all diagnostic exceptions expose a top-level reason | in_progress | `v0.1.103.10.97` focused deterministic tests; live diagnostic pending | v0.1.103.10.97 |

| DOD-267 | Project Source processing reaches exact terminal identity before rendered persistence verification; SSE body capture occurs after request completion and watcher disposal follows persistence verification | in_progress | `v0.1.103.10.98` focused deterministic tests; live diagnostic pending | v0.1.103.10.98 |

| DOD-268 | The real backend-protocol diagnostic upload path cannot verify Project Source persistence while its processing stream is pending; pending stream state requires a non-null terminal stream result and watcher disposal follows persistence verification | in_progress | `v0.1.103.10.99` legacy-path order test, diagnostic caller invariant test, focused deterministic suites; live diagnostic pending | v0.1.103.10.99 |
| DOD-269 | Generic Fetch/XHR diagnostic response capture is bounded, stream-safe, reports unresolved task classifications/counts, and cannot suppress structured diagnostic JSON | in_progress | `v0.1.103.10.100` focused watcher/diagnostic tests and packaged validation; live diagnostic pending | v0.1.103.10.100 |
| DOD-270 | Disposable visible-Library upload has dedicated bounded terminal stream identity capture and never derives deletion identity from generic trace body samples | done | `v0.1.103.10.101` live diagnostic proved exact terminal file/libfile/filename identity, stable backend presence, and exact UI row binding | v0.1.103.10.101 |


| DOD-271 | Soft-delete protocol discovery uses immutable request phases and a pre-click request-sequence boundary, requires paired 2xx exact-ID mutation evidence, and reports sanitized post-boundary candidates on failure | in_progress | `v0.1.103.10.102` focused phase/boundary/discovery tests and packaged validation; live diagnostic pending | v0.1.103.10.102 |

| DOD-272 | Library soft-delete reports `delete_triggered` only after unique confirmation plus exact mutation proof, or exact direct mutation proof for a no-confirmation flow | in_progress | `v0.1.103.10.103` focused confirmation/direct-mutation tests and packaged validation; live diagnostic pending | v0.1.103.10.103 |
| DOD-273 | After authoritative backend presence, one bounded Library UI recovery cycle may restore exact row binding without weakening deletion safety | done | `v0.1.103.10.104` focused tests plus live run proving exact row binding, confirmation, exact soft-delete mutation, and stable active absence | v0.1.103.10.104 |
| DOD-274 | Artifact state uses one authoritative project registry; explicit repository identity and configured membership are mandatory; missing, invalid, unreadable, stale repo-local, or noncanonical registry state fails closed without migration | done | `v0.1.103.10.105` clean-break validation plus fresh project datasets verified from active repositories | v0.1.103.10.105 |
| DOD-275 | Backend-assigned indexed Project Source names are accepted only with unique upload correlation, stable identity read-back, idempotent retry reuse, and ambiguity-safe adoption metadata | in_progress | `v0.1.103.10.106` focused correlation, retry, adoption, control-surface, and packaged validation | v0.1.103.10.106 |

| DOD-276 | A normal file-source add uses one canonical/indexed-family matcher, records the previous maximum suffix, uploads once, immediately verifies the exact processing-stream assigned filename, and never performs canonical-name persistence retries after assigned identity is known | in_progress | `v0.1.103.10.107` focused assigned-name fast-path, malformed-name, duplicate-card, control-surface, and packaged validation | v0.1.103.10.107 |

| DOD-277 | A default file-source add leaves exactly one canonical/indexed family member: the stream-assigned source from the current upload; older siblings are removed only after new-source verification, and cleanup failure blocks success | focused_candidate | `v0.1.103.10.108` singleton-family replacement, exact-removal, cleanup-failure, control-surface, and packaged validation | v0.1.103.10.108 |
| DOD-278 | At the 25-file boundary, release source add prunes exactly one safe obsolete same-repository release, protects candidate/current identities, proves 25→24, uploads once, and proves the final count is 25 | in_progress | `promptbranch_browser_auth/client.py`, `promptbranch_cli.py`, `tests/test_project_source_capabilities.py`, `docs/repair-v0.1.103.10.109.md` | v0.1.103.10.109 |

| DOD-279 | Read-only source-sync planning reports a missing registry without mutation; invalid registries and artifact mutations remain blocked; agent/full tests always emit terminal JSON | in_progress | `promptbranch_artifacts.py`, `promptbranch_test_suite.py`, `promptbranch_test_report.py`, `promptbranch_cli.py`, `tests/` | v0.1.103.10.110 |
| DOD-280 | Any file-source overwrite without an in-place Replace action uses upload-new/verify/delete-old and ends with one family member; structured read-only uninitialized smoke states are accepted without mutation; lifecycle plans expose execution blockers; both full transports are release acceptance gates | in_progress | `promptbranch_browser_auth/client.py`, `promptbranch_cli.py`, `tests/test_project_source_capabilities.py`, `tests/test_promptbranch_cli.py`, `docs/repair-v0.1.103.10.111.md` | v0.1.103.10.111 |

| DOD-281 | Changed-content file overwrite proves distinct initial/replacement SHA-256 values; accepts the exact backend-assigned canonical or indexed filename without index prediction; requires completed processing plus new processed-file and Library object identities before deleting only pre-upload family members; and ends with the assigned source as the sole family member in both full transports | focused_candidate | `promptbranch_full_integration_test.py`, `promptbranch_browser_auth/client.py`, `tests/test_project_source_capabilities.py`, `tests/test_full_integration_harness.py`, `docs/repair-v0.1.103.10.112.md` | v0.1.103.10.112 |

| DOD-282 | When same-basename replacement would be suppressed, Promptbranch stages changed bytes under a collision-free numeric canonical-family member, proves byte identity and family membership, treats the token as non-authoritative, cleans the staging file, captures exact processing-stream assignment/backing IDs, deletes only pre-upload members, and passes both full transports | focused_candidate | `promptbranch_browser_auth/client.py`, `promptbranch_full_integration_test.py`, `tests/test_project_source_capabilities.py`, `tests/test_full_integration_harness.py`, `docs/repair-v0.1.103.10.113.md` | v0.1.103.10.113 |
| DOD-283 | Continuous external-live validation uses one exact physical profile slot without nested pooling; current ChatGPT submit flow or a valid new post-submit reply envelope proves causality; Cloudflare requires actual challenge evidence; full_localhost executes independently | focused_candidate | `promptbranch_cli.py`, `promptbranch_browser_auth/client.py`, `chatgpt_claudecode_workflow_release_control.sh`, `tests/test_promptbranch_cli.py`, `tests/test_response_completion.py`, `tests/test_promptbranch_shell_scripts.py`, `docs/repair-v0.1.103.10.114.md` | v0.1.103.10.114 |

| DOD-284 | Adoption preflight joins authoritative project/repo identity before expensive validation; exact assigned-source and backing IDs are carried into fail-closed adoption; response completion is parse-independent; rate-limit retries require structured true telemetry | focused_candidate | `chatgpt_claudecode_workflow_release_control.sh`, `promptbranch_cli.py`, `promptbranch_artifacts.py`, `promptbranch_browser_auth/client.py`, `chatgpt_browser_auth/client.py`, `tests/test_promptbranch_cli.py`, `tests/test_response_completion.py`, `tests/test_promptbranch_shell_scripts.py`, `docs/repair-v0.1.103.10.115.md` | v0.1.103.10.115 |
| DOD-285 | Final post-adoption verification distinguishes canonical artifact identity from exact assigned Project Source identity, verifies both backing IDs, retains all four version checks and three consistency booleans, and emits release_adopted_and_verified only after success | focused_candidate | `scripts/verify-release-adoption-current.py`, `chatgpt_claudecode_workflow_release_control.sh`, `tests/test_release_adoption_verification.py`, `docs/repair-v0.1.103.10.116.md` | v0.1.103.10.116 |
| DOD-286 | A copied sandbox fixture is mutated only after correction-plan evidence; exact before/after hashes and contents are proven; one exact allowlisted sandbox validation passes without mutation; rollback restores the before snapshot; the repository fixture remains unchanged; the workspace is deleted; and the loop stops without deployment, Project Source mutation, artifact adoption, or Project deletion | focused_candidate | `promptbranch_loop.py`, `promptbranch_cli.py`, `examples/loop-targets/sandboxed-file-mutation-target.json`, `tests/test_promptbranch_loop.py`, `tests/test_cli_loop.py`, `docs/project/promptbranch-plan-v0.1.104.md`, `docs/release-v0.1.104.md` | v0.1.104 |
| DOD-287 | The sandbox mutation/rollback proof is a required release-validation manifest group and explicit all-tests step; exact terminal status and all 13 gates are mandatory; manifest identity is signed into reusable evidence; v0.1.104.1 forbids direct reuse and retains independent localhost execution | focused_candidate | `promptbranch_test_suite.py`, `scripts/verify-sandbox-mutation-rollback-release-gate.py`, `chatgpt_claudecode_workflow_release_control.sh`, `tests/test_sandbox_mutation_rollback_release_gate.py`, `tests/test_release_control_sandbox_gate_contract.py`, `docs/repair-v0.1.104.1.md` | v0.1.104.1 |

| DOD-288 | Post-bootstrap continuous-live asks probe readiness before fill; only interrupted_answer_state permits one same-conversation reload; bootstrap sentinel and no stop/thinking/running state are reverified; persistent busy state fails before ask submission; sandbox and transport gates remain unchanged | focused_candidate | `promptbranch_browser_auth/client.py`, `tests/test_release_live_continuous_direct_conversation.py`, `docs/repair-v0.1.104.2.md` | v0.1.104.2 |

| DOD-289 | Historical Retry controls do not block an idle composer; pre-bootstrap readiness is separate; post-bootstrap recovery requires completed exact sentinel; reload waits for hydration; latest-turn interruption fails closed; sandbox gate remains unchanged and standalone-runnable | focused_candidate | `promptbranch_browser_auth/client.py`, `tests/test_release_live_continuous_direct_conversation.py`, `tests/test_project_list_browser_client.py`, `docs/repair-v0.1.104.3.md` | v0.1.104.3 |

| DOD-290 | Visual artifact response completion is independent of envelope parsing; causally confirmed virtualized turn-count reduction is accepted only after generation; stable idle UI terminates the wait; one exact literal-whitespace normalization and one 90-second same-conversation correction retry are allowed; download requires exactly one valid ZIP candidate with matching active IDs | focused_candidate | `promptbranch_browser_auth/client.py`, `promptbranch_cli.py`, `tests/test_response_completion.py`, `tests/test_promptbranch_cli.py`, `docs/repair-v0.1.104.4.md` | v0.1.104.4 |

| DOD-291 | Every release-validation pytest subprocess owns explicit temporary HOME, XDG, Promptbranch profile, project state/config/cache paths; child-process preflight proves all resolved paths are inside the isolation root; ambient repository browser-lock contents are never read or waited upon; the previously timed-out scheduler node finishes promptly; timeout remains 300 seconds and no timed-out node is retried | focused_candidate | `promptbranch_test_suite.py`, `tests/test_promptbranch_test_suite.py`, `docs/repair-v0.1.104.5.md` | v0.1.104.5 |

| DOD-292 | Sandbox correction promotion readiness runs the unchanged sandbox-only proof three independent times, requires complete exact 13-gate evidence, compares one canonical SHA-256 fingerprint, emits ready/not_ready/blocked, and grants no broader mutation or promotion authority | focused_candidate | `promptbranch_loop.py`, `promptbranch_cli.py`, `tests/test_promptbranch_loop.py`, `tests/test_cli_loop.py`, `docs/project/promptbranch-plan-v0.1.105.md`, `docs/release-v0.1.105.md` | v0.1.105 |

| DOD-293 | Promotion-readiness derives repository authority from the resolved target or validated explicit root, requires target containment, and blocks before evidence on invalid resolution while preserving the v0.1.105 evidence and authority model | focused_candidate | `promptbranch_loop.py`, `promptbranch_cli.py`, `tests/test_promptbranch_loop.py`, `tests/test_cli_loop.py`, `docs/repair-v0.1.105.1.md`, `docs/release-v0.1.105.1.md` | v0.1.105.1 |


| DOD-294 | Controlled correction promotion records exactly GO or NO-GO from 32 mandatory readiness and safety checks; GO requires exactly three complete independent runs and one fingerprint, authorizes only v0.1.107 design, and grants no correction execution or broader mutation authority | focused_candidate | `promptbranch_loop.py`, `promptbranch_cli.py`, `tests/test_promptbranch_loop.py`, `tests/test_cli_loop.py`, `docs/project/correction-promotion-decision-v0.1.106.json`, `docs/project/promptbranch-plan-v0.1.106.md`, `docs/release-v0.1.106.md` | v0.1.106 |
| DOD-295 | Controlled correction execution envelope design emits one canonical deterministic envelope containing exact target, file, operation, pre/post state, validation, rollback, limits, timeouts, evidence requirements, and zero correction-execution authority while creating no workspace and executing no command | focused_candidate | `promptbranch_loop.py`, `promptbranch_cli.py`, `tests/test_promptbranch_loop.py`, `tests/test_cli_loop.py`, `docs/project/controlled-correction-execution-envelope-v0.1.107.json`, `docs/project/promptbranch-plan-v0.1.107.md`, `docs/release-v0.1.107.md` | v0.1.107 |

| DOD-296 | Controlled correction execution-envelope validation reloads and recomputes the canonical v0.1.107 envelope, requires exact object and fingerprint equality, validates all target/operation/validation/rollback/evidence/authority constraints, executes zero commands, creates zero workspaces, mutates zero files, and formally defines v0.1.109 as the PROJECT_SETTINGS.md/AGENTS.md authority-graph definition slice | focused_candidate | `promptbranch_loop.py`, `promptbranch_cli.py`, `tests/test_promptbranch_loop.py`, `tests/test_cli_loop.py`, `docs/project/controlled-correction-execution-envelope-validation-v0.1.108.json`, `docs/project/promptbranch-plan-v0.1.108.md`, `docs/release-v0.1.108.md` | v0.1.108 |

## DOD-297 — v0.1.108.1 Project Source staged-overwrite and removal-proof reliability

- [x] Failed staged-upload requests retain redacted URL, method, and error diagnostics.
- [x] Upload initiation, commit, processing-stream, assigned filename, and backing identities are evaluated separately.
- [x] Exactly one retry is allowed only before any commit, processing stream, or backing identity and only while the original source remains verified.
- [x] The original source is never deleted before the replacement assigned filename and backing identities are verified.
- [x] Removal proof refreshes the authoritative Project Sources surface and returns exactly `verified_absent`, `still_present`, or `surface_unresolved`.
- [x] `verified_absent` requires two stable authoritative observations.
- [x] Deterministic regressions cover retry eligibility, failed-request diagnostics, original-source preservation, and all three removal states.
- [x] `pb test project-source-file-reliability` runs overwrite and removal as independent scenarios.
- [ ] Focused direct live profile passes.
- [ ] Focused localhost live profile passes.
- [ ] Full `full_direct` and `full_localhost` release gates pass.
- [ ] Artifact Guardian, evidence-bound adoption, and final current-state verification pass.
- [x] `v0.1.109` remains planned_after_acceptance and no authority-graph implementation is included.

## v0.1.109 project authority graph

| ID | DoD item | Status | Evidence | Last release |
|---|---|---|---|---|
| DOD-298 | Stable project policy and agent instructions exist without duplicating mutable release state | done | `PROJECT_SETTINGS.md`, `AGENTS.md`, authority policy tests | v0.1.109 |
| DOD-299 | Every declared project fact domain has exactly one machine-readable authority and fail-closed conflict policy | done | `docs/project/project-authority-graph-v0.1.109.json`, authority graph tests | v0.1.109 |
| DOD-300 | Read-only authority show/validate commands classify missing authority, ambiguity, and projection drift while performing zero writes | done | `promptbranch_project_authority.py`, `pb project authority show/validate`, deterministic tests | v0.1.109 |
| DOD-301 | Runtime identity, adopted registry, and external Project Settings are explicit deferred/read-only domains rather than inferred fallbacks | done | authority graph and validation payloads | v0.1.109 |

## v0.1.109.1 behavioral surface inventory

| ID | DoD item | Status | Evidence | Last release |
|---|---|---|---|---|
| DOD-302 | Runtime authority validation resolves the joined repository identity to the authoritative project-scoped artifact registry and verifies a current adopted release without fallback state | focused_candidate | `promptbranch_project_authority.py`, `tests/test_behavioral_surface.py` | v0.1.109.1 |
| DOD-303 | Executable instructions, skills, agents, tools, and prompts have stable IDs, one owner, declared consumers, execution boundaries, mutation authority, and tests | focused_candidate | `docs/project/promptbranch-behavioral-surface-v0.1.109.1.json`, `promptbranch_behavioral_surface.py` | v0.1.109.1 |
| DOD-304 | Behavioral-surface validation fails closed on duplicate IDs, missing owners, unknown skill tools, blocked-tool exposure, tool registry drift, embedded-skill drift, and incomplete prompt contracts while performing zero writes | focused_candidate | `tests/test_behavioral_surface.py`, `pb project behavioral-surface validate` | v0.1.109.1 |
| DOD-305 | The behavioral registry is an explicit project authority domain with a human-readable projection and is included in mandatory full release-validation groups | focused_candidate | `docs/project/project-authority-graph-v0.1.109.json`, `docs/project/behavioral-surface.md`, `promptbranch_test_suite.py` | v0.1.109.1 |



## v0.1.110

| ID | DoD item | Status | Evidence | Last release |
|---|---|---|---|---|
| DOD-306 | A tracked machine-readable Promptbranch backlog exists with unique IDs, explicit status, priority, implementation order, dependencies, and repository-relative ticket paths | focused_candidate | `docs/backlog/backlog.json`, `tests/test_backlog_contract.py`, project control-surface validation | v0.1.110 |
| DOD-307 | ISSUE-001 and PBAI-001 are preserved as complete open tickets and are distinguished from release-horizon and historical DoD records | focused_candidate | `docs/backlog/README.md`, both ticket Markdown files | v0.1.110 |

## v0.1.111.3 normalised progress and browser fail-fast

| ID | DoD item | Status | Evidence | Last release |
|---|---|---:|---|---|
| DOD-308 | Expected browser outcomes are normalised before terminal progress accounting; genuine failed normalised steps stop before the next main browser step; pending browser/agent/validation units become skipped and terminal progress reaches 100%; all release gates remain unchanged | focused_candidate | `promptbranch_full_integration_test.py`, `promptbranch_test_suite.py`, `tests/test_full_integration_harness.py`, `tests/test_promptbranch_test_suite.py`, `docs/repair-v0.1.111.3.md` | v0.1.111.3 |

## v0.1.111.4 deterministic external-live idle handoff

| ID | Requirement | Status | Evidence | Version |
|---|---|---|---|---|
| DOD-309 | The trusted external-live conversation is identity-only; release-live preserves browser/profile scope, hands off to an idle exact Project home, creates a dedicated conversation, never clicks Stop, submits nothing on failed handoff, and reports downstream gates as dependency skips after one causal failure | focused_candidate | `promptbranch_browser_auth/client.py`, `chatgpt_claudecode_workflow_release_control.sh`, `tests/test_release_live_continuous_direct_conversation.py`, `tests/test_promptbranch_shell_scripts.py`, `docs/repair-v0.1.111.4.md` | v0.1.111.4 |

## v0.1.111.5 named-step ETA planning and stable countdown

| ID | Requirement | Status | Evidence | Version |
|---|---|---|---|---|
| DOD-311 | Progress ETA uses successful named-step/transport medians, direct-to-localhost ETA-only priors, phase fallback, known-skip exclusion, confidence-labelled ranges, stable countdown clamping, and bounded atomic history while remaining unable to alter validation authority | done | `promptbranch_eta.py`, `promptbranch_test_suite.py`, `chatgpt_claudecode_workflow_release_control.sh`, `tests/test_promptbranch_eta.py`, `tests/test_promptbranch_test_suite.py`, `tests/test_promptbranch_shell_scripts.py`, `docs/repair-v0.1.111.5.md` | v0.1.111.5 |

## v0.1.111.5.1 empty-step-safe ETA and stable range countdown

| ID | Requirement | Status | Evidence | Version |
|---|---|---|---|---|
| DOD-312 | Top-level ETA progress handles an empty current step without associative-array errors and, while the active plan is unchanged or shrinking, clamps both ETA midpoint and high bound without affecting validation authority | repair_required | `chatgpt_claudecode_workflow_release_control.sh`, `promptbranch_eta.py`, `promptbranch_test_suite.py`, `tests/test_promptbranch_eta.py`, `tests/test_promptbranch_shell_scripts.py`, `docs/repair-v0.1.111.5.1.md` | v0.1.111.5.1 |


## v0.1.111.5.2 null-safe previous active-step ETA state

| ID | Requirement | Status | Evidence | Version |
|---|---|---|---|---|
| DOD-313 | Missing, omitted, or null previous active-step progress state is normalised to an empty sequence at both release-controller and estimator boundaries while retaining empty-step safety, stable range countdown, and informational-only ETA authority | focused_candidate | `chatgpt_claudecode_workflow_release_control.sh`, `promptbranch_eta.py`, `tests/test_promptbranch_eta.py`, `tests/test_promptbranch_shell_scripts.py`, `docs/repair-v0.1.111.5.2.md` | v0.1.111.5.2 |

## v0.1.112 PBAI-001 declaration and structural validation

| ID | Definition | Evidence level | Evidence | Version |
|---|---|---|---|---|
| DOD-314 | A tracked `.promptbranch-ai.json` declaration and packaged schema support `runtime_application` and `domain_module` with one sole version authority | focused_candidate | `.promptbranch-ai.json`, `promptbranch_protocol/schemas/application.architecture.schema.json`, `promptbranch_application_architecture.py`, `tests/test_promptbranch_application_architecture.py` | v0.1.112 |
| DOD-315 | Structural validation requires all ten AI application layers and fails closed on unknown fields, unsafe paths, missing/empty assets, ambiguous layer ownership, unsafe commands, delegation conflicts, and self-granted authority | focused_candidate | `promptbranch_application_architecture.py`, `tests/test_promptbranch_application_architecture.py` | v0.1.112 |
| DOD-316 | `pb application architecture plan` is read-only, structural validation reports only the highest proven level, and registry/executable/operational requests do not overclaim | focused_candidate | `promptbranch_cli.py`, `promptbranch_application_architecture.py`, `tests/test_promptbranch_application_architecture.py` | v0.1.112 |
| DOD-317 | PBAI-001 structural validation is a required release-validation group and Promptbranch itself passes as a runtime application | focused_candidate | `promptbranch_test_suite.py`, `.promptbranch-ai.json`, `tests/test_promptbranch_test_suite.py`, `tests/test_promptbranch_application_architecture.py` | v0.1.112 |
| DOD-318 | Candidate passes strict direct/localhost/live release validation and exact evidence-bound adoption/current verification | open | full release-control log and adopted registry evidence required | v0.1.112 |


## v0.1.113 PBAI-001 registry validation and reference resolution

| ID | Requirement | Status | Evidence | Version |
|---|---|---|---|---|
| DOD-319 | A tracked `.promptbranch/ai-registry.json` and packaged strict registry schema enumerate all required AI object kinds | focused_candidate | registry file, schema, declaration schema `1.1`, parser tests | v0.1.113 |
| DOD-320 | Every Agent, Skill, Tool, Validator, state contract, and evidence contract reference resolves exactly and implementation bindings are statically verified | focused_candidate | registry validator and negative reference tests | v0.1.113 |
| DOD-321 | Registered agent capabilities exactly cover declared ownership and every authority boundary resolves to one bounded controller | focused_candidate | capability and controller regressions | v0.1.113 |
| DOD-322 | Registry validation is read-only, executes no declared command, reports registry as the highest proven level, and keeps executable/operational proof fail-closed | focused_candidate | CLI and no-execution tests | v0.1.113 |
| DOD-323 | Candidate passes strict direct/localhost/live release validation and exact evidence-bound adoption/current verification | open | full release-control log and adopted registry evidence required | v0.1.113 |

## v0.1.114 PBAI-001 executable validation and SkillRun evidence

| ID | Requirement | Status | Evidence | Version |
|---|---|---|---|---|
| DOD-324 | A sole tracked executable proof skill declares its request, exact ordered tools, validators, evidence contract, maximum steps, and timeout | focused_candidate | `.promptbranch/ai-registry.json`, schema `1.1`, parser regressions | v0.1.114 |
| DOD-325 | Executable validation invokes the real Promptbranch MCP stdio boundary and permits only registered read-only tools in the declared order | focused_candidate | executable validator, source/clean-extraction proof, wrong-order tests | v0.1.114 |
| DOD-326 | Every SkillRun includes typed application/skill identity, ordered step inputs/results, per-step SHA-256 digests, validator outcomes, safety boundaries, run ID, and canonical evidence SHA-256 | focused_candidate | `promptbranch_skillrun.py`, packaged schema, tamper tests | v0.1.114 |
| DOD-327 | Failed tools, excessive steps, evidence tampering, missing validators, or mutation/authority flags fail closed at `proven_level=registry` | focused_candidate | negative executable and SkillRun regressions | v0.1.114 |
| DOD-328 | Operational proof remains unimplemented and cannot be inferred from executable evidence | focused_candidate | operational fail-closed test and CLI result | v0.1.114 |
| DOD-329 | Candidate passes strict direct/localhost/live release validation and exact evidence-bound adoption/current verification | open | full release-control log and adopted registry evidence required | v0.1.114 |

## v0.1.114.1 candidate runtime and FastAPI/Starlette compatibility repair

| ID | Requirement | Status | Evidence | Version |
|---|---|---|---|---|
| DOD-330 | Release control binds all release-critical candidate validation to the exact pipx venv and fails closed on ambient PATH shadowing or interpreter-prefix drift | focused_candidate | `chatgpt_claudecode_workflow_release_control.sh`, shell/runtime regressions | v0.1.114.1 |
| DOD-331 | Package import validation verifies the exact candidate Python plus the tracked FastAPI `0.128.2` and Starlette `0.50.0` runtime versions | focused_candidate | `promptbranch_test_suite.py`, dependency and identity regressions | v0.1.114.1 |
| DOD-332 | The repair preserves PBAI structural, registry, executable, SkillRun, operational fail-closed, publication, adoption, and current-verification semantics | focused_candidate | existing PBAI/SkillRun/release groups | v0.1.114.1 |
| DOD-333 | Candidate passes strict direct/localhost/live validation and exact evidence-bound adoption/current verification | open | full release-control log and adopted registry evidence required | v0.1.114.1 |

## v0.1.114.2 deterministic candidate test-runner dependency repair

| ID | Requirement | Status | Evidence | Version |
|---|---|---|---|---|
| DOD-334 | The exact candidate venv contains pinned `pytest==9.0.2` as package metadata, not an ambient or implicit test dependency | focused_candidate | `pyproject.toml`, `requirements.txt`, installed metadata checks | v0.1.114.2 |
| DOD-335 | Release control verifies pytest version, module path, interpreter prefix, and release-validation Python identity before Project Source mutation | focused_candidate | release controller preflight and regressions | v0.1.114.2 |
| DOD-336 | `pb test full` resolves every release-validation command through the verified candidate Python and fails closed before group execution on test-runner drift | focused_candidate | `promptbranch_test_suite.py`, release-validation runner tests | v0.1.114.2 |
| DOD-337 | Candidate passes strict direct/localhost/live validation and exact evidence-bound adoption/current verification | open | full release-control log and adopted registry evidence required | v0.1.114.2 |

## v0.1.115.1 release-live profile ownership handoff repair

| ID | Requirement | Status | Evidence | Version |
|---|---|---|---|---|
| DOD-338 | Cross-process profile `flock` contention waits within the configured scheduler deadline and succeeds when the external owner releases | focused_candidate | `_SharedProfileAsyncLock`, cross-process release regression | v0.1.115.1 |
| DOD-339 | A cross-process timeout reports the observed owner and proves the actual queue wait instead of returning after approximately 0.001 seconds | focused_candidate | structured busy payload and timeout regression | v0.1.115.1 |
| DOD-340 | Live preflight and continuous live use the same service owner and are separated by service-idle plus host-flock release proof | focused_candidate | release controller and shell regressions | v0.1.115.1 |
| DOD-341 | Strict direct, localhost, external-live, rollback, Guardian, operational-evidence, adoption and current-verification gates remain unchanged | open | full all-all release-control adoption log required | v0.1.115.1 |

| DOD-347 | Same adopted version with a different or missing artifact SHA-256 fails before Project Source or registry mutation | done | release identity and artifact registry tests | v0.1.117.1 |
| DOD-348 | Same version and same SHA-256 is idempotent and skips duplicate publication/adoption | done | release pipeline idempotence test | v0.1.117.1 |
| DOD-349 | Reusable release evidence binds to canonical rebuilt artifact SHA-256, repository identity, Git commit and validation dimensions | done | release-control contract tests | v0.1.117.1 |


## v0.1.118 resumable/importable release-pipeline evidence and recovery

| ID | Requirement | Status | Evidence | Version |
|---|---|---|---|---|
| DOD-350 | Every release-pipeline phase atomically updates a crash-consistent checkpoint containing ordered phase results, immutable repository/version/artifact/contract bindings, the exact requested mutation envelope and stop reason | focused_candidate | `promptbranch_release_pipeline.py`, checkpoint failure regression | v0.1.118 |
| DOD-351 | `pb release pipeline import` validates a prior checkpoint, summary or evidence directory without mutation and fails closed on repository, version, artifact, contract, Git or Project Source identity drift | focused_candidate | import planner and negative identity regressions | v0.1.118 |
| DOD-352 | `pb release pipeline resume` requires the exact imported mutation envelope, re-runs safe repository-owned local gates, and reuses exact successful Git and Project Source mutation evidence instead of replaying those mutations | focused_candidate | publication/adoption partial-failure recovery regressions | v0.1.118 |
| DOD-353 | Successful imported adoption/current evidence is accepted only when authoritative current identity reconfirms it; divergence blocks automatic replay and records explicit recovery failure | focused_candidate | adoption/current recovery and divergence tests | v0.1.118 |
| DOD-354 | Candidate passes strict direct/localhost/live validation and exact evidence-bound adoption/current verification | open | full release-control log and adopted registry evidence required | v0.1.118 |

## v0.1.118.1 deterministic canonical rebuild and failed-attempt identity binding

| ID | DoD item | Status | Evidence | Last release |
|---|---|---|---|---|
| DOD-355 | Rebuilding the same committed repository and release contract produces byte-identical canonical ZIP bytes with fixed entry order, timestamps, permissions and archive method | focused_candidate | `scripts/build-release-artifact.py`, deterministic mtime/rebuild regression, release-control double-build comparison | v0.1.118.1 |
| DOD-356 | Release control atomically binds repository, version, canonical artifact SHA-256, Git commit and release-contract SHA-256 before Project Source mutation | focused_candidate | `promptbranch_release_attempt.py`, checkpoint preflight regression | v0.1.118.1 |
| DOD-357 | Successful Project Source publication becomes a provisional immutable identity containing exact assigned filename, processed file id, Library metadata id, persistence proof and canonical SHA-256 before validation/adoption | focused_candidate | checkpoint source-recording implementation and evidence validation regression | v0.1.118.1 |
| DOD-358 | A same-version rerun with changed artifact/commit/contract fails before Project Source mutation; an exact rerun imports the checkpoint and reuses the existing source without indexed replacement | focused_candidate | conflict and exact-source-reuse regressions plus release-controller ordering assertions | v0.1.118.1 |
| DOD-359 | Failed validation followed by cleanup and rerun preserves Git commit, artifact SHA-256, assigned source filename, processed file id and Library metadata id, then strict host validation/adoption verifies the repair | open | focused interrupted-run regression passed; strict host lifecycle evidence pending | v0.1.118.1 |

## v0.1.119 read-only multi-repository release-set dependency planner

| ID | Requirement | Status | Evidence | Release |
|---|---|---|---|---|
| DOD-360 | A strict `promptbranch.release_set` v1.0 manifest resolves only repositories joined to the same tracked Promptbranch Project | focused_candidate | `promptbranch_release_set.py`, schema, project mismatch and unconfigured-repo regressions | v0.1.119 |
| DOD-361 | The planner emits deterministic dependency-first order, parallel execution waves, compatibility matrix rows and canonical `plan_sha256` | focused_candidate | happy-path and deterministic-repeat regressions | v0.1.119 |
| DOD-362 | Dependencies resolve from release-set targets or accepted/current project registry evidence, and cycles, missing dependencies or incompatible constraints fail closed | focused_candidate | cycle, unknown dependency, external current and incompatibility regressions | v0.1.119 |
| DOD-363 | Canonical target artifact names, repository-relative paths, ZIP integrity, VERSION and SHA-256 are validated without mutation | focused_candidate | artifact name, SHA mismatch, ZIP and read-only regressions | v0.1.119 |
| DOD-364 | `pb release set plan` performs no repository, Git, registry, Project Source, publication, adoption, execution or rollback mutation | focused_candidate | safety payload, before/after digest regression, CLI contract | v0.1.119 |

## v0.1.120 guarded multi-repository rollout execution and rollback evidence

| ID | Requirement | Status | Evidence | Release |
|---|---|---|---|---|
| DOD-365 | `pb release set apply` recomputes the plan and blocks before mutation unless the plan is compatible, execution-ready and confirmed by exact release-set ID plus plan SHA-256 | focused_candidate | confirmation, drift and unbound-target regressions | v0.1.120 |
| DOD-366 | The rollout requires the complete per-repository release pipeline authorization and executes repositories in dependency-wave order with deterministic order inside each wave | focused_candidate | CLI parser, command construction and happy-path order regressions | v0.1.120 |
| DOD-367 | Accepted/current artifact and Project Source identities are captured before the first mutation and verified after each apply or rollback transition | focused_candidate | registry target verification and previous-identity restoration regressions | v0.1.120 |
| DOD-368 | The first failed repository stops later execution and completed repositories roll back in exact reverse completion order through repository-owned rollback contracts | focused_candidate | apply-failure and reverse rollback regressions | v0.1.120 |
| DOD-369 | Any rollback command failure or artifact/source identity mismatch fails closed as incomplete rollback evidence | focused_candidate | rollback failure and registry mismatch regressions | v0.1.120 |
| DOD-370 | Rollout checkpoints are atomic and tamper-evident through a per-event SHA-256 chain plus final evidence SHA-256, independently validated by `pb release set evidence-validate` | focused_candidate | valid evidence and tamper-detection regressions | v0.1.120 |

## v0.1.120.1 checkpoint resume exit-code handling repair

| ID | Requirement | Status | Evidence | Release |
|---|---|---|---|---|
| DOD-371 | An exact failed-release retry receiving checkpoint code `10` reuses the bound source identity and continues into validation without duplicate publication or premature shell exit | focused_candidate | executable extracted-function regression plus strict host retry | v0.1.120.1 |

## v0.1.121 resumable release-set rollout recovery and operator reconciliation

| ID | Requirement | Status | Evidence | Release |
|---|---|---|---|---|
| DOD-372 | `pb release set reconcile` validates checkpoint/evidence integrity and performs no repository, Git, registry, Project Source, publication, adoption, or current-state mutation | focused_candidate | deterministic before/after checkpoint regression and reconciliation safety payload | v0.1.121 |
| DOD-373 | Reconciliation reconstructs the original plan SHA-256 from the manifest plus exact pre-rollout current identities even after some repositories have reached target current | focused_candidate | interrupted-forward reconciliation regression | v0.1.121 |
| DOD-374 | Every repository is classified as exact target, exact previous, missing, or ambiguous current identity and the result emits deterministic pending order, rollback order, recovery mode, and reconciliation SHA-256 | focused_candidate | classification, repeatability and ambiguous-state regressions | v0.1.121 |
| DOD-375 | `pb release set resume` requires exact release-set ID, original plan SHA-256, reconciliation SHA-256, rollback-on-failure, and the complete release-pipeline mutation envelope | focused_candidate | parser and authorization regressions | v0.1.121 |
| DOD-376 | Interrupted forward rollout resumes without replaying repositories already verified at target identity and preserves final tamper-evident evidence validation | focused_candidate | interrupted apply/resume and evidence-chain regression | v0.1.121 |
| DOD-377 | Interrupted reverse rollback resumes only unreverted target-current repositories in reverse dependency order and fails closed on incomplete restoration | focused_candidate | interrupted rollback recovery regression | v0.1.121 |
| DOD-378 | Operator-repaired incomplete rollback finalizes without command replay only after every repository is authoritatively restored to its exact pre-rollout artifact and Project Source identity | focused_candidate | manual-repair reconciliation/finalization regression | v0.1.121 |
| DOD-379 | Candidate passes strict direct/localhost/live validation, Artifact Guardian, exact Project Source publication, adoption and accepted/current verification | open | strict host release-control log required | v0.1.121 |

## v0.1.121.1 backend 403/429 auth-bootstrap classification repair

| ID | DoD item | Status | Evidence | Last release |
|---|---|---|---|---|
| DOD-380 | Auth-bootstrap 403 detection ignores generic guardrail summaries and explicit HTTP 429 events | focused_candidate | executable real-function regression with representative 429 telemetry | v0.1.121.1 |
| DOD-381 | Auth-bootstrap 403 detection remains terminal for an explicit structured backend guardrail event with status 403 | focused_candidate | executable real-function positive 403 regression | v0.1.121.1 |
| DOD-382 | Repair preserves all v0.1.121 release-set recovery semantics and is included in mandatory deterministic release validation | focused_candidate | release_pipeline group plus release-set planner/rollout groups | v0.1.121.1 |
| DOD-383 | Candidate passes strict direct/localhost/live validation, Artifact Guardian, exact Project Source publication, adoption and accepted/current verification | open | strict host release-control log required | v0.1.121.1 |
| DOD-384 | A normal MVP proof cycle is evaluated from explicit artifact-intake, all-tests, visual transport, adoption, current identity, and continuation-ask evidence rather than inferred from prose or a generic green release | focused_candidate | `promptbranch_mvp_proof.py`, `scripts/verify-mvp-proof-cycle.py`, `tests/test_promptbranch_mvp_proof.py` | v0.1.122 |
| DOD-385 | MVP proof fails closed when real download/verification evidence is missing, the candidate is a repair version, any outer release gate failed or skipped, or continuation resolves from a stale baseline | focused_candidate | negative evaluator regressions in `tests/test_promptbranch_mvp_proof.py` | v0.1.122 |
| DOD-386 | Post-adoption continuation proof uses `pb ask --protocol --from-current-baseline` targeting the next normal version and performs no publication or adoption mutation | focused_candidate | `scripts/finalize-mvp-proof-cycle.sh`, shell contract regression | v0.1.122 |
| DOD-387 | Strict host `v0.1.122` lifecycle plus proof finalization produces `mvp_proof_cycle_passed` and a canonical proof SHA-256 | open | strict host release log, artifact intake JSON, continuation ask JSON, `mvp-proof-cycle-1.v0.1.122.json` | v0.1.122 |

## v0.1.122.1 MVP proof finalizer fail-closed repair

| ID | Requirement | Status | Evidence | Version |
|---|---|---|---|---|
| DOD-388 | MVP proof resolves accepted/current identity from the authoritative project-level `repos.<repo-id>` payload returned by `pb artifact current --json` | focused_candidate | `promptbranch_mvp_proof.py`, project-level current regression | v0.1.122.1 |
| DOD-389 | Canonical candidate, artifact intake, adoption result, and accepted/current registry all expose the same non-empty SHA-256 before proof can pass | focused_candidate | evaluator SHA-binding checks and mismatch regressions | v0.1.122.1 |
| DOD-390 | Invalid or incomplete intake/release/adoption/current evidence fails a read-only preflight before any continuation Ask is issued | focused_candidate | `--preflight-only`, no-Ask executable regression | v0.1.122.1 |
| DOD-391 | Failed preflight or failed complete proof exits nonzero and never prints a verified-success message | focused_candidate | `set -Eeuo pipefail`, explicit verifier-result handling, shell regressions | v0.1.122.1 |
| DOD-392 | Strict host validation and adoption prove the repair while accepted/current remains immutable until evidence is green | done | 10/10 GO, exact Project Source, Artifact Guardian, adoption/current verification, `release_adopted_and_verified` | v0.1.122.1 |


## v0.1.123 canonical MVP proof cycle 1

| ID | Requirement | Status | Evidence | Version |
|---|---|---|---|---|
| DOD-393 | The candidate is a normal release from accepted/current `v0.1.122.1` and adds no platform capability beyond proof execution and evidence projection | focused_candidate | plan-state, release note, control-surface validation | v0.1.123 |
| DOD-394 | Real artifact intake proves download, ZIP verification, exact `v0.1.123` filename/version, and canonical SHA-256 before proof finalization | open | `v0.1.123.artifact-intake.json` bound to candidate bytes | v0.1.123 |
| DOD-395 | Strict host release control passes 10/10 with zero outer skips, visual ZIP transport, Artifact Guardian, exact Project Source, adoption, and accepted/current verification | open | full release-control and adoption/current evidence | v0.1.123 |
| DOD-396 | The post-adoption continuation Ask resolves from accepted/current `v0.1.123` and targets `v0.1.124` without publication or adoption mutation | open | continuation request/run/combined JSON evidence | v0.1.123 |
| DOD-397 | The fail-closed evaluator emits `mvp_proof_cycle_passed` with exact four-way SHA-256 binding and records formal consecutive proof count 1/2 | open | `mvp-proof-cycle-1.v0.1.123.json` | v0.1.123 |

## v0.1.123.1 integrated one-command MVP proof lifecycle repair

| ID | DoD item | Status | Evidence | Last release |
|---|---|---|---|---|
| DOD-398 | The exact operator spelling `pb ask continue --target-version <next-normal> --release-type normal` activates the integrated proof lifecycle while ordinary `pb ask` behavior remains unchanged | focused_candidate | parser/dispatch regression in `tests/test_promptbranch_mvp_ask_lifecycle.py` | v0.1.123.1 |
| DOD-399 | Candidate intake is bound to the exact request, conversation, user message, and assistant answer returned by the candidate-producing Ask; generic `--latest` selection is absent | focused_candidate | exact selector assertions and stopped-before-intake negative test | v0.1.123.1 |
| DOD-400 | Download, ZIP verification, migration, and candidate SHA-256 equality are required before strict release control starts | focused_candidate | integrated lifecycle stage checks and SHA mismatch fail-closed branch | v0.1.123.1 |
| DOD-401 | Strict release control, Project Source publication, 10/10 validation, adoption, accepted/current evidence, continuation Ask, and proof finalization are owned by the same command | focused_candidate | command-plan regression and canonical evidence path checks | v0.1.123.1 |
| DOD-402 | Any failed stage returns nonzero and cannot emit `mvp_proof_cycle_passed` or `mvp_verified` | focused_candidate | failed candidate-Ask regression and finalizer proof checks | v0.1.123.1 |
| DOD-403 | Repair acceptance preserves formal count 0/2 and schedules `v0.1.124` and `v0.1.125` as the two normal one-command proof cycles | candidate | plan-state, status, release-status, and slice-horizon authority | v0.1.123.1 |


## v0.1.123.2 explicit conversation pinning repair

| ID | DoD item | Status | Evidence | Last release |
|---|---|---|---|---|
| DOD-404 | Integrated proof requires an explicit `--conversation-url` and never falls back to remembered task state, project home, latest chat, or visible browser tab | focused_candidate | missing-argument regression and command construction assertions | v0.1.123.2 |
| DOD-405 | The explicit URL must be a complete ChatGPT Project conversation and must belong to the accepted/current release-authority project | focused_candidate | malformed and cross-project fail-closed regressions | v0.1.123.2 |
| DOD-406 | Release-candidate Ask, exact response correlation, and artifact intake use the same pinned conversation ID | focused_candidate | ask command, returned conversation mismatch, and intake task assertions | v0.1.123.2 |
| DOD-407 | Post-adoption continuation Ask uses the same pinned conversation and fails when the observed continuation conversation differs | focused_candidate | finalizer argument and observed conversation checks | v0.1.123.2 |
| DOD-408 | Repair acceptance preserves formal proof count 0/2 and leaves `v0.1.124` and `v0.1.125` as normal proof cycles 1 and 2 | candidate | plan-state and project control-surface evidence | v0.1.123.2 |


## v0.1.123.2.1 project authority URL alias reconciliation repair

| ID | DoD item | Status | Evidence | Last release |
|---|---|---|---|---|
| DOD-409 | Project ids and URLs expose one immutable `g-p-<32-hex>` authority identity across bare and slugged forms | focused_candidate | immutable id extraction regressions | v0.1.123.2.1 |
| DOD-410 | `pb project join` accepts matching bare/slugged aliases during release adoption preflight | focused_candidate | subprocess join regression using slugged tracked and bare requested values | v0.1.123.2.1 |
| DOD-411 | A genuinely different immutable Project UUID remains fail-closed | focused_candidate | cross-project mismatch regressions | v0.1.123.2.1 |
| DOD-412 | Alias reconciliation preserves the tracked authority bytes and formal proof count remains 0/2 | candidate | binding immutability and project control-surface evidence | v0.1.123.2.1 |


## v0.1.123.2.2 release-control post-join Project alias verification repair

| ID | Requirement | Evidence level | Evidence | Target |
|---|---|---|---|---|
| DOD-413 | Release control accepts a bare requested Project identity when `pb project join` returns the matching tracked slugged alias | focused_candidate | executable embedded-verifier regression | v0.1.123.2.2 |
| DOD-414 | Requested, returned, and tracked Project ids and URLs are compared through the immutable `g-p-<32-hex>` UUID | focused_candidate | alias success and payload/identity checks | v0.1.123.2.2 |
| DOD-415 | True cross-project UUID mismatches remain fail-closed before strict validation | focused_candidate | executable mismatch regression | v0.1.123.2.2 |
| DOD-416 | Caller-side alias verification preserves tracked authority bytes and repair acceptance does not advance formal proof count | candidate | binding immutability and project control-surface evidence | v0.1.123.2.2 |
## v0.1.123.2.3 operation-scoped response wait repair

| ID | DoD item | Status | Evidence | Last release |
|---|---|---|---|---|
| DOD-417 | Response waiting ignores backend-403 events recorded before the current causally confirmed submit boundary | focused_candidate | executable pre-submit file-download 403 regression | v0.1.123.2.3 |
| DOD-418 | Unrelated post-submit attachment-download 403 telemetry remains diagnostic and does not terminate a healthy pinned conversation | focused_candidate | executable post-submit unrelated-file regression | v0.1.123.2.3 |
| DOD-419 | Current-operation conversation 403s and real challenge/root/closed-target states remain fail-closed | focused_candidate | executable conversation-submit 403 and existing challenge regressions | v0.1.123.2.3 |
| DOD-420 | The integrated outer step timeout exceeds response, fresh-turn, artifact-materialization, and safety budgets without an extra operator flag | focused_candidate | executable timeout-budget invariant and generated ask command assertions | v0.1.123.2.3 |
| DOD-421 | Repair acceptance preserves formal proof count 0/2 and leaves `v0.1.124` and `v0.1.125` as normal proof cycles 1 and 2 | candidate | project control-surface and release-status authority | v0.1.123.2.3 |



## v0.1.123.2.6 correlated rendered-attachment intake repair

| ID | DoD item | Status | Evidence | Last release |
|---|---|---|---|---|
| DOD-431 | Artifact intake selects the exact correlated assistant turn by persisted answer/request/turn identity before looking for a rendered attachment | focused_candidate | exact-turn selection and ambiguity regressions | v0.1.123.2.6 |
| DOD-432 | Exactly one matching rendered ZIP is downloaded through the active authenticated browser context into the artifact inbox | focused_candidate | browser download mock and saved-answer replay path | v0.1.123.2.6 |
| DOD-433 | Downloaded filename, SHA-256, byte size, ZIP entry count, CRC, and embedded version are verified against the envelope before success | focused_candidate | metadata match and mismatch regressions | v0.1.123.2.6 |
| DOD-434 | A JSON-only `sandbox:` artifact remains invalid when no matching rendered attachment exists, while a correlated rendered control permits browser-context resolution | focused_candidate | JSON-only rejection and rendered-link acceptance regressions | v0.1.123.2.6 |
| DOD-435 | Integrated lifecycle reuses a verified inbox artifact and does not download or mutate release state twice | focused_candidate | lifecycle command construction and no-mutation assertions | v0.1.123.2.6 |

## v0.1.123.2.6 candidate-collection compatibility correction

| ID | DoD item | Status | Evidence | Last release |
|---|---|---|---|---|
| DOD-436 | The service module remains importable when an ambient environment combines FastAPI 0.128.x with a Starlette Router API that no longer accepts `on_startup` and `on_shutdown`, while the supported pinned dependency pair remains unchanged | focused_candidate | real module-import subprocess regression plus synthetic modern-Router lifecycle regression | v0.1.123.2.6 |
| DOD-437 | Focused ask-release tests are hermetic with respect to local Project identity and preserve mandatory repository-bound artifact records | focused_candidate | isolated project-scope fixture and Gate 4 regression group | v0.1.123.2.6 |
| DOD-438 | Persisted artifact replay selects one exact validated protocol run by request ID and cannot drift to a newer unrelated no-artifact reply | focused_candidate | exact older-run selection, missing-record, identity-mismatch, and selector-source regressions | v0.1.123.2.6 |
| DOD-439 | An exact-ID `artifact_declared_but_not_attached` record is replayable only through an explicit opt-in that requires download plus verification and proves intact request, envelope, answer, failure, and no-mutation invariants before browser access | focused_candidate | allowlist eligibility, rejection matrix, and browser-byte verification regression | v0.1.123.2.6 |


## v0.1.123.2.6 historical protocol-record compatibility correction

| ID | DoD item | Status | Evidence | Last release |
|---|---|---|---|---|
| DOD-440 | Explicit replay normalizes the observed historical selection-summary, ZIP media-type, baseline-alias, and attachment-failure record shapes without weakening normal validated-run intake | focused_candidate | historical-shape end-to-end replay fixture and 16-test replay group | v0.1.123.2.6 |
| DOD-441 | Legacy normalization remains fail-closed for contradictory identities, non-ZIP MIME types, baseline drift, extra validation failures, failed filename/version/role/count checks, and any prior materialization or state mutation | focused_candidate | parameterized rejection matrix; browser backend remains unreachable on rejection | v0.1.123.2.6 |

## v0.1.123.2.6 post-materialization finalization correction

| ID | DoD item | Status | Evidence | Last release |
|---|---|---|---|---|
| DOD-442 | Release-candidate request validation treats `input_baseline`/`input_artifact` and target-version projections as equivalent only when every present value agrees | focused_candidate | direct normalization and contradiction regressions | v0.1.123.2.6 |
| DOD-443 | An exact already materialized protocol run can be finalized idempotently from its verified artifact inbox without redownload or release-state mutation | focused_candidate | persisted-run success, tampered-bytes rejection, and prior-mutation rejection regressions | v0.1.123.2.6 |


## v0.1.123.2.6 validated materialization migration correction

| ID | DoD item | Status | Evidence | Last release |
|---|---|---|---|---|
| DOD-444 | Persisted-run ZIP-kind and baseline normalization is shared by replay, finalization, ordinary validated intake, and migration; MIME-only ZIPs and `input_baseline` are accepted only with agreeing filename, media type, and request evidence | focused_candidate | shared-classifier regressions plus exact validated-run migration integration | v0.1.123.2.6 |
| DOD-445 | `candidate-run` preserves the exact validated request ID and repository/filename/version expectations, reuses the verified artifact-inbox ZIP, and creates exactly one migrated candidate without browser redownload | focused_candidate | finalized-run-to-candidate-registry integration test | v0.1.123.2.6 |

## Active repair candidate — v0.1.125.3.3

- accepted/current baseline: `chatgpt_claudecode_workflow-2_v0.1.125.3.2.zip` (`v0.1.125.3.2`)
- accepted baseline SHA-256: `c6e6617a22b526b6bb3ae7f65274ce6edd75898ce926e24bda204bfc8b68504f`
- active repair artifact: `chatgpt_claudecode_workflow-2_v0.1.125.3.3.zip`
- active repair slice: v0.1.125.3.3 — Acceptance/adoption transactional reconciliation
- next normal slice: `v0.1.126 — Persistent whole-release ETA estimator`
- planned after repair acceptance: `v0.1.126 — Persistent whole-release ETA estimator`
- scope advancement: forbidden; repair only fixes action-aware acceptance/current result selection, post-side-effect reconciliation, idempotent stale-attempt recovery, and final state convergence


## Active repair candidate — v0.1.125.3.4.1

- control-plane accepted/current baseline: `chatgpt_claudecode_workflow-2_v0.1.125.3.3.zip` (`v0.1.125.3.3`)
- active repair artifact: `chatgpt_claudecode_workflow-2_v0.1.125.3.4.1.zip`
- active repair slice: v0.1.125.3.4.1 — Candidate-test retry isolation and authoritative runtime final convergence
- observed pre-repair authoritative Docker service: `promptbranch-service:0.1.125.2` on port `8000`
- required promotion: retag the exact tested candidate image as `promptbranch-service:0.1.125.3.4.1`, recreate only the canonical `chatgpt_claudecode_workflow` service on port `8000`, and require live health plus version/SHA/attempt labels to match before `ADOPTED_CURRENT`
- rollback: restore the previously healthy production image when promotion fails; keep the release attempt retryable
- cleanup: remove isolated `pb-candidate-*` service containers only after authoritative runtime convergence
- `FINAL_VERIFIED`: must independently re-probe the live port-8000 service and fail on runtime drift
- next normal slice remains `v0.1.126 — Persistent whole-release ETA estimator`; repair scope does not advance application work

## v0.1.125.3.4.2 post-adoption historical verification repair

| ID | DoD item | Status | Evidence | Last release |
|---|---|---|---|---|
| DOD-446 | `RUNTIME_PREPARED` requires live candidate health before adoption, but after `ADOPTED_CURRENT` uses immutable recorded candidate health/identity evidence and does not require the intentionally retired endpoint to remain reachable | focused_candidate | release-state-machine regression with candidate cleanup followed by all-state verification | v0.1.125.3.4.2 |
| DOD-447 | Post-adoption historical verification requires successful candidate cleanup and exact equality between tested candidate Docker image id and promoted production image id | focused_candidate | positive and corrupted-evidence release-state-machine regressions | v0.1.125.3.4.2 |
| DOD-448 | Acceptance has one canonical projection path; successful command output without the accepted-candidate projection fails closed and no compatibility fallback reconstructs it | focused_candidate | projectionless acceptance regression | v0.1.125.3.4.2 |
| DOD-449 | v0.1.125 closes only when `FINAL_VERIFIED` succeeds with no failed invariants and the authoritative port-8000 runtime is exact after candidate cleanup | live_pending | canonical host lifecycle, `release verify --all-states`, artifact current, Docker container and `/healthz` evidence | v0.1.125.3.4.2 |


## Active repair candidate — v0.1.125.3.4.2

- accepted/current baseline: `chatgpt_claudecode_workflow-2_v0.1.125.3.4.1.zip` (`v0.1.125.3.4.1`)
- active repair artifact: `chatgpt_claudecode_workflow-2_v0.1.125.3.4.2.zip`
- active repair slice: v0.1.125.3.4.2 — Post-adoption historical verification and final convergence
- no backward-compatibility path for superseded post-adoption candidate-liveness semantics
- next normal slice: `v0.1.126 — Persistent whole-release ETA estimator`

## v0.1.126 persistent whole-release ETA DoD

| ID | DoD item | Status | Evidence | Last release |
|---|---|---|---|---|
| DOD-450 | Successful canonical release-transition durations persist by profile, phase, transport, and step without duplicate observations | focused_candidate | release ETA history and state-machine regression tests | v0.1.126 |
| DOD-451 | Whole-release ETA exposes remaining duration, expected finish range, confidence, and per-step evidence source through a read-only `pb release eta` command | focused_candidate | ETA unit/integration and CLI parser checks | v0.1.126 |
| DOD-452 | Candidate-test and optional outer-wrapper timeout risk are advisory and profile-aware; ETA degradation cannot alter validation authority | focused_candidate | timeout-risk and degraded-ETA state-machine regressions | v0.1.126 |
| DOD-453 | `v0.1.126` closes only after the full canonical live lifecycle reaches `FINAL_VERIFIED` from accepted/current `v0.1.125.3.4.2` with independent all-state verification green | live_pending | project next-slice read-only validation command plus canonical operator-host release proof | v0.1.126 |

## v0.1.126.1 repair DoD

| ID | Requirement | Validation | Evidence | Version |
|---|---|---|---|---|
| DOD-454 | Exact tested source is materialized before Git publication and tested/materialized/committed fingerprints are identical | focused + live | state-machine publication evidence | v0.1.126.1 |
| DOD-455 | Publication subprocess output selects exactly one complete top-level action result and retains hashed stdout/stderr evidence | focused | parser/publication regressions | v0.1.126.1 |
| DOD-456 | Project Source upload is idempotently reconciled across ChatGPT-assigned indexed filename family members | focused + live | source-list reconciliation evidence | v0.1.126.1 |
| DOD-457 | Retry may reuse cryptographically verified green candidate-test evidence; ETA exposes publication subphases separately | focused + live | retry/ETA regressions | v0.1.126.1 |
| DOD-458 | Repair closes only after the full canonical live lifecycle reaches FINAL_VERIFIED from accepted/current v0.1.125.3.4.2 with Git push and Project Source publication verified | live_pending | canonical operator-host release proof | v0.1.126.1 |

## v0.1.126.1.1 repair DoD

| ID | Requirement | Validation | Evidence | Version |
|---|---|---|---|---|
| DOD-459 | One canonical full-source fingerprint implementation is used by runtime preparation, Docker build verification, tested-source materialization, and committed-tree identity | focused + live | shared fingerprint unit/state-machine tests and live Docker build | v0.1.126.1.1 |
| DOD-460 | `BLOCKED_RETRYABLE` ETA suppresses a wall-clock finish timestamp while retaining advisory estimated work after resume | focused | ETA snapshot/status regressions | v0.1.126.1.1 |
| DOD-461 | Repair closes only after the full canonical live lifecycle reaches `FINAL_VERIFIED` from accepted/current `v0.1.125.3.4.2` with Git push, Project Source reconciliation, and exact production-image convergence verified | live_pending | canonical operator-host release proof | v0.1.126.1.1 |

## v0.1.126.1.1.1 repair DoD

| ID | Requirement | Proof | Evidence | Version |
|---|---|---|---|---|
| DOD-462 | Text-source value selection cannot resolve a generic title input; exact body/title values and save disabled state are diagnosable | focused | selector/readiness regressions | v0.1.126.1.1.1 |
| DOD-463 | HTTP/timeout failures preserve structured save-request evidence and the deferred integration step reaches fail-closed reconciliation | focused | harness/container regressions | v0.1.126.1.1.1 |
| DOD-464 | Zero-request text add reconciles first and retries at most once; unrelated or ambiguous source state blocks | focused + live | reconciliation evidence | v0.1.126.1.1.1 |
| DOD-465 | Focused live `project_source_add_text` passes before another full release attempt | live_pending | targeted operator-host proof | v0.1.126.1.1.1 |
| DOD-466 | Repair closes only after canonical full lifecycle reaches `FINAL_VERIFIED` from accepted/current `v0.1.125.3.4.2` | live_pending | full release proof | v0.1.126.1.1.1 |

## v0.1.126.1.1.1.1 repair DoD

| ID | Requirement | Proof | Version |
|---|---|---|---|
| DOD-467 | Docker integration ask propagates the explicit service timeout and the internal service deadline is lower than the HTTP client boundary | focused | adapter/container regressions | v0.1.126.1.1.1.1 |
| DOD-468 | Canonical `browser.ask_question` retains structured answer, conversation, submit, timeout, and phase evidence | focused + live | full-integration report | v0.1.126.1.1.1.1 |
| DOD-469 | Residual service-client `ReadTimeout` is structured and cannot trigger duplicate submission; confirmed/ambiguous submit timeout remains fail-closed | focused | timeout regressions | v0.1.126.1.1.1.1 |
| DOD-470 | Ask-only live proof passes before another full canonical release attempt | live_pending | targeted operator-host proof | v0.1.126.1.1.1.1 |
| DOD-471 | Repair closes only after full lifecycle reaches `FINAL_VERIFIED` from accepted/current `v0.1.125.3.4.2` | live_pending | canonical release proof | v0.1.126.1.1.1.1 |

## v0.1.126.1.1.1.1.1 repair DoD

| ID | Requirement | Proof | Version |
|---|---|---|---|
| DOD-472 | Runtime checkpoint is the authoritative source fingerprint and `RUNTIME_PREPARED` projects exactly the same value | focused | accessor/projection/verifier regressions | v0.1.126.1.1.1.1.1 |
| DOD-473 | Worktree materialization and Git committed-tree guards consume one canonical runtime fingerprint accessor | focused + live | publication-path regression and live publication evidence | v0.1.126.1.1.1.1.1 |
| DOD-474 | Missing runtime fingerprint and checkpoint/projection disagreement fail closed with distinct codes before unsafe publication continuation | focused | negative accessor/publication regressions | v0.1.126.1.1.1.1.1 |
| DOD-475 | Repair closes only after full lifecycle reaches `FINAL_VERIFIED` from accepted/current `v0.1.125.3.4.2` | live_pending | canonical release proof | v0.1.126.1.1.1.1.1 |


## v0.1.126.1.1.1.1.2 repair DoD

| ID | Requirement | Proof | Version |
|---|---|---|---|
| DOD-476 | `RUNTIME_PREPARED` blocks before candidate install/build/start unless accepted/current production is exactly one healthy port-8000 runtime matching the configured baseline version and exposing image identity/artifact-SHA labels | focused | missing/unhealthy/baseline-mismatch regressions | v0.1.126.1.1.1.1.2 |
| DOD-477 | Accepted-runtime precondition is re-snapshotted on retry so explicit operator recovery can resume without deleting the attempt checkpoint | focused | recovery/resume regression | v0.1.126.1.1.1.1.2 |
| DOD-478 | After candidate preparation, the accepted runtime must still satisfy the exact baseline precondition and preserve container ID, immutable Docker image ID, and artifact-SHA label | focused | disappearance/image-drift regressions | v0.1.126.1.1.1.1.2 |
| DOD-479 | Release-state verification independently requires the stronger accepted-runtime before/after evidence; the old `absent == unchanged` semantic is not retained | focused | verifier regression + state-machine suite | v0.1.126.1.1.1.1.2 |
| DOD-480 | Repair closes only after the canonical lifecycle reaches `FINAL_VERIFIED` from accepted/current `v0.1.125.3.4.2` | live_pending | canonical release proof | v0.1.126.1.1.1.1.2 |


## v0.1.126.1.1.1.1.3 repair DoD

| ID | Requirement | Status | Evidence | Version |
|---|---|---|---|---|
| DOD-481 | Release-contract sanitized execution forwards `PROMPTBRANCH_RELEASE_VALIDATION_PYTHON` selected by the canonical state machine | focused | tracked-contract + execute-env regression | v0.1.126.1.1.1.1.3 |
| DOD-482 | A poisoned ambient `PATH` pointing at a foreign pytest environment cannot replace explicit candidate validation-Python authority | focused | poisoned-PATH regression + deterministic runner preflight | v0.1.126.1.1.1.1.3 |
| DOD-483 | All required deterministic release groups execute under the candidate interpreter rather than being preflight-skipped | construction | mandatory release-validation groups | v0.1.126.1.1.1.1.3 |
| DOD-484 | Repair closes only after the canonical lifecycle reaches `FINAL_VERIFIED` from accepted/current `v0.1.125.3.4.2` | live_pending | canonical release proof | v0.1.126.1.1.1.1.3 |


## v0.1.127 normal-slice DoD

| ID | Requirement | Status | Evidence | Version |
|---|---|---|---|---|
| DOD-485 | Canonical AI registry tracks exactly one `promptbranch-tool-authoring` skill whose allowed runtime surface is read-only inspection only | focused | skill validation + registry validation | v0.1.127 |
| DOD-486 | `promptbranch.tool.authoring` schema/semantic validation requires bounded JSON input, explicit risk/read-only classification, named validators, required evidence, stable failure codes, and rejects authority escalation | focused | positive/negative tool-spec regressions | v0.1.127 |
| DOD-487 | Portable export contains `SKILL.md`, tool schema, valid example, `PROJECT_SOURCE.md`, `AGENTS.md`, and digest-bound `manifest.json` with deterministic ZIP metadata | focused + construction | byte-identical export regression + bundle verifier | v0.1.127 |
| DOD-488 | Tool-authoring validation/export grants no execution, mutation, release, publication, or adoption authority | focused | manifest/source authority assertions | v0.1.127 |
| DOD-489 | Bundle verification fails closed on missing/extra/tampered entries, digest mismatch, unsafe paths, non-deterministic metadata, or manifest authority escalation | focused | tamper/negative regressions | v0.1.127 |
| DOD-490 | Normal slice closes only after canonical lifecycle reaches `FINAL_VERIFIED` from accepted/current `v0.1.126.1.1.1.1.3` and scoped artifact-current aligns | superseded_by_DOD-515 | consolidated v0.1.127.2.1 closure proof | v0.1.127 |


## v0.1.127.1 repair DoD

| ID | Requirement | Status | Evidence | Version |
|---|---|---|---|---|
| DOD-491 | Exact origin conversation URL/ID and correlated protocol identity persist on accepted artifacts | focused | provenance regressions | v0.1.127.1 |
| DOD-492 | Legacy binding is explicit, immutable, idempotent for same URL, conflict/project mismatch fail closed | focused | bind regressions | v0.1.127.1 |
| DOD-493 | Successor ask uses explicit CLI first, baseline artifact provenance otherwise; mutable current chat cannot redirect | focused | routing regressions | v0.1.127.1 |
| DOD-494 | Full release routes only ask_question to baseline origin, matching project URL; source/task stay isolated; missing provenance blocks | construction | harness/state-machine + required groups | v0.1.127.1 |
| DOD-495 | Repair closes only at FINAL_VERIFIED from `.1.3` with scoped current exact `.127.1` and own origin provenance | superseded_by_DOD-515 | canonical live proof | v0.1.127.1 |


## v0.1.127.1.1 repair DoD

| ID | Requirement | Status | Evidence | Version |
|---|---|---|---|---|
| DOD-496 | Artifact provenance accepts slugged and unslugged URLs when both canonicalize to the same `g-p-<32hex>` identity | focused | project-identity provenance regressions | v0.1.127.1.1 |
| DOD-497 | Different canonical ChatGPT project identities remain rejected and the exact origin conversation URL is preserved | focused | negative provenance regressions | v0.1.127.1.1 |
| DOD-498 | Repair proceeds beyond legacy migration only after the exact `.1.3` `artifact bind-conversation` live proof succeeds; closure still requires canonical `FINAL_VERIFIED` plus scoped current | superseded_by_DOD-515 | exact bind + consolidated v0.1.127.2.1 closure proof | v0.1.127.1.1 |


## v0.1.127.1.1.1 repair DoD

| ID | DoD item | Status | Evidence | Last release |
|---|---|---|---|---|
| DOD-499 | `pb test full --ask-conversation-url` propagates the exact pin into the browser/full runner and browser summary instead of dropping it at CLI dispatch | focused | CLI dispatch + browser namespace regression | v0.1.127.1.1.1 |
| DOD-500 | `TESTED_GREEN` fails closed unless exactly one executed `ask_question` step reports the expected baseline conversation URL and exact conversation ID | focused | route-mismatch state-machine regression | v0.1.127.1.1.1 |
| DOD-501 | Independent release verification recomputes the ask route from the persisted browser report and detects route tampering even when generic suite status remains green | focused | persisted-report tamper regression | v0.1.127.1.1.1 |
| DOD-502 | Repair closes only after fresh canonical live proof executes `ask_question` on conversation `6a78783b-3e00-83eb-8dc1-1e814fcf2a59`, reaches `FINAL_VERIFIED`, and scoped current aligns | superseded_by_DOD-515 | consolidated v0.1.127.2.1 closure proof | v0.1.127.1.1.1 |


## v0.1.127.1.1.1.1 repair DoD

| ID | Requirement | Proof class | Construction proof | Release |
|---|---|---|---|---|
| DOD-503 | Acceptance uses a defined canonical ChatGPT project-conversation predicate and artifact-origin validation delegates to the same predicate | focused | helper unit/acceptance branch regression | v0.1.127.1.1.1.1 |
| DOD-504 | A tested candidate carrying complete selected protocol provenance executes `artifact accept-candidate --adopt-if-green` without exception and preserves exact conversation URL/ID plus correlated request/message/answer identifiers | focused | provenance-bearing acceptance executable-path regression | v0.1.127.1.1.1.1 |
| DOD-505 | Repair closes only after a fresh immutable `v0.1.127.1.1.1.1` attempt repeats exact baseline-routed `TESTED_GREEN`, independently verifies it, reaches `ACCEPTED`, `ADOPTED_CURRENT`, `FINAL_VERIFIED`, and fresh scoped current aligns | superseded_by_DOD-515 | consolidated v0.1.127.2.1 closure proof | v0.1.127.1.1.1.1 |


## v0.1.127.1.1.1.1.1 repair DoD

| ID | Requirement | Proof class | Construction proof | Release |
|---|---|---|---|---|
| DOD-506 | The Python interpreter that launches Promptbranch is the sole release Python authority and is persisted as candidate/release-validation Python | focused | state-machine authority regressions | v0.1.127.1.1.1.1.1 |
| DOD-507 | Explicit candidate or validation Python values that resolve to a different interpreter fail closed before release mutation | focused | configuration/preflight mismatch regressions | v0.1.127.1.1.1.1.1 |
| DOD-508 | Release-contract `python`/`python3` and `pb`/`promptbranch` operations execute through the same launcher interpreter and do not depend on PATH-selected Promptbranch/Python | focused | release-engine poisoned-PATH regressions | v0.1.127.1.1.1.1.1 |
| DOD-509 | Repair closes only after a fresh immutable `v0.1.127.1.1.1.1.1` attempt repeats exact baseline-routed `TESTED_GREEN`, independently verifies it, reaches `ACCEPTED`, `ADOPTED_CURRENT`, `FINAL_VERIFIED`, and fresh scoped current aligns | superseded_by_DOD-515 | consolidated v0.1.127.2.1 closure proof | v0.1.127.1.1.1.1.1 |

## v0.1.127.2.1 consolidated v0.1.127 closure DoD

| ID | Requirement | Status | Evidence | Release |
|---|---|---|---|---|
| DOD-510 | The exact interpreter path that launches Promptbranch is the sole release Python authority; venv/pipx launcher symlinks are executed unchanged and retain their environment prefix instead of being resolved to a system Python target | construction_proven | symlink-path + real-venv subprocess regressions | v0.1.127.2.1 |
| DOD-511 | Canonical release CLI, validation, contract, pipeline, and release-set execution expose no alternate candidate/validation Python or PB-command selector; obsolete selector environment values cannot become authority | construction_proven | CLI/source assertions + poisoned-environment contract/validation regressions | v0.1.127.2.1 |
| DOD-512 | One candidate preserves the full v0.1.127 tool-authoring contract plus artifact project identity, exact conversation provenance, executed ask-route verification, and acceptance-path correlated provenance repairs | construction_proven | tool-authoring + provenance + route + executable acceptance regressions | v0.1.127.2.1 |
| DOD-513 | Construction tests exercise every canonical release state through `FINAL_VERIFIED`, independent all-state verification, interruption/resume, fail-closed acceptance/adoption guards, and route-proof tamper detection | construction_proven | canonical release-state-machine group | v0.1.127.2.1 |
| DOD-514 | Exact final ZIP is deterministic, CRC/path/hygiene clean, contains no nested ZIP, passes every required release-validation group, and Artifact Guardian reports `release_ready=true` | construction_proven | exact final ZIP + 17 required groups + Guardian | v0.1.127.2.1 |
| DOD-515 | v0.1.127 closes only after a fresh immutable v0.1.127.2.1 attempt from accepted/current `.1.3` repeats exact baseline-routed `TESTED_GREEN`, independently verifies it, reaches `ACCEPTED`, `ADOPTED_CURRENT`, `FINAL_VERIFIED`, and fresh scoped `pb artifact current --repo chatgpt_claudecode_workflow-2 --json` aligns exactly | live_proven | FINAL_VERIFIED + independent all-state verification + fresh scoped current exact SHA/alignment | v0.1.127.2.1 |


## v0.1.128 PB environment authority cleanup DoD

| ID | Requirement | Status | Evidence | Release |
|---|---|---|---|---|
| DOD-516 | Tracked control-surface accepted/current authority matches live FINAL_VERIFIED `v0.1.127.2.1` before new scope is packaged | construction_proven | plan-state/control-surface validation | v0.1.128 |
| DOD-517 | Artifact-current consumers use repository-loop projections only; no top-level legacy current fallback can become authority | construction_proven | focused current/parallel-ask/post-release tests | v0.1.128 |
| DOD-518 | Canonical and still-operational PB delegation is rooted in the exact active launcher Python plus repo-local CLI; PATH/PB-command selectors cannot become authority | construction_proven | poisoned-PATH + shell/helper regressions | v0.1.128 |
| DOD-519 | Hidden `--include-controlled-writes` is removed; controlled process/write exposure has one current flag and contract | construction_proven | CLI/MCP parser and manifest regressions | v0.1.128 |
| DOD-520 | Executable `legacy_10_75` Project Source mutation and its mutating diagnostics are absent; one current source-write transaction remains | construction_proven | source scan + current add/overwrite/persistence regressions | v0.1.128 |
| DOD-521 | External-library compatibility, browser resilience, and fail-closed historical-state detection are retained where they do not create alternate authority | construction_proven | dependency/browser/legacy-detection regressions | v0.1.128 |
| DOD-522 | Exact final ZIP is deterministic, hygiene-clean, passes every canonical construction group, and Artifact Guardian reports release-ready | construction_proven | exact ZIP + canonical groups + Guardian | v0.1.128 |
| DOD-523 | One fresh immutable v0.1.128 lifecycle from accepted/current v0.1.127.2.1 reaches FINAL_VERIFIED, independently verifies all reached states, and fresh scoped current aligns exactly | live_proven | canonical live release proof + independent FINAL_VERIFIED verify + fresh scoped current | v0.1.128 |


## v0.1.128.1 artifact single-authority repair DoD

| ID | Requirement | Status | Evidence | Release |
|---|---|---|---|---|
| DOD-524 | Every authoritative release identity `(repo_id, version)` binds to exactly one SHA-256 across release/adopt lifecycle kinds; conflicting bytes fail closed without registry mutation | construction_proven | artifact authority conflict/idempotence regressions | v0.1.128.1 |
| DOD-525 | Explicit artifact paths are terminal inputs: a missing `--local-path` fails immediately and no cwd/Downloads/same-name fallback may substitute bytes | construction_proven | explicit-path negative regression | v0.1.128.1 |
| DOD-526 | External ZIPs are verified imports into one PB-owned SHA-addressed project artifact object; subsequent registry/adoption operations use that immutable object | construction_proven | object import/SHA/path regressions | v0.1.128.1 |
| DOD-527 | Release-to-adopt is lifecycle state for one immutable object; registry cannot retain competing release/adopt records for the same repo/version and `current` selects adopted identity only | construction_proven | registry uniqueness/current regressions | v0.1.128.1 |
| DOD-528 | `artifact current --repo` verifies registry object existence/SHA and state/source projection agreement without hidden registry-to-state synthesis | construction_proven | current projection regressions | v0.1.128.1 |
| DOD-529 | `repo doctor` fails on multi-SHA release identity, duplicate logical identities, missing/tampered current object, non-PB object authority, or state projection conflict | construction_proven | doctor authority regressions | v0.1.128.1 |
| DOD-530 | Project Source remains publication evidence only and external repository version/runtime domains remain explicitly non-applicable where appropriate | construction_proven | source/current external-domain regressions | v0.1.128.1 |
| DOD-531 | One resumable operator command drives each canonical state and performs an independent all-state verify after every transition, then fresh scoped `artifact current`, using only the launcher Python and tracked repo identity | construction_proven | lifecycle-proof wrapper regression + source review | v0.1.128.1 |
| DOD-532 | Exact final v0.1.128.1 ZIP is deterministic, hygiene-clean, passes all canonical construction groups and Artifact Guardian | construction_proven | exact ZIP + canonical groups + Guardian | v0.1.128.1 |
| DOD-533 | Fresh controlled repository release→adopt→current→doctor flow passes, a deliberate second SHA for the same repo/version fails closed with current unchanged, and the v0.1.128.1 canonical PB lifecycle reaches independently verified FINAL_VERIFIED/current | live_pending | disposable authority proof + one-command canonical lifecycle proof | v0.1.128.1 |


## v0.1.128.1.1 repair DoD

| ID | Requirement | Status | Evidence | Release |
|---|---|---|---|---|
| DOD-534 | One-command lifecycle wrapper resumes directly from `BLOCKED_RETRYABLE` at the next legal transition without replaying/rejecting already-reached states | construction_proven | retry-resume wrapper regression | v0.1.128.1.1 |
| DOD-535 | Lifecycle wrapper emits live transition/subphase/ETA progress to stderr while stdout remains one final JSON object | construction_proven | wrapper stderr/stdout regression | v0.1.128.1.1 |
| DOD-536 | Candidate ask failure classification distinguishes exact-route timeout/failure from true route mismatch | construction_proven | state-machine classification regressions | v0.1.128.1.1 |
| DOD-537 | `ADOPTED_CURRENT` synchronizes tracked project control projection from authoritative adopted identity, and the one-command wrapper guarded-commits/pushes only known projection files with HEAD/upstream convergence | construction_proven | control synchronization + Git-backed publication regressions | v0.1.128.1.1 |
| DOD-538 | `project validate-control-surface` fails closed when tracked accepted/current or an already-adopted active candidate disagrees with authoritative project artifact registry | construction_proven | authoritative-current drift regressions | v0.1.128.1.1 |


## v0.1.128.1.1.1 projection-completeness repair DoD

| ID | Requirement | Status | Evidence | Release |
|---|---|---|---|---|
| DOD-539 | Post-adoption synchronization generically projects accepted/current, next-normal, and planned-after-next values into every dynamic document required by `project validate-control-surface` | construction_proven | synchronization→validation regression reproducing the `.128.1.1` live failure | v0.1.128.1.1.1 |
| DOD-540 | Synchronizer and guarded Git publication use one canonical `CONTROL_PROJECTION_PATHS` definition including `migration.md`; no independently maintained projection allowlist remains | construction_proven | canonical-path identity + Git guard regressions | v0.1.128.1.1.1 |
| DOD-541 | Exact final v0.1.128.1.1.1 ZIP is deterministic, hygiene-clean, passes all canonical construction groups and Artifact Guardian | construction_proven | exact ZIP + 17 canonical groups + Guardian | v0.1.128.1.1.1 |
| DOD-542 | Repair closes only when canonical lifecycle resumes from adopted/current `v0.1.128.1.1`, reaches independently verified `FINAL_VERIFIED`, publishes the complete control projection, and fresh scoped current remains exact | superseded_by_DOD_546 | live browser ask exposed fresh-response continuity defect before TESTED_GREEN | v0.1.128.1.1.1 |



## v0.1.128.1.1.1.1 fresh assistant-chain continuity repair DoD

| ID | Requirement | Status | Evidence | Release |
|---|---|---|---|---|
| DOD-543 | A post-submit assistant chain is latched as fresh only after confirmed submit, observed generation, and independent fresh-turn evidence such as count advance or baseline-different same/reduced-count replacement | construction_proven | response-freshness causal-latch regressions | v0.1.128.1.1.1.1 |
| DOD-544 | Once latched, same-visible-count streaming updates remain fresh when the final text becomes byte-identical to the historical baseline; baseline-identical text without the latch still fails closed | construction_proven | exact reproduced `Thinking → partial → INTEGRATION_OK` regression plus stale negative case | v0.1.128.1.1.1.1 |
| DOD-545 | The `.1.1.1` post-adoption projection-completeness repair remains unchanged and its synchronization→validation/canonical-projection regressions remain green in the exact new candidate | construction_proven | canonical project-control validation groups + exact ZIP proof | v0.1.128.1.1.1.1 |
| DOD-546 | Repair closes only when the exact immutable candidate passes canonical construction validation/Guardian and one canonical live lifecycle reaches independently verified `FINAL_VERIFIED`, publishes the complete control projection, and fresh scoped current is exact | live_pending | exact ZIP + one-command canonical lifecycle proof | v0.1.128.1.1.1.1 |

## v0.1.128.2 Promptbranch learning and skills completeness DoD

| ID | Requirement | Status | Evidence | Release |
|---|---|---|---|---|
| DOD-547 | A single canonical `promptbranch-learning` skill teaches the PB mental model, authority model, read-only quickstart, operator model, developer model, skills/tools, artifact authority, browser/conversation causality, release lifecycle, external-application boundary, exercises, and glossary | construction_proven | tracked curriculum + semantic source validator + focused tests | v0.1.128.2 |
| DOD-548 | A tracked `promptbranch-operator` skill provides the canonical read-first/fail-closed operator procedure while remaining risk `read` and granting no mutation/publication/release/adoption/deployment authority | construction_proven | skill registry/validation + operator bundle tests | v0.1.128.2 |
| DOD-549 | Humans, ChatGPT Projects, Claude/coding agents, generic coding agents, and PB-aware agents have explicit adapters into one shared PB contract rather than divergent audience-specific semantics | construction_proven | `LEARNING_PATH.md`, `PROJECT_SOURCE.md`, `AGENTS.md`, `CLAUDE.md`, `SKILL.md`/manifest audience matrix | v0.1.128.2 |
| DOD-550 | The portable `promptbranch-learning` bundle is self-contained, embedding all required learning materials plus related canonical PB skills needed for repo inspection, final-MVP inspection, application architecture proof, operator procedure, and tool authoring | construction_proven | deterministic bundle content regression | v0.1.128.2 |
| DOD-551 | `pb skill export` and `pb skill verify-bundle` canonically support learning, operator, and tool-authoring bundles; missing/extra/tampered content, unsafe ZIP paths, nondeterministic metadata, or authority escalation fail closed | construction_proven | export/verify/tamper/authority regressions | v0.1.128.2 |
| DOD-552 | A fresh human can discover the canonical learning entry point from README/how-to documentation and follow beginner → operator → developer exercises without undocumented tribal knowledge | construction_proven | `docs/howto/00-learn-promptbranch.md` + curriculum/exercises | v0.1.128.2 |
| DOD-553 | Exact final v0.1.128.2 ZIP is deterministic, hygiene-clean, passes every canonical construction group, and Artifact Guardian reports release-ready | construction_proven | exact ZIP + 17 canonical groups + deterministic rebuild + Guardian | v0.1.128.2 |
| DOD-554 | The learning-completeness release closes only after one canonical normal lifecycle from accepted/current v0.1.128.1.1.1.1.1 reaches independently verified FINAL_VERIFIED/current and advances the active normal slice to v0.1.129 | live_pending | canonical lifecycle + post-adoption control projection | v0.1.128.2 |

## v0.1.128.2.1 Release smoke timeout auto-recovery DoD

| ID | Requirement | Status | Proof | Release |
|---|---|---|---|---|
| DOD-555 | Canonical release `ask_question` and `task_message_flow.ask` absorb supported transient service/assistant-response timeouts inside the original test/lifecycle invocation; no operator retry/fix command is part of the normal path | construction_proven | resilient release-smoke wrapper + integration regression | v0.1.128.2.1 |
| DOD-556 | After a transient timeout, recovery observes the correlated conversation first and reuses an already-completed expected token without resubmitting; new-project task/message recovery can discover the correlated conversation from the unique prompt | construction_proven | pinned-backend and new-project discovery regressions | v0.1.128.2.1 |
| DOD-557 | Recovery is bounded and auditable: default maximum three attempts, 90-second per-attempt budget, attempt/recovery evidence retained in `promptbranch.release_ask_recovery` | construction_proven | focused harness tests + canonical browser group | v0.1.128.2.1 |
| DOD-558 | Authentication/challenge, 429/cooldown, permission, exact-route mismatch, and ambiguous submit-causality failures remain non-retryable and fail closed | construction_proven | rate-limit/route regressions + classifier contract | v0.1.128.2.1 |
| DOD-559 | v0.1.128.2 learning/operator skill contents and portable bundle authority semantics remain unchanged while timeout recovery is release-test-specific | construction_proven | learning/tool-authoring suites + scope review | v0.1.128.2.1 |
| DOD-560 | The exact v0.1.128.2.1 artifact closes only after deterministic construction/Guardian and one initial canonical repair lifecycle reaches independently verified FINAL_VERIFIED/current without operator retry commands, advancing next normal to v0.1.129 | live_pending | exact ZIP + canonical lifecycle + post-adoption control projection | v0.1.128.2.1 |

## v0.1.128.2.2 Accepted-runtime baseline auto-reconciliation DoD

| ID | Requirement | Status | Proof | Release |
|---|---|---|---|---|
| DOD-561 | `RUNTIME_PREPARED` automatically reconciles an absent, unhealthy, or wrong-version authoritative service from the exact repository-scoped adopted/current artifact before candidate mutation | construction_proven | release-state-machine reconciliation regressions | v0.1.128.2.2 |
| DOD-562 | Reconciliation proves adopted kind, repo identity, baseline version, registry SHA, ZIP integrity, artifact SHA, and embedded VERSION before rebuilding port 8000; candidate bytes cannot be used as baseline authority | construction_proven | authority resolver + fail-closed tests | v0.1.128.2.2 |
| DOD-563 | After reconstruction, Promptbranch verifies one healthy port-8000 container at the exact baseline and exact adopted artifact SHA before isolated candidate preparation continues | construction_proven | reconciliation exact-check contract | v0.1.128.2.2 |
| DOD-564 | v0.1.128.2 learning/operator skills and v0.1.128.2.1 release-smoke timeout recovery remain unchanged while accepted-runtime reconciliation is added as operational resilience | construction_proven | learning/browser/release regression groups | v0.1.128.2.2 |
| DOD-565 | The exact v0.1.128.2.2 artifact closes only after one initial canonical repair lifecycle reaches independently verified FINAL_VERIFIED/current without operator baseline-repair or timeout-retry commands and advances next normal to v0.1.129 | live_pending | exact ZIP + live canonical lifecycle + post-adoption control projection | v0.1.128.2.2 |


## v0.1.128.2.3 Project-scoped baseline registry authority DoD

| ID | Requirement | Status | Evidence | Release |
|---|---|---|---|---|
| DOD-566 | Accepted-baseline recovery resolves `.promptbranch-repo.json`, proves repo/project binding, and reads adopted/current only from `project_registry_dir(project_id)`; browser/session `profile_dir` is never artifact authority | construction_proven | release-state-machine authority resolver + regression with absent profile registry | v0.1.128.2.3 |
| DOD-567 | Recovery verifies configured repo root, adopted kind, repo identity, baseline version, registry SHA, ZIP integrity, artifact SHA, and embedded VERSION before any baseline runtime mutation; ambiguity remains fail-closed | construction_proven | project registry + artifact authority regressions | v0.1.128.2.3 |
| DOD-568 | v0.1.128.2 learning/operator skills, v0.1.128.2.1 automatic smoke-timeout recovery, and v0.1.128.2.2 accepted-runtime reconstruction remain intact while registry namespace selection is corrected | construction_proven | canonical learning/browser/state-machine/release groups | v0.1.128.2.3 |
| DOD-569 | The exact v0.1.128.2.3 artifact closes only after one initial canonical repair lifecycle reaches independently verified FINAL_VERIFIED/current without operator baseline-registry, runtime-repair, or timeout-retry commands and advances next normal to v0.1.129 | live_pending | exact ZIP + live canonical lifecycle + post-adoption projection | v0.1.128.2.3 |


## v0.1.128.2.4 Accepted-baseline exact-byte self-healing DoD

| ID | Requirement | Status | Evidence | Release |
|---|---|---|---|---|
| DOD-570 | Accepted/current logical authority is exact repo + version + SHA from the canonical project registry; physical record path is not itself authority | construction_proven | baseline authority resolver + project-registry regressions | v0.1.128.2.4 |
| DOD-571 | Missing/corrupt accepted object bytes are recovered only from bounded canonical/PB/local cache candidates whose ZIP integrity, exact registered SHA, and embedded VERSION all verify; wrong-SHA copies are ignored | construction_proven | missing-object recovery + wrong-SHA fail-closed regressions | v0.1.128.2.4 |
| DOD-572 | Exact recovered bytes restore the canonical SHA-addressed project object; accepted immutable bytes are checked for integrity without retroactively applying newer candidate hygiene policy | construction_proven | canonical-object restoration + historical-integrity regression | v0.1.128.2.4 |
| DOD-573 | The exact v0.1.128.2.4 artifact closes only after one initial canonical repair lifecycle reaches independently verified FINAL_VERIFIED/current with no operator baseline-byte, registry, runtime, or timeout repair commands and advances next normal to v0.1.129 | live_pending | exact ZIP + live canonical lifecycle + post-adoption projection | v0.1.128.2.4 |


## v0.1.128.2.5 Authoritative baseline auto-resolution DoD

| ID | Requirement | Status | Evidence | Release |
|---|---|---|---|---|
| DOD-574 | Fresh canonical lifecycle resolves baseline from tracked repo identity plus project-scoped adopted/current authority; operators do not provide baseline bookkeeping | construction_proven | lifecycle launcher resolver + authoritative-current regression | v0.1.128.2.5 |
| DOD-575 | Durable retries reuse the attempt-bound baseline even after adoption changes current; explicit baseline is assertion-only and mismatch fails closed | construction_proven | retry-bound and stale-assertion regressions | v0.1.128.2.5 |
| DOD-576 | v0.1.128.2 learning/skills, smoke-timeout recovery, accepted-runtime reconstruction, project registry authority, and exact-byte recovery remain intact | construction_proven | canonical learning/browser/state-machine/artifact groups | v0.1.128.2.5 |
| DOD-577 | Exact v0.1.128.2.5 closes after one canonical lifecycle with no baseline-version argument reaches FINAL_VERIFIED/current and advances next normal to v0.1.129 | live_pending | exact ZIP + live canonical lifecycle + post-adoption projection | v0.1.128.2.5 |

## v0.1.128.2.6 External-repository skill sync and publication-resume DoD

| ID | Requirement | Status | Evidence | Release |
|---|---|---|---|---|
| DOD-578 | `pb skill sync` resolves Promptbranch source authority only from the source repo's tracked Project identity plus exact adopted/current artifact; an in-development PB worktree is never the skill source of truth | construction_proven | source-authority and SHA/version regressions | v0.1.128.2.6 |
| DOD-579 | Sync exports and verifies portable learning/operator/tool-authoring bundles from exact accepted bytes, stages them, atomically replaces requested external-repo skills with rollback, writes deterministic provenance, and validates the target | construction_proven | skill-sync functional/idempotency/rollback tests | v0.1.128.2.6 |
| DOD-580 | Skill sync never implicitly commits or pushes the target repository and reports the resulting `.promptbranch` Git diff/status for operator review | construction_proven | skill-sync Git-safety regression | v0.1.128.2.6 |
| DOD-581 | Publication subprocess timeout emits structured retryable evidence rather than empty stdout/parser crash; the canonical lifecycle wrapper retries a bounded publication timeout inside the same invocation | construction_proven | publication-timeout + wrapper retry regressions | v0.1.128.2.6 |
| DOD-582 | Exact v0.1.128.2.6 closes only after canonical full/live lifecycle reaches FINAL_VERIFIED/current and preserves v0.1.129 as the next normal slice | superseded_by_DOD-583 | historical v0.1.128.2.6 is already SHA-bound to 4ac66b37cba7b367... and finalized replacement bytes correctly fail artifact_identity_conflict | v0.1.128.2.6 |


## v0.1.128.2.6.1 Immutable successor DoD

| ID | Requirement | Status | Evidence | Version |
|---|---|---|---|---|
| DOD-583 | Preserve historical `v0.1.128.2.6` / `4ac66b37cba7b3676d487f082e9fe64239fd97b71f53b10f66b28b67fe1cf026` attempt unchanged; exact `v0.1.128.2.6.1` bytes must have a distinct deterministic SHA and carry the construction-proven DOD-578 through DOD-581 behavior without normal-scope advancement | construction_proven | 134 focused tests; verified pytest 9.0.2 runner; all 17 canonical constituent validation groups green; byte-identical rebuild; canonical Artifact Guardian pass | v0.1.128.2.6.1 |
| DOD-584 | Exact `v0.1.128.2.6.1` closes only after canonical full/live lifecycle reaches `FINAL_VERIFIED`, independent `release verify --all-states` succeeds, and fresh scoped `pb artifact current --repo chatgpt_claudecode_workflow-2 --json` aligns runtime/state/source/registry | live_pending | canonical lifecycle + post-adoption current proof | v0.1.128.2.6.1 |
| DOD-585 | Installed-package metadata/import proof must validate the exact candidate ZIP, including `promptbranch_skill_sync`, before acceptance | live_proven_predecessor | exact `v0.1.128.2.6.1.1` candidate package metadata/import smoke passed before later structural failure | v0.1.128.2.6.1.1 |
| DOD-586 | Portable-skill and current control-surface tests derive mutable release identity from root `VERSION`, and the exact final successor ZIP is validated against every nodeid in the application architecture structural group from a clean extraction | construction_proven | Exact clean-extraction structural coverage is 62/62 nodeids green (29 application architecture, 14 migration, 8 tool-authoring, 7 learning, 4 skill-sync) using pytest 9.0.2 with ambient plugin autoload disabled. The artifact container could not retain the one-process aggregate long enough for a summary, so canonical host lifecycle must still rerun the normal single structural group. | v0.1.128.2.6.1.1.1 |
| DOD-587 | Exact `v0.1.128.2.6.1.1.1` closes only after canonical lifecycle reaches `FINAL_VERIFIED`, independent all-state verification is green, and fresh scoped artifact-current alignment succeeds | live_pending | canonical lifecycle + post-adoption current proof | v0.1.128.2.6.1.1.1 |

