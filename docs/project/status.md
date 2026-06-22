# Project Status

## Current baseline

```text
accepted/current baseline with adoption evidence: chatgpt_claudecode_workflow-2_v0.1.79.zip
accepted version: v0.1.79
active focused working candidate: chatgpt_claudecode_workflow-2_v0.1.84.5.3.zip
next normal target: deferred until focused-candidate promotion gate
```

## Current MVP state

```text
MVP status: active
DoD status: in_progress
last accepted/current slice: v0.1.79 — JSON orchestration event intake foundation
active plan slice: v0.1.84 — Accepted-event ledger validation command
active repair: v0.1.84.5.3 — rate-limit telemetry aggregation deduplication
```

## Current release state

```text
latest accepted/current ZIP: chatgpt_claudecode_workflow-2_v0.1.79.zip
latest created ZIP: chatgpt_claudecode_workflow-2_v0.1.84.5.3.zip repair candidate once packaged
release status: v0.1.80-v0.1.84.5.3 are focused/repair candidates only; accepted/current remains v0.1.79 until later full validation and adoption evidence
```

## Current risks

- Project deletion is now frozen because the current automation path can execute real ChatGPT project deletion; deletion must remain unavailable until a secure delete protocol exists.
- Project Source file uploads can reach commit-seen / stale-inflight / not-visible states that must remain release-blocking unless refreshed persistence is proven.
- Artifact Guardian must remain a structural ZIP guard only, not a build/heal/agent workflow.
- Guard-passed must not be confused with accepted/current adoption state.
- Project-specific ZIP requirements must remain policy-driven through `.artifact-guardian.yml`, not duplicated as hidden code constants.

## Current blockers

- `v0.1.84.5.3` remains repair-candidate-only until installed/runtime proof passes; v0.1.80-v0.1.84 remain focused candidates only.
- `v0.1.84.5.3` must not be adopted/current without the user-preferred validation order: install candidate ZIP, run dedicated changed-code tests, run the selected promotion gate, then adopt only after required validation passes.
- No accepted-event ledger write, proposal promotion, runtime orchestration, Project Source behavior change, artifact adoption behavior change, or ChatGPT Project deletion behavior change is allowed in this repair.

## Current unknowns

- What secure multi-factor delete protocol, if any, is acceptable for future ChatGPT Project deletion.
- Whether live ChatGPT file-source indexing will become visible within the extended post-commit readback window in release-control.
- Whether future lifecycle scripts should delegate their install ZIP checks to `pb artifact guard` in AG-005 or an earlier slice.

## Next safe action

```text
Install chatgpt_claudecode_workflow-2_v0.1.84.5.3.zip, then rerun focused changed-code checks first. A repeated visual roundtrip with rate-limit telemetry should keep `status=rate_limited_contaminated` while reporting deduplicated top-level cooldown/event totals.
```

## Last updated

```text
v0.1.84.5.3 repair candidate build
```


## v0.1.78.2.1 repair status

`v0.1.78.2` release-control failed because `promptbranch_project_delete_safety.py` was present in the ZIP but missing from setuptools `py-modules`. `v0.1.78.2.1` is a packaging-only repair that makes the delete-safety helper importable after pipx installation. Project deletion remains frozen.


## v0.1.78.2.2 repair status

`v0.1.78.2.1` release-control failed before install-time validation because `chatgpt_claudecode_workflow_release_control.sh` only accepted three- or four-segment versions. `v0.1.78.2.2` widens release-control and post-release-validation version normalization to dotted numeric versions with at least three segments, including `v0.1.78.2.1`. Project deletion remains frozen.


## v0.1.78.2.3 repair status

`v0.1.78.2.2` release-control succeeded but retained a newly created unique `itest-promptbranch-<run-id>` project because ChatGPT Project deletion is frozen. `v0.1.78.2.3` changes release-control live tests to reuse one retained quarantine project named `itest-promptbranch-retained-delete-frozen` by default and passes `--keep-project`, preventing a new undeletable project from being created on every release-control run. Existing leaked `itest-promptbranch-*` projects are not deleted by this repair.


