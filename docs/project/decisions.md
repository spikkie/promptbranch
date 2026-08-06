# Durable decisions

## ADR-PROJ-12324 — Artifact execution precedes release-candidate envelope success

For `v0.1.123.2.4`, `ask-release` must instruct ChatGPT to create a fresh ZIP from the exact accepted/current artifact, attach it to the exact answer, and only then emit `status=completed`. A JSON filename, textual `sandbox:` path, or unsupported existence claim is not materialization evidence. Failure to physically create and attach must produce `status=failed`, `result_type=release_candidate`, and `artifacts=[]`. This repair preserves `v0.1.124` and `v0.1.125` as the next normal proof cycles.

## ADR-PROJ-109.1 — Behavioral surface ownership

`v0.1.109.1` defines `docs/project/promptbranch-behavioral-surface-v0.1.109.1.json` as the stable inventory for executable instructions, skills/agents, tools, and prompts. Validation is read-only and fail-closed. File-backed skills are authoritative when present; embedded skill documents are projections. The next planned normal slice remains `v0.1.110 — Authority-backed project snapshot and drift report`.
# Decisions

| ID | Date | Decision | Reason | Consequence |
|---|---|---|---|---|
| ADR-PROJ-001 | 2026-06-10 | Adopt `docs/project/` as the canonical continuation control surface | MVP, DoD, plan, status, release state, decisions, and migration evidence were scattered across multiple historical documents | Future slices and ZIP responses must refer to `docs/project/` |
| ADR-PROJ-002 | 2026-06-10 | Treat accepted `pb artifact current --json` evidence as baseline authority | Older documents contain stale baseline references from prior lines | Current accepted baseline is v0.1.66 until v0.1.67 adoption evidence exists |
| ADR-PROJ-003 | 2026-06-10 | Preserve historical planning/status documents during migration | Old documents contain durable decisions, context, and release evidence | `docs/project/migration.md` records mappings instead of deleting or rewriting old docs |
| ADR-PROJ-004 | 2026-06-10 | Keep v0.1.67 documentation-only except release metadata and focused validator | The slice is intended to create a control surface without widening behavior | Runtime, deployment, source mutation, adoption, and lifecycle automation remain out of scope |
| ADR-PROJ-005 | 2026-06-10 | Require focused control-surface validation before packaging | Prompt-only enforcement is insufficient | `tests/test_project_control_surface.py` guards required files/tables/headings |
| ADR-PROJ-006 | 2026-06-10 | Add browser-idle barrier after successful Project Source mutations | my_awx 0.0.199 showed adoption/source-list verification can race the shared browser profile after `pb src add` | v0.1.69 adds `pb browser wait-idle`, automatic post-source-add wait, and structured busy retry guidance |
| ADR-PROJ-007 | 2026-06-10 | Scope artifact current-state by repo id | Multi-repo ChatGPT Projects need independent accepted baselines per repository; global current state can silently point future work at the wrong repo | v0.1.70 adds `repo_id`, repo-scoped state, `pb artifact current --repo`, `pb artifact current --all`, and ambiguous unscoped-current failure |
| ADR-PROJ-008 | 2026-06-10 | Explicit missing repo artifact-current lookups must fail closed | v0.1.70 field testing showed `pb artifact current --repo <missing>` could combine a requested repo id with another repo's legacy/current state | v0.1.70.1 returns `repo_current_not_found` with `state=null` and does not advance the release line |
| ADR-PROJ-009 | 2026-06-10 | Remove remembered coordinator/main repo from multi-repo workflows | Multi-developer use cannot rely on operators remembering which repo owns the combined `.pb_profile` | v0.1.71 adds `.promptbranch-repo.json`, user-local project registry resolution, `pb project join/status`, and `pb repo list/doctor` so any joined repo resolves the same project registry |
| ADR-PROJ-010 | 2026-06-10 | Default-resolved profile dirs must not disable project registry resolution | v0.1.71 field testing showed a split truth: repo diagnostics used the project registry while artifact-current could read the repo-local `.pb_profile` | v0.1.71.1 tracks explicit `--profile-dir`, creates the project registry during join, and keeps default joined-repo commands on project-scoped state |
| ADR-PROJ-011 | 2026-06-10 | Required root files must be preserved in repair ZIP packaging | v0.1.71.1 failed install ZIP import guard because `.gitignore` was missing | v0.1.71.2 restores `.gitignore` and treats root-file completeness as release-blocking |
| ADR-PROJ-013 | 2026-06-11 | Normalize service health versions in release-control Docker wait gate | v0.1.71.3 returned healthy service JSON with canonical `v0.1.71.3` while the lifecycle expected bare `0.1.71.3` | v0.1.71.4 compares normalized versions and prefers `package_version` when present |
| ADR-PROJ-014 | 2026-06-11 | Keep `VERSION_TAG` canonical and prevent double `v` prefixes | v0.1.71.4 full-test import smoke observed `promptbranch_version.VERSION_TAG=vv0.1.71.4` while other surfaces normalized correctly | v0.1.71.5 computes `VERSION_TAG` through `version_tag()` and adds regression coverage against `vv0.1.71.5` |
| ADR-PROJ-015 | 2026-06-11 | Make legacy-to-project registry migration explicit and dry-run capable | Existing repo-local `.pb_profile/promptbranch_artifacts.json` state should not be manually copied or automatically adopted during join | v0.1.72 adds `pb project import-current-registry` with dry-run, conflict diagnostics, and explicit replace semantics |
| ADR-PROJ-016 | 2026-06-11 | Standardize Promptbranch artifact filenames as `<repo_id>_<version>.zip` with v-prefixed versions | Multi-repo adoption failed when historical repos used mixed separators and version prefixes | v0.1.73 enforces canonical adopt names, normalizes internal bare versions, adds `--local-only`, and documents copy-to-canonical migration |
| ADR-PROJ-017 | 2026-06-11 | Treat canonical adoption diagnostics as a repair to v0.1.73, not a new normal slice | Field testing proved the v0.1.73 feature but exposed JSON semantics and hygiene diagnostic defects | v0.1.73.1 repairs local-only source verification reporting, external repo current-state relation fields, local-artifact-not-found diagnostics, and `.promptbranch-repo.json` ZIP hygiene without advancing scope |
| ADR-PROJ-018 | 2026-06-11 | Supersede v0.1.73.2 instead of adopting it | v0.1.73.2 repaired JSON/reporting regressions but failed release-control with browser_profile_busy | v0.1.73.3 rebuilds from accepted/current v0.1.73.1 and carries forward only the validated repair intent |
| ADR-PROJ-019 | 2026-06-11 | Enforce universal browser-operation scheduler coverage for source/project lifecycle paths | Full release-control can run list/add/remove/cleanup against the same browser profile and must not rely on ad-hoc retry/timeout behavior | Source/project remove and cleanup paths use scheduler-aware waits and expose scheduler diagnostics |


| ADR-026 | 2026-06-12 | Isolate scheduler lifecycle-plan tests from ambient profile state | Synthetic plan tests must not depend on the operator repo `.pb_profile` current baseline | v0.1.73.4 changes test setup only and preserves production reconciliation behavior |
| ADR-PROJ-027 | 2026-06-12 | Make release-validation groups explicit in full-test/report evidence | v0.1.73.x repairs showed focused JSON-contract and scheduler tests could be run manually outside the normal release path | v0.1.74 adds a validation matrix, full-test release-validation group execution, report fields, and release-control summary enforcement |
| ADR-PROJ-028 | 2026-06-12 | Release-validation groups must run with repo/operator Python, not the installed Promptbranch runtime interpreter | `v0.1.74` release-control showed pipx runtime Python lacked pytest | v0.1.74.1 defaults release-validation commands to `python3` and supports `PROMPTBRANCH_RELEASE_VALIDATION_PYTHON` override |
| ADR-PROJ-029 | 2026-06-12 | Synthetic release-lifecycle plan tests must use isolated Promptbranch profiles | `v0.1.74.1` release-control showed plan tests could read ambient operator artifact state | v0.1.74.2 adds explicit `profile_dir` isolation to those tests without changing production reconciliation behavior |
| ADR-PROJ-030 | 2026-06-12 | Full integration source mutation waits must use the scheduler wait budget | `v0.1.74.2` release-control showed `project_source_remove_text` timed out at 120s while `add_project_source` still held the shared profile under scheduler control | v0.1.74.3 aligns the full integration source-mutation wait with the universal browser-operation scheduler default and allows environment override |

| ADR-PROJ-031 | 2026-06-13 | Use one repo-loop management model for one repo or many repos | KISS: project management commands should not have different operator semantics for one repo versus multiple repos | v0.1.75 makes joined-project `pb artifact current --json` use the same repo-loop payload as `--all`, with `--repo` as a filter |

| ADR-PROJ-032 | 2026-06-13 | Operator/release consumers must read artifact-current through the repo-loop model | v0.1.75 changed the producer shape, but release-control/post-release checks still contained old top-level `state` assumptions | v0.1.76 updates release consumers and keeps legacy top-level parsing only as compatibility fallback |

| ADR-PROJ-033 | 2026-06-14 | Confine artifact-current legacy top-level parsing to explicit compatibility paths | v0.1.75/v0.1.76 completed producer and core release consumers, but helper paths still needed a clear migration boundary | v0.1.77 adds normalized section selection, focused repo-loop/legacy fallback tests, and operator migration guidance |

| ADR-PROJ-034 | 2026-06-14 | Treat remove-project sidebar-not-found as success only after explicit absence verification | Old cleanup behavior could hide leaked temporary test projects by classifying sidebar-not-found as idempotent success | v0.1.77.1 makes cleanup fail unless `resolve_project` confirms zero matches and adds project-create disabled-submit hardening |

| ADR-PROJ-035 | 2026-06-14 | Retry cleanup when sidebar-not-found is not absence-verified and isolate release-validation subprocesses from ambient pytest plugins | v0.1.77.1 proved the project can still exist after a sidebar-not-found cleanup response, and one release-validation group timed out without diagnostic output | v0.1.77.2 retargets cleanup to the exact resolved project URL when available, retries before failing, verifies successful cleanup when a project name is known, and disables ambient pytest plugin autoload in release-validation groups |

| ADR-PROJ-036 | 2026-06-14 | Search the More-projects surface before failing project cleanup when exact-name resolve proves the temporary project is still present | v0.1.77.2 proved fail-closed cleanup but still could not remove a resolvable test project from the normal sidebar path | v0.1.77.3 widens only the cleanup discovery path while preserving fail-closed cleanup semantics |

| ADR-PROJ-037 | 2026-06-15 | Make temporary-project cleanup rate-limit-aware before failing | v0.1.77.3 failed after ChatGPT 429/modal pressure left an exact-name project resolvable but not removable through the normal path | Cleanup retry delay now reads nested rate-limit telemetry and uses extended attempts; no normal slice advanced |

| ADR-PROJ-038 | 2026-06-15 | Treat missing required root `.gitignore` in v0.1.77.4 as a repair-only packaging defect | Release-control import validation blocks install before tests when required root files are absent | v0.1.77.5 restores `.gitignore`; no normal slice advances |

| ADR-PROJ-039 | 2026-06-15 | Add project-page generic delete-menu fallback and bound scheduler validation timeout | v0.1.77.5 still failed cleanup because the temporary project was exact-name resolvable but the sidebar removal path could not find it; the scheduler validation timeout also cost 600 seconds after browser failure | v0.1.77.6 widens project-page delete-menu selectors and caps `browser_scheduler_source_lifecycle` validation timeout at 120 seconds without changing release/adoption semantics |

| ADR-PROJ-040 | 2026-06-15 | Pass resolved project URL explicitly during cleanup retry | v0.1.77.6 still failed cleanup because the exact temporary project was resolvable but remove_project retried without sending the resolved `project_url` to the service client | v0.1.77.7 keeps fail-closed cleanup but retargets the actual remove/resolve requests to the exact resolved project URL; no normal slice advances |

| ADR-PROJ-041 | 2026-06-15 | Docker-service cleanup adapters must accept explicit per-call project URLs | v0.1.77.7 still failed cleanup because the exact resolved project URL was discovered, but the Docker-service adapter remove/resolve methods did not accept that URL as a request argument | v0.1.77.8 forwards per-call project_url through Docker-service cleanup calls; no normal slice advances |
| ADR-PROJ-042 | 2026-06-15 | Source-save stale inflight is not enough for success; cleanup must forward project name with exact URL | v0.1.77.8 showed a text source save commit with one stale inflight request and cleanup still could not remove an exact-name-resolvable temporary project | v0.1.77.9 allows stale-inflight only as a soft boundary before post-refresh persistence verification and forwards `project_name` plus exact `project_url` through Docker/service/browser cleanup paths; no normal slice advances |
| ADR-PROJ-043 | 2026-06-15 | Release-control must pin the Docker service image to the release-derived version by default | v0.1.77.9 failed because service version verification kept seeing stale `0.1.77.8` after rebuilds | v0.1.77.10 exports `PROMPTBRANCH_SERVICE_IMAGE=promptbranch-service:<release>` for release-control/service scripts unless explicit override is enabled |
| ADR-PROJ-044 | 2026-06-15 | Project cleanup must search name-matched non-anchor project rows before failing | v0.1.77.10 proved the exact temporary project was still resolvable by name while anchor/sidebar lookup could not remove it | v0.1.77.11 widens cleanup lookup to non-anchor sidebar/menu rows and remains fail-closed |


| ADR-PROJ-045 | 2026-06-16 | Artifact Guardian policy source is `.artifact-guardian.yml` | Missing required root files such as `.gitignore` caused late lifecycle failures after operator download/install started | v0.1.78 adds `pb artifact guard` as deterministic policy-driven ZIP structure validation; guard passed remains candidate evidence only, not accepted/current |
| ADR-PROJ-046 | 2026-06-16 | Put Artifact Guardian AG-001 before the k8s-game foundation slice | Future k8s-game foundation releases should benefit from a structural artifact guard first | v0.1.78 is AG-001; k8s-game foundation moves to v0.1.79 |

| ADR-PROJ-047 | 2026-06-16 | Project Source mutation must expose explicit transaction states and fail-step reporting | v0.1.78 release-control failed with file source `persistence_not_verified`, commit evidence, stale inflight, and weak failure summary visibility | v0.1.78.1 classifies commit-seen/not-visible states as release-blocking ambiguous transactions, extends file-source post-commit readback, and records returned `{ok:false}` steps as failed immediately |

| ADR-PROJ-048 | 2026-06-16 | Freeze public ChatGPT Project deletion until secure protocol exists | v0.1.78.1 live-log evidence showed Promptbranch can execute real ChatGPT project deletion; even test-project deletion is too dangerous on the real profile | v0.1.78.2 returns canonical `project_delete_disabled` payloads before service/browser execution and treats cleanup as intentionally retained instead of deleting projects |

| ADR-PROJ-049 | 2026-06-16 | Top-level helper modules must be included in setuptools py-modules | v0.1.78.2 release-control failed with ModuleNotFoundError for `promptbranch_project_delete_safety` after pipx install | v0.1.78.2.1 adds the helper to `pyproject.toml` and keeps project deletion frozen |

| ADR-PROJ-050 | 2026-06-16 | Release tooling must accept multi-segment repair versions | `v0.1.78.2.1` was rejected by the candidate release-control validator even though Promptbranch already uses nested repair versions during emergency repair lines | `v0.1.78.2.2` changes release-control, post-release validation, and artifact-candidate schema version grammar to dotted numeric versions with at least three segments |
| ADR-PROJ-051 | 2026-06-16 | Release-control full tests must reuse a retained quarantine project while project deletion is frozen | v0.1.78.2.2 succeeded but left a unique `itest-promptbranch-<run-id>` project because deletion is intentionally disabled | v0.1.78.2.3 passes `--project-name itest-promptbranch-retained-delete-frozen --keep-project` by default from release-control; existing leaked projects are left untouched until a secure delete protocol exists |


| ADR-PROJ-052 | 2026-06-17 | Delete-frozen live tests use one retained quarantine project and full operator validation runs through one continue-on-failure release-control option | Project deletion is frozen, so live test defaults must not create disposable projects that require deletion; operators also need one command instead of many manual validation steps | `ask-live`, `visual-artifact-roundtrip`, and `release-live` default to `itest-promptbranch-retained-delete-frozen`; release-control `--run-all-tests` emits a final GO/FIX JSON report |

## Decision — v0.1.78.2.6 Docker provenance over always-no-cache

Promptbranch should not default every release build to `docker compose build --no-cache`. Instead, release-control must verify host build context, built image content, running container content, and `/healthz` version alignment. A no-cache rebuild is permitted as a single fallback when the normal cached build produces stale or unverifiable content.


## Decision — v0.1.78.2.7 repair probe syntax, not provenance policy

The Docker provenance policy from v0.1.78.2.6 remains correct. v0.1.78.2.7 changes only the broken embedded Python JSON-writer syntax that prevented provenance evidence from being emitted.


## Decision — Docker provenance probes must avoid fragile nested shell/Python quoting

For v0.1.78.2.8, Docker image/container pyproject version extraction uses a shell-safe reader instead of nested inline Python with quoted file paths. This keeps the Docker provenance guard useful while reducing release-control failure risk from quoting syntax errors.


## Decision — Docker provenance pyproject probes must avoid awk `$2` under `set -u`

The v0.1.78.2.8 Docker container-content probe failed because an awk expression containing `$2` was evaluated by the shell under `set -u`, causing `parameter not set`. v0.1.78.2.9 replaces that reader with a `grep | head | cut` pipeline that avoids shell positional parameters while preserving the Docker provenance policy.

## Decision — v0.1.78.2.11 live seed profiles are local state, pool slots are disposable

Release-control must preserve `.pb_profile_local_debug/` across install because it is an operator-authenticated live-test seed. It must not preserve `.pb_profile_local_debug_pools/`, because pool slots are generated clones that should be refreshed for each run. Run-all rate-limit retry detection must rely on strict 429 / "Too many requests" evidence instead of broad rate-limit wording.