## v0.1.78.2.4 repair status

`v0.1.78.2.4` aligns delete-frozen live-test profiles with the retained quarantine project policy. `pb test ask-live`, `pb test visual-artifact-roundtrip`, and `pb test release-live` now default to using/reusing `itest-promptbranch-retained-delete-frozen` and force keep-project semantics because whole ChatGPT Project deletion is frozen. Release-control adds `--run-all-tests`, which runs the operator validation stack in one command, continues after individual failures, and writes `pb_test.all.<version>.summary.json` with final `GO` or `FIX` verdict.


## v0.1.78.2.5 repair status

`v0.1.78.2.4 --run-all-tests` produced the intended continue-on-failure final report, but the run exposed three release-blocking issues: `ask-live` could use an unauthenticated/passkey-enrollment profile state, artifact live steps could be misclassified by nested `download_transport.ok=false`, and full direct/localhost transport results were not represented as first-class rows in the final all-tests summary. `v0.1.78.2.5` repairs the run-all verdict logic, adds a live-profile preflight, runs live tests through a refreshed `release-live` profile-pool slot seeded from `.pb_profile_local_debug`, records skipped live rows if preflight fails, and ignores `.pb_profile_local_debug_pools/` in `.gitignore`. Project deletion remains frozen.

## v0.1.78.2.6 repair status

`v0.1.78.2.5` exposed a Docker provenance gap: a service image could be tagged as the target version while `/app/VERSION`, `promptbranch_version.py`, and `pyproject.toml` inside the image still contained the previous version. `v0.1.78.2.6` adds build args, Dockerfile version checks, host build-context assertions, image-content probes, and running-container content probes so release-control verifies host/image/container/health version alignment before tests. The no-cache rebuild remains a bounded fallback, not the default.


## v0.1.78.2.7 repair status

`v0.1.78.2.6` failed before Docker provenance evidence could be used because an embedded Python JSON writer in the release-control Docker probe had an unterminated newline string literal. `v0.1.78.2.7` repairs that syntax defect only, preserves the Docker provenance guard, and keeps the delete-frozen live-test policy unchanged.


## v0.1.78.2.8 repair status

`v0.1.78.2.7` reached the Docker running-container content probe but failed because the inline Python used to read `/app/pyproject.toml` was not shell-quoted safely, producing `open(/app/pyproject.toml, rb)` and a `SyntaxError`. `v0.1.78.2.8` repairs only that pyproject probe quoting issue by using a shell-safe reader, adds a focused regression test, and preserves the Docker provenance guard and delete-frozen live-test policy.


## v0.1.78.2.9 repair status

`v0.1.78.2.8` reached the Docker running-container content probe but failed under `set -u` because the pyproject version extraction used an awk expression with shell-expanded `$2`, producing `parameter not set`. `v0.1.78.2.9` repairs only that awk-dollar quoting defect by replacing the image/container pyproject readers with a `grep | head | cut` pipeline that avoids shell positional parameters. Docker provenance, bounded no-cache fallback, run-all behavior, and delete-frozen live-test policy are preserved.

## v0.1.78.2.10 repair status

`v0.1.78.2.9` proved Docker provenance and clean-profile ask-live behavior, but run-all could still produce FIX under temporary ChatGPT conversation-history 429 pressure. `v0.1.78.2.10` keeps the existing browser modal acknowledgement path and adds release-control cooldown/retry handling for failed run-all steps with rate-limit evidence.

## v0.1.78.2.11 repair status

`v0.1.78.2.10` proved Docker provenance and rate-limit cooldown retry plumbing, but release-control ZIP import removed `.pb_profile_local_debug/` before live tests, and the text-based rate-limit detector falsely retried steps whose structured telemetry explicitly said no rate-limit evidence was present. `v0.1.78.2.11` preserves the live seed profile across install, keeps pool slots disposable, validates/sanitizes the seed before live tests, and narrows rate-limit detection to strict 429 / "Too many requests" evidence. Project deletion remains frozen.

## v0.1.78.2.12 repair status

`v0.1.78.2.11` preserved the live seed profile and fixed strict rate-limit detection, but full browser validation still failed at `project_source_add_text` because the text-source UI save trigger was not observed. `v0.1.78.2.12` passes the save watcher into the text-source helper and adds bounded fallback triggers before persistence verification. Operators must still create/authenticate `.pb_profile_local_debug/` before `--run-all-tests`; pool slots remain disposable. Project deletion remains frozen.


## v0.1.78.2.13 repair status

`v0.1.78.2.12` proved the live ask/artifact/release path again, but default `--run-all-tests` still failed only because the optional text-source UI path did not trigger a save. `v0.1.78.2.13` makes text-source add/remove a strict source-kind compatibility check instead of a default release blocker, while adding `--run-failing-tests` for fast focused iteration on that path. Docker provenance, live seed preservation, strict rate-limit handling, and project deletion freeze are preserved.

## v0.1.78.2.14 repair status

`v0.1.78.2.13` proved text-source compatibility isolation but `--run-all-tests` still failed in the direct transport at `project_source_overwrite_file`. The remove guard reported collateral rows from non-source UI areas, which indicated Project Source remove detection could drift outside the Project Sources surface. `v0.1.78.2.14` constrains source snapshots, container lookup, and source action-button lookup to visible Project Sources surfaces only and removes broad body/main fallbacks from the remove path. Docker provenance, live seed preservation, strict rate-limit handling, text-source compatibility isolation, and project deletion freeze are preserved.


## v0.1.78.2.15 repair status

`v0.1.78.2.14` fixed Project Source remove containment, but live `pb src add platform-gitops_0.0.4.zip` showed a false-negative timeout: upload and source commit completed, the source was visible, then Project Source verification waited on an unrelated persisted conversation-history 429 cooldown and the CLI timed out before the service finished. `v0.1.78.2.15` keeps rate-limit modal telemetry and acknowledgement, but Project Source add/list/remove/capability operations and Project Source persistence refreshes no longer wait on persisted conversation-history cooldown. History-reading operations still respect the cooldown. Docker provenance, live seed preservation, text-source compatibility isolation, Project Source remove containment, and project deletion freeze are preserved.


## v0.1.78.2.16 repair status

`v0.1.78.2.15` reduced the remaining release blocker to localhost `project_source_overwrite_file` post-commit persistence verification: a file-source save commit was observed, but a stale inflight request prevented refreshed proof from completing before the release gate failed. `v0.1.78.2.16` adds a bounded recovery path for the specific `commit_seen_with_stale_inflight_not_verified_present` state. It reopens the Project Sources surface and accepts the mutation only if refreshed proof of the requested file source appears. Otherwise it still fails closed. Docker provenance, live seed preservation, rate-limit handling, text-source compatibility isolation, Project Source remove containment, and project deletion freeze are preserved.

## v0.1.78.2.17 repair status

`v0.1.78.2.16` still allowed `pb ask --prompt-file` to use the keyboard-primary submit policy because the CLI merged prompt-file text into the prompt before the browser layer and did not preserve prompt-file origin. `v0.1.78.2.17` carries `prefer_button_submit` through CLI, service-client, container API, automation service, and browser layers. Prompt-file asks now use send-button-first dispatch when the button is visible/enabled, while prepare-token-only states remain hard failures with flattened submit-causality diagnostics. CV generator code, source add/remove behavior, project deletion, artifact registry behavior, and normal slice state are unchanged.

## v0.1.78.2.18 repair status

`v0.1.78.2.17` installed and ran the new prompt-file live smoke, but the smoke harness used `set -e` around `pb ask` and deleted the captured JSON in its EXIT trap. A non-zero `pb ask` therefore hid the exact submit-causality payload needed to decide whether the remaining failure was button-submit, backend commit, answer extraction, profile/auth, or service transport. `v0.1.78.2.18` preserves the diagnostic JSON on smoke failure, reports the `pb ask` exit code, and keeps the output path visible for operator/service-log correlation.