## Decision — v0.1.78.2.12 text-source save trigger must be observed before persistence wait

The text Project Source add path can fail with `ui_trigger_not_observed_not_verified_present` even when the current ChatGPT UI advertises `Text input` as supported. Release validation must not wait only for eventual persistence after a no-op primary click. The text-source helper now verifies that a save request was observed after the primary click and uses bounded fallback triggers before handing control to persistence verification.


| ADR-PROJ-061 | 2026-06-19 | Project Source verification must not wait on conversation-history cooldown | Live service logs showed source upload/commit and final verification succeeded, but the CLI timed out while browser automation slept on a persisted conversation-history 429 cooldown | Project Source operations still acknowledge modals and record cooldown telemetry, but their persistence refresh path skips the persisted conversation-history cooldown; history operations continue to respect it |

| ADR-PROJ-062 | 2026-06-20 | `pb ask --prompt-file` must carry prompt-file origin as submit policy, not only merged prompt text | Prompt-file live calls are automation-critical and observed keyboard Enter dispatch can stop at prepare-token-only without backend commit | `v0.1.78.2.17` forwards `prefer_button_submit` through CLI/service/API/browser layers, prefers send-button click for prompt-file asks, and keeps prepare-token-only as a hard submit failure with diagnostics |

| ADR-PROJ-063 | 2026-06-20 | Prompt-file live-smoke failures must preserve the raw submit payload | `v0.1.78.2.17` smoke used `set -e` and trap cleanup, so a non-zero `pb ask` deleted the diagnostic JSON before validation could print it | `v0.1.78.2.18` captures the `pb ask` exit code, keeps JSON on failure, prints its path, and keeps prompt-file button-submit fail-closed without keyboard Enter after a successful button dispatch |
| ADR-PROJ-064 | 2026-06-20 | Prompt-file submit-policy flags must be accepted at every wrapper boundary | `v0.1.78.2.18` carried `prefer_button_submit` through the service path but the intermediate automation wrapper still rejected the keyword before the browser layer | `v0.1.78.2.19` adds wrapper signature/forwarding coverage so `pb ask --prompt-file` can reach button-first browser submit instead of HTTP 500 |
| ADR-PROJ-065 | 2026-06-20 | `pb ask --json` prompt-file smoke must validate the structured answer contract, not a raw string-only answer | The live `v0.1.78.2.19` smoke proved button-click submit and freshness, but failed because the harness compared the whole structured answer object/string rendering to the token | `v0.1.78.2.20` treats `answer.token == CV_LIVE_PROMPT_FILE_OK` as the exact-token proof for JSON-mode asks and flattens successful submit evidence onto the top-level ask JSON envelope |
| ADR-PROJ-066 | 2026-06-20 | Full release-control may adopt after validation through an explicit guarded flag | Operators need one deterministic command for validate-then-adopt after focused smoke passes; `--adopt-if-green` remains tests-only and `--adopt-current` remains explicit adoption-only | `v0.1.78.2.20.1` adds `--adopt-after-validation` for full `--run-tests`/`--run-all-tests` workflows and refuses unsafe combinations such as `--skip-tests`, `--tests-only`, `--adopt-current`, and `--run-failing-tests` |

| ADR-PROJ-067 | 2026-06-20 | Large `pb ask --prompt-file` packages should use automated attachment-mode transport instead of huge composer text by default | The CV RAG prompt package proved button-click submit but failed committed-turn proof because the large prompt became a pasted/document-style user turn without reliable exact-marker binding | `v0.1.78.2.20.2` adds `--prompt-file-mode` and defaults auto mode to attach prompt files at or above 12,000 UTF-8 bytes; small prompt files keep inline behavior |
| ADR-PROJ-068 | 2026-06-20 | Large prompt-file attachment mode must expose stable top-level diagnostics | `v0.1.78.2.20.2` proved the large CV prompt can succeed through attachment mode, but required evidence such as attachment upload/readiness, submit causality, and response causality remained nested or null at the top level | `v0.1.78.2.20.3` flattens attachment/upload/submit/response diagnostics while preserving the working attachment transport path |
| ADR-PROJ-069 | 2026-06-20 | Project Source text-add validation must prove document-converted text by current-run content, not generic `pasted.txt` identity | ChatGPT can render pasted text as a `.txt` document source, and retained test projects can already contain stale `pasted.txt Document` cards | `v0.1.78.2.20.4` uses a large run-id-bearing text source in the live test, adds first-line `.txt` document candidates, rejects generic stale document cards without run-id proof, and prunes only safe retained-test sources at the observed source-capacity boundary |
| ADR-PROJ-070 | 2026-06-20 | Generic document-converted text source cards are not sufficient proof without a current-run anchor | `v0.1.78.2.20.4` proved save/persistence but accepted `pasted.txt Document` with `source_content_match_verified=false`; the UI may also generate dedicated names instead of the old generic name | `v0.1.78.2.20.5` fails generic `pasted.txt` / `Document` conversion without current-run proof, while allowing generated/dedicated names when the visible identity carries the run anchor |
| ADR-PROJ-071 | 2026-06-20 | Legacy `pasted.txt` text-source identities are cleanup noise, not current success proof | Operator UI observation clarified that current large pasted text conversion generates dedicated document names; building automation around `pasted.txt` would preserve stale behavior | `v0.1.78.2.20.6` removes `pasted.txt` fallback persistence matching for current text-source adds and requires a dedicated/generated document name with the current run anchor |

| ADR-PROJ-072 | 2026-06-20 | Project Sources text-add persistence is the release gate; large-paste document naming is characterization | Focused `.20.6` evidence showed persistence verified and a visible source card, but the Project Sources surface still exposed `pasted.txt Document` rather than a dedicated generated name | `v0.1.78.2.20.7` stops making dedicated document naming release-blocking, keeps generic document identity/content-proof diagnostics, and makes the full integration text-add input below the conversion threshold |
| ADR-PROJ-073 | 2026-06-20 | Fresh integration projects may be removed only by strict same-run ephemeral cleanup | Fresh `.20.7` evidence showed source-add succeeds on a newly created project, but cleanup did not run and broad project deletion remains unsafe | `v0.1.78.2.20.8` allows deletion only when the run proves the project was created in the same integration run, the name starts with `itest-promptbranch-`, and project identity matches; all other project deletion remains frozen |
| ADR-PROJ-074 | 2026-06-20 | Release transport ZIPs must preserve required root control files | `.20.8` import planning failed because the ZIP omitted `.gitignore` although the worktree had it | `.20.8.1` is a packaging-only repair that preserves `.gitignore` and `.not_to_zip` at ZIP root; future ZIP validation must check required root files before handoff |

| ADR-PROJ-075 | 2026-06-20 | Ephemeral cleanup removal must normalize exact same-run project URLs before browser navigation | `.20.8.1` proved source-add and expected-missing classification but failed cleanup because `_normalize_project_url` was missing in the browser remove path | `.20.8.2` restores project URL normalization for cleanup targets while preserving strict same-run ephemeral guards and leaving source-add behavior unchanged |

| ADR-PROJ-076 | 2026-06-20 | Same-run cleanup identity is the stable Project id, not the visible slug route | `.20.8.2` retargeted cleanup from a bare Project URL to a slugged route and then failed the strict guard with `project_id_mismatch`; text-source saves could also observe a commit with stale inflight state without post-commit recovery | `.20.8.3` canonicalizes slugged same-run `itest-promptbranch-*` route ids before cleanup validation and extends bounded post-commit Project Source recovery/readback to text-source saves while keeping source-add semantics and broad deletion freeze unchanged |

| ADR-PROJ-077 | 2026-06-20 | ChatGPT Project deletion is never allowed by Promptbranch automation | `v0.1.78.2.20.8.3` reintroduced a same-run ephemeral cleanup delete path and an operator reported the real ChatGPT Project was gone after focused source-add validation | `v0.1.78.2.20.8.4` removes the exception. API, service, browser, private browser operation, and full-integration cleanup all return/delete-frozen retained-project results. Same-run identity fields are diagnostics only and cannot authorize deletion. |
| ADR-PROJ-078 | 2026-06-20 | Project deletion evidence labels must not use stale cleanup terminology | `v0.1.78.2.20.8.4` enforced the no-delete invariant but fresh-project test evidence still contained the stale top-level label `cleanup_policy="same_run_ephemeral_cleanup"` | `v0.1.78.2.20.8.5` makes full-integration cleanup evidence consistently report `no_project_delete_until_secure_protocol`; stale same-run cleanup wording is removed from executable/test evidence surfaces |
| ADR-PROJ-079 | 2026-06-20 | Joined repo workflow state must default to the project-scoped state authority | Operator logs showed `pb task use` wrote Kubernetes task state to `~/.local/state/promptbranch/projects/kubernetes/.promptbranch_state.json`, while `promptbranch state` read stale repo-local `.pb_profile/.promptbranch_state.json` with old artifact state | `v0.1.78.2.20.8.6` makes backend state reads use `_state_store_from_args(args)`, preserving browser profile resolution separately and keeping explicit `--profile-dir` as the override |
| ADR-PROJ-080 | 2026-06-21 | Plain-text response waits must initialize diagnostic breakdown before debug/deadline branches | Live `pb ask` evidence showed a correct sentinel answer was detected, but completion remained blocked by stop-button/composer-idle predicates; when debug artifact writing was skipped due to exhausted deadline budget, `_wait_and_get_response()` raised `NameError` because `breakdown` was undefined | `v0.1.78.2.20.8.7` mirrors the JSON response-wait initialization pattern for plain-text waits and adds focused regression coverage without changing completion semantics |
| ADR-PROJ-081 | 2026-06-21 | Localhost source-mutation clients must outwait service-side post-commit recovery | `v0.1.78.2.20.8.7 --run-all-tests` showed the browser service eventually returned `post_commit_source_surface_not_refreshed`, but the localhost full-test client timed out first and reported only `ReadTimeout` | `v0.1.78.2.20.8.8` gives Project Source add service calls a larger source-mutation timeout floor, keeps stale-inflight not-verified states release-blocking, and records a post-failure `pb src list --json` diagnostic for retained projects |

| ADR-PROJ-082 | 2026-06-21 | JSON orchestration event intake is proposal-only until a later accepted-event path records trusted state | The `.8.x` repairs stabilized release transport, but the MVP still needs a narrow structured intake surface that does not mutate state merely because ChatGPT produced JSON | `v0.1.79` adds `promptbranch.orchestration.event_intake`, `pb orchestration validate-event`, and fail-closed tests. Valid event intake only means the proposal may be reviewed; it does not write accepted state, mutate Project Sources, adopt artifacts, deploy, or execute model-proposed actions. |


| ADR-PROJ-083 | 2026-06-21 | Accepted-event validation remains read-only until a separate ledger/promotion slice exists | `v0.1.79` validated proposal/event-intake JSON but did not define the trusted accepted-event authority layer. Jumping straight to writes/runtime execution would create authority drift. | `v0.1.80` exposes `pb orchestration validate-accepted-event`, validates G0-G6 accepted-event fixtures from installed module code in `promptbranch_orchestration.py`, requires baseline binding, and keeps accepted-state writes, Project Source mutation, artifact adoption, deployment, and model execution disabled. |

| ADR-PROJ-084 | 2026-06-21 | Accepted-event promotion must start as dry-run only | `v0.1.80` validates accepted-event fixtures but does not define how an operator can preview future accepted-state writes. Adding writes immediately would create authority drift. | `v0.1.81` adds `pb orchestration accept-event --dry-run --json`, which previews validated accepted-event records and preserves all no-mutation flags. Ledger writes, proposal promotion, runtime execution, Project Source mutation, artifact adoption, and deployment remain out of scope. |

| ADR-PROJ-085 | 2026-06-21 | Accepted-event dry-run explicit inputs must be repo-local and fail closed before ledger writes exist | `v0.1.81` previewed committed fixtures only. Operators need to dry-run one supplied accepted-event file before any future ledger design, but accepting external or parent-relative paths would create authority and evidence ambiguity. | `v0.1.82` allows explicit repo-local accepted-event input for dry-run only, reports `input_mode=explicit_paths`, and rejects parent-relative, external absolute, missing, or invalid files without writing accepted state, mutating Project Sources, adopting artifacts, deploying, or executing model-proposed actions. |

## Decision — v0.1.82 explicit orchestration input resolves from worktree

For installed `pb` commands, explicit repo-relative orchestration input must resolve from the operator repository worktree / supplied file location, not from the installed package directory. Package/module code may be installed under `site-packages`, but orchestration examples, state machines, and accepted-event fixtures remain repository content for this MVP slice.

## Decision — Accepted-event ledger must be scaffolded before writes

`v0.1.83` keeps the accepted-event ledger as a read-only scaffold. The project now exposes `pb orchestration ledger-status --json` so operators can verify the future ledger path, record schema, append-only requirement, and no-mutation authority before any `accept-event --write` implementation exists. This prevents a jump from dry-run previews directly into mutable accepted state.

## Decision — Validate ledger before enabling ledger writes

`v0.1.84` adds `pb orchestration validate-ledger --json` as a read-only validation command before any ledger write path exists. An absent ledger is valid for this pre-write phase when the ledger directory and record schema scaffold are present. Existing ledger JSONL content, if present, must validate before any future write command can be considered. This preserves the authority boundary: no accepted state write, Project Source mutation, artifact adoption/current mutation, deployment, or model execution is introduced by validation.

## Decision — Root `.gitignore` remains release-required

Artifact Guardian continues to require a repo-root `.gitignore` in Promptbranch release ZIPs. Focused working slices may move quickly, but release candidates must still carry the root hygiene surface so generated files, local browser profiles, and `.pb_profile_local_debug_pools/` are excluded from future packaging.

| ADR-PROJ-088 | 2026-06-21 | Delete-frozen validation runs use a fresh Project name by default | Reusing one retained delete-frozen Project caused browser/project history to accumulate and slowed Promptbranch browser traversal | Release-control and live-test profiles now generate run-scoped `itest-promptbranch-*` Project names by default while still forcing keep-project because deletion remains frozen; explicit `--project-name` and `--conversation-url` remain operator overrides |


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

`v0.1.84.5.3` repairs rate-limit telemetry aggregation evidence only. `v0.1.84.5.2` remains functionally correct for downgrade behavior; this repair deduplicates repeated event-backed telemetry snapshots from visual artifact download/smoke-verification result carrying so top-level wait/event totals are reliable. It does not change Project deletion, Project creation identity, `/v1/ask` telemetry propagation, non-clean 429 classification, Project Source, artifact adoption/current, ledger/write/orchestration, deployment, or model-execution scope.


## v0.1.84.5.4 decision — recovered 429 is warning, not retry failure

A ChatGPT 429 modal or history 429 observed during live tests is release-blocking only if it is unrecovered or functional verification fails. If Promptbranch clicks `Got it`, waits/consumes cooldown, keeps the browser operation alive, and the sentinel/artifact proof passes, the live test reports `verified_with_recovered_rate_limit` and returns success while preserving telemetry.


## Decision — recovered 429 is a warning, not a replay trigger

If browser automation acknowledges ChatGPT's rate-limit modal, satisfies cooldown, continues in the same browser operation, and the functional assertion passes, release-control must preserve telemetry but must not retry the entire step solely because the log still contains 429 evidence.

## v0.1.84.5.6 repair note

`v0.1.84.5.6` repairs release-control `--run-all-tests` live Project reuse on top of `v0.1.84.5.5`. The run-all live phase now ensures one run-scoped ChatGPT Project once after live profile preflight and passes the returned Project URL to `ask-live`, `visual-artifact-roundtrip`, and `release-live` with `--conversation-url`. This prevents every live subtest from creating a separate retained Project while preserving delete-frozen safety, 50-character Project name caps, project-create recovery, recovered 429 retry suppression, and visual artifact reply-envelope hardening. No ledger/write/orchestration, Project Source mutation, artifact adoption/current, deployment, or model-execution scope advances.

## v0.1.84.5.7 repair note

`v0.1.84.5.7` repairs the shared live Project ensure command introduced in `v0.1.84.5.6`. Release-control `--run-all-tests` now uses the supported top-level `pb project-ensure` command to create or resolve one run-scoped ChatGPT Project, extracts the returned Project URL, and passes that exact URL to `ask-live`, `visual-artifact-roundtrip`, and `release-live` with `--conversation-url`. This preserves the one-Project-per-full-test-run policy without calling the unsupported nested `pb project ensure` surface. No project deletion, ledger/write/orchestration, Project Source mutation, artifact adoption/current, deployment, or model-execution scope advances.

## Decision — browser ReadTimeout requires bounded service recovery before next browser phase

A client-side timeout from a browser-backed Promptbranch service command can leave the underlying browser operation still running after the CLI exits. During release-control `--run-all-tests`, strict `ReadTimeout` or `service_client_read_timeout` evidence must trigger bounded service recovery before the workflow sends the next browser-backed command. Recovery may make later phases possible, but it must not convert the original failed full-test step into a pass.

## Decision — shared live Project URL extraction must select the successful Project ensure payload

Release-control must not use the last JSON object in a browser log as the Project ensure result. Browser/rate-limit telemetry can append nested JSON after a successful `pb project-ensure` payload. The shared live Project URL must be extracted from an `ok=true` `ensure_project` / `project_ensure` payload with `project_url`, `resolved_project_home_url`, or `project_home_url`. If recovered 429 telemetry is present but the Project ensure payload is functionally successful and contains a URL, release-control may continue with warning semantics; missing or invalid Project URL remains fail-closed.

## Decision — v0.1.84.5.10 localhost validation and ask-live streaming timeout