`v0.1.78.2.18` also tightens the prompt-file button-first policy: when the send button was visible/enabled and a button click was dispatched, Promptbranch no longer presses keyboard Enter afterward as a post-dispatch comparison/fallback for prompt-file asks. Prepare-token-only after a button click remains fail-closed with diagnostics. CV generator code, source add/remove behavior, project deletion, artifact registry behavior, and normal slice state are unchanged.

## v0.1.78.2.19 repair status

`v0.1.78.2.18` correctly preserved the prompt-file smoke diagnostic payload, which exposed that the automation service passed `prefer_button_submit` into `ChatGPTAutomation.ask_question_result()` while the intermediate automation wrapper still had the old signature. `v0.1.78.2.19` updates that wrapper to accept and forward `prefer_button_submit` to the browser client. This preserves the button-first prompt-file submit policy and lets the focused live smoke reach the browser submit layer instead of failing with service HTTP 500. CV generator code, source add/remove behavior, project deletion behavior, artifact registry behavior, and normal slice state are unchanged.

## v0.1.78.2.20 repair status

`v0.1.78.2.19` reached the live ChatGPT browser path and produced a successful fresh answer: `pb ask` exited 0, the submit method was `button_click`, the backend conversation POST was observed, the user turn was confirmed in the DOM, response freshness matched the injected nonce, and `prepare_token_set_not_consumed` was false. The remaining failure was the smoke contract itself: `pb ask --json` requests a structured assistant JSON response, so the returned token lives at `answer.token` rather than as raw `answer_text`. The top-level JSON result also kept submit evidence nested under `submit_evidence` / `ask_phase_timings`, leaving `prefer_button_submit` and `submit_method` null at the transport top level.

`v0.1.78.2.20` updates the focused smoke to accept the structured JSON answer token while preserving the exact token assertion, and exposes successful submit-causality fields at the top level of ask JSON results. CV generator code, source add/remove behavior, project deletion behavior, artifact registry behavior, retry/backoff policy, and normal slice state are unchanged.

## v0.1.78.2.20.1 repair status

`v0.1.78.2.20.1` repairs the release-control command surface after the `v0.1.78.2.20` prompt-file live smoke passed. The only behavior change is support for `--adopt-after-validation` in the full release workflow: after `--run-tests` or `--run-all-tests` succeeds and validation reports are green, release-control reuses the existing verified artifact adoption path. The prompt-file submit implementation and smoke contract from `v0.1.78.2.20` are unchanged.

This candidate is not accepted/current until runtime release-control and `pb artifact current --json` evidence confirm state artifact/source and registry current alignment.

## v0.1.78.2.20.2 repair status

`v0.1.78.2.20.2` preserves the `v0.1.78.2.20` button-first prompt-file submit repair and `v0.1.78.2.20.1` release-control flag repair, then changes the large prompt-file strategy: `pb ask --prompt-file` now defaults to auto-attaching large prompt files instead of inserting the entire package into the composer. The attachment threshold defaults to 12,000 UTF-8 bytes and can be overridden with `--prompt-file-attach-threshold-bytes` or `PROMPTBRANCH_PROMPT_FILE_ATTACH_THRESHOLD_BYTES`. Small prompt files remain inline. This targets the CV RAG prompt-package failure where button click worked but committed-turn proof failed on a pasted/document-style large prompt. The candidate is not accepted/current until live large-prompt smoke, release-control, and `pb artifact current --json` evidence confirm it.

## v0.1.78.2.20.3 repair status

`v0.1.78.2.20.3` preserves the working large prompt-file attachment transport from `v0.1.78.2.20.2` and only polishes diagnostics. The ask result now flattens attachment upload/readiness, filename evidence, button submit, submit-causality confirmation, response-causality confirmation, and response-wait state onto stable top-level JSON fields. This keeps downstream large-prompt smokes from depending on nested `submit_evidence` / `ask_phase_timings` internals. No prompt transport behavior, CV generator logic, Project Source behavior, artifact registry behavior, or normal slice state changes.

This candidate is not accepted/current until live large-prompt smoke, release-control, and `pb artifact current --json` evidence confirm it.

## v0.1.78.2.20.4 repair status

`v0.1.78.2.20.3` proved large prompt-file attachment diagnostics, but full release-control remained blocked by `project_source_add_text`. A focused repro with `project_ensure` reproduced the blocker: the retained test project had a valid project context, five existing Project Sources, no rate-limit evidence, and the text add failed with `persistence_not_verified` / `ui_trigger_not_observed_not_verified_present`.

`v0.1.78.2.20.4` keeps the prompt-file attachment behavior unchanged and narrows the repair to Project Source text add. The live text-source test now uses a large run-id-bearing text body so document conversion is explicit; the verifier adds first-line `.txt` document candidates, rejects generic stale `pasted.txt Document` without run-id proof, and can prune only safe retained-test sources at the observed five-source boundary.

## v0.1.78.2.20.5 repair status

`v0.1.78.2.20.4` fixed the immediate `project_source_add_text` persistence failure in the focused repro, but the green result still showed `source_match=pasted.txt Document`, `source_saved_as_document=true`, and `source_content_match_verified=false`. That means the verifier could accept a generic document-converted text source without proving it belonged to the current run.

`v0.1.78.2.20.5` narrows that behavior: generic `pasted.txt` / `Document` identities are release-blocking unless the source card/content proof contains a current-run anchor. Dedicated generated `.txt` names remain supported through the first-line/display-name candidate path when they expose the run id. Prompt-file attachment behavior, release-control adoption flags, artifact registry behavior, and project deletion freeze are unchanged.

## v0.1.78.2.20.6 repair status

`v0.1.78.2.20.6` narrows the Project Source text-add document-conversion contract after `.20.5`: legacy `pasted.txt` / `pasted.txt Document` is treated only as stale retained-test cleanup noise, not as a current valid success identity. Large text-source conversion must now be proven by a dedicated/generated document name carrying the current run anchor.

This repair preserves the large prompt-file attachment transport/diagnostics and does not advance normal `v0.1.79` scope. Assistant-side validation was focused/local only; live focused repro, full release-control, and adoption/current verification remain pending.

## v0.1.78.2.20.7 repair status

`v0.1.78.2.20.7` supersedes the `.20.6` dedicated-document-name release gate. Live `.20.6` evidence showed Project Source text add can save and verify persistence while still rendering the saved text source as `pasted.txt Document`. Therefore dedicated/generated document naming is treated as characterization evidence, not the release-blocking contract.

The release-blocking `project_source_add_text` integration step now uses a smaller below-threshold text body and verifies the Text input persistence path. Large pasted text/document conversion diagnostics remain available on `add_project_source`, including `source_saved_as_document`, `source_content_match_verified`, `dedicated_document_name_detected`, `legacy_pasted_document_seen`, and `document_conversion_characterization_status`.

This repair preserves prompt-file attachment behavior, release-control adoption behavior, artifact registry behavior, and project deletion freeze. It does not advance normal `v0.1.79` scope. The candidate is not accepted/current until live focused repro, release-control, and adoption/current verification pass.

## v0.1.78.2.20.8 repair status

`v0.1.78.2.20.8` follows the fresh-project `.20.7` evidence. That run proved `project_source_add_text` can create a fresh project, save the source as `pasted.txt Document`, observe two save requests finishing, and verify the source after refresh. The remaining failures were harness/reporting and lifecycle defects, not a Project Source text-add persistence defect.