In run-all release validation, offline release-validation groups are primary local proof and must not inherit browser-service transport state from a localhost browser leg. Once the primary direct leg has proven the release-validation groups, later transports may report those groups as duplicate-skipped instead of rerunning identical local pytest commands. Also, selector-probe lines with `visible=False` are diagnostics, not rate-limit evidence. ask-live may treat a timeout with a visible expected sentinel as functionally verified only inside the bounded ask-live sentinel smoke contract; missing sentinel, wrong Project, stale sentinel, and unrecovered 429 stay fail-closed.

## Decision — localhost/offline validation must never sleep for browser cooldown telemetry

Browser/backend 429 telemetry can be real while still being outside the authority of localhost/offline release-validation groups. Release-control may apply browser cooldown retry only to live browser steps. If `full_localhost` or another localhost/offline validation step sees rate-limit evidence, release-control must deny the cooldown path before parsing cooldown seconds or printing the generic waiting warning, record the denial, and preserve the failed validation result for operator diagnosis.

## Decision — direct transport is not a localhost/offline cooldown-deny target

`full_direct` / `direct` must not be included in the localhost/offline browser-cooldown retry denylist unless a future change explicitly classifies them as offline-only. The hard denial is reserved for `full_localhost` and explicit localhost/offline validation groups.

## Decision — all-tests summary must prefer command result payloads over nested metadata

Release logs may contain nested JSON helper objects such as `profile_lease` and `profile_lease.metadata` inside a top-level command result. Raw brace scanning must rank the real command result payload above nested helper/metadata objects so recovered live-test statuses such as `verified_with_recovered_rate_limit` are not misclassified in `all_tests_failed_steps`.

## Decision — v0.1.84.5.10.3 ask-live recovered summary boundary

Recovered live-step classification may override top-level `ok=false` only when the command payload itself proves `status=verified_with_recovered_rate_limit`, acknowledged cooldown telemetry is present, `functional_failure_count=0`, and every ask-live child step confirms the expected sentinel. A recovered-rate-limit label without functional proof remains release-blocking. This decision does not apply to `full_direct` or `full_localhost` source-add timeout/rate-limit failures.

## Decision — v0.1.84.5.11 release-control diagnostics are observability-only

Release-control diagnostics may classify and explain live validation failures, but they must not convert `full_direct`, `full_localhost`, source-add ReadTimeout, unrecovered 429, missing sentinel, malformed artifact, or ChatGPT Project deletion failures into green results. Diagnostics are evidence for operator action, not acceptance authority.

## Decision — v0.1.84.5.12 `pb ask` conversation target selection is explicit

`pb ask` must distinguish between continuing a remembered task conversation and starting a fresh Project task. Default `pb ask` continues the remembered conversation when it is idle. `pb ask --new-task` / `--new-conversation` is the only CLI-controlled path that ignores the remembered `conversation_url` and starts from the remembered `project_home_url`. Literal prompt text such as `new task` is never interpreted as a command. `--new-task` and `--conversation-url` are mutually exclusive.

## Decision — v0.1.84.5.12.2 release-validation groups must use deterministic nodeids for scheduler/source lifecycle

The `browser_scheduler_source_lifecycle` release-validation group is a required offline release gate for scheduler, source queue, same-profile queueing, browser-profile-busy diagnostics, and release-lifecycle queue invariants. It must use explicit fast pytest nodeids rather than broad selector terms such as `cleanup`, because generic selectors can include unrelated cleanup tests and create nondeterministic release-control timeouts in operator environments.


## v0.1.85 decision — State proof uses schema-v2 current path

`pb ask --new-task` proof and operator smoke commands must use `.current.conversation_url` as the authoritative remembered task path. The stale top-level `.conversation_url` shape is not a valid proof source for schema-v2 Promptbranch state.

`pb state --proof` is read-only and may expose proof metadata, but it must not run a live ask, mutate Project Source, adopt artifacts, or alter ChatGPT Project state.

## Decision — v0.1.86 reconcile k8s-game plan before implementation

The next Kubernetes game work must not begin with implementation. The accepted Promptbranch baseline is `chatgpt_claudecode_workflow-2_v0.1.85.zip`, and orchestration docs must first be reconciled to that baseline.

The k8s-game remains a controlled test vehicle for JSON orchestration state. It is not a product goal and not a deployment target in `v0.1.86`.

A later implementation slice may add static app and manifest source files only. Any actual Kubernetes mutation requires a separate, explicit dry-run/deploy evidence gate accepted in a later release.

## Decision — v0.1.87 loop planner is dry-run and side-effect free

Promptbranch's loop-based problem-solving MVP starts with target schema validation and deterministic dry-run planning. The loop planner may classify targets, list states, and emit safety flags, but it must not execute validation commands, mutate files, deploy to Kubernetes, mutate Project Sources, adopt artifacts, or delete ChatGPT Projects.

Kubernetes game work is a future target fixture. It is not implemented or deployed by `v0.1.87`.

## Decision — v0.1.88 validation evidence reuse is artifact-hash and dimension bound

Release-control may reuse already-passed validation evidence only when the artifact SHA256 and validation dimensions match exactly. Version strings and filenames alone are not sufficient. The initial scope is direct `pb test full` evidence from `--run-tests` reused by `--run-all-tests`; live/browser, localhost, deployment, Project Source, and adoption behavior are not reused by this slice.

## Decision — v0.1.88.1 source-mutation timeouts are longer and diagnostic, not green

Project Source mutation calls through the Docker service may need a larger timeout than the general full-integration HTTP client timeout. Release validation must pass the extended source-mutation timeout to source-add requests. If the request still times out, Promptbranch must fail closed with structured diagnostics and a post-failure source-list probe where possible; it must not convert a text-source timeout into a successful source add.

## Decision — v0.1.89 every extra click is cooldown risk

Live browser validation must treat browser clicks as an expensive resource. Any click beyond the shortest safe path can increase ChatGPT cooldown/429 exposure. Promptbranch should therefore expose a reviewable browser action audit with click attempts, fallback click strategies, repeated click labels, and a cooldown-risk score. The audit is observational and must not authorize additional browser actions.


## Decision — v0.1.90 global conversation-history auto-requests are shieldable

The global `/backend-api/conversations` endpoint is rate-limit sensitive and can trigger repeated 429/cooldown pressure during live validation even when Promptbranch does not explicitly fetch conversation history. Non-essential frontend auto-requests to that global endpoint may therefore be shielded with an empty Promptbranch-marked response. Explicit Promptbranch history fetches and project-scoped `/backend-api/gizmos/{project_id}/conversations` calls must remain allowed.

The shield is a cooldown-pressure reduction mechanism, not an authority shortcut. It must not convert failed functional validation into green results, must not change Project Source mutation semantics, and must remain observable through rate-limit telemetry and test reports.

## Decision — v0.1.90.1 file-source stale inflight is not quiet enough

A file-source save can observe a commit while another file-source request remains inflight. For file uploads and overwrites, that state is not a safe quiet boundary because the remaining request may still be the upload/indexing path required for source visibility. Promptbranch must therefore wait for normal file-source request quiet before post-save persistence verification.

If post-commit recovery times out but the current Project Sources surface visibly contains the requested source and no save failure was observed, Promptbranch may classify the result as recovered from a visible surface snapshot. If the requested source is still absent, Promptbranch must fail closed with `post_commit_source_absent_after_stale_inflight` rather than calling it a generic surface-refresh problem.

## Decision — v0.1.91 run-all direct evidence reuse must be proof-based

`--run-all-tests` may reuse direct `full_direct` validation only when evidence proves the same artifact SHA256, version, artifact ref, transport, service base, runtime mode, strict source-kind matrix mode, command signature, and green test/report status. Same filename or same version is not enough.

The localhost matrix remains a separate validation dimension. It must be executed unless it has its own matching evidence in a later slice. Localhost/offline validation must not sleep/retry on browser cooldown evidence; any such evidence is surfaced by `localhost_matrix_cooldown_audit`.


## Decision — v0.1.91.1 null-project Retry is transient only without Project evidence

The first ask-live plain prompt may receive ChatGPT's generic “Something went wrong... Retry” response without a conversation URL or Project identity. That condition may be retried once as a transient service response. A response with a concrete wrong Project identity remains a real wrong-project failure and must not be retried away or marked green.

Run-all summary aggregation must prefer top-level live command result payloads over nested helper/schema JSON objects emitted in verbose browser logs. Successful live steps must not be listed in `failed_steps` merely because a later nested helper object had a schema/status field.

## Decision — run-all summary must parse pretty live command JSON from noisy logs

Release-control live command logs can contain browser telemetry, shell trace lines, and pretty-printed JSON. Final all-tests summary extraction must scan the full log for JSON objects and rank real command payloads above nested helper/schema/profile metadata. A live step that returned an `ok=true` verified command payload must not be reported as failed merely because the payload was pretty-printed or preceded by noisy log text.

## DEC-115 — Docker verification must distinguish lifecycle absence from version mismatch

Decision: release-control must not report `container_not_found` as a Docker content-version mismatch. Missing/non-running containers after recreate are Docker lifecycle/bootstrap failures and require Compose service-ID lookup, wait/health checks, and diagnostic collection before fail-closed release refusal.

## Decision — v0.1.91.4 pre-source-add service bootstrap

Release-control must not assume a Promptbranch service is already running. On a clean system, `promptbranch src add` depends on `localhost:8000`; therefore the candidate CLI and candidate service must be installed/verified or bootstrapped before source-add. Dirty-system success with a stale pre-existing service is not sufficient release evidence.

This is a repair-only release-control ordering decision and does not alter Project Source mutation semantics or adoption/current rules.


## Decision — v0.1.91.5 aggregation-only repair

`ensure_project` live command payloads may omit `status`; a valid `ok=true` payload with `project_url` is the authoritative command result and must outrank trailing `shared_live_project_url:` terminal text and nested helper/schema JSON.


## Decision — v0.1.91.6 run-all reused evidence is a valid adoption proof input

When `--run-all-tests` reuses direct validation evidence, the old direct report JSON path may be absent by design. The adoption verifier must therefore validate the green all-tests summary and the matching direct validation evidence instead of requiring `pb_test.full.direct.<version>.report.json`. This is a report-path repair only; evidence matching remains fail-closed.


## Decision — v0.1.91.7 pre-source-add candidate Docker builds are no-cache

Release-control candidate service bootstrap is adoption-grade validation, not a developer convenience build. Pre-source-add Docker bootstrap must use a no-cache build with explicit repo-root Compose invocation so stale application-source layers cannot pass into Project Source mutation. A Docker build-context version mismatch is classified before health probing and remains release-blocking.


## Decision — v0.1.91.8 run-all uses one authoritative browser/source lifecycle proof

Release-control must not duplicate live Project Source mutations in `full_localhost` after `full_direct` already proved the same browser/source lifecycle for the same artifact/version/hash/dimensions. The localhost matrix should reuse that proof and remain visible through transport/report/cooldown audit metadata. This avoids redundant ChatGPT UI/source-surface churn without weakening fail-closed evidence matching.

## Decision — v0.1.91.9 reused localhost lifecycle is a valid adoption proof input

When `full_localhost` is intentionally reused from matching green `full_direct` browser/source lifecycle evidence, `pb_test.full.localhost.<version>.report.json` may be absent by design. Adopt-after-validation must validate the green all-tests summary, matching direct evidence, and `full_localhost` `reused_browser_source_lifecycle` step instead of requiring a missing report file. Run-all should also emit progress percentages after each step so operators do not need to wait for the final summary to see whether the run is failing.

## Decision — v0.1.91.10 browser scheduler validation reports active nodeids

The required `browser_scheduler_source_lifecycle` release-validation group remains required and continues to use the same explicit fast pytest nodeids, but its execution now reports per-nodeid progress. This avoids opaque 300-second timeouts with empty stdout/stderr tails and gives operators the active nodeid without increasing timeouts or weakening validation. The run-all progress writer uses `chr(10)` to avoid shell-generated Python newline quoting defects.

| ADR-PROJ-092 | 2026-06-26 | MVP-1 starts with a state-only loop walkthrough | The original Kubernetes game target was a useful acceptance scenario, but the real product direction is Promptbranch working through a plan in controlled steps | `v0.1.92` adds `pb loop run --state-only`; it prints only planned states and preserves no-execution/no-mutation boundaries. The k8s game remains a future acceptance scenario, not the opening implementation slice. |

| ADR-PROJ-093 | 2026-06-26 | MVP-1 next step is planned-action walkthrough, not execution | After state-only proof, the operator needs to see what each state would do before any real execution is allowed | `v0.1.93` adds `pb loop run --planned-actions`; it remains dry-run/no-side-effect and does not execute commands, mutate Project Sources, deploy, adopt artifacts, or delete ChatGPT Projects. |

| ADR-PROJ-094 | 2026-06-26 | Offline release-validation scheduler nodeids must not inherit live ChatGPT/service/profile environment | `v0.1.93` proved the planned-action feature but direct validation timed out after live browser/source work left ambient lock state visible | `v0.1.93.1` strips live browser/service env, isolates per-nodeid HOME/TMPDIR/XDG/profile state, and records ambient lock diagnostics without changing validation semantics. |

## Decision — Project Source capacity-prune drift is fail-closed

For release ZIP file source-add capacity pruning, if the exact remove of the selected prune target reports identity drift or collateral removal, Promptbranch must stop immediately, suppress any looser retry, return `operator_review_required=true`, and require operator review. The system must not continue pruning after source-row identity drift.

This decision was added for `v0.1.94.1` after a `v0.1.94` run targeted old source `v0.1.85` but observed collateral removal of older rows.


| ADR-PROJ-096 | 2026-06-27 | Read-only loop execution must produce evidence before real execution is introduced | The loop can only become safe if operators can inspect what was checked, what was skipped, and which side-effect boundaries stayed true before any command execution slice exists. | `v0.1.95` adds `promptbranch.loop.read_only_evidence_report` and `pb loop run --read-only-execution --evidence-report`; it remains no-command/no-mutation/no-deploy/no-adoption. |

| ADR-PROJ-097 | 2026-06-27 | Generated release ZIP Project Sources are retained per repository family, not globally deleted | A single ChatGPT Project has a 25-resource source cap and may service multiple repositories. Automatic cleanup must avoid deleting documentation or project sources while still keeping generated source ZIP accumulation bounded. | `v0.1.96` keeps at most five generated release ZIPs per release family after upload, prunes only same-family canonical generated ZIPs, and fails closed when no safe same-family ZIP is available. |

| ADR-PROJ-098 | 2026-06-27 | Read-only loop evidence needs a gate before execution | Evidence reports are useful for operators, but the loop engine needs a deterministic pass/block contract before any later slice can execute validation commands. | `v0.1.97` adds `promptbranch.loop.read_only_evidence_gate` and `pb loop run --read-only-execution --evidence-gate`; it performs no command execution, file mutation, deployment, Project Source mutation, artifact adoption, or ChatGPT Project deletion. |


| ADR-PROJ-099 | 2026-06-27 | Text-source post-commit reconciliation requires exact text proof | `v0.1.97` showed the release ZIP source can be visible while `project_source_add_text` remains unverified due stale-inflight source-surface refresh. | `v0.1.97.1` reuses the spikkies-site reconciliation principle but adapts it to text sources: after commit, re-read Project Sources and recover only when exact text-source identity/content proof is visible. Nearby text sources and ZIP source cards are rejected. |

| ADR-PROJ-100 | 2026-06-27 | Make plan-state.json the machine-readable anti-drift authority before first command execution | Markdown-only control surfaces drifted after repair patches and stale current-baseline sections could mislead the next-slice choice | `v0.1.98` adds `docs/project/plan-state.json` and `pb project validate-control-surface --json`; repair releases must not advance scope, and first controlled read-only validation command execution is deferred to `v0.1.99`. |

| ADR-PROJ-101 | 2026-06-27 | Defer first command execution until rolling slice horizon and architecture-decision protocol are documented | v0.1.98 made the anti-drift gate executable, but the next 4–5 slices and architecture invariants were still conversation-level guidance rather than repo authority. | `v0.1.99` adds `docs/project/architecture.md`, `docs/project/slice-horizon.md`, a machine-readable `rolling_slice_horizon`, and `pb project next-slice --json`; first controlled read-only validation command execution moves to `v0.1.100`. |

| ADR-PROJ-102 | 2026-06-28 | Repair Docker build-context freshness before accepting v0.1.99 | Docker copied stale v0.1.98 version surfaces after deterministic ZIP install left same-size files with fixed mtimes, and release-control degraded the root cause to service unavailable. | `v0.1.99.1` refreshes build-context mtimes, passes/verifies a source fingerprint, uses explicit build then `up --no-build`, and keeps `v0.1.100` deferred. |

| ADR-PROJ-103 | 2026-06-28 | Limit first command execution to one JSON syntax validation command | v0.1.100 is the first slice that may run a local command, so broad shell execution would create avoidable mutation and security risk. | Only `python3 -m json.tool <repo-relative-json-file>` is allowlisted; the existing evidence gate must pass first; v0.1.101 will diagnose results later without correction or mutation. |


## ADR-PROJ-105 — v0.1.100.1 text-source stale-inflight recovery diagnostics repair

Decision: create `v0.1.100.1` as a repair-only release after `v0.1.100` failed full release-control in `project_source_add_text` with `commit_seen_with_stale_inflight_not_verified_present` and `current_source_count=0`.

Rationale: the normal `v0.1.100` loop-command slice did not fail; the blocker was Project Source text-add verification. Recovery must re-open/re-read Project Sources and collect diagnostics, while preserving fail-closed behavior unless exact text identity/content proof is visible.

Scope rule: no normal-slice advancement; `v0.1.101` remains deferred.


## ADR-PROJ-106 — v0.1.100.2 browser scheduler source-lifecycle timeout repair

Decision: create `v0.1.100.2` as a repair-only release after `v0.1.100.1` failed full release-control in the required `browser_scheduler_source_lifecycle` group while running `tests/test_promptbranch_automation_service.py::test_source_remove_waits_behind_source_list_with_same_profile`.