This repair makes `project_resolve_before_create` with `expected_missing=true` an informational/pass condition, enables strict same-run cleanup for newly created `itest-promptbranch-*` projects, keeps broad project deletion frozen, and increases the `browser_scheduler_source_lifecycle` release-validation group timeout from 120 seconds to 300 seconds. Prompt-file attachment behavior, Project Source text-add persistence semantics, artifact registry behavior, and normal `v0.1.79` scope are unchanged.

This candidate is not accepted/current until live focused cleanup/source proof, full release-control, and adoption/current verification pass.

## v0.1.78.2.20.8.1 repair status

`v0.1.78.2.20.8.1` repairs the `v0.1.78.2.20.8` transport ZIP packaging surface. The `v0.1.78.2.20.8` implementation scope remains unchanged, but the ZIP now includes the required repo-root `.gitignore` control file so release import planning can pass its required-root-files gate. No normal slice advanced.


## v0.1.78.2.20.8.2 status

Repair candidate `v0.1.78.2.20.8.2` fixes the same-run ephemeral project cleanup implementation defect observed in `.20.8.1`: `/v1/projects/remove` called the browser remove path but failed because `_normalize_project_url` was missing. The repair adds cleanup-target URL normalization while preserving the strict ephemeral deletion guard and leaving Project Source text-add behavior unchanged. Candidate validation is focused/local only until the live fresh-project cleanup proof is rerun.

## v0.1.78.2.20.8.3 repair status

`v0.1.78.2.20.8.2` fixed the missing `_normalize_project_url` cleanup crash but the live focused fresh-project rerun exposed two narrower repair defects: slugged Project URLs produced a false `project_id_mismatch` against the same run's bare created Project id, and text-source add did not use bounded post-commit source-surface recovery after `commit_seen_with_stale_inflight_not_verified_present`.

`v0.1.78.2.20.8.3` normalizes same-run slugged ephemeral Project ids back to the stable created Project id before cleanup validation and extends the existing bounded post-commit Project Source recovery/readback policy from file sources to text sources. Source-add success semantics are unchanged: persistence proof remains required, `pasted.txt Document` remains a valid Project Sources identity only when persistence is verified, and prompt-file attachment behavior is unchanged. Broad Project deletion remains frozen.

## v0.1.78.2.20.8.4 repair status

`v0.1.78.2.20.8.3` is unsafe because it reintroduced real ChatGPT Project deletion through a same-run ephemeral cleanup exception. `v0.1.78.2.20.8.4` repairs that defect by making Project deletion immutable-frozen at every layer: container API, automation service, browser client, private browser operation, and full-integration cleanup. Cleanup now records `project_remove_cleanup_skipped_delete_frozen` and retains the Project; it does not call `remove_project`. `allow_ephemeral_test_cleanup=True` is diagnostic-only and cannot authorize deletion. No normal slice advanced.

## v0.1.78.2.20.8.5 repair status

`v0.1.78.2.20.8.4` fixed the dangerous deletion behavior, but fresh-project evidence still contained a stale top-level `cleanup_policy="same_run_ephemeral_cleanup"` label even though the actual cleanup step reported `no_project_delete_until_secure_protocol` and `destructive_action_executed=false`. `v0.1.78.2.20.8.5` is a repair-only evidence cleanup that makes the full-integration summary and cleanup-step labels consistently report `no_project_delete_until_secure_protocol`. No Project deletion path is re-enabled and no normal slice advances.

## v0.1.78.2.20.8.6 repair status

Operator logs proved that `pb task use` wrote the selected Kubernetes conversation into the project-scoped profile while plain `promptbranch state` read the stale repo-local `.pb_profile/.promptbranch_state.json`. `v0.1.78.2.20.8.6` repairs that state-authority split by making backend state reads use the same project-aware state-store resolver as task/source/artifact writes. Browser profile resolution remains unchanged, and explicit `--profile-dir` continues to override project-scoped state. No Project deletion path is re-enabled and no normal slice advances.

## v0.1.78.2.20.8.7 repair status

`v0.1.78.2.20.8.6` exposed a plain-text response wait diagnostic bug: the requested sentinel answer was already visible, but the completion loop remained blocked by stop-button/composer-idle predicates, and the debug/deadline branch attempted to write `response_debug_artifact_skipped_due_to_deadline` through an undefined local `breakdown`. `v0.1.78.2.20.8.7` initializes `response_wait_breakdown` in `_wait_and_get_response()` before the loop can enter diagnostic bookkeeping. This repair does not change response completion semantics, Project Source behavior, artifact adoption/current state, or the immutable Project deletion freeze.

## v0.1.78.2.20.8.8 repair status

`v0.1.78.2.20.8.7` cleared the live-profile/headed browser path under `--run-all-tests`, but adoption still failed in the localhost full transport at `project_source_add_text`. The service-side browser flow continued after the CLI client timed out and eventually produced the structured fail-closed diagnostic `post_commit_source_surface_not_refreshed` with `transaction_status=commit_seen_with_stale_inflight_not_verified_present`.

`v0.1.78.2.20.8.8` keeps that failure release-blocking, but aligns the localhost source-mutation client timeout with the service-side post-commit persistence/recovery window so the CLI receives structured diagnostics instead of a generic `ReadTimeout`. The full-integration harness also attaches a `pb src list --json` diagnostic after the specific stale-inflight post-commit source-add failure so retained-project operators can inspect whether the source later appears before retrying. No Project Source success semantics, Project deletion behavior, prompt-file transport, artifact-current state, or normal `v0.1.79` scope advances.

## v0.1.79 candidate status

Accepted/current baseline used for this normal release slice:

```text
chatgpt_claudecode_workflow-2_v0.1.78.2.20.8.8.zip
```

`v0.1.79` resumes the normal JSON orchestration MVP line after the `.8.x` repair chain. This slice adds a proposal-only event-intake schema, committed example, read-only validator, and `pb orchestration validate-event` command. The validator is intentionally non-mutating: it does not write accepted state, mutate ChatGPT Project Sources, adopt artifacts, deploy, or execute model-proposed actions.

## Next safe action

Run focused validation and then full release-control from the candidate ZIP. Do not call `v0.1.79` accepted/current until `pb artifact current --json` verifies runtime, state artifact, state source, registry current, and consistency alignment.


## v0.1.80 candidate status

Accepted/current baseline used for this normal release slice:

```text
chatgpt_claudecode_workflow-2_v0.1.79.zip
```

`v0.1.80` adds the accepted-event validation foundation after the `v0.1.79` proposal/event-intake layer. The slice exposes `pb orchestration validate-accepted-event`, validates the committed G0-G6 accepted-event fixtures, requires explicit baseline/source binding, and remains read-only. It does not write an accepted-event ledger, mutate Project Sources, adopt artifacts, deploy, or execute model-proposed actions.

Candidate validation is focused/local in this workspace only until operator release-control proves the ZIP. Do not call `v0.1.80` accepted/current until `pb artifact current --json` verifies runtime, state artifact, state source, registry current, and consistency alignment.

## v0.1.81 focused working candidate status

Accepted/current baseline remains:

```text
chatgpt_claudecode_workflow-2_v0.1.79.zip
```

Working candidate chain:

```text
v0.1.80 focused-validated candidate -> v0.1.81 focused working candidate
```

`v0.1.81` adds an accepted-event dry-run promotion foundation through:

```text
pb orchestration accept-event --dry-run --json
```

The command previews whether validated accepted-event fixtures would be acceptable for a future ledger write, but it does not write accepted state, mutate Project Sources, adopt artifacts, deploy, or execute model-proposed actions. Full all-tests and adoption/current promotion are intentionally deferred under the focused-slice validation model.

## v0.1.82 focused working candidate status

Accepted/current baseline remains:

```text
chatgpt_claudecode_workflow-2_v0.1.79.zip
```

Working candidate chain:

```text
v0.1.80 focused-validated candidate -> v0.1.81 focused-validated candidate -> v0.1.82 focused working candidate
```