Rationale: the normal `v0.1.100` loop-command slice did not fail, and the `v0.1.100.1` text-source repair path passed. The remaining blocker was an offline test fixture with an unbounded wait for active-operation visibility. The repair keeps the same scheduler/source lifecycle semantics but uses an explicit bounded `asyncio.Event` start signal and cleanup path so the test fails fast with diagnostics instead of consuming the whole group timeout.

Scope rule: no normal-slice advancement; `v0.1.101` remains deferred.

## ADR-PROJ-107 — v0.1.100.3 generated debug artifacts are release-blocking ZIP entries

Decision: create `v0.1.100.3` as a repair-only release after `v0.1.100.2` failed release-control ZIP install verification because generated `debug_artifacts/` files were present in the candidate archive.

Rationale: `debug_artifacts/` is operator/runtime diagnostic state, not repository source. It must be preserved during install but never shipped inside release ZIPs. Artifact Guardian must reject this class before a candidate is handed to the operator.

Scope control: preserve `v0.1.100`, `v0.1.100.1`, and `v0.1.100.2` behavior; do not advance to `v0.1.101`.



## ADR-PROJ-108 — v0.1.101 diagnoses read-only command results without correction

Decision: add a diagnostic layer over `promptbranch.loop.read_only_command_execution` that classifies command evidence as `passed`, `blocked`, or `failed`.

Rationale: `v0.1.100` proved that one allowlisted read-only JSON validation command can execute safely. The next safe capability is not correction; it is stable diagnosis of outcomes, with blocked vs failed reason codes that later slices can consume.

Consequence: `v0.1.101` may read existing command evidence and emit diagnosis metadata, but it must not generate correction plans, retry commands, mutate files, deploy, mutate Project Sources, adopt artifacts, or delete ChatGPT Projects. `v0.1.102` remains the first planned correction-plan slice.

## ADR-PROJ-109 — v0.1.102 correction plans are proposal-only

Status: accepted for v0.1.102 candidate.

Context: `v0.1.101` can classify read-only command evidence as passed, blocked, or failed. The next architectural layer needs a structured plan for operator review, but applying fixes or retrying commands would cross into mutation before sandbox gates exist.

Decision: `v0.1.102` may generate bounded correction-plan evidence from diagnosis results, but the generated plan must contain no file changes, no write actions, no immediate command retries, no Project Source mutation, no artifact adoption, no deployment, no ChatGPT Project deletion, and no patch/diff artifacts.

Consequence: file mutation remains explicitly deferred to `v0.1.103.1`, where it must occur only inside a sandbox fixture with before/after evidence.


## ADR-PROJ-110 — v0.1.103.1 file mutation is sandbox-only

Status: accepted for v0.1.103.1 candidate.

Context: `v0.1.102` can generate bounded correction-plan evidence without writing files. The next safety layer must prove that Promptbranch can perform a write while preventing uncontrolled repository mutation.

Decision: `v0.1.103.1` may perform a file mutation only on a copied fixture inside a temporary sandbox workspace. The source fixture path must be repo-relative, under `examples/loop-sandbox/`, covered by `target.allowed_paths`, and optionally pinned by an expected SHA-256. The repository fixture must remain unchanged.

Consequence: rollback and promotion decisions remain deferred to later slices, starting with v0.1.104 — Sandbox mutation verification and rollback evidence gate. Repository-wide correction workflows remain out of scope.

## ADR-PROJ-136 — Docker browser parity investigation is diagnostic first

`v0.1.103.1` introduces a diagnostic Docker browser envelope based on the
reference Docker browser pattern. The diagnostic may test Xvfb service mode, FedCM
disabled mode, preserved Docker no-sandbox behavior, and `/app/profile`, but it
must not bypass Cloudflare, automate challenges, mutate Project Sources, adopt
artifacts, or delete ChatGPT Projects.

## ADR-PROJ-112 — v0.1.103.2 passive Docker auth readiness

Status: accepted for diagnostic candidate.

Decision: Docker browser parity diagnostics must use passive auth readiness. The diagnostic may navigate to ChatGPT and wait for ordinary challenge settling, but it must not click the login button, start Google login, or wait for hidden manual-login under Xvfb. Profile bootstrap is handled explicitly by host Chrome seeding `.pb_profile_docker`, which Docker mounts as `/app/profile`.

Consequence: unauthenticated Docker profiles now fail fast with structured `auth_profile_not_logged_in` evidence instead of hanging for the manual-login timeout.

## ADR-PROJ-113 — v0.1.103.3 runtime browser client owns passive auth-readiness

Decision: passive auth-readiness must be implemented on `promptbranch_browser_auth.ChatGPTBrowserClient`, because `promptbranch_automation` imports that runtime client. Compatibility code in `chatgpt_browser_auth` is insufficient for the Docker service.

Consequence: future browser-client repairs must verify the actual runtime import path, not only compatibility aliases.


## ADR-PROJ-114 — v0.1.103.5 Docker parity Project Source mutation requires passive readiness and explicit opt-in

Docker browser parity mode may mutate Project Sources only when `PROMPTBRANCH_ALLOW_PROJECT_SOURCE_MUTATION=1` is set and passive auth-readiness proves `logged_in=true`, `challenge_detected=false`, `composer_visible=true`, and `release_blocking=false`. This preserves the diagnostic recovery path without allowing accidental source mutation during profile/bootstrap research.

## ADR-PROJ-115 — v0.1.103.6 Docker challenge artifact export must be bounded and staged

Context: copying `/app/debug_artifacts/.` directly from the Docker service into a host path under `debug_artifacts/` can recursively grow when the source is a bind-mounted repo debug tree.

Decision: Docker parity challenge artifact export must stage only matching `auth_readiness_auth_challenge_detected_*` files through `/tmp/pb-challenge-artifacts`, enforce maximum file count and total bytes, and refuse recursive debug-tree destinations.

Consequence: operators use `scripts/docker-browser-parity-export-challenge-artifacts.sh` instead of manual wholesale `docker cp` commands.
## ADR-PROJ-116 — v0.1.103.8 Docker Cloudflare challenge is tested before downstream mutation

Decision: Docker parity work must focus first on whether the held `/app/profile` Patchright Chrome session can clear the ChatGPT Cloudflare `Just a moment...` challenge. Project Source mutation, login clicking, and Google auth flows remain out of scope until challenge settling is proven with same-session polling and bounded evidence export.

Consequence: operators use `scripts/docker-browser-parity-cloudflare-check.sh` for the next diagnostic run.


## ADR-PROJ-117 — v0.1.103.9 Bonnetjes Cloudflare parity profile hygiene

Decision: The Bonnetjes Cloudflare parity path is the supported Docker auth diagnostic path. Browser profiles used by `PROMPTBRANCH_HOST_PROFILE_DIR` must be bind-mounted into `/app/profile` and must not enter Docker build context. Repository-local profiles are allowed only when `.dockerignore` excludes `.pb_profile*`; challenge evidence export must treat an absence of challenge artifacts as `ok=true,status=no_matching_artifacts`.

Consequence: operators use `scripts/docker-bonnetjes-clean-login-profile-bootstrap.sh` and `scripts/docker-browser-parity-cloudflare-check.sh` for clean logged-in Cloudflare checks. Project Source mutation remains out of scope.

### v0.1.103.10.4 — standard browser Cloudflare validation

Decision: provide a single operator script that runs the full Cloudflare validation phase: optional candidate install, visible clean-login profile bootstrap, Docker Bonnetjes Cloudflare parity check, and strict summary validation.

Consequence: operators can validate the working Cloudflare path with `scripts/docker-bonnetjes-cloudflare-validation.sh` before any downstream Project Source mutation slice.

### v0.1.103.10.6 — standard browser profile ownership guard

Decision: standard browser validation must prepare `.pb_profile/browser/default` before host Chrome or Docker uses it. Empty non-writable bind-mount placeholders may be removed and recreated by the host user; non-empty non-writable profiles must fail fast with an explicit ownership repair instruction.

Consequence: the validation path fails before Chrome profile corruption risk and avoids silently running host Chrome against a root-owned profile. Project Source mutation remains disabled and the Cloudflare-safe browser envelope is unchanged.

### v0.1.103.10.6 — keep source-add gate closed and repair the CLI guidance

Decision: keep Project Source mutation disabled for the standard-browser auth-only validation slice. Do not tell operators to solve `pbsa` failures by enabling mutation for release validation. Instead, preserve the service gate status in the CLI payload and point candidate ZIP validation to `pb-browser-cloudflare-validation.sh --install-artifact`.

Rationale: this prevents authority drift from an auth-readiness/Cloudflare validation slice into ChatGPT Project Source mutation while still giving a clear next command when old release habits invoke `pbsa`.


### v0.1.103.10.8 — reject generated caches in release transport ZIPs

Decision: a candidate ZIP containing `.pytest_cache/`, `__pycache__/`, `.pyc`, or similar generated cache entries must not be installed or adopted. The packaging repair for `v0.1.103.10.8` keeps behavior unchanged and only provides a clean release transport artifact.

### v0.1.103.10.8 — successful auth readiness does not require challenge artifacts

Decision: the Docker browser parity Cloudflare check may normalize a `missing_staged_manifest` challenge-artifact export result only when the auth-readiness state already reached `cloudflare_cleared_*`. This prevents a green login/composer result from being marked noisy by an absent challenge manifest, while preserving strict export failure behavior for timeout or active challenge states.

### v0.1.103.10.9 — ask must not compete with a held auth-ready profile session

Decision: when a standard-browser auth-readiness run keeps a browser context alive, `pb ask` must first probe and reuse that held session if the profile, browser driver, and channel are compatible. It must not clear `SingletonLock`, `SingletonSocket`, or `SingletonCookie` while the held session is active. If the held session is challenged, stale, or invalid, the safe behavior is to close it and fail fast with recovery guidance rather than silently opening a second competing persistent context.

### v0.1.103.10.10 — held auth-ready ask must not navigate away before send

Decision: when `pb ask` reuses an auth-readiness-held browser page that is already logged in with a visible composer, it must send through that page instead of first navigating to the configured target conversation URL. The observed `v0.1.103.10.9` path reused the session but immediately navigated from `https://chatgpt.com/` to a project conversation URL and triggered Cloudflare again. This repair keeps Project Source mutation disabled and does not introduce the later host-CDP session manager.

### v0.1.103.10.11 — standard profile should be bootstrapped by Docker Chrome when Docker fingerprint is challenged

Decision: auth-only standard-browser validation may use a Docker-launched visible Chrome bootstrap by default. Host Chrome bootstrap remains a compatibility option, but Docker-originated trust is preferred when Docker/Patchright receives Cloudflare despite a host-created profile. Project Source mutation remains disabled.
| ADR-PROJ-156 | 2026-07-01 | Held-session `pb ask` reuse must still honor the current project/conversation scope | v0.1.103.10.11 proved generic ChatGPT ask could work but created a conversation outside Promptbranch3 when state targeted a `/g/.../c/...` URL | A visible composer alone is insufficient; project-scoped targets require matching project/conversation URL or fail-fast project-scope navigation diagnostics |

<!-- v0.1.103.10.12 -->


<!-- v0.1.103.10.13 -->
- `pbsa` is treated as an explicit operator mutation command, but the service still requires a per-request mutation intent or the legacy environment gate and must pass Docker browser auth/profile preflight before mutating Project Sources.

<!-- v0.1.103.10.15 -->
- Decision: `pbsa` must not create a second persistent browser context while a compatible auth-ready session is held. Project Source mutation preflight and upload may reuse that held session; if unavailable, failures must be structured and non-500.


## DEC-v0.1.103.10.17 — separate bootstrap URL from validation URL

Visible Docker browser bootstrap is a trust/session establishment step and should default to `https://chatgpt.com/`. Project/conversation scope remains enforced by the subsequent auth-readiness validation URL. Operators can still pass an explicit project bootstrap URL for diagnosis.


## DEC-v0.1.103.10.17 — reuse held session for remembered overwrite removal

Project Source overwrite removal must not launch a second persistent browser context while an auth-readiness session owns `/app/profile`; remove and add flows should reuse the held session and only require authenticated/no-challenge UI state.


## Decision — API coverage runner defaults to non-destructive mode

The API coverage runner must not create/delete ChatGPT Projects or remove Project Sources by default. Mutation paths require explicit flags and are serialized by the operator workflow.


control token: chatgpt_claudecode_workflow-2_v0.1.103.10.19.zip

## Decision — v0.1.103.10.19 installs API coverage runner as package module

`pb test api` must not depend on a source-tree-only `scripts/` directory after pipx installation. The runner is packaged as `promptbranch.api_coverage_test`; the shell script remains a source-tree convenience wrapper.

control token: chatgpt_claudecode_workflow-2_v0.1.103.10.19.zip

## Decision — v0.1.103.10.21 serializes API coverage browser checks

`pb test api` defaults to serial browser mode and does not keep an auth-readiness session open before projects/chats/sources checks. Held-session reuse testing remains explicit via flags.

control token: chatgpt_claudecode_workflow-2_v0.1.103.10.21.zip

## Decision — v0.1.103.10.22 Docker Chrome shm sizing

Promptbranch service and visible Docker browser bootstrap paths declare Docker shared-memory sizing to avoid Chrome crashes caused by default small `/dev/shm` mounts.

control token: chatgpt_claudecode_workflow-2_v0.1.103.10.22.zip


## Decision — v0.1.103.10.42 API coverage semantic assertions

`pb test api` must fail semantically unsuccessful HTTP 200 responses. This repair is report/assertion-only and does not change browser/session architecture.

control token: chatgpt_claudecode_workflow-2_v0.1.103.10.42.zip

## Decision — v0.1.103.10.42 pb test api service config token

`pb test api` now uses the normal Promptbranch CLI service configuration path for host-side service transport defaults. When `--base-url` is absent, it maps `service_base_url` from `~/.config/promptbranch/config.json` to the API coverage runner base URL. When `--token` is absent, it maps `service_token` from the same config to the runner token. The token is not printed in JSON reports, logs, or summaries. This keeps `.env` out of the API coverage token handoff and preserves the v0.1.103.10.25 ask-submit repair, held-session preflight, browser/session architecture, and Project Source mutation behavior.
## Decision — v0.1.103.10.42 full/browser validation skips generic-root login check

`v0.1.103.10.42` disables the forced `login_check` step in browser/full validation by default. The suite now relies on the same auto-login/session path used by real browser operations, avoiding generic `https://chatgpt.com/` root navigation that can trigger a challenge. The login check endpoint and explicit diagnostic step remain available via `--only login` or `PROMPTBRANCH_TEST_ENABLE_LOGIN_CHECK=1`. No browser/session architecture or Project Source mutation behavior changes.



## Decision — v0.1.103.10.42 release-control clears auth bootstrap held session explicitly

`v0.1.103.10.42` adds a release-control `pb_auth_bootstrap` phase that runs the existing standard browser Cloudflare/auth validation flow before Project Source add and before test execution. The bootstrap resolves the current Promptbranch state URL first and uses it for both validation and browser bootstrap, avoiding generic root navigation where possible. Auth-only validation remains the dedicated bootstrap-only path. No browser/session architecture or Project Source endpoint behavior changes.

## Decision — v0.1.103.10.42 missing live seed profile is non-blocking

Decision: absence of `.pb_profile_local_debug` must not fail `--run-all-tests` adoption when release-blocking validation has already passed. The live-only steps depend on an optional local seed profile and are now recorded as non-blocking skips with reason `live_profile_seed_missing`. Existing blocking behavior remains for a present-but-invalid live seed profile, full direct validation, Project Source add, import smoke, and artifact guard.

## Decision — v0.1.103.10.42 source-add auth preflight may accept project page readiness

Decision: `pre_source_add` release-control auth bootstrap may accept a logged-in, Cloudflare-clear ChatGPT project home page (`/project`) even when no chat composer is visible. This exception is explicit and phase-scoped via `PROMPTBRANCH_BROWSER_VALIDATION_ALLOW_PROJECT_PAGE_READY=1`. Normal ask/live/conversation validation continues to require composer readiness.

Rationale: Project Source add requires authenticated project context, not a conversation composer. Failing before Project Source add on a valid project page is over-strict and blocks the release path without improving safety.
### v0.1.103.10.42 — pre_tests auth bootstrap must prefer current conversation scope

Decision: `pre_tests` auth bootstrap should not target the project home page when a current project conversation URL is recorded. The project home page can prove login/project visibility, but it does not necessarily expose a composer. Composer validation remains meaningful only on conversation-scoped URLs.

Consequence: release-control resolves `pre_tests` through conversation state first and keeps `/project` page readiness as a documented fallback rather than the default strict-composer target.

### v0.1.103.10.42 — all-in-Docker browser direction and explicit live profiles

Decision: abort the host-CDP/session-manager direction for this line. Promptbranch browser automation continues with the Docker/Patchright path only. Live `--run-all-tests` profiles must be explicitly bootstrapped in the exact profile directories that the tests use; copied profile slots are not trusted for Cloudflare-sensitive validation.

Consequence: release-control fails fast when `.pb_profile_local_debug` or `.pb_profile_local_debug_pools/release-live/slots/slot-1` is missing or unauthenticated, and it reports the Docker bootstrap command instead of skipping live tests.

### v0.1.103.10.42 — preserve live Docker pool state across ZIP import

Decision: `.pb_profile_local_debug_pools/` is local Docker browser state that must be preserved across release ZIP import when `--run-all-tests` requires explicitly bootstrapped live pool profiles. It must still be rejected if packaged inside a release ZIP.

Rationale: `v0.1.103.10.40` correctly stopped copying live profiles, but install/import removed the manually authenticated release-live slot before validation. Preserving the pool aligns the lifecycle with the all-in-Docker profile strategy.

### v0.1.103.10.42 — live ask requires `/c/...`, not `/project`