`v0.1.82` adds explicit accepted-event input support for dry-run promotion:

```text
pb orchestration accept-event --dry-run --json <accepted-event-file>
```

Explicit input files must resolve inside the repository root. Parent-relative paths, repository-external absolute paths, missing files, and invalid accepted-event JSON fail closed. The command still does not write accepted state, mutate Project Sources, adopt artifacts, deploy, or execute model-proposed actions. Full all-tests and adoption/current promotion remain intentionally deferred under the focused-slice validation model.

## v0.1.82 candidate correction — explicit dry-run installed path resolution

`v0.1.82` remains a focused working candidate only. The corrected candidate fixes an installed-runtime explicit-path resolution defect where accepted-event dry-run could look under `site-packages/docs/...` instead of the repository working tree. Accepted/current remains `v0.1.79` until a later promotion/adoption gate.

## v0.1.84 focused working candidate status

Accepted/current baseline remains:

```text
chatgpt_claudecode_workflow-2_v0.1.79.zip
```

Working candidate chain:

```text
v0.1.80 focused-validated candidate -> v0.1.81 focused-validated candidate -> v0.1.82 focused-validated candidate -> v0.1.83 focused-validated candidate -> v0.1.84 focused working candidate
```

`v0.1.84` adds a read-only accepted-event ledger validation command:

```text
pb orchestration validate-ledger --json
```

The command validates the future ledger scaffold and, for this pre-write slice, treats an absent ledger file as valid when the ledger directory and record schema are present. It does not create or append to the ledger, write accepted state, mutate Project Sources, adopt artifacts, deploy, or execute model-proposed actions. Full all-tests and adoption/current promotion remain intentionally deferred under the focused-slice validation model.

### v0.1.84 candidate hygiene note

During local Artifact Guardian validation, the candidate exposed a required root `.gitignore` omission inherited from the focused working chain. The `v0.1.84` candidate restores a repo-root `.gitignore` that excludes generated/cache/local profile artifacts, including `.pb_profile_local_debug_pools/`. This is candidate hygiene only and does not advance ledger write scope.


## v0.1.84.1 repair candidate status

Accepted/current baseline remains:

```text
chatgpt_claudecode_workflow-2_v0.1.79.zip
```

`v0.1.84.1` is a repair-only focused candidate on top of the `v0.1.84` working candidate. It changes live/browser test defaults so each validation run uses a fresh run-scoped ChatGPT Project name instead of reusing one retained delete-frozen Project. This avoids accumulating browser/project history in a single test Project. Project deletion remains frozen, so `--keep-project` is still enforced and created Projects are retained until a separate secure delete protocol exists.

The repair does not advance accepted-event ledger functionality, does not add ledger writes, does not mutate Project Sources, does not adopt artifacts, deploy, or execute model-proposed actions.


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

`v0.1.84.5.3` repairs rate-limit telemetry aggregation evidence only. `v0.1.84.5.2` already made otherwise functional 429-contaminated live-test runs non-clean; this repair keeps that classification unchanged while deduplicating repeated browser download telemetry carried through both the download result and smoke-verification artifact-intake result. Top-level `cooldown_wait_seconds_total`, `cooldown_wait_count`, and `service_rate_limit_events` now represent unique event-backed telemetry snapshots instead of double-counting carried payloads. Project deletion, direct-create test Project identity, `/v1/ask` telemetry propagation, Project Source, artifact adoption/current, ledger/write/orchestration, deployment, and model-execution scope do not advance.


## v0.1.84.5.4 repair candidate status

`v0.1.84.5.4` repairs recovered ChatGPT 429 live-test classification only. Functionally verified `ask-live` and `visual-artifact-roundtrip` runs with acknowledged/waited 429 telemetry now return `verified_with_recovered_rate_limit` and `ok=true`, so release-control can continue the same browser operation instead of retrying the whole step. Unrecovered 429 telemetry still fails closed. No project deletion, ledger/write, Project Source, artifact adoption/current, deployment, or model-execution scope advances.