Decision: release-control must not pass a Project home URL directly to `ask_live`. A live Project page can be authenticated without showing a composer, so release-control creates/opens a conversation after `live_project_ensure` and passes that conversation URL to the live ask/artifact/release gates. Docker live profile Cloudflare challenge evidence is classified as `docker_live_profile_challenged` and not retried by release-control.


### v0.1.103.10.43 — release-live Cloudflare challenge is terminal

Release-live browser validation must not ask the operator to prove humanity inside an automation-owned headed Chrome window. If the Docker live profile reaches a Cloudflare/Just-a-moment challenge, release-live mode now fails fast with `docker_live_profile_challenged`, closes the browser context, and records a structured release-control failure. Manual-login waits remain for explicit bootstrap/login workflows, not for release-control live validation.

## Decision — v0.1.103.10.45

`v0.1.103.10.45 — repair package version surface for Docker build context coherence` keeps the Docker-only live validation architecture. Challenge detection in release-live mode now logs with `challenge_stage` instead of a duplicate `_log(stage=...)` keyword, returns structured `docker_live_profile_challenged`, and prevents later live browser steps from opening once `ask_live` has already proven the live slot is challenged.


## Decision — v0.1.103.10.48

`v0.1.103.10.48 — classify backend-api 403 guardrail as terminal browser challenge across release validation paths` keeps the all-in-Docker live validation path and makes a challenged release-live slot terminal across both the internal `ask-live` matrix and release-control. The repair uses fixed-string/JSON-aware challenge detection and records later live browser steps as skipped-blocked instead of opening new Chrome contexts. No host-CDP/session-manager or copied-profile trust is reintroduced.


## Active repair slice — v0.1.103.10.48

`v0.1.103.10.48 — classify backend-api 403 guardrail as terminal browser challenge across release validation paths` preserves the Docker-only live-validation line and extends fail-fast challenge classification beyond ask-live. Observed ChatGPT `/backend-api/...` 403 responses are diagnostic guardrail evidence only, not an operational API contract. Release-control now enables fail-fast challenge handling for full/direct, localhost/service, live preflight, project selection, and live ask paths; after a full-validation backend guardrail, remaining live browser phases are skipped and import/artifact guards still run.

## Active repair slice — v0.1.103.10.53

`v0.1.103.10.53 — release-live bootstrap 429/guardrail is terminal before ask_live` preserves the Docker-only challenge classification chain through `v0.1.103.10.48`, then fixes the remaining human-likeness topology bug: release-live setup and execution now use `.pb_profile_local_debug_pools/release-live/slots/slot-1` as the single actor profile for project ensure, project selection, conversation bootstrap, ask-live, visual artifact roundtrip, and release-live. `.pb_profile_local_debug` remains optional/reference state and is no longer used to create the live conversation that the slot later opens. The Docker bootstrap default image also derives from `VERSION`/`PROMPTBRANCH_VERSION` instead of depending on an unset `PROMPTBRANCH_SERVICE_IMAGE_TAG` local fallback.


## Active repair slice — v0.1.103.10.53

`v0.1.103.10.53 — release-live bootstrap 429/guardrail is terminal before ask_live` preserves the Docker-only live-profile repair chain through `v0.1.103.10.49`, then makes backend-api 403 guardrail telemetry during auth bootstrap terminal. Release-control now refuses to treat a visually logged-in/composer-visible browser as clean when the standard Docker profile is already forbidden by backend-api guardrail responses; it restarts the candidate service to clear the held browser owner and stops before Project Source add/full validation.


## Active repair slice — v0.1.103.10.55

`v0.1.103.10.55 — release-live bootstrap and ask use one continuous browser session` adds a fast replay harness for release-control run-all orchestration, including terminal live bootstrap 429/guardrail behavior before ask_live. It preserves all-in-Docker, no host-CDP/session-manager, no copied-profile trust, and no private backend-api operational dependency.


## v0.1.103.10.56 — wire release-live-continuous into real CLI test dispatch

Repair candidate `chatgpt_claudecode_workflow-2_v0.1.103.10.56.zip` wires `release-live-continuous` into the real CLI test dispatcher while preserving the continuous release-live session design.

## v0.1.103.10.59

Active candidate: v0.1.103.10.59

Artifact: chatgpt_claudecode_workflow-2_v0.1.103.10.59.zip

Slice: v0.1.103.10.59 — extract live preflight warmup URL from login-check url field

Scope: release-live-continuous starts the initial auth/warmup check from the trusted conversation URL proven by live_profile_preflight instead of bare https://chatgpt.com/.



## v0.1.103.10.61

Active candidate: v0.1.103.10.61

Artifact: chatgpt_claudecode_workflow-2_v0.1.103.10.61.zip

Slice: v0.1.103.10.61 — classify Docker live preflight challenge as external live challenge and stop browser-repair loop


## v0.1.103.10.65

Artifact: `chatgpt_claudecode_workflow-2_v0.1.103.10.65.zip`

Slice: v0.1.103.10.65 — classify release-live-continuous first-ask Cloudflare challenge as LIVE_BLOCKED

Default `--run-all-tests` no longer calls `POST /v1/login-check`; external ChatGPT live probes are explicit and default live rows are `external_live_not_requested`.

## Decision — v0.1.103.10.65 external-live first-ask challenge is LIVE_BLOCKED

Decision: when explicit external-live validation reaches `release-live-continuous` and the first ask returns `docker_live_profile_challenged`, release-control must report `LIVE_BLOCKED` rather than `FIX`, provided product validation steps are otherwise healthy.

Rationale: `FIX` means product/code repair is needed. A clean Cloudflare/Docker live browser challenge during explicit external ChatGPT live validation is an external browser condition, not a deterministic product-validation failure.

## Decision — v0.1.103.10.65 trusted conversation warmup is authoritative for release-live-continuous

Decision: when `release-live-continuous` is given a trusted project conversation URL via `--warmup-conversation-url`, that URL is sufficient project identity for the live-only test. The command must not navigate to `https://chatgpt.com/` to rediscover or create a project in that path. Bootstrap and first ask should remain in the same conversation/session.

Rationale: the live log showed the trusted conversation was logged in and composer-ready before the command navigated away for root project discovery. The root navigation introduced avoidable page/context loss and extra external web-app surface area.


## Decision — v0.1.103.10.65 trusted conversation page must be opened before held send guard

When `release-live-continuous` receives a trusted project-scoped `/g/.../c/...` warmup URL, the URL is not only identity evidence. It is also the required active browser surface. The command must navigate to that conversation and verify readiness before invoking the held-page send guard, otherwise `about:blank` can be misclassified as an auth/challenge failure before any live prompt is sent.


## v0.1.103.10.66 repair note

Candidate artifact: `chatgpt_claudecode_workflow-2_v0.1.103.10.66.zip`.

Active candidate version: `v0.1.103.10.66`.

Active repair slice: `v0.1.103.10.66 — release-live-continuous handles page/context close during composer submit as explicit browser-lifetime failure`.

This remains repair-only and does not advance the normal horizon. It keeps trusted conversation direct mode and adds structured `browser_context_closed_during_submit` evidence for live browser page/context close during composer submit.

## Decision — v0.1.103.10.67 composer wait target-close is browser lifetime failure

When `release-live-continuous` has already verified a trusted project conversation and the browser target closes while waiting for chat input selectors, Promptbranch must stop iterating the remaining selectors and return structured `browser_context_closed_during_submit` with `submit_subphase=composer_wait`. This is not Cloudflare unless challenge evidence exists, and it must not be converted into a generic response timeout.

Active repair slice: `v0.1.103.10.67 — composer wait target-close is classified as browser_context_closed_during_submit`.


## Decision — v0.1.103.10.68 completed sentinel run is successful release-live-continuous evidence

When release-live-continuous keeps the trusted direct conversation session and both bootstrap and ask sub-results return `status=completed` with exact expected sentinel answers, the top-level result must be `ok=true` with no `failed_phase`, even if the sub-results omit `ok=true`. Browser action audit warnings remain preserved and are not part of this success predicate.

Active repair slice: `v0.1.103.10.68 — release-live-continuous marks completed bootstrap/ask sentinel run as ok`.

## Decision — v0.1.103.10.69 strict all-all install script

Active repair slice: `v0.1.103.10.69 — add install.sh strict all-all release gate`.

Add `install.sh` at repo root as the operator-facing strict full release gate for a new ZIP. It intentionally combines product validation and explicit external-live validation with `--adopt-after-validation`, so adoption occurs only when both deterministic and live gates are green. This does not change release-control semantics and does not bypass Cloudflare.


## v0.1.103.10.70 repair note

Active repair slice: `v0.1.103.10.70 — classify release-live-continuous bootstrap guardrail as external live blocked`.

Decision: keep the `v0.1.103.10.69` strict all-all install gate unchanged, but classify `live_bootstrap_guardrail` and `skipped_blocked_by_live_bootstrap_guardrail` as external-live blockage evidence so all-all adoption remains blocked with `LIVE_BLOCKED`, not product `FIX`.

No Cloudflare/rate-limit bypass, host-CDP/session-manager, or copied-profile trust is introduced.


## v0.1.103.10.72 repair decision

`v0.1.103.10.72` keeps repair scope only: the project control surface must identify `chatgpt_claudecode_workflow-2_v0.1.103.10.72.zip` as the active candidate, and all-all release aggregation must prefer product `FIX` over external `LIVE_BLOCKED` whenever product validation has failed. `LIVE_BLOCKED` is reserved for clean product validation with external ChatGPT live blockage. The planned normal horizon after repair acceptance remains `v0.1.104`.


## v0.1.103.10.73 repair decision

`v0.1.103.10.73` keeps the strict all-all install gate, live bootstrap guardrail cascade normalization, and product-failure precedence over `LIVE_BLOCKED`. The repair decision is to remove stale hardcoded release-version expectations from `tests/test_promptbranch_version.py`; version-surface assertions must derive expected values from `VERSION`, `pyproject.toml`, and `promptbranch_version.py`, while preserving the no-double-v-prefix invariant.

## v0.1.103.10.76 repair decision

`v0.1.103.10.76` keeps the strict all-all install gate and product-clean `LIVE_BLOCKED` classification. The repair decision is to add one bounded `release-live-continuous` bootstrap guardrail cooldown/re-readiness retry. The retry is allowed only when the same live browser profile remains authenticated, challenge-free, composer-visible, and scoped to the trusted conversation URL. No Cloudflare/rate-limit bypass, host-CDP/session-manager path, or copied-profile trust is introduced.

## v0.1.103.10.76 repair decision

`v0.1.103.10.76` normalizes only the known visible thinking preambles `Thought for a couple of seconds` and `Thought for a few seconds` before release-live exact sentinel validation. The matcher remains fail-closed: the final non-empty line must equal the expected sentinel exactly and every preceding non-empty line must be one of the known preambles.

## v0.1.103.10.78 repair decision

`v0.1.103.10.78` keeps sentinel normalization and product-clean `LIVE_BLOCKED` classification. The decision is to require exact canonical filenames for normal `pb src add` / `pbsa`: visible suffix-renamed sources such as `name(1).zip` block before upload, and backend-created suffixes after upload return `backend_renamed_source` instead of success.


## v0.1.103.10.79 repair decision

`v0.1.103.10.79` preserves exact canonical file-source semantics and adds an authoritative surface gate. A zero-card snapshot without an explicit empty-state marker is a loading/unknown state, not proof that the project is empty. Backend suffix allocation is detected immediately after a committed upload and never accepted as success.

## v0.1.103.10.80 repair note

Candidate artifact: `chatgpt_claudecode_workflow-2_v0.1.103.10.80.zip`.

Active repair slice: `v0.1.103.10.80 — reuse the verified candidate image during auth bootstrap and preserve Docker dependency cache`.

`v0.1.103.10.80` keeps the strict all-all gate, sentinel normalization, and authoritative Project Sources preflight. Pre-source-add auth bootstrap reuses the exact verified candidate service with `--no-recreate`; stable Docker dependency layers precede release metadata, browser automation versions are pinned, and exhausted Chrome transport downloads are classified as `docker_browser_dependency_download_failed`.

## v0.1.103.10.81 repair note

Canonical artifact: `chatgpt_claudecode_workflow-2_v0.1.103.10.81.zip`.

Download transport artifact: `chatgpt_claudecode_workflow-2_transport_v0.1.103.10.81_b7c1de9f28.zip`.

Active repair slice: `v0.1.103.10.81 — separate candidate transport filename from canonical Project Source filename`.

`v0.1.103.10.81` keeps the strict all-all gate, sentinel normalization, authoritative Project Sources preflight/suffix rollback, and verified candidate-image reuse. It separates the unique ChatGPT attachment transport basename from the canonical repo+version release artifact, validates the transport ZIP's internal VERSION and integrity, materializes the canonical local copy, and uploads/adopts only that canonical identity.


## v0.1.103.10.82 — Library-backed overwrite reconciliation

Decision: keep `pbsa <file>` unchanged and replace the obsolete assumption that removing a Project Source frees its filename. Same-name overwrite must reconcile only exact, attributable backing file IDs in ChatGPT Library and Recently deleted before canonical re-upload. Loose text deletion and ambiguous cross-project deletion are prohibited.

## v0.1.103.10.83 — authoritative Library surfaces and upload identity capture

Decision: Library and Recently deleted are separate release-blocking evidence surfaces. Empty results require the configured stable observation count on the actual loaded route. An unavailable Recently deleted surface is not equivalent to empty. File upload responses retain bounded, redacted diagnostics and must provide an exact backing file ID before suffix cleanup is considered reconcilable.

## v0.1.103.10.84 — source replacement before Library cleanup

Decision: normal fresh file adds must not inspect Library or Recently deleted. Same-name overwrite must first use an explicit replace/update action bound to the exact existing Project Source identity. Remove-and-reupload is not a live fallback. Library cleanup is evidence-driven and may run only after a visible suffix family or a backend-assigned suffix proves a collision.


## v0.1.103.10.86 diagnostic decision

Decision: preserve normal `pbsa` behavior and add a diagnostic-only A/B runner that executes the verbatim 10.75 transaction beside the current transaction against two disposable projects. No release artifact upload, adoption, existing source mutation, or platform-gitops file is allowed. Planned after acceptance remains v0.1.104.

## v0.1.103.10.87 diagnostic authentication decision

Decision: the diagnostic endpoint remains bearer-token protected. The standalone runner must resolve the same standard Promptbranch CLI configuration and environment sources rather than weakening endpoint authentication or requiring operators to duplicate secrets on the command line.

## v0.1.103.10.89 exact backing-object deletion decision

Decision: the diagnostic may delete a Library object only when both the processed `file_...` ID and `libfile_...` metadata-object ID are captured from the authoritative upload transaction. Filename-only deletion and guessed backend endpoints are forbidden. It must remove the Project Source, prove stable source absence, delete the exact backing object from active Library and Recently deleted, prove the exact IDs absent on both authoritative surfaces, and only then call the unchanged 10.75 fresh-upload transaction with changed bytes. The prior `(1)` Project Source remains untouched as evidence.


## v0.1.103.10.90 exact backend protocol decision

Decision: the visible Library UI is not an authoritative exact-ID control surface for Project Source backing files. The diagnostic therefore captures all redacted fetch/XHR traffic without URL-token filtering, derives inventory and deletion contracts from a newly created disposable Library file, requires exact `libfile_...` or `file_...` identity binding, replays only the discovered authenticated mutations, verifies exact absence through the discovered backend inventory, shields automatic conversation-history requests on Library routes, and fails closed before reupload when any contract or exact-ID proof is missing. `pbsa` remains unchanged.


## v0.1.103.10.91 ID-driven Library inventory decision

A completed `process_upload_stream` event establishes the disposable file's `file_...` and `libfile_...` identity but does not establish immediate rendered Library visibility. Backend inventory discovery and visibility verification therefore use `/backend-api/files/library/nodes` plus exact identity polling. UI visibility is a later, separate prerequisite only for observing the disposable delete mutation. Diagnostic failure before that point is classified as inconclusive and cannot trigger target deletion or canonical reupload.


## v0.1.103.10.92 private authenticated replay decision

The successful browser request and the public diagnostic protocol are separate representations. Raw executable request headers, including any authorization/account context, exist only in the in-memory protocol watch and are never serialized. Replays use the private representation. Public reports use the sanitized representation. A captured exact-ID `200` is observation one; one further authenticated exact-ID observation is required. `401` and `403` stop immediately as `backend_inventory_replay_unauthorized`.


## v0.1.103.10.93 exact Library UI binding decision

The Library grid may insert layout whitespace inside a filename. The diagnostic may reconstruct only the already expected canonical basename from contiguous rendered tokens or stable DOM attributes. It may not infer an arbitrary filename, select by extension, select the first result, or accept a numeric-suffix sibling. A destructive UI action requires one exact reconstructed UI record, zero suffix-family records, a unique backend-proven `libfile_...`, and one uniquely marked card.


## v0.1.103.10.94: Library mutation requires a unique actionable row

A filename match in an ancestor, navigation item, or column header is not mutation authority. A disposable Library mutation requires one leaf-like row with local exact-filename evidence, file metadata, one row-owned action menu, and a unique backend `libfile_...` binding.


## v0.1.103.10.95: Library row proof and menu proof are separate gates

A Library file row may be authoritative before its action menu is visible. Promptbranch first binds one exact filename leaf to the nearest local metadata-bearing row, then scrolls and hovers that exact row to discover one row-owned menu. Repeated backend observations of the same `libfile_...` are one object, not competing records. A non-authoritative Library surface stops before row binding and cannot be classified as row absence.

## v0.1.103.10.96: a soft-delete click is not deletion proof

The diagnostic must capture one successful exact-ID backend mutation and then prove the disposable `libfile_...` is absent from active inventory or explicitly marked trashed for two authenticated observations. Recently deleted navigation, endpoint discovery, exact deleted-inventory presence, and permanent deletion are separate gates. Accepted/current remains `v0.1.103.10.68`; release `pbsa` and adoption remain prohibited.


## v0.1.103.10.97: processing completion is a separate proof phase

`/backend-api/files/process_upload_stream` is a long-lived event stream, not an ordinary save request. Ordinary save quietness may be reached while this known stream remains open, but the source operation cannot succeed until the stream emits terminal completion and the combined events prove the exact processed-file ID, Library metadata ID, and expected filename. Stream failure, timeout, incomplete identity, and generic diagnostic exceptions must produce explicit machine-readable `reason` values.

## v0.1.103.10.98: processing proof precedes UI persistence proof

A Project Source file cannot be checked for rendered persistence until `/backend-api/files/process_upload_stream` has reached terminal completion with exact `file_...`, `libfile_...`, and canonical filename identity. Response headers are not body-completion evidence for the long-lived SSE request. The response is retained privately and parsed only after `requestfinished`; the watcher remains installed through terminal processing and persistence verification.


## v0.1.103.10.99: diagnostic upload path owns the processing-before-persistence invariant

The backend-protocol diagnostic intentionally uses the isolated `v0.1.103.10.75` transaction body rather than normal `pbsa`. Therefore processing-stream ordering must be enforced in that exact diagnostic-only path, not merely in the normal source-add implementation. A caller-level invariant rejects any result where ordinary quietness reports a pending processing stream but no `processing_stream` result is present.

## v0.1.103.10.100: diagnostic trace capture is observational and time-bounded

Generic Fetch/XHR trace capture may never hold the diagnostic lifecycle open indefinitely. Streaming response bodies are omitted from the generic trace, non-streaming body reads and task settlement are bounded, unresolved tasks are reported with sanitized URL/phase/method/resource/content-type metadata, and the main diagnostic returns `fetch_xhr_protocol_watch_settle_timeout` rather than hanging. Project Source processing-stream ownership remains unchanged.

## v0.1.103.10.101: visible-Library upload identity requires a dedicated stream owner

Generic Fetch/XHR tracing remains observational and must not read long-lived processing streams. The disposable visible-Library upload therefore owns a separate bounded watcher installed before file selection and disposed after terminal handling. Only its exact terminal `file_...`/`libfile_...`/filename tuple may authorize later deletion identity.


## v0.1.103.10.102: deletion discovery is sequence-bound, phase is audit metadata

A mutable global phase is not a reliable transaction boundary because requests may start in one phase and their response-capture tasks may finish after a later phase transition. Every request therefore snapshots its phase and sequence once at request start. For the row-scoped visible-Library Delete action, the diagnostic first settles prior capture work, freezes the maximum request sequence, then clicks Delete. A successful paired mutation with `sequence` greater than that boundary is authoritative; phase remains useful for audit but cannot exclude a valid post-boundary mutation. Exact backing identity is still mandatory before replay or further deletion.


## v0.1.103.10.103: Library deletion requires confirmation or exact direct mutation proof

A row-menu Delete click is only an intent signal. Promptbranch may report `delete_triggered` only after a unique destructive confirmation has been clicked and an exact post-boundary backend mutation is discovered, or after an exact direct mutation proves a no-confirmation UI flow.

## v0.1.103.10.104: authoritative backend presence permits one bounded Library UI recovery

When the exact disposable Library identity is stably present in authenticated backend inventory but the active Library UI remains non-authoritative, the diagnostic may perform exactly one bounded recovery cycle: clear and reapply the exact filename search, poll again, then perform at most one controlled page reload and reapply the exact search. Backend presence alone never authorizes an unrelated row click; exact UI row binding remains mandatory. The v0.1.103.10.103 deletion-confirmation contract is unchanged.

## v0.1.103.10.105: artifact state is project-scoped only; legacy registry compatibility is removed

Promptbranch is still under active development, so artifact state uses a clean-break model rather than migration compatibility. Every artifact read or mutation requires an explicit `.promptbranch-repo.json`, configured project membership, canonical repo-root agreement, and an already initialized valid project registry. Repo-local `.pb_profile/promptbranch_artifacts.json` files are obsolete and block artifact operations until removed or archived. Missing, unreadable, invalid, or noncanonical project-registry state fails closed. `pb project join` is the sole registry initializer; read commands never synthesize empty state. No legacy import, registry reconciliation, filename-order inference, or automatic adoption is provided.

## v0.1.103.10.106: canonical artifacts and backend-assigned Project Source names are separate identities

A canonical local artifact such as `platform-gitops_v0.0.6.6.zip` remains the release, Git, version, and registry artifact identity even when ChatGPT persists it as `platform-gitops_v0.0.6.6(14).zip`. Promptbranch accepts that assigned name only when one exact indexed card is correlated to the current upload through terminal processing-stream `file_...` and `libfile_...` identities and stable read-back. One existing correlated indexed source is reused; multiple family members or incomplete identity proof fail closed. Service retries do not pre-delete remembered sources.


## v0.1.103.10.107: the stream-assigned filename becomes the verification target immediately

A pre-existing indexed Project Source such as `(14)` is pre-upload family evidence, not a reuse target for a normal `pb src add`. Promptbranch uses one escaped canonical/indexed-family regex, records the highest existing suffix, uploads exactly once, and then treats the processing-stream `assigned_filename` such as `(15)` as the sole persistence-verification target. Once that assigned identity is known, canonical unsuffixed persistence retries are forbidden. An index increment of one is diagnostic evidence, not mutation authority; exact current-upload file/libfile identity and one unique exact assigned card remain authoritative.


## v0.1.103.10.109: capacity pruning is one-slot, exact, and fail-closed

A successful file-source add is now a replacement transaction, not merely proof that the new assigned card exists. After the assigned source is proven, every other visible member of the same escaped filename family is removed by exact identity. Success requires an authoritative final surface with exactly one family member, the source assigned to the current upload.


## v0.1.103.10.110: uninitialized registry is observable in read-only plans, never implicit mutation authority

Read-only source-sync validation may report a missing project artifact registry as an uninitialized state. It must not initialize, repair, or infer artifact authority. Invalid or unreadable registries and every artifact mutation remain fail-closed. Test commands must retain a complete terminal JSON envelope even when a preflight step fails.

## v0.1.103.10.111: unavailable Replace uses the verified family transaction; read-only uninitialized state is not mutation authority

- A missing in-place Replace action is a capability result, not permission to delete the existing source first.
- Generic file replacement follows upload-new, exact assigned-name verification, exact old-family removal, and singleton verification.
- Read-only smoke may accept `project_scope_unresolved` or `artifact_registry_missing` only when every mutation flag is false.
- Lifecycle planning may describe an uninitialized authority surface, but execution remains blocked.
- Artifact adoption and registry mutation still require valid initialized project-scoped authority.


## v0.1.103.10.112: overwrite authority is the changed upload identity, never a predicted suffix or rediscovered old singleton

- The full integration fixture rewrites the file with deterministic replacement content and requires a different SHA-256 before requesting overwrite.
- A backend-assigned `<stem>(index).<ext>` name is a normal member of the canonical file family. The exact `process_upload_stream` result is authoritative; visible suffix maxima do not predict the next index.
- Upload-new/verify/delete-old may delete only Project Source identities frozen before upload. A concurrently appearing family member is not deleted and makes final singleton verification fail closed.
- Old-source deletion is prohibited until the new upload has a completed processing stream, an exact assigned filename in the requested family, a `processed_file_id`, and a `library_metadata_object_id`.
- An unchanged/no-network second upload cannot return replacement success; it reports a structured release-blocking failure.
- `full_direct` and `full_localhost` both remain mandatory before adoption.

## v0.1.103.10.113: replacement staging changes the browser-selected basename, not the canonical identity

- When in-place Replace is unavailable, changed bytes are copied to a temporary collision-free numeric family member such as `name(8472193501).ext` before browser file selection.
- The staging token is a local transaction identifier only. It never predicts, reserves, or validates the backend-assigned Library index.
- The canonical requested identity remains `name.ext`; `process_upload_stream` remains the sole authority for the actual assigned canonical/indexed filename and backing IDs.
- The staged copy must be byte-identical to the requested replacement, match the canonical family regex, and be removed after browser selection.
- No old Project Source may be deleted until the newly assigned source has completed processing, both backing identities are present, and exact assigned-card read-back succeeds.
- `full_direct` and `full_localhost` remain mandatory before adoption.

## v0.1.103.10.114: continuous live evidence uses one physical slot and current-flow causality

- A path already ending in `slots/slot-N` is a resolved physical profile and must never be passed through profile pooling again.
- External visual-artifact and release-live steps use the same exact host slot, mapped to `/app/profile`, with profile leasing disabled for those commands.
- Submit causality may be proven by a post-click `POST /backend-api/f/conversation`, a Sentinel prepare/finalize pair, or `IS_STREAMING`; the obsolete prompt-marker shape is not the only authority.
- A structurally valid `promptbranch.ask.reply` on a newly created post-submit assistant turn is causal response evidence and may end the long wait.
- `submit_causality_not_confirmed` is not a Cloudflare classification without an actual challenge marker.
- `full_localhost` is an independent execution gate; direct browser/source evidence reuse is forbidden.


## v0.1.103.10.115: adoption is bound to joined identity and exact upload evidence

Release-control adoption must not reconstruct authority from a canonical filename. When `--adopt-after-validation` is requested, the same run must upload the Project Source, capture the backend-assigned filename and both backing identities, and invoke `pb project join` with the explicit release repository identity and source-add project URL before validation. The later artifact-adopt mutation must consume that evidence and fail closed on any identity mismatch. Response completion is a collection concern independent of envelope parsing, and rate-limit retry classification is structured-only.

## v0.1.103.10.116: post-adoption verification distinguishes artifact and assigned-source identity

`v0.1.103.10.115` is accepted/current because its validation and evidence-bound adoption completed successfully. The post-adoption verifier must not collapse the canonical release artifact filename and the backend-assigned Project Source filename into one identity. `state.artifact_ref` and `registry_current.filename` remain canonical; `state.source_ref` must equal the exact assigned filename captured before validation. Both backing IDs and all existing version/consistency invariants remain mandatory. No adoption mutation is repeated by this repair.

## ADR-PROJ-101 — v0.1.104 sandbox mutation verification remains temporary, exact, and terminal

- **Status:** accepted for candidate implementation
- **Baseline:** `v0.1.103.10.116`
- **Active slice:** `v0.1.104 — Sandbox mutation verification and rollback evidence gate`
- **Decision:** the loop may mutate only one copied fixture in a temporary workspace. Success requires declared before/after hashes, exact corrected contents, one allowlisted sandbox validation command, proof that validation is read-only, exact rollback, an unchanged repository fixture, workspace deletion, and an immediate stop.
- **Fail-closed rule:** missing or contradictory identity/evidence, validation failure, repository drift, rollback failure, or cleanup failure blocks the result.
- **Next slice:** `v0.1.105 — Sandbox correction promotion readiness check` evaluates evidence only and does not grant broader mutation authority.
- **Forbidden:** repository mutation, deployment, Kubernetes mutation, Project Source mutation, artifact adoption from the loop, and ChatGPT Project deletion.

## v0.1.104.1 — mandatory sandbox release gate

Decision: the sandbox mutation/rollback proof is release-blocking. It must appear in the release-validation manifest and as an explicit all-tests step. Reusable evidence identity includes the manifest SHA-256. This repair forbids direct evidence reuse and retains independent localhost execution without broadening sandbox authority.


## v0.1.104.2 — bounded post-bootstrap conversation-idle recovery

Decision: preserve the `v0.1.104.1` sandbox and transport gates unchanged. After a completed bootstrap response, perform a bounded composer-readiness probe. Only `interrupted_answer_state` by itself permits one reload of the same trusted conversation in the same page/context/profile. Reverify the bootstrap sentinel and a clean idle composer before the ask. Never resubmit bootstrap, create another conversation, or infer rate limiting without structured evidence.


## v0.1.104.4 — current-turn-scoped interrupted-state readiness

- A visible Retry or Regenerate control is release-blocking only when it belongs to the latest assistant turn or active composer state.
- Historical Retry controls are recorded as ignored evidence and do not block an otherwise idle composer.
- Pre-bootstrap readiness is a separate gate and cannot invoke post-bootstrap recovery.
- Post-bootstrap recovery is eligible only after successful submission, exact sentinel observation, and completed generation.
- The one permitted reload must preserve the same page/context/profile/conversation and wait boundedly for hydration before sentinel/readiness checks.
- No Retry click, historical prompt resubmission, new conversation, or general retry is permitted.
- The v0.1.104 sandbox verifier remains unchanged and may be run standalone before strict release validation.

## v0.1.104.5 — Hermetic release-validation profile isolation

Decision: offline release-validation subprocesses must own explicit temporary HOME, TMPDIR, XDG cache/config/data/state, Promptbranch profile, project state/config, and project cache paths. A child-process preflight must prove every resolved path stays inside the isolation root before pytest starts. If repository `.pb_profile` or its browser lock remains reachable, the node fails closed before execution. Ambient lock contents are never read and no lock wait is attempted. The 300-second scheduler-group timeout, per-node progress, and no automatic retry remain unchanged.

## ADR-PROJ-102 — v0.1.105 readiness is repeated evidence assessment, not promotion authority

- **Status:** accepted for candidate implementation
- **Baseline:** `v0.1.104.5`
- **Active slice:** `v0.1.105 — Sandbox correction promotion readiness check`
- **Decision:** execute the existing sandbox-only mutation/validation/rollback proof three independent times by default. Assess exact evidence completeness, require distinct temporary workspaces, canonicalize deterministic evidence only, and require one identical SHA-256 fingerprint for `ready`.
- **Result states:** `ready`, `not_ready`, and `blocked` are the only terminal readiness states.
- **Authority boundary:** `ready` permits only the planned `v0.1.106 — Controlled correction promotion decision record`. It does not record a GO decision and grants no repository, deployment, Kubernetes, Project Source, artifact-adoption, or Project-deletion authority.
- **Fail-closed rule:** invalid target/run count, missing runs, execution failure, incomplete evidence, failed sandbox gates, unsafe evidence, non-deterministic fingerprints, or non-independent workspace identity cannot produce `ready`.
- **Preserved:** the v0.1.104 sandbox implementation and 13-gate release verifier, ten release gates, fresh direct, independent localhost, current-turn readiness, visual completion, source handling, and adoption behavior.


## ADR-PROJ-103 — v0.1.105.1 promotion-readiness repository authority is target-anchored

- **Decision:** An absolute readiness target must derive one authoritative repository root from target ancestors unless `--repo-root` is supplied explicitly.
- **Fail closed:** Missing, ambiguous, marker-invalid, or non-containing roots return `blocked` before evidence execution.
- **Authority:** No broader mutation or promotion authority is granted.


## ADR-PROJ-104 — v0.1.106 records GO for execution-envelope design only

- **Status:** accepted for candidate implementation
- **Baseline:** `v0.1.105.1` accepted/current after 10/10 GO and `release_adopted_and_verified`.
- **Decision:** record GO only when exactly three complete independent sandbox evidence runs satisfy all mandatory readiness, determinism, rollback, cleanup, and zero-authority checks. Otherwise record NO-GO.
- **Recorded evidence:** one canonical fingerprint `470e04f73c008bcd49827102f94f84e447f6f8618db69ae3272159f637959756`, three distinct temporary workspaces, and 32/32 mandatory decision checks.
- **GO scope:** authorize only `v0.1.107 — Controlled correction execution envelope design`.
- **Forbidden:** correction execution, disposable- or real-repository mutation, deployment, Kubernetes mutation, Project Source mutation, artifact adoption from the loop, ChatGPT Project deletion, generic write authority, and automatic correction.
- **Fail closed:** any missing, contradictory, unsafe, non-deterministic, non-independent, failed-validation, repository-drift, rollback, cleanup, root-resolution, or authority evidence records NO-GO.

## ADR-PROJ-105 — v0.1.107 execution envelope is design data, not execution authority

- **Status:** accepted for candidate implementation
- **Baseline:** `v0.1.106` accepted/current after 10/10 GO and `release_adopted_and_verified`.
- **Decision:** define one deterministic future disposable-repository correction envelope with exact target, mutable file, operation, pre/post hashes, validation, rollback, limits, timeouts, evidence requirements, and a canonical fingerprint.
- **Authority boundary:** the design authorizes only `v0.1.108` envelope validation. Correction execution, disposable- or real-repository mutation, generic shell authority, deployment, Kubernetes mutation, Project Source mutation, artifact adoption, and Project deletion remain forbidden.
- **Fail closed:** missing or contradictory decision, target, path, hash, validation, rollback, limit, timeout, or authority evidence blocks design before any execution.

## ADR-PROJ-106 — v0.1.108 validates the envelope and resolves the duplicate roadmap assignment

- **Decision:** `v0.1.108` remains `Controlled correction execution envelope validation gate`, as assigned by the adopted `v0.1.107` project control surface.
- **Reason:** repository control data is authoritative over earlier conversational roadmap proposals.
- **Validation boundary:** validation recomputes and compares the complete envelope and canonical fingerprint while creating no workspace, executing no command, mutating no file, and granting no correction execution authority.
- **Roadmap resolution:** the earlier `PROJECT_SETTINGS.md` proposal is renumbered to `v0.1.109 — PROJECT_SETTINGS.md, AGENTS.md and project authority-graph definition`.
- **v0.1.109 boundary:** definition, normalization, conflict detection, and read-only drift verification only; remote ChatGPT Project Settings mutation remains forbidden.

## ADR-PROJ-107 — Repair v0.1.108 before beginning the authority-graph slice

- **Status:** accepted for the active candidate.
- **Decision:** `v0.1.108` remains not adopted after strict release validation reproduced independent Project Source lifecycle failures. `v0.1.108.1 — Project Source staged-overwrite and removal-proof reliability` is the active repair.
- **Overwrite rule:** when in-place Replace is unavailable, upload-new/verify/delete-old may retry exactly once only when no upload commit, processing stream, or backing identity exists and the original source remains authoritatively present.
- **Removal rule:** a delete interaction is not success evidence. The refreshed authoritative Project Sources surface must classify the target as `verified_absent`, `still_present`, or `surface_unresolved`; only two stable absent observations pass.
- **Scope rule:** the repair does not redesign the v0.1.108 execution-envelope validator and does not begin `v0.1.109`.
- **Promotion:** focused direct and localhost reliability profiles must pass before full release validation; adoption still requires green `full_direct` and `full_localhost` plus all existing gates.

## ADR-PROJ-108 — v0.1.109 assigns one owner per fact domain without precedence

- **Status:** accepted for candidate implementation.
- **Baseline:** `v0.1.108.1` is accepted/current after focused reliability validation and a 10/10 retry release run ending in `release_adopted_and_verified`.
- **Decision:** every declared project fact domain has exactly one authority owner. Other representations are projections, runtime observations, or evidence.
- **Conflict rule:** missing authority, duplicate ownership, forbidden fallback/precedence rules, and projection drift fail closed.
- **Runtime rule:** `.promptbranch-repo.json` and the project artifact registry remain runtime authorities and are reported as deferred in clean static package validation; they are not inferred from repository prose.
- **External rule:** ChatGPT Project Settings are externally owned read-only observations. This slice performs no remote settings mutation.
- **Next:** `v0.1.110` may derive a structured read-only project snapshot from the accepted graph; it may not auto-repair drift without a later explicit authority grant.

## ADR-PROJ-109 — v0.1.109.1.1 tracks intended Project binding and separates runtime evidence

- **Status:** accepted for repair candidate implementation.
- **Baseline:** `v0.1.109` remains accepted/current; `v0.1.109.1` was not adopted.
- **Decision:** `.promptbranch-repo.json` is stable repository authority, committed to Git and included in release ZIPs.
- **Runtime separation:** checkout membership, project registry storage, adopted artifact records, assigned Project Source names, processed-file IDs, Library metadata IDs, and adoption timestamps remain user-local runtime evidence.
- **Join rule:** `pb project join` consumes the tracked binding to recreate user-local configuration. Explicit supplied values are verification inputs and must match; mismatch fails closed without rewriting authority.
- **Recovery rule:** accidental deletion is recoverable from Git or the canonical release ZIP.
- **Import rule:** candidate ZIP import installs the tracked binding and must not preserve a stale checkout-local copy.
- **Migration:** other projects follow `docs/migrations/tracked-project-binding-v0.1.109.1.1.md`; there is no silent missing-binding compatibility fallback.


## ADR-PROJ-110 — Establish the tracked backlog before implementing ISSUE-001 and PBAI-001

- **Status:** accepted for candidate implementation.
- **Baseline:** `v0.1.109.1.1` is accepted/current after 10/10 validation and `release_adopted_and_verified`.
- **Decision:** `v0.1.110` creates `docs/backlog/backlog.json` as the machine-readable backlog authority and records exactly two open tickets: `ISSUE-001` followed by `PBAI-001`.
- **Priority:** ISSUE-001 is implemented first. PBAI-001 depends on ISSUE-001 lifecycle evidence integration.
- **Invariant:** Promptbranch controls the release lifecycle. Each project defines what must be validated and how its artifact is built.
- **Classification:** historical DoD rows, failed candidates, repair history, and rolling-horizon slices are not backlog tickets unless explicitly entered in the backlog authority.
- **Scope boundary:** `v0.1.110` adds tickets and validation only; it does not implement `.promptbranch-release.json`, lifecycle execution/publication/adoption, or PBAI runtime validators.
- **Next:** `v0.1.111 — Global release lifecycle contract and read-only planner`.

## ADR-PROJ-1112 — Observable full-test progress and bounded fail-fast

`v0.1.111.2` reports current work, pass/fail/skip counts, percentage complete, elapsed time, and approximate ETA. Fail-fast stops only after a failed browser phase or required validation group; it does not weaken any gate. Next normal version: `v0.1.112`.

## v0.1.111.3 browser fail-fast boundary

Expected-result normalisation is part of the browser step transaction and must occur before a terminal progress event. `--fail-fast` stops only on the final normalised result of a main browser step. Expected missing, expected unsupported, and expected skip remain passes. A genuine failure records one failed unit, prevents the next main browser step, and marks all remaining work units skipped. The wider release controller remains continue-on-failure so it can produce a complete release verdict; this repair does not introduce a global release-gate fast-stop option.

## ADR-PROJ-1114 — Trusted external-live conversations are identity-only

- **Status:** accepted for candidate implementation.
- **Baseline:** `v0.1.109.1.1` remains accepted/current; `v0.1.111.3` was not adopted after two complete runs reproduced the same busy trusted-conversation failure.
- **Decision:** the trusted warmup conversation proves login and exact Project scope but is never the release mutation target. Release-live hands off in the same browser context/profile to the exact Project home and creates a dedicated task conversation only after bounded idle readiness.
- **Safety:** no automatic Stop action, no typing into a running conversation, no root Project discovery, no profile copy, and no fallback to the operator-owned conversation when the dedicated task does not produce a conversation URL.
- **Accounting:** one causal idle-handoff failure blocks release; dependent live gates are `skipped_dependency_failed`, not independent defects.
- **Next repair:** `v0.1.111.5` corrects ETA without changing validation authority or transport independence.

## ADR-PROJ-1115 — ETA is named-step observability, never validation authority

- **Status:** accepted for candidate implementation.
- **Baseline:** `v0.1.111.4.1` is accepted/current after 10/10 strict validation and `release_adopted_and_verified`.
- **Decision:** progress ETA is calculated from successful named-step timing observations, preferring same-step/same-transport medians and using same-phase fallback only when necessary.
- **Transport boundary:** direct timing may be used as an ETA-only prior for localhost; it cannot satisfy, replace, reuse, or weaken localhost validation evidence.
- **Skip boundary:** steps known to be skipped are excluded before ETA calculation.
- **Stability:** while the active plan only shrinks, the countdown cannot increase; a visibly running overrun step retains a bounded non-zero tail.
- **Persistence:** bounded timing history is atomically stored under `.pb_profile`; missing, malformed, or unwritable history degrades ETA to unknown.
- **Authority:** ETA cannot change pass/fail, fail-fast, release verdict, publication, adoption, or accepted/current verification.
- **Next:** after acceptance, open `v0.1.112 — PBAI-001 declaration and structural validation`.

## ADR-PROJ-11151 — Stable ETA includes an empty-step-safe shell boundary and monotonic high range

- **Status:** accepted for corrective candidate implementation.
- **Baseline:** `v0.1.111.5` is accepted/current after 10/10 strict validation and `release_adopted_and_verified`.
- **Shell boundary:** progress emitted after a completed top-level step may have no active current step; the associative array is indexed only when the step name is non-empty.
- **Range boundary:** while the active plan is unchanged or shrinking, both the ETA midpoint and high bound are non-increasing.
- **Expansion boundary:** the range may expand only when the active plan genuinely expands or an unknown estimate becomes known.
- **Authority:** ETA remains informational and cannot change pass/fail, fail-fast, transport independence, release verdict, publication, adoption, or accepted/current verification.
- **Next:** after acceptance, open `v0.1.112 — PBAI-001 declaration and structural validation`.

## ADR-PROJ-112 — Introduce PBAI-001 declaration and structural proof without overclaiming

- **Status:** accepted for candidate implementation.
- **Baseline:** `v0.1.111.5.2` is accepted/current.
- **Decision:** `v0.1.112` introduces `.promptbranch-ai.json` as the sole tracked AI application architecture declaration and implements only declaration and structural proof.
- **Schema:** `promptbranch.ai.application` version `1.0` supports `runtime_application` and `domain_module`.
- **Required structure:** one sole version authority, runtime provider/contract version, ten non-empty architecture layers, generic-runtime delegation/ownership, bounded authority boundaries, and bounded project-local validation commands.
- **Safety:** planning and structural validation are read-only. Declared commands are inspected but not executed. Mutation, release, publication, and adoption require explicit request plus verified evidence and cannot be self-granted.
- **Proof boundary:** registry, executable, and operational levels fail closed as not implemented. Structural evidence may never be promoted to a higher proof level.
- **Release integration:** the Promptbranch runtime declaration must pass as a required release-validation group.
- **Ticket state:** PBAI-001 remains `in_progress`; registry resolution, executable evidence, operational proof, templates, migrations, and the first domain-module proof remain open.
- **Next:** after acceptance, open `v0.1.113 — PBAI-001 registry validation and reference resolution`.


## ADR-PROJ-113 — Add strict PBAI registry proof without executing application behavior

- **Decision:** `v0.1.113` introduces `.promptbranch/ai-registry.json`, declaration schema `1.1`, and read-only registry validation.
- **Resolution:** every Agent, Skill, Tool, Validator, state contract, evidence contract, capability, and authority controller must resolve exactly once to a declared and statically inspectable implementation.
- **Safety:** registry validation imports no project module, executes no declared command, mutates no state, and grants no release, publication, or adoption authority.
- **Failure policy:** missing/ambiguous IDs, mismatched Skill or MCP manifests, unresolved symbols/contracts, incomplete capability ownership, and unbounded authority fail closed at structural proof.
- **Ticket state:** PBAI-001 remains `in_progress`; executable, operational, templates, migrations, and domain-module proof remain open.
- **Next:** after acceptance, open `v0.1.114 — PBAI-001 executable validation and SkillRun evidence`.

## Decision — v0.1.114 executable proof uses one portable read-only skill

- **Decision:** PBAI-001 executable proof is provided by `promptbranch.skill.application-architecture-proof`, not by a Git-dependent inspection skill.
- **Reason:** source trees, clean ZIP extractions, and installed package validation must execute the same proof even when the extraction directory is not a Git worktree.
- **Contract:** the proof executes exactly `filesystem.read` then `filesystem.list` through MCP stdio, with two steps maximum and a 30-second per-call bound.
- **Evidence:** `promptbranch.ai.skill_run` version `1.0` records full step results plus argument/result digests and a canonical evidence hash.
- **Authority:** executable proof grants no mutation, release, publication, or adoption authority.
- **Next:** after acceptance, open `v0.1.115 — PBAI-001 operational validation and lifecycle evidence`.

## ADR-PROJ-1141 — Candidate runtime identity is explicit release evidence

- **Status:** accepted for corrective candidate implementation.
- **Baseline:** `v0.1.113` remains accepted/current; `v0.1.114` is repair-required after strict host validation failed package import in an ambient shadow environment.
- **Decision:** release control resolves the pipx candidate venv after installation and treats its exact Python, `pb`, and `promptbranch` paths as release evidence.
- **Fail-closed boundary:** PATH shadowing, distribution-version drift, interpreter-prefix drift, or missing candidate executables stops before Project Source mutation or tests.
- **Dependency boundary:** FastAPI and Starlette are pinned as one tested compatibility pair and import-smoke verifies the installed versions.
- **Scope:** no PBAI capability, SkillRun behavior, lifecycle authority, publication authority, or adoption authority is added.
- **Next:** after repair acceptance, open `v0.1.115 — PBAI-001 operational validation and lifecycle evidence`.

## ADR-PROJ-115 — Development tests may be selective; adoption tests may not

- Status: accepted for candidate `v0.1.115`.
- Decision: use a checked-in impact map and dependency closure for edit/component/candidate development loops.
- Boundary: unknown changed paths fail closed, and every result declares the strict release gate deferred and still required.
- Operational proof: generated only after strict adoption and validated against exact artifact, Project Source, registry, state, rollback, and recovery evidence.
- Next: `v0.1.116` — PBAI-001 templates, migration reports, and first domain-module proof.

## ADR-PROJ-1151 — Cross-process browser ownership must use the advertised bounded queue

- **Status:** accepted for corrective candidate implementation.
- **Baseline:** `v0.1.114.2` remains accepted/current; `v0.1.115` is repair-required after strict external-live validation failed before adoption.
- **Decision:** in-process and cross-process browser-profile locks share one bounded queue deadline. External `flock` contention is polled until acquisition or deadline; it cannot bypass the scheduler with an immediate failure.
- **Evidence:** timeout payloads identify the observed owner PID, operation, operation ID, acquisition time, liveness, poll count, and owner transitions where available.
- **Handoff:** live preflight and continuous live use the same service transport. Release control additionally proves service idle and host-level `flock` release before continuous live begins.
- **Authority:** the repair changes no PBAI, publication, adoption, accepted/current, or strict-gate authority.
- **Next:** after repair acceptance, open `v0.1.116 — PBAI-001 templates, migration reports, and first domain-module proof`.
## v0.1.116 — PBAI template and differential-validation boundary

- Templates are deterministic plans by default and write only with explicit `--write`.
- Migration reporting is read-only and emits explicit gaps; it never silently changes a repository.
- Differential validation executes the local reference validator and Promptbranch validator on identical isolated copies and fails if Promptbranch is weaker.
- The embedded `promptbranch-method` proof snapshot is based on the real v0.1.0 project structure and authoritative corpus metadata, but does not claim an external repository commit, push, or release.

Planned after `v0.1.116` acceptance: `v0.1.117 — PBAI compliance inventory and multi-repository rollout`.

## ADR-REL-117 — Generic release pipeline uses explicit ordered authority boundaries

- **Status:** accepted for `v0.1.117` candidate implementation.
- **Baseline:** Promptbranch `v0.1.116` remains accepted/current.
- **Decision:** local proof precedes Git synchronization; Project Source publication follows same-run push; adoption consumes exact source evidence; accepted/current verification is a separate final phase.
- **Safety:** plan mode is read-only, apply requires exact version confirmation, mutation flags are opt-in, and later phases are skipped after failure.
- **Independence:** `promptbranch-method` continues independently on Promptbranch `>= v0.1.116` and may adopt this pipeline later through an explicit compatibility release.
- **Next:** `v0.1.118` adds resumable/importable evidence and recovery without replaying completed mutation phases.

## ADR-REL-117.1 — Adopted release identity is immutable and reusable evidence is canonical-artifact bound

- **Baseline:** `v0.1.117` accepted/current.
- **Decision:** once a repository/version is adopted, a different SHA-256 for that same version fails closed before Project Source mutation or artifact-registry mutation.
- **Idempotence:** the same version, canonical filename, SHA-256 and consistent accepted/current state is an idempotent success; duplicate upload and adoption are skipped.
- **Evidence reuse:** reusable direct validation evidence binds to the canonical rebuilt artifact SHA-256, repository identity, Git commit, transport, service base, runtime mode, source-kind matrix and command signature. The transport ZIP is not acceptance authority.
- **Versioning:** changed bytes require a new version. No override or silent replacement path is introduced.


## ADR-REL-118 — Importable checkpoints and guarded pipeline recovery

- **Baseline:** `v0.1.117.1` accepted/current.
- **Decision:** `v0.1.118` writes incremental checkpoints, validates imported evidence read-only, and resumes only from immutable phase evidence.
- **Safety:** successful remote mutation phases are reused rather than silently replayed; changed bytes, divergent Git identity, ambiguous Project Source identity, or stale accepted/current evidence fail closed.
- **Next planned after acceptance:** `v0.1.119 — Read-only multi-repository release-set dependency planner`.

## ADR-REL-118.1 — Canonical ZIP bytes and pre-adoption publication identity are immutable

- **Context:** The first `v0.1.118` run published SHA-256 `e45cb908...` and then failed from host disk exhaustion. A clean rerun from the same Git commit rebuilt a byte-different ZIP with SHA-256 `d28cae9...`, uploaded an indexed replacement and removed the first source before adoption.
- **Decision:** The repository-owned builder is the only authority for canonical release bytes. It fixes ordering, timestamps, permissions and uses stored ZIP entries to eliminate compressor implementation variance. Release control rebuilds twice and requires exact byte identity.
- **Decision:** Release control writes an atomic checkpoint before source mutation. The first successful publication binds the exact canonical hash and backend-assigned source identity as a provisional immutable release identity, even before validation or adoption.
- **Decision:** Full reruns automatically import this checkpoint. Exact bindings reuse the existing source; artifact, Git or contract drift fails before source mutation. Successful adoption finalizes the same checkpoint.
- **Consequence:** Interrupted releases no longer create indexed replacement sources or silently change same-version bytes. The normal roadmap remains at `v0.1.119`; this repair advances no normal scope.

## ADR-PROJ-119 — Release-set planning is project-scoped, deterministic, and read-only

- **Status:** accepted for candidate `v0.1.119`.
- **Decision:** Add `pb release set plan` using schema `promptbranch.release_set` version `1.0`. Resolve repositories through the tracked project binding and joined-repo configuration. Resolve dependencies from release-set targets first and accepted/current project registry state second. Emit deterministic dependency order, parallel waves, a compatibility matrix, artifact verification observations, and a canonical plan SHA-256.
- **Fail-closed rule:** Unknown repositories, project mismatch, cycles, unsupported constraints, missing external current state, incompatible versions, noncanonical artifacts, unsafe paths, invalid ZIPs, VERSION mismatch, and SHA-256 drift block the plan.
- **Mutation boundary:** No Git, repository, registry, Project Source, publication, adoption, deployment, or rollback mutation is permitted.
- **Consequence:** `v0.1.120` may consume only an explicit compatible and immutable plan under a separately authorized guarded execution contract.

## Decision D-0120 — Exact-plan-bound release-set execution with mandatory reverse rollback

- **Status:** accepted for candidate `v0.1.120`.
- **Decision:** `pb release set apply` may execute only a freshly recomputed `promptbranch.release_set` plan that is compatible, locally artifact-verified and SHA-256-bound. Mutation requires exact `release_set_id` and `plan_sha256` confirmation plus explicit `--execute`, `--rollback-on-failure`, `--stage-all`, `--commit`, `--push`, `--publish`, `--adopt` and `--verify-current` flags.
- **Decision:** Each target repository executes through its existing generic release pipeline. Dependency waves determine order, while repositories inside a wave execute deterministically rather than concurrently.
- **Decision:** Before mutation, Promptbranch records every target repository's accepted/current version, canonical artifact, SHA-256, assigned Project Source, processed file ID and Library metadata ID. The first repository failure stops the rollout. Previously completed repositories invoke their repository-owned `operations.rollback` contract in reverse completion order.
- **Decision:** Rollback succeeds only when the exact previous artifact and Project Source identity are observed again. Any command failure or identity mismatch yields `release_set_rollout_failed_rollback_incomplete`.
- **Decision:** Every transition is atomically checkpointed. Events are SHA-256 hash chained and the complete summary has a canonical evidence SHA-256 validated by `pb release set evidence-validate`.
- **Consequence:** Arbitrary shell execution, implicit lifecycle flags, plan drift, unverified artifacts, parallel mutation, Project deletion and automatic interrupted-run resume remain unavailable.
- **Next:** `v0.1.121` may add import/resume and operator reconciliation for interrupted or incompletely rolled-back release sets without weakening the exact-plan and evidence rules.

## Decision D-0120.1 — Checkpoint helper must not restore caller-owned errexit

- **Status:** accepted for repair candidate `v0.1.120.1`.
- **Decision:** `release_control_checkpoint_preflight` may return control codes `0` and `10` but must not enable Bash `errexit` internally. The caller owns the `set +e` / capture / `set -e` envelope and is the only layer permitted to classify those codes.
- **Reason:** `v0.1.120` correctly imported the exact provisional identity and returned `10`, but its inner `set -e` caused the shell to terminate before the caller selected the source-reuse branch.
- **Consequence:** The original `v0.1.120` bytes are repair-required. `v0.1.120.1` must execute the actual checkpoint function under code `10` and prove continuation to test execution.

## DEC-2026-08-03-121 — Recovery requires read-only identity reconciliation and exact digest confirmation

**Decision:** An interrupted release-set rollout or rollback may resume only from an existing atomic checkpoint after a read-only reconciliation proves each repository is exactly at its pre-rollout identity or exact target identity. The reconciliation result is canonically hashed and must be explicitly confirmed by the operator before mutation.

**Rationale:** Process interruption can occur between a successful external mutation and checkpoint persistence. Replaying the repository pipeline risks duplicate Git, Project Source, publication, or adoption mutations. Current registry identity is therefore authoritative for deciding which repositories are already complete, pending, require rollback, or are ambiguous.

**Consequences:** Verified target repositories are skipped, pending repositories continue in deterministic order, rollback resumes in reverse dependency order, manually repaired rollback can be finalized without command replay, and ambiguous or missing state blocks automatically. No operator override is inferred.

- **Next planned after acceptance:** `v0.1.122 — Bounded parallel release-set wave execution and concurrency evidence`.

## D-0121.1 — Require explicit HTTP status for auth-bootstrap 403 classification

- **Decision:** The release-control auth-bootstrap wrapper may classify a backend challenge only from an explicit structured `backend_api_guardrail` event with numeric status `403` or an already terminal explicit 403 challenge status.
- **Reason:** `v0.1.121` proved that the generic `backend_api_guardrail_seen=true` summary flag is also emitted for conversation-history HTTP 429 events and therefore cannot identify the status class.
- **Safety:** Explicit 403 remains terminal and fail-closed. HTTP 429 remains rate-limit telemetry and does not bypass authentication or strict validation requirements.
- **Scope:** Repair-only. Release-set reconciliation, resume, rollback, publication, adoption, and mutation authority are unchanged.
- **Next:** `v0.1.122` remains the next normal slice after repair acceptance.

## D-0122 — Freeze scope and require explicit evidence for MVP proof cycle 1

- **Status:** accepted for candidate `v0.1.122`.
- **Baseline:** `v0.1.121.1` is accepted/current after strict 10/10 validation and evidence-bound adoption.
- **Decision:** Defer bounded parallel release-set wave execution until after MVP completion. Reserve `v0.1.122` and `v0.1.123` for two consecutive normal proof cycles.
- **Decision:** A proof cycle is valid only when explicit evidence confirms real artifact download and verification, strict 10/10 GO with no failed or skipped outer gates, visual smoke ZIP transport, adoption, exact accepted/current identity, and a continuation protocol request whose baseline is the newly adopted release.
- **Decision:** Proof evaluation is deterministic and read-only. The evaluator emits a canonical SHA-256 and fails closed on missing, malformed, stale, ambiguous, repair-version, or mismatched evidence.
- **Consequence:** `v0.1.122` does not claim MVP completion at package build time. Cycle 1 completes only after strict host evidence produces `mvp_proof_cycle_passed`. A repair resets the consecutive normal-cycle count.
- **Next:** `v0.1.123 — Canonical MVP proof cycle 2 and final MVP verdict`.

## ADR-PROJ-123 — MVP proof continuation is authorized only after exact evidence preflight

**Status:** accepted for candidate `v0.1.122.1`

**Context:** Accepted/current `v0.1.122` passed strict release validation, but the post-adoption MVP proof finalizer could not read the real project-level `repos.<repo-id>` current shape, did not bind intake/adoption/current evidence to the candidate SHA-256, issued the continuation Ask before validating intake, and could print `verified` after a failed verifier because shell errexit was not enabled.

**Decision:** Treat continuation as an action authorized only by a successful read-only proof preflight. The preflight must resolve the requested repository from project-level current output and prove exact version, artifact filename, and SHA-256 equality across candidate, intake, adoption, and current evidence. The finalizer uses `set -Eeuo pipefail`, preserves verifier exit status, and prints success only after `mvp_proof_cycle_passed`.

**Consequence:** `v0.1.122` remains accepted/current but does not count as a completed normal MVP proof cycle. `v0.1.122.1` is repair-only. The clean consecutive sequence resets to `v0.1.123` for cycle 1 and `v0.1.124` for cycle 2/final verdict.

## D-0138 — One `pb ask` command owns each canonical MVP proof cycle

- **Decision:** The only operator command for a normal proof cycle is `pb ask continue --target-version <next-normal> --release-type normal`.
- **Reason:** The split operator workflow allowed a later generic answer lookup to select an unrelated historical `no_artifact` response after `v0.1.123` had already been adopted.
- **Consequence:** `pb ask` must create the candidate-producing request, retain exact request/message/answer identity, perform intake, strict validation/adoption, current verification, continuation proof, and final proof evaluation as one fail-closed transaction.
- **Safety:** Attachments, explicit conversation override, and `--new-task` are rejected for this exact integrated spelling. Ordinary `pb ask` behavior is unchanged.
- **MVP sequence:** `v0.1.123.1` is repair-only; `v0.1.124` is cycle 1 and `v0.1.125` is cycle 2.


## DEC-2026-08-04 — Explicit conversation pinning is mandatory for MVP proof

- **Decision:** `pb ask continue` proof mode requires `--conversation-url`.
- **Authority:** the CLI argument is authoritative for candidate Ask, response correlation, artifact intake, and continuation Ask.
- **Failure policy:** missing, malformed, cross-project, or mismatched conversation identity fails before release mutation.
- **No fallback:** remembered task state, project home, latest chat, and visible browser tab are not valid implicit selectors for formal proof.
- **Sequence:** `v0.1.123.2` is repair-only; `v0.1.124` and `v0.1.125` remain proof cycles 1 and 2.


## DEC-2026-08-04-123.2.1 — Project authority compares immutable UUID aliases without rewriting tracked state

- **Decision:** Project authority comparisons extract the immutable `g-p-<32-hex>` UUID from bare ids, slugged ids, Project URLs, and Project conversation URLs.
- **Alias rule:** Bare and slugged forms are equivalent only when both contain the same immutable UUID. Values without an immutable UUID retain exact comparison.
- **Authority preservation:** The tracked `.promptbranch-repo.json` remains authoritative and must not be rewritten during reconciliation.
- **Failure policy:** A different immutable Project UUID remains a release-blocking mismatch.
- **Sequence:** `v0.1.123.2.1` is repair-only; `v0.1.124` and `v0.1.125` remain normal proof cycles 1 and 2.


## DEC-2026-08-04-123.2.2 — Release-control caller verifies Project aliases by immutable UUID

- **Decision:** The release-control post-`pb project join` verifier compares requested, returned, and tracked Project identities through the immutable `g-p-<32-hex>` UUID.
- **Exact boundary:** `repo_id` remains an exact comparison and non-UUID Project identifiers retain exact comparison.
- **Authority preservation:** The tracked `.promptbranch-repo.json` remains authoritative and is not rewritten.
- **Failure policy:** Missing identity, mixed UUID/non-UUID identity, or a different immutable Project UUID remains release-blocking before validation.
- **Sequence:** `v0.1.123.2.2` is repair-only; `v0.1.124` and `v0.1.125` remain normal proof cycles 1 and 2.
## DEC-184 — Scope backend-403 response failure to confirmed submission

- **Decision:** response waiting evaluates only backend-403 events at or after the current confirmed-submit cursor; unrelated attachment-download telemetry is non-terminal while the pinned conversation remains healthy.
- **Fail-closed boundary:** current-operation conversation 403s, challenge/root transitions, or target closure remain terminal.
- **Timeout invariant:** browser response 1800s, fresh-turn 120s, artifact materialization 180s, safety 120s; outer lifecycle step is at least 2220s.
- **Sequence:** `v0.1.123.2.3` is repair-only; `v0.1.124` and `v0.1.125` remain proof cycles 1 and 2.



## v0.1.123.2.5 two-component release answer

A successful ask-release answer is exactly one rendered ZIP output followed by one marked reply envelope. The generic JSON-only lead-in is not used for release candidates.


## ADR-PROJ-124 — Correlated rendered attachment is authoritative transport evidence

The exact assistant answer selected by persisted request/answer identity is the only valid source for release attachment discovery. The browser must resolve and download the rendered control through its authenticated context; textual sandbox metadata alone is insufficient. This repair preserves `v0.1.124` and `v0.1.125` as proof cycles and schedules `v0.1.126` and `v0.1.127` after them.

## ADR-PROJ-125 — Contain ambient FastAPI/Starlette drift without changing release pins

- **Decision:** Keep the supported `fastapi==0.128.2` and `starlette==0.50.0` constraints unchanged. At service-module import, install a narrow Router compatibility bridge only when the ambient Starlette constructor no longer accepts the legacy event arguments that FastAPI 0.128.x still passes.
- **Boundary:** The bridge restores only constructor/event lifecycle compatibility. It does not suppress unrelated dependency failures or declare Starlette 1.x supported for release validation.
- **Testing:** A subprocess regression must simulate the modern Router signature and import the real service module. Focused CLI fixtures must establish their own Project/repository identity rather than relying on the current working tree.
- **Consequence:** Local focused tests can diagnose the rendered-attachment repair instead of failing during unrelated module collection, while strict release installation remains governed by the pinned candidate environment.


## DEC-2026-08-05-123.2.6 — Historical artifact replay requires exact persisted request identity

- **Status:** accepted for candidate `v0.1.123.2.6`.
- **Decision:** A staged replay of a named historical protocol result must select `.pb_profile/ask_protocol_runs/<request-id>.json` by exact request ID. Chronological `latest validated` selection remains available for generic inspection but is not authoritative for evidence-bound replay.
- **Fail-closed rule:** Invalid or sanitized request-ID aliases, missing files, unvalidated records, and payload/request-ID mismatches stop before candidate extraction, browser download, verification, migration, or adoption.
- **Reason:** A newer valid `no_artifact` continuation reply correctly displaced the older `v0.1.124` artifact-producing run, causing Gate 2 to replay the wrong evidence while behaving according to the old CLI contract.
- **Consequence:** Gate 2 uses `--protocol-run-request-id req_20260805T105438125979Z`. No valid no-artifact record is skipped or reclassified, and no attachment/candidate validation rule is weakened.

## DEC-2026-08-05-123.2.6-R2 — Unvalidated artifact replay is explicit, exact-ID, and attachment-failure-only

- **Status:** accepted for corrected candidate `v0.1.123.2.6`.
- **Decision:** A persisted run with `reply_validation_ok=false` may enter artifact intake only when the operator supplies the exact request ID and the explicit `--replay-unvalidated-artifact-run` flag together with `--download --verify`.
- **Allowlist:** The initial and only replayable prior run status is `artifact_declared_but_not_attached`, with only the corresponding download-proof validation/failure codes.
- **Identity boundary:** Request, correlation, request envelope, reply envelope, conversation, message, selected answer, and selected-protocol-reply identities must be complete and internally equal before browser access.
- **Mutation boundary:** Any evidence of prior download, verification, materialization, migration, Project Source mutation, registry/state mutation, or adoption makes the record non-replayable. Migration is forbidden during this replay command.
- **No bypass:** Normal `--from-last-protocol-run` and exact validated-run selection remain unchanged. The flag cannot ignore arbitrary validation failures, replay `no_artifact`, or reinterpret failed generation.
- **Reason:** The historical run failed at missing rendered-attachment proof; requiring that same proof to be already validated made the repair Gate 2 unreachable.
- **Sequence:** This correction only opens Gate 2 for the existing answer. It does not authorize a fresh `v0.1.124` generation, publication, adoption, or proof-count movement.



## DEC-2026-08-05-123.2.6-R3 — Legacy persisted-run normalization is replay-local and contradiction-sensitive

- **Status:** accepted for replacement candidate `v0.1.123.2.6`.
- **Decision:** The explicit attachment-failure replay path may normalize the historical record aliases proven by request `req_20260805T105438125979Z`: missing selection-summary copies, MIME-type-only ZIP typing, `input_baseline`, and the historical three-code attachment failure set.
- **Identity rule:** Missing duplicate fields may fall back to exact run/request/correlation and selected-answer identity. Any present contradictory value is terminal.
- **Artifact rule:** Missing `kind` is accepted only with an exact `.zip` filename and allowlisted ZIP MIME type. An explicit non-ZIP kind or MIME type remains terminal.
- **Failure rule:** `reply_validated` is treated as attachment-derived only when filename, version, role, exact count, release-candidate status, and no-successful-download checks prove the rest of the envelope matched.
- **Boundary:** The normal validated-run loader, generic parser, and migration/adoption paths are not relaxed.
- **Reason:** The real Gate 2 record is structurally safe but predates fields introduced by the replay repair itself; requiring those newer duplicate fields made the replay circular.

## Decision — finalize already materialized ask-release runs idempotently

For an exact request-ID record whose rendered attachment was already downloaded and verified but whose final result remained `release_candidate_validation_failed`, Promptbranch may perform an inbox-only finalization pass. Eligibility requires exact request/correlation/message/answer identity, one expected candidate ZIP, normalized request/reply baseline agreement, positive rendered-attachment proof, exact persisted inbox path, matching SHA-256/size/entry-count/CRC/version, and no migration, Project Source, registry/current, or adoption mutation. The finalizer must not redownload. Any contradiction remains fail-closed.


## DEC-2026-08-05-123.2.6-R4 — Exact validated-run identity is preserved through candidate migration

- **Status:** accepted for replacement candidate `v0.1.123.2.6`.
- **Decision:** Replay, finalization, normal validated intake, and migration use one contradiction-sensitive persisted-run ZIP/baseline normalizer.
- **Transport rule:** A validated materialized run may reuse only its exact artifact-inbox path; ordinary verification must reopen the ZIP and recheck envelope metadata before migration.
- **Orchestration rule:** `candidate-run` uses `--from-last-protocol-run --protocol-run-request-id <exact-id>` and carries expected repository, filename, and version. It must not fall back to `--from-last-answer` when an exact validated run is available.
- **State rule:** This step may create one candidate-registry entry only. Candidate tests, Project Source publication, adoption, current-state advancement, commit, and push remain separate gates.
- **Reason:** The verified `v0.1.124` bytes were safe, but duplicated normalization and chronology-based command construction prevented migration.


## ADR-PROJ-126 — Separate PB environment completion from external application development

- **Status:** accepted for documentation and `v0.1.125` planning.
- **Decision:** Treat Promptbranch as System A, the deterministic control plane. Treat every application/tool developed with PB as System B with independent repository, architecture, tests, candidate registry, accepted/current baseline, and deployment authority.
- **Preserved roadmap:** `v0.1.125`, `v0.1.126`, and `v0.1.127` retain their previously defined scopes.
- **Extended roadmap:** append `v0.1.128` PB environment hardening; `v0.1.129` external app bootstrap; `v0.1.130` controlled change; `v0.1.131` test/diagnose/correct; `v0.1.132` app candidate/acceptance; `v0.1.133` non-production deployment; `v0.1.134` reusable/multi-repo workflow.
- **Authority boundary:** PB environment validation is not application validation. Application source mutation begins only after an app-specific execution envelope, exact allowlists, pre-change snapshot, rollback evidence, and operator authorization.
- **Release inclusion:** the boundary document, roadmap, plan-state update, and draw.io pages are mandatory contents of `v0.1.125`.


## Active repair candidate — v0.1.125.1

- accepted/current baseline: `chatgpt_claudecode_workflow-2_v0.1.124.zip` (`v0.1.124`)
- failed normal candidate retained as evidence: `chatgpt_claudecode_workflow-2_v0.1.125.zip`
- active repair artifact: `chatgpt_claudecode_workflow-2_v0.1.125.1.zip`
- active repair slice: v0.1.125.1 — Isolated compileall and repeatable template-snapshot validation repair
- next normal slice remains: `v0.1.125 — Canonical PB environment proof cycle 2 and final control-plane verdict`
- planned after repair acceptance: `v0.1.126 — Persistent whole-release ETA estimator`
- scope advancement: forbidden; repair only isolates compileall bytecode and restores repeatable cache-free validation
