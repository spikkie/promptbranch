# Project Status

<!-- v0.1.111.5.2 current control-surface header -->
- Accepted/current version: `v0.1.111.5`
- Accepted/current artifact: `chatgpt_claudecode_workflow-2_v0.1.111.5.zip`
- Active candidate version: `v0.1.111.5.2`
- Active candidate artifact: `chatgpt_claudecode_workflow-2_v0.1.111.5.2.zip`
- Next normal version: `v0.1.112`
- Next normal slice: `v0.1.112 — PBAI-001 declaration and structural validation`
- Next planned version after acceptance: `v0.1.112`
- Next planned slice after acceptance: `v0.1.112 — PBAI-001 declaration and structural validation`

## Current baseline

```text
accepted/current artifact: chatgpt_claudecode_workflow-2_v0.1.111.5.zip
accepted/current version: v0.1.111.5
active candidate: chatgpt_claudecode_workflow-2_v0.1.111.5.2.zip
active candidate version: v0.1.111.5.2
active repair slice: v0.1.111.5.2 — Null-safe previous active-step ETA state
next normal version: v0.1.112
next normal slice: v0.1.112 — PBAI-001 declaration and structural validation
```

## Current MVP state

Promptbranch remains in the loop-based problem-solving MVP. This corrective changes ETA observability only; execution, safety, mutation, Project Source, artifact, and adoption authority are unchanged.

## Current release state

- `v0.1.111.5` passed all 10 strict release gates and is adopted/current.
- `v0.1.111.5.1` is repair-required after strict host validation exposed null previous active-step state.
- `v0.1.111.5.2` is the unadopted corrective candidate.
- The accepted ETA implementation remains informational, but strict-log review exposed ten empty associative-array key errors after completed top-level steps.
- The accepted countdown midpoint remained informational and validation stayed green, but its high range could expand while the active plan shrank.

## Current risks

- Empty current-step progress must not index the step-start associative array.
- A shrinking active plan must not increase either the ETA midpoint or high bound.
- Missing or malformed ETA history must still degrade to unknown without affecting validation.

## Current blockers

Strict host release validation, publication, adoption, and accepted/current verification are required for `v0.1.111.5.2` before opening `v0.1.112`.

## Current unknowns

Operational ETA accuracy after several completed runs remains observational and is not release authority.

## Next safe action

Run focused and packaged-byte tests, then one strict all/all host release workflow. Require all 10 gates, zero `bad array subscript` diagnostics, adoption, and final current verification before opening `v0.1.112`.

## Last updated

```text
2026-07-29
v0.1.111.5.2 null-safe previous active-step ETA state candidate build
```

## v0.1.102 candidate status

`v0.1.102` is the next normal slice after accepted/current `v0.1.101`. It generates bounded, proposal-only correction-plan evidence from `v0.1.101` diagnosis results while performing no file mutation, retry, deployment, Project Source mutation, artifact adoption, or ChatGPT Project deletion.

## Last updated

```text
v0.1.104.5 hermetic release-validation profile isolation candidate build
```


## v0.1.101 accepted/current status

`v0.1.101` was accepted/current after full release-control and adoption alignment. It remains the baseline for `v0.1.102`.

## v0.1.101 candidate status

`v0.1.101` is the next normal slice after accepted/current `v0.1.100.3`. It classifies the `v0.1.100` read-only command execution payload as `passed`, `blocked`, or `failed`, while generating no correction plan and performing no file mutation, deployment, Project Source mutation, artifact adoption, or ChatGPT Project deletion.

## Last updated

```text
v0.1.101 read-only command result diagnosis candidate build
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


## v0.1.84.5.5 repair status

`v0.1.84.5.5` is a repair-only candidate on top of the `v0.1.84.5.4` recovered-rate-limit policy candidate. The repair suppresses release-control whole-step retries when a run-all step proves recovered-rate-limit success: functional verification passed, ChatGPT's rate-limit modal was acknowledged, cooldown was satisfied, and the same browser operation continued. Unrecovered 429 evidence remains retryable/failing. Accepted/current remains `chatgpt_claudecode_workflow-2_v0.1.84.5.zip` until adoption/current evidence proves a later repair.

## v0.1.84.5.6 repair note

`v0.1.84.5.6` repairs release-control `--run-all-tests` live Project reuse on top of `v0.1.84.5.5`. The run-all live phase now ensures one run-scoped ChatGPT Project once after live profile preflight and passes the returned Project URL to `ask-live`, `visual-artifact-roundtrip`, and `release-live` with `--conversation-url`. This prevents every live subtest from creating a separate retained Project while preserving delete-frozen safety, 50-character Project name caps, project-create recovery, recovered 429 retry suppression, and visual artifact reply-envelope hardening. No ledger/write/orchestration, Project Source mutation, artifact adoption/current, deployment, or model-execution scope advances.

## v0.1.84.5.7 repair note

`v0.1.84.5.7` repairs the shared live Project ensure command introduced in `v0.1.84.5.6`. Release-control `--run-all-tests` now uses the supported top-level `pb project-ensure` command to create or resolve one run-scoped ChatGPT Project, extracts the returned Project URL, and passes that exact URL to `ask-live`, `visual-artifact-roundtrip`, and `release-live` with `--conversation-url`. This preserves the one-Project-per-full-test-run policy without calling the unsupported nested `pb project ensure` surface. No project deletion, ledger/write/orchestration, Project Source mutation, artifact adoption/current, deployment, or model-execution scope advances.

## v0.1.84.5.8 repair note

`v0.1.84.5.8` repairs release-control service recovery after browser-backed `ReadTimeout` failures in `--run-all-tests`. When `full_direct`, `full_localhost`, or `live_profile_preflight` logs contain strict browser-service timeout evidence such as `ReadTimeout` or `service_client_read_timeout`, release-control records recovery intent and, in detached service mode, restarts/re-verifies the Promptbranch service before continuing to the next browser-backed phase. A live profile preflight timeout is retried once after recovery. Original full-test failures remain failed in the all-tests summary; recovery does not mask functional failures. No project deletion, ledger/write/orchestration, Project Source mutation, artifact adoption/current, deployment, or model-execution scope advances.

## v0.1.84.5.9 repair note

`v0.1.84.5.9` repairs `live_project_ensure` URL extraction and recovered-rate-limit success handling after the `v0.1.84.5.8` full run reached `pb project-ensure` but release-control still treated the returned `project_url` as missing. The extractor now selects an `ok=true` `ensure_project` / `project_ensure` payload with a Project URL instead of blindly using the last JSON object in the log, because trailing telemetry may contain nested JSON. If `project-ensure` exits non-zero only with recovered rate-limit evidence while an `ok=true` Project URL payload is present, release-control continues the live phase with a warning and passes the shared URL to `ask-live`, `visual-artifact-roundtrip`, and `release-live`. Missing URL, malformed JSON, `ok=false`, non-rate-limit non-zero exit, timeout, and unrecovered 429 remain fail-closed. No project deletion, ledger/write/orchestration, Project Source mutation, artifact adoption/current, deployment, or model-execution scope advances.

## v0.1.84.5.10 repair note

`v0.1.84.5.10` repairs the two remaining `v0.1.84.5.9` full-gate blockers without advancing normal scope. Release-control now isolates offline release-validation groups from live browser/service transport environment and skips duplicate release-validation group execution in later run-all transports once the primary direct transport has already proven those groups. Rate-limit detection no longer treats absent selector probes containing modal text as evidence when structured telemetry reports no 429/modal/guardrail event. Browser timeout partial ask results now expose the visible assistant answer, and `ask-live` can accept a bounded streaming-timeout result only when the expected sentinel is visibly present in the expected Project and no forbidden stale sentinel is present. Missing sentinel, wrong Project, real unrecovered 429, malformed/missing artifact, and project deletion remain fail-closed.

## v0.1.84.5.10.1 repair note

`v0.1.84.5.10.1` repairs the remaining release-control cooldown boundary defect found on top of `v0.1.84.5.10`: `full_localhost` can no longer enter the generic browser rate-limit cooldown sleep/retry path. Release-control now denylists localhost/offline validation step names before parsing cooldown seconds or printing the generic `waiting ... before retry` warning, and the retry call sites stop instead of falling through under `set +e`. This repair does not advance normal ledger/write/orchestration scope and does not change Project Source, artifact adoption/current, deployment, or ChatGPT Project deletion behavior.

## v0.1.84.5.10.2 repair note

`v0.1.84.5.10.2` repairs the `v0.1.84.5.10.1` repair boundary only. `full_localhost` remains denied from browser cooldown retry before cooldown parsing or generic `waiting ... before retry` warnings, but `full_direct` / `direct` are removed from that localhost/offline hard denylist because the direct transport can still run browser-backed full-suite behavior. The all-tests summary reader now ranks real command result payloads above nested helper/metadata JSON objects such as `profile_lease.metadata`, so `ask_live` results with `ok=true` and `status=verified_with_recovered_rate_limit` are summarized as successful instead of being displaced by nested metadata. No Project Source mutation, artifact adoption/current, deployment, ChatGPT Project deletion, ledger/write, or model-execution scope advances.

## v0.1.84.5.10.3 repair note

`v0.1.84.5.10.3` repairs only the remaining ask-live recovered-success all-tests summary classification from `v0.1.84.5.10.2`. `full_localhost` remains denied from browser cooldown retry, `full_direct` remains outside the localhost/offline denylist, and `test_ask_live` payloads with `status=verified_with_recovered_rate_limit`, acknowledged cooldown telemetry, `functional_failure_count=0`, and verified expected-sentinel child steps are summarized as recovered success. Functional ask-live failures remain release-blocking, and `full_direct` / `full_localhost` source-add timeout or rate-limit failures remain visible. No Project Source mutation, artifact adoption/current, deployment, ChatGPT Project deletion, ledger/write, or model-execution scope advances.

## v0.1.84.5.11 normal release candidate status

`v0.1.84.5.11` opens the next normal Promptbranch slice from accepted/current repair baseline `chatgpt_claudecode_workflow-2_v0.1.84.5.10.3.zip`.

The slice adds live validation diagnostics and Project Source add timeout observability to release-control summaries. The all-tests summary now records per-step transport class, browser ReadTimeout evidence, source-add evidence, source-add timeout detection, rate-limit evidence, retry-denial state, likely failure phase, and recommended next action. The full transport post-release summary also carries `promptbranch.release_control.full_transport_diagnostics`, so `full_direct` and `full_localhost` failures remain visible and diagnosable without treating them as green.

This is observability only. It does not change ChatGPT Project deletion policy, does not mask source-add failures, does not mutate Project Sources, and does not adopt artifacts.

## v0.1.84.5.12 normal release candidate status

`v0.1.84.5.12` opens the next normal Promptbranch slice from the user-declared accepted/current `chatgpt_claudecode_workflow-2_v0.1.84.5.11.zip` baseline.

The candidate adds explicit `pb ask --new-task` / `--new-conversation` support. Default `pb ask` still continues the remembered conversation. New-task mode uses the remembered Project home, does not pass the remembered conversation URL, fails closed when no Project home is known, and updates remembered task state only after successful returned-conversation/submission evidence.

Busy remembered conversations that expose stop/thinking/interrupted composer blockers are now classified as `target_conversation_busy` with a recovery hint while preserving no-fill safety and lower-level composer diagnostics.

Out of scope remains unchanged: no Project Source mutation, no artifact adoption/current behavior change, no project deletion, no release-control broad rewrite, and no interpretation of literal prompt text as a CLI command.

## v0.1.84.5.12.1 repair status

`v0.1.84.5.12.1` is a repair candidate for `v0.1.84.5.12`. It fixes release-control all-tests summary classification for functionally verified `ask_live` runs that report `status=verified_with_recovered_rate_limit` and top-level `rate_limit_recovered=true` after conversation-history 429 cooldown handling. No slice or line advanced; the active feature slice remains explicit new-task ask mode.

## v0.1.84.5.12.2 repair candidate status

`v0.1.84.5.12.2` repairs the failed `v0.1.84.5.12.1` full release-control run. The prior run no longer failed on ask-live recovered-rate-limit classification; instead, `full_direct` failed because the offline `browser_scheduler_source_lifecycle` release-validation group timed out after 300 seconds.

The repair replaces that group's broad pytest `-k` selector with explicit fast nodeids for scheduler, source queue, browser-profile-busy, source-remove, and release-lifecycle-plan queue invariants. This prevents unrelated cleanup-oriented tests from entering the offline release-validation group while preserving the intended required gate.

No normal slice advanced. `v0.1.84.5.12 — Explicit new-task ask mode` remains the active slice.


## v0.1.85 candidate status

`v0.1.85` opens from accepted/current `chatgpt_claudecode_workflow-2_v0.1.84.5.12.2.zip` as the next normal slice: Ask state observability and new-task proof hardening.

The slice addresses the operational confusion found during the `v0.1.84.5.12.2` short verification: the authoritative schema-v2 conversation path is `.current.conversation_url`, not top-level `.conversation_url`.

Current candidate work adds `pb state` schema/current observability, `pb state --proof`, and `scripts/smoke-pb-ask-new-task.sh`. Candidate status remains not accepted/current until full release-control/adoption/current proof is provided.

## v0.1.86 status — k8s-game orchestration plan reconciliation

Accepted/current baseline with adoption evidence:

```text
chatgpt_claudecode_workflow-2_v0.1.85.zip
```

Active candidate:

```text
v0.1.86 — K8s-game orchestration plan reconciliation
```

Current finding:

```text
The Kubernetes game plan remains strategically on track, but the documentation/control surface needed reconciliation after the accepted baseline advanced to v0.1.85.
```

This slice is documentation/control-surface only. It does not implement the game, add deployment files, apply Kubernetes manifests, mutate Project Source, adopt artifacts, write accepted-event ledger state, or change runtime/browser behavior.

## v0.1.86 next safe action

Install the `v0.1.86` candidate, run focused project-control/orchestration documentation validation, then run full release-control/adopt only if the focused checks pass.

## v0.1.87 status — Loop target schema and dry-run planner

Accepted/current baseline with adoption evidence:

```text
chatgpt_claudecode_workflow-2_v0.1.86.zip
```

`v0.1.87` is a normal candidate slice for the loop-based problem-solving MVP. It adds a target schema and dry-run planner only. The loop does not yet execute actions, tests, corrections, deployments, Project Source mutation, or artifact adoption.

Current safety posture:

```text
side_effects_performed=false
commands_executed=false
deployment_performed=false
kubernetes_mutation_performed=false
project_source_mutation_performed=false
artifact_adoption_performed=false
chatgpt_project_deletion_performed=false
```

## Next safe action

Install and validate `chatgpt_claudecode_workflow-2_v0.1.87.zip` with focused loop tests before any release-control/adoption run.

## v0.1.87.1 repair status — packaged loop module

`v0.1.87.1` is a repair-only candidate for the `v0.1.87` loop target schema and dry-run planner candidate. It fixes the installed CLI import failure where `promptbranch_cli.py` imports `promptbranch_loop`, but `promptbranch_loop.py` was omitted from setuptools `py-modules`. No loop behavior, deployment behavior, Project Source behavior, artifact adoption/current behavior, or ChatGPT Project deletion behavior changes.

## v0.1.88 candidate status — Incremental release validation evidence reuse

`v0.1.88` opens from accepted/current `chatgpt_claudecode_workflow-2_v0.1.87.1.zip`.

The slice adds a conservative evidence-reuse path for release-control: after a successful `--run-tests` direct validation, a later `--run-all-tests` run may reuse the identical `full_direct` evidence only when the artifact SHA256 and validation dimensions match. Missing, failed, malformed, or dimension-mismatched evidence is not trusted; release-control reruns the group.

This candidate does not change Promptbranch loop behavior, live browser behavior, Project Source mutation, artifact adoption/current behavior, Kubernetes/deployment behavior, or ChatGPT Project deletion behavior.

## v0.1.88.1 repair status — Project-source-add-text timeout diagnostics/recovery

`v0.1.88.1` is a repair-only candidate on top of the unaccepted `v0.1.88` evidence-reuse candidate. It addresses the reproduced `project_source_add_text` `ReadTimeout` from the `v0.1.88` adoption gate and existing-Project focused retry.

The repair keeps the evidence-reuse slice intact but does not advance it. Docker-service source add requests now use the extended source-mutation timeout budget, and any remaining client-side source-add timeout is converted into a structured, release-blocking diagnostic payload with post-failure `pb src list --json` evidence collection where possible.

Accepted/current remains `chatgpt_claudecode_workflow-2_v0.1.87.1.zip` until `v0.1.88.1` is installed, validated, source-added/adopted, and proven current by `pb artifact current --json`.

## v0.1.89 candidate status — Live validation timing visibility and shortest-path click audit

Accepted/current baseline with operator adoption evidence:

```text
chatgpt_claudecode_workflow-2_v0.1.88.1.zip
```

`v0.1.89` opens a normal observability slice before repeated broad `--run-all-tests` runs. The release-control timing evidence from `v0.1.88.1` showed that the fast local validation groups took only a few seconds while live browser validation spent most wall time in browser operations and cooldown waits.

This candidate makes browser action/click review first-class. Browser-operation results now carry a `browser_action_audit` with click attempts, fallback strategies, repeated click labels, and a cooldown-risk score. Test reports aggregate this into a reviewable overview so the operator can inspect whether Promptbranch took the shortest safe path to the goal.

Important policy: every extra click increases the chance of cooldown/rate-limit pressure. Repeated or fallback clicks are therefore flagged for review instead of hidden in verbose logs.

Out of scope: Project Source mutation semantics, adoption/current behavior, Project deletion behavior, Kubernetes/deployment behavior, loop behavior, and broad run-all reuse expansion.


## v0.1.90 candidate status — Conversation-history/backend-api 429 pressure reduction

Accepted/current baseline with operator adoption evidence:

```text
chatgpt_claudecode_workflow-2_v0.1.89.zip
```

`v0.1.90` opens a normal reduction slice after `v0.1.89` proved timing and click visibility. The `v0.1.89` report showed minimal observed click paths but excessive cooldown pressure from global `/backend-api/conversations` responses and rate-limit modal handling.

This candidate shields non-essential global conversation-history auto-requests from the ChatGPT frontend by fulfilling them with an empty Promptbranch-marked response, while still allowing explicit Promptbranch conversation-history fetches and project-scoped `/backend-api/gizmos/{project_id}/conversations` calls. The goal is to reduce unnecessary 429/cooldown pressure without weakening functional validation.

Out of scope: changing Project Source mutation semantics, artifact adoption/current behavior, Project deletion behavior, Kubernetes/deployment behavior, loop behavior, and evidence-reuse expansion.

## v0.1.90.1 repair status

`v0.1.90` reduced global conversation-history/backend-api 429 pressure but failed release-control at `project_source_overwrite_file` with `commit_seen_with_stale_inflight_not_verified_present`. `v0.1.90.1` is a repair-only candidate that preserves the conversation-history shield while making file-source uploads/overwrites wait for normal save-request quiet, adding visible-surface post-commit recovery, and distinguishing true source absence after stale-inflight recovery from a generic source-surface refresh failure.

Accepted/current remains the latest adopted baseline until `v0.1.90.1` has release-control/adoption and `pb artifact current --json` evidence.

## v0.1.91 candidate status — Run-all evidence reuse proof and localhost matrix cooldown audit

Accepted/current baseline with operator adoption evidence:

```text
chatgpt_claudecode_workflow-2_v0.1.90.1.zip
```

`v0.1.91` opens a normal validation-control slice after `v0.1.90.1` proved the conversation-history shield and overwrite-file stale-inflight repair in the direct `--run-tests` gate.

The goal is not to add new live browser behavior. The goal is to make the broad `--run-all-tests` path auditable and cheaper: if direct `--run-tests` already passed for the same artifact hash and validation dimensions, `--run-all-tests` may reuse that direct proof and must still execute the localhost matrix and live-only groups that have not been proven.

This slice also adds a first-class localhost cooldown audit. Localhost/offline matrix groups must not consume browser cooldown sleeps or retries; any rate-limit evidence in those groups is surfaced for operator review instead of hidden in repeated reruns.

Out of scope: Project Source mutation semantics, adoption/current behavior, ChatGPT Project deletion behavior, loop behavior, Kubernetes/deployment behavior, and live selector/path changes.

## v0.1.91.1 repair status — Ask-live first-turn retry and run-all aggregation

`v0.1.91.1` is a repair-only candidate on top of accepted/current `v0.1.91`. It keeps the `v0.1.91` run-all evidence reuse and localhost cooldown audit scope intact while repairing the failed run-all proof.

The repair is limited to two defects: the first `ask_live` plain step may retry once when ChatGPT returns the generic null-project Retry answer with no conversation URL or Project identity, and the all-tests summary now prefers live command result payloads over nested helper/schema objects so successful `live_project_ensure`, `visual_artifact_roundtrip`, and `release_live` steps are not listed as failed.

Accepted/current remains `chatgpt_claudecode_workflow-2_v0.1.91.zip` until `v0.1.91.1` is installed, validated, source-added/adopted, and proven current by `pb artifact current --json`.

## v0.1.91.2 repair status — run-all final summary aggregation

`v0.1.91.2` is a repair-only candidate on top of accepted/current `v0.1.91.1`. The `v0.1.91.1 --run-all-tests` proof showed functionally green live steps, but the final all-tests summary still reported `live_project_ensure`, `ask_live`, `visual_artifact_roundtrip`, and `release_live` as failed.

This repair changes only final all-tests summary payload extraction/ranking for noisy logs containing pretty-printed live command JSON. It preserves ask-live retry recovery, evidence reuse, localhost cooldown audit, live command behavior, adoption/current semantics, Project Source behavior, Project deletion freeze, loop behavior, and deployment boundaries.

Accepted/current remains `chatgpt_claudecode_workflow-2_v0.1.91.1.zip` until `v0.1.91.2` is installed, validated, source-added/adopted, and proven current by `pb artifact current --json`.

## v0.1.91.3 repair candidate status

`v0.1.91.3` is a repair-only candidate on top of the `v0.1.91.2` candidate state while accepted/current remains `chatgpt_claudecode_workflow-2_v0.1.91.1.zip` until adoption proof. It hardens Docker service recreate/version verification for clean-system and dirty-system cases by adding Docker/Compose preflight diagnostics, resolving the service container by explicit Compose service name, waiting for running/healthy state before content probing, and classifying missing containers separately from version mismatches.

## v0.1.91.4 repair candidate status

`v0.1.91.4` is a repair-only candidate on top of the `v0.1.91.3` candidate state while accepted/current remains `chatgpt_claudecode_workflow-2_v0.1.91.1.zip` until adoption proof. It preserves `v0.1.91.1`, `v0.1.91.2`, and `v0.1.91.3` repairs and fixes the clean-system pre-source-add bootstrap ordering defect: release-control now reinstalls the candidate CLI, verifies or bootstraps the candidate service, and only then performs Project Source add.

No live/browser behavior, adoption/current semantics, Project deletion behavior, or normal slice scope advances.


## v0.1.91.5 repair candidate status

`v0.1.91.5` repairs only run-all `live_project_ensure` summary aggregation when valid `ensure_project` JSON is followed by a `shared_live_project_url:` terminal line. Accepted/current remains `v0.1.91.1` until this repair is adopted/current.


## v0.1.91.6 repair candidate status

`v0.1.91.6` repairs only the adopt-after-validation footer when `--run-all-tests` reaches `GO` through reused direct evidence. In that mode the direct report file may be absent by design, so adoption verification now accepts a green all-tests summary plus valid `validation_evidence/full_direct.<version>.json`. Live behavior, validation semantics, adoption/current semantics, Project Source behavior, and Project deletion behavior are unchanged.


## v0.1.91.7 repair candidate status

`v0.1.91.7` repairs only the pre-source-add Docker bootstrap build freshness path. It preserves the `v0.1.91.1` through `v0.1.91.6` repair stack and changes release-control so candidate service bootstrap uses explicit repo-root Docker Compose invocation with a no-cache candidate build. Docker build-context version mismatches are classified before health probing. Live/browser behavior, validation semantics, adoption/current semantics, Project Source semantics, and Project deletion behavior are unchanged.


## v0.1.91.8 repair candidate status

`v0.1.91.8` repairs only the run-all localhost duplicate live-source mutation path. After matching green `full_direct` evidence exists for the same artifact/version/hash/dimensions, `full_localhost` reuses the direct browser/source lifecycle proof instead of rerunning Project Source mutations. Localhost service/report/cooldown audit visibility is preserved. No live/browser command behavior, adoption/current semantics, Project Source semantics, or Project deletion behavior changed.

## v0.1.91.9 repair candidate status

`v0.1.91.9` repairs only the adopt-after-validation footer when `full_localhost` is intentionally represented by `reused_browser_source_lifecycle` instead of a standalone `pb_test.full.localhost.<version>.report.json`. It also adds incremental run-all progress telemetry so operators can see tested/succeeded/failed percentages before the final summary. It preserves all `v0.1.91.1` through `v0.1.91.8` repairs and does not change live/browser behavior, validation semantics, adoption/current semantics, Project Source semantics, or Project deletion behavior.

## v0.1.91.10 repair candidate status

`v0.1.91.10` repairs only the `v0.1.91.9` progress-writer syntax defect and the opaque `browser_scheduler_source_lifecycle` release-validation timeout diagnostics. Run-all progress JSON now writes newlines via `chr(10)` to avoid shell/heredoc escaping corruption. The browser scheduler/source lifecycle group keeps the same explicit pytest nodeids and required status, but executes them with per-nodeid progress markers and timeout summaries that include the active nodeid, completed nodeids, failed nodeids, and timed-out nodeids. Live/browser behavior, validation pass/fail semantics, adoption/current semantics, Project Source semantics, Project deletion behavior, Docker bootstrap behavior, and localhost lifecycle reuse policy are unchanged.


## MVP-0 / MVP-1 status after v0.1.91.10

MVP-0 foundation is complete by accepted/current evidence for `chatgpt_claudecode_workflow-2_v0.1.91.10.zip`. The next normal line opens MVP-1: automatic multi-step plan execution.

The first MVP-1 slice is deliberately minimal: walk a target through the existing dry-run loop state machine and print only the state transitions. The Kubernetes game remains the first future acceptance scenario, not implementation scope for the opening slice.

## v0.1.92 accepted/current status

`v0.1.92` added `pb loop run --state-only` as a presentation-only dry-run walkthrough. It prints only planned state names in text mode and emits a compact `mode=state_only` JSON payload when `--json` is supplied. Full release-control/adoption completed successfully and `v0.1.92` is the accepted/current MVP-1 opening baseline.

No execution semantics change: no commands, tests, file mutation, deployment, Kubernetes apply, Project Source mutation, artifact adoption, or ChatGPT Project deletion are performed.


## v0.1.93 candidate status

`v0.1.93` advances MVP-1 with `pb loop run --planned-actions`. The command prints one planned action and validation gate per state while preserving the same dry-run/no-execution semantics as `--state-only` and default loop run.

This slice is intentionally still non-mutating: it does not execute commands, tests, corrections, deployment, Project Source mutation, artifact adoption, or ChatGPT Project deletion.

## v0.1.93.1 repair candidate status

`v0.1.93.1` is a repair-only candidate for the `v0.1.93` MVP-1 planned-action walkthrough. It preserves `pb loop run --planned-actions` and changes only offline release-validation subprocess isolation for `browser_scheduler_source_lifecycle`.

The repair strips inherited live ChatGPT/service environment from release-validation pytest subprocesses, gives each scheduler/source nodeid isolated `HOME`, `TMPDIR`, XDG directories, and release-validation profile state, and records ambient repo profile-lock diagnostics. It does not change loop behavior, browser behavior, adoption/current semantics, Project Source mutation semantics, Docker behavior, or Project deletion behavior.

## v0.1.94.1 accepted/current status

`v0.1.94.1` is the accepted/current repair for the intended `v0.1.94` first controlled read-only execution step. The failed `v0.1.94` release-control run showed Project Source capacity pruning targeted old source `chatgpt_claudecode_workflow-2_v0.1.85.zip` but drifted to collateral older rows. This repair stops capacity-prune retries immediately after identity drift and requires operator review instead of trying a looser remove. Full release-control/adoption passed and future work builds from `chatgpt_claudecode_workflow-2_v0.1.94.1.zip`.

The active MVP-1 loop behavior remains read-only: target path scopes and validation commands are inspected, no commands are executed, no files are mutated, no Kubernetes mutation occurs, no Project Source mutation is performed by the loop engine, and no artifact adoption occurs from the loop engine.


## v0.1.95 candidate status

`v0.1.95` is a normal MVP-1 candidate from accepted/current `chatgpt_claudecode_workflow-2_v0.1.94.1.zip`. It adds a controlled read-only execution evidence report for `pb loop run --read-only-execution`.

The evidence report is read-only and summarizes allowed path inspection, unsafe path blockers, declared validation commands, skipped command count, and explicit no-side-effect assertions. It does not execute commands, mutate files, deploy, mutate Kubernetes, mutate Project Sources, adopt artifacts, or delete ChatGPT Projects.

## v0.1.96 candidate status

`v0.1.96` is a normal candidate built from the user-pinned `chatgpt_claudecode_workflow-2_v0.1.95.zip` baseline. It adds Project Source generated release ZIP retention control so a ChatGPT Project can remain serviceable with up to five repositories under the 25-resource source cap.

The candidate keeps at most five generated release ZIP Project Sources per release family/repository after a new generated ZIP upload. Automatic removal is restricted to same-family canonical generated release ZIPs. Documentation files, non-ZIP Project Sources, text/link sources, and generated ZIPs from other repositories are not selected for deletion. If the 25-resource cap is reached and no safe same-family generated ZIP is available, the operation fails closed for operator review.

This candidate does not change loop execution, deployment, Kubernetes, artifact adoption/current behavior, or ChatGPT Project deletion behavior.

## v0.1.96 accepted/current status

Operator-provided release-control evidence accepted `chatgpt_claudecode_workflow-2_v0.1.96.zip` as current after full `--run-all-tests --strict-source-kind-matrix --adopt-after-validation`. Future work continues from `v0.1.96` unless superseded by later adoption evidence.

## v0.1.97 candidate status

`v0.1.97` is a normal candidate built from accepted/current `chatgpt_claudecode_workflow-2_v0.1.96.zip`. It adds a deterministic read-only loop evidence gate over the `v0.1.95` evidence report so future execution-capable slices have a machine-checkable pass/block contract. The loop still executes no commands, mutates no files, performs no deployment/Kubernetes action, mutates no Project Sources, adopts no artifacts, and deletes no ChatGPT Projects.


## v0.1.97.1 repair candidate status

`v0.1.97.1` repairs only the failed `v0.1.97` text-source Project Source validation path. The `v0.1.97` release ZIP was visible in Project Source, but the `project_source_add_text` validation step reached `commit_seen_with_stale_inflight_not_verified_present` and could not prove the expected text source after the Sources surface failed to refresh.

This repair adapts the visibility reconciliation pattern used by the spikkies-site lifecycle to text sources: after a text-source commit is observed, Promptbranch re-reads the Project Sources surface and accepts recovery only when the expected text-source identity or content anchor is visible. A nearby unrelated source or a release ZIP source card does not satisfy text-source proof. The `v0.1.97` read-only evidence gate behavior is unchanged and no loop action executes commands or mutates files.


## v0.1.103.1 candidate status

`v0.1.103.1` is a normal candidate built from accepted/current `chatgpt_claudecode_workflow-2_v0.1.102.zip`. It adds the first controlled file mutation path for MVP-1, but only against a copied fixture inside a temporary sandbox workspace. The repository fixture is snapshotted before and after and must remain unchanged.

This slice does not verify rollback, mutate repository files, deploy, mutate Kubernetes, mutate Project Sources, adopt artifacts, or delete ChatGPT Projects. `v0.1.104` remains the first planned sandbox mutation verification and rollback evidence gate.

## v0.1.103.1 diagnostic candidate status

`v0.1.103.1` is a diagnostic-only candidate built on top of `v0.1.103` to
start the Docker browser parity investigation. It adds Docker browser runtime
metadata and an auth-readiness diagnostic script, but it does not mutate Project
Sources, adopt artifacts, delete ChatGPT Projects, or change the host-CDP repair
line.

## v0.1.103.2 candidate status

`v0.1.103.2` repairs the Docker browser parity diagnostic after the first live run. The release remains diagnostic-only: it adds passive auth readiness, fail-fast summary semantics, and a host-Chrome bootstrap script for `.pb_profile_docker` mounted as `/app/profile`. It does not mutate ChatGPT Project Sources, adopt artifacts, deploy, or delete ChatGPT Projects.

Next safe action:

```bash
./scripts/docker-browser-profile-bootstrap-host-chrome.sh
PROMPTBRANCH_DOCKER_BROWSER_PROFILE=docker-browser-parity ./scripts/docker-browser-parity-auth-readiness.sh
```

## v0.1.103.3 candidate status

`v0.1.103.3` repairs the Docker browser parity passive-auth wiring bug from `v0.1.103.2`. The runtime service imports `promptbranch_browser_auth.ChatGPTBrowserClient`, so passive auth-readiness is now implemented on that class as well as the compatibility client. The `/v1/auth-readiness` endpoint remains passive and must not click Login, start Google auth, wait for hidden manual login, mutate ChatGPT Project Sources, adopt artifacts, deploy, or delete ChatGPT Projects.

Next safe action:

```bash
PROMPTBRANCH_DOCKER_BROWSER_PROFILE=docker-browser-parity ./scripts/docker-browser-parity-auth-readiness.sh
```

Status: focused_candidate.


Control-surface token: Passive auth-readiness runtime-client wiring repair


## v0.1.103.5 candidate status

`v0.1.103.5` continues the Docker browser parity investigation after `v0.1.103.3` proved passive authenticated Docker reuse. This slice adds a guarded Project Source mutation path: Docker parity mode must pass passive auth-readiness and must receive explicit `PROMPTBRANCH_ALLOW_PROJECT_SOURCE_MUTATION=1` before `/v1/project-sources` can mutate ChatGPT Project Sources. The candidate is diagnostic-only and is not accepted/current.

## v0.1.103.6 candidate status

`v0.1.103.6` adds Docker parity artifact export safety. It keeps the authenticated-readiness and Project Source mutation gates from `v0.1.103.5`, and adds a bounded exporter so operators do not copy `/app/debug_artifacts` wholesale into the repo debug tree. The candidate is diagnostic-only and is not accepted/current.
## v0.1.103.8 candidate status

`v0.1.103.8` narrows the Docker parity investigation to the Cloudflare challenge itself. It adds a KISS settle-loop script that starts or reuses the parity service, requires `/app/profile`, opens one keep-open browser session, polls `/v1/auth-readiness/session/status`, and exports bounded challenge artifacts through the safe exporter. It does not call `/v1/project-sources`, `/v1/login-check`, or Google login flows. The candidate is diagnostic-only and is not accepted/current.



## v0.1.103.9 candidate status

`v0.1.103.9` keeps the proven standard browser mode and adds profile/build-context hygiene. It documents the clean anonymous and clean logged-in Cloudflare test procedure, adds a visible host Chrome bootstrap script, prevents repository-local browser profiles from entering Docker build context, and fixes no-artifact evidence export. Project Source mutation remains out of scope.

## v0.1.103.10.4 candidate status

Adds one operator workflow for standard browser Cloudflare validation: optional install, visible clean-login profile bootstrap, Docker standard-browser Cloudflare check, and strict `validation-summary.json` verification. Project Source mutation remains out of scope.

Control-surface tokens: v0.1.103.10.4 chatgpt_claudecode_workflow-2_v0.1.103.10.4.zip standard browser profile default

## v0.1.103.10.8 candidate status

`v0.1.103.10.8` repairs the failed standard browser validation bootstrap observed after `v0.1.103.10.4`. The standard profile path `.pb_profile/browser/default` can be created as `root:root` when Docker creates the bind-mount target before host Chrome bootstrap. The bootstrap now removes and recreates an empty non-writable placeholder, while non-empty non-writable profiles fail fast with an explicit ownership repair command.

Next safe action:

```bash
./scripts/pb-browser-cloudflare-validation.sh --install-artifact chatgpt_claudecode_workflow-2_v0.1.103.10.8.zip --install-version v0.1.103.10.8
```

## v0.1.103.10.8 candidate status

`v0.1.103.10.8` is a packaging repair after release import rejected `v0.1.103.10.6` with `generated_cache_entries_present` because `.pytest_cache/` was present inside the ZIP. The slice behavior remains unchanged: standard browser profile default, ownership guard, and source-add gate guidance are preserved. Project Source mutation remains out of scope.

Operator command:

```bash
ver=v0.1.103.10.8
zip="$HOME/Downloads/chatgpt_claudecode_workflow-2_${ver}.zip"
timeout --foreground 10800 ./chatgpt_claudecode_workflow_release_control.sh \
  --install-from-zip "$zip" \
  --version "$ver" \
  --auth-only-validation \
  --skip-tests \
  --adopt-after-validation \
  --skip-docker-logs \
  --prune-release-logs \
  --release-log-keep 12 \
  2>&1 | tee ~/tmp/release_control.$ver.auth_only.adopt.log
```

## v0.1.103.10.8 candidate status

`v0.1.103.10.8` repairs the post-success evidence export weakness observed after `v0.1.103.10.7` auth readiness passed. The validation result was green (`cloudflare_cleared_auth_ready`), but the evidence exporter still reported `missing_staged_manifest`. This candidate keeps the successful auth path green by normalizing that exporter status only when the readiness status is already `cloudflare_cleared_*`.

Out of scope preserved: Project Source mutation, Patchright/CDP session-manager redesign, ChatGPT Project deletion, Git commit/push, and artifact adoption.

## Next safe action

Run auth-only validation against `chatgpt_claudecode_workflow-2_v0.1.103.10.8.zip` and confirm the summary contains `evidence_export.status=successful_auth_readiness_no_challenge_manifest_required` or another `ok=true` evidence export status when no challenge artifacts exist.

## v0.1.103.10.9 candidate status

`v0.1.103.10.9` repairs the first `pb ask` smoke failure after standard-browser auth-readiness went green. The auth-readiness path held a logged-in browser session, but `pb ask` opened a second persistent context against the same `/app/profile`, cleared `Singleton*` lock artifacts, and then hit a Cloudflare challenge. This repair makes `pb ask` probe and reuse a compatible held auth-ready session before launching a new context.

Expected next validation:

```bash
pb ask "Reply with exactly the single token PB_ASK_OK and nothing else."
```

Expected evidence: `held_session_reused=true` in service result/log evidence and final answer `PB_ASK_OK`.

## v0.1.103.10.10 candidate status

`v0.1.103.10.10` repairs the remaining `pb ask` smoke failure after `v0.1.103.10.9`. The log showed `pb ask` did reuse the held auth-readiness browser session, but then navigated from the ready `https://chatgpt.com/` composer to the configured project conversation URL, which triggered Cloudflare (`Just a moment...`) and manual-login polling. This candidate makes held-session ask send through the already auth-ready current page instead of navigating away first.

Expected next validation: auth-only validation, then `pb ask "Reply with exactly the single token PB_ASK_OK and nothing else."` should show `navigation_mode=held_auth_ready_current_page` / `navigation_skipped=true` and return `PB_ASK_OK`.

## v0.1.103.10.11 candidate status

`v0.1.103.10.10` still hit Cloudflare immediately during auth-only validation even though the same standard profile had previously worked after host bootstrap. The likely weakness is that a host-created browser profile does not always carry the same trust/fingerprint state when reused by Docker/Patchright/Xvfb. `v0.1.103.10.11` adds a Docker-originated visible Chrome bootstrap so the operator can clear Cloudflare and log in using Chrome launched from the Promptbranch Docker image against the same `/app/profile` bind mount later used by auth-readiness and `pb ask`.

Out of scope preserved: Project Source mutation, v0.1.104.x host-CDP browser manager, ChatGPT Project deletion, Git commit/push, and adoption behavior changes.


## v0.1.103.10.13 status

Active repair: `pbsa` guarded Project Source mutation intent.

Baseline: `v0.1.103.10.12` candidate line after project-scoped `pb ask` repair.

Candidate intent: allow explicit CLI source-add mutation again while preserving service fail-closed behavior for calls that do not carry operator mutation intent.

Validation required: focused API/client tests, control-surface validation, artifact hygiene, operator live `pbsa` source-add proof.

## v0.1.103.10.15 status

Baseline: `v0.1.103.10.13` candidate after guarded per-request `pbsa` mutation intent.

Status: candidate.

Scope: reuse compatible held auth-readiness session during Project Source mutation preflight and source upload, preserving Project Source mutation as explicit operator intent only.

Validation: focused held-session/API tests pending/live operator `pbsa` pending.


## v0.1.103.10.15 status

`v0.1.103.10.15` repairs the live `pbsa` 504 where clicking/opening Sources escaped from the Promptbranch3 project page to a generic `/c/...` conversation before Add source lookup. The repair opens the direct `?tab=sources` route first, skips risky tab clicks when already on that route, and recovers/fails closed if a tab click leaves project scope. Project Source mutation remains explicit per-request operator intent only.


## v0.1.103.10.17 — pbsa reuses held session for remembered overwrite removal

`v0.1.103.10.17` keeps Docker visible browser bootstrap on a stable generic URL by default while preserving the current Promptbranch project/conversation URL for Docker auth-readiness validation. This repairs the `v0.1.103.10.15` auth-only adoption failure where bootstrap opened the project conversation URL directly and Chrome exited before validation could run.

Artifact: chatgpt_claudecode_workflow-2_v0.1.103.10.17.zip

Validation target: auth-only adoption must show `bootstrap_url=https://chatgpt.com/` and `target_url=<current project conversation URL>`, then `pbsa chatgpt_claudecode_workflow-2_v0.1.103.10.17.zip` may be retried.


## v0.1.103.10.17 — pbsa reuses held session for remembered overwrite removal

`v0.1.103.10.17` repairs the live `pbsa` failure after `v0.1.103.10.16`: when overwrite_existing uses a remembered verified source, Project Source removal now reuses the active held auth-readiness browser session instead of launching a competing persistent context against `/app/profile`. Project Source add/remove held-session checks now require logged-in/no-challenge state rather than a visible chat composer, because the Project Sources page is authenticated but normally has no composer.

Artifact: chatgpt_claudecode_workflow-2_v0.1.103.10.17.zip

Validation target: auth-only adoption, project-scoped `pb ask`, then `pbsa chatgpt_claudecode_workflow-2_v0.1.103.10.17.zip` should not fail with `browser_context_unavailable_held_auth_session_active` during remembered overwrite removal.


## v0.1.103.10.19 status

Candidate slice `v0.1.103.10.19 — install-safe pb test api module runner` adds a rerunnable API coverage runner through `pb test api` plus standalone scripts. The default profile is safe for repeated post-release checks: destructive endpoints are skipped or guard-tested, and Project Source mutation requires explicit operator flags.

## v0.1.103.10.19 status

Candidate slice `v0.1.103.10.19 — install-safe pb test api module runner` repairs the `pb test api` packaging bug found after installation. The API coverage runner is now available as `promptbranch.api_coverage_test` and the CLI invokes it with `python -m promptbranch.api_coverage_test`, avoiding missing `site-packages/scripts/...` paths.

## v0.1.103.10.21 status

Candidate slice `v0.1.103.10.21 — pb test api classification cleanup` repairs the API coverage runner self-conflict observed in `v0.1.103.10.19`: the full runner held an auth-readiness session and then caused later browser-owning endpoints to fail with `browser_context_unavailable_held_auth_session_active`. The new default is serial/no-held-session between unrelated endpoints.

## Backlog repair after v0.1.103.10.21

`v0.1.103.10.21 — browser-owning API endpoints reuse held auth-ready session` is recorded as the next possible repair after `pb test api` no longer self-conflicts. It is not implemented in v0.1.103.10.21.
## v0.1.103.10.21 status

Candidate slice `v0.1.103.10.21 — pb test api classification cleanup` keeps endpoint behavior unchanged and narrows API coverage report classification to actual failure/warning fields. It removes misleading `browser_profile_busy`, `rate_limited`, and `auth_challenge_or_cloudflare` labels from successful clear responses.

## Active repair slice — v0.1.103.10.42

`v0.1.103.10.42 — missing live seed profile is non-blocking for run-all release validation` adds a `pb test api` held-session preflight that detects an active held auth-readiness session across default, project, and conversation scopes; without `--reuse-held-session`, it fails early with `preflight.browser_profile_busy=true` instead of running doomed browser-owning endpoint calls. No browser/session architecture changes.


## Active repair slice — v0.1.103.10.42

`v0.1.103.10.42 — missing live seed profile is non-blocking for run-all release validation` adds a `pb test api` held-session preflight that detects an active held auth-readiness session across default, project, and conversation scopes; without `--reuse-held-session`, it fails early with `preflight.browser_profile_busy=true` instead of running doomed browser-owning endpoint calls. No browser/session architecture changes.

## Active repair slice — v0.1.103.10.42

`v0.1.103.10.42 — missing live seed profile is non-blocking for run-all release validation` keeps the successful `v0.1.103.10.35` auth bootstrap/session-clear behavior and repairs the remaining adoption blocker from the uploaded `release_control.v0.1.103.10.35.full.adopt.log`. When `.pb_profile_local_debug` is absent, live-only browser steps are recorded as non-blocking skips while full direct/full localhost validation, Project Source add, import smoke, and artifact guard remain release-blocking.

Next safe action after installing the candidate is a full validation/adoption run with `--run-all-tests --adopt-after-validation`.

## v0.1.103.10.42 candidate status

`v0.1.103.10.42` repairs the new `v0.1.103.10.36` full-adoption blocker where pre-source-add auth bootstrap reached a logged-in, Cloudflare-clear project page but failed strict validation because the project home page did not expose a composer. Release-control now allows project-page readiness only for `pre_source_add`; ask/live/conversation validation still requires composer readiness.

Control-surface active slice token: v0.1.103.10.42 — release-control auth bootstrap accepts project-page readiness for source-add preflight

Control-surface active slice token: v0.1.103.10.42 — release-control pre_tests auth bootstrap targets current conversation URL before requiring composer

## v0.1.103.10.42 candidate status

`v0.1.103.10.42` makes `--run-all-tests` require explicit, manually authenticated live browser profiles instead of copying `.pb_profile/browser/default` into live test profiles. The all-in-Docker browser direction is retained and host-CDP/session-manager work remains aborted/out of scope.

Required live bootstrap before adoption:

```bash
./scripts/pb-docker-live-profile-bootstrap.sh --fresh --url <Promptbranch conversation URL>
```

Release-control validates `.pb_profile_local_debug` and `.pb_profile_local_debug_pools/release-live/slots/slot-1` before live steps. Missing or challenged profiles are release-blocking.

Control-surface active slice token: v0.1.103.10.42 — preserve Docker live profile pool across release ZIP import

## v0.1.103.10.42 candidate status

`v0.1.103.10.42` repairs the `v0.1.103.10.40` release-import lifecycle blocker. The explicit Docker live profile pool `.pb_profile_local_debug_pools/release-live/slots/slot-1` must survive `--install-from-zip`; release import now preserves `.pb_profile_local_debug_pools/` alongside `.pb_profile_local_debug/`. Missing live profiles remain release-blocking for `--run-all-tests`.

## v0.1.103.10.42 candidate status

`v0.1.103.10.42` repairs the live ask target semantics from `v0.1.103.10.41`: `live_project_ensure` may return `/project`, but `ask_live` requires a `/c/...` conversation URL. Release-control now creates/opens a live conversation after project ensure, refuses to run ask/live steps against `/project`, and stops release-control retries when the Docker live profile is Cloudflare-challenged.

## v0.1.103.10.43 candidate status

`v0.1.103.10.43 — release live browser challenge fails fast without manual-login wait` is a repair-only candidate. It preserves the all-in-Docker direction, explicit Docker live profile bootstrap, live pool preservation, and `/c/...` live conversation URL routing from `v0.1.103.10.40` through `v0.1.103.10.42`. The narrow repair is terminal Cloudflare handling for release-live browser operations: when a Docker live profile lands on `Just a moment...` or otherwise reports `challenge_detected=true`, the browser client returns `docker_live_profile_challenged` and closes the context instead of waiting up to 600 seconds for manual login/human verification. No host-CDP/session-manager or copied-profile trust is reintroduced.


## Active repair slice — v0.1.103.10.45

`v0.1.103.10.45 — repair package version surface for Docker build context coherence` repairs the `v0.1.103.10.43` fail-fast implementation bug where Cloudflare challenge handling called `_log()` with a duplicate `stage` argument. It preserves explicit Docker live profiles, live pool preservation, `/c/...` conversation routing, and `--retries 0`, and prevents `visual_artifact_roundtrip` / `release_live` from launching after `ask_live` returns `docker_live_profile_challenged`. No host-CDP/session-manager or copied-profile trust is reintroduced.


## Active repair slice — v0.1.103.10.48

`v0.1.103.10.48 — classify backend-api 403 guardrail as terminal browser challenge across release validation paths` preserves the Docker-only live validation line from `v0.1.103.10.40` through `v0.1.103.10.45`, then repairs the remaining mid-run challenge classification bug: backend-api 403 and Cloudflare evidence observed during response wait are classified as terminal `docker_live_profile_challenged`, `TargetClosedError` after that evidence is mapped to the same structured status, and release-live mode does not persist the conversation-history cooldown for that challenge path.

Out of scope: host-CDP/session-manager, copied-profile trust, browser architecture redesign, and ChatGPT Project deletion.


## Active repair slice — v0.1.103.10.48

`v0.1.103.10.48 — classify backend-api 403 guardrail as terminal browser challenge across release validation paths` preserves the Docker-only live-validation line and extends fail-fast challenge classification beyond ask-live. Observed ChatGPT `/backend-api/...` 403 responses are diagnostic guardrail evidence only, not an operational API contract. Release-control now enables fail-fast challenge handling for full/direct, localhost/service, live preflight, project selection, and live ask paths; after a full-validation backend guardrail, remaining live browser phases are skipped and import/artifact guards still run.

## Active repair slice — v0.1.103.10.53

`v0.1.103.10.53 — release-live bootstrap 429/guardrail is terminal before ask_live` preserves the Docker-only challenge classification chain through `v0.1.103.10.48`, then fixes the remaining human-likeness topology bug: release-live setup and execution now use `.pb_profile_local_debug_pools/release-live/slots/slot-1` as the single actor profile for project ensure, project selection, conversation bootstrap, ask-live, visual artifact roundtrip, and release-live. `.pb_profile_local_debug` remains optional/reference state and is no longer used to create the live conversation that the slot later opens. The Docker bootstrap default image also derives from `VERSION`/`PROMPTBRANCH_VERSION` instead of depending on an unset `PROMPTBRANCH_SERVICE_IMAGE_TAG` local fallback.


## Active repair slice — v0.1.103.10.53

`v0.1.103.10.53 — release-live bootstrap 429/guardrail is terminal before ask_live` preserves the Docker-only live-profile repair chain through `v0.1.103.10.49`, then makes backend-api 403 guardrail telemetry during auth bootstrap terminal. Release-control now refuses to treat a visually logged-in/composer-visible browser as clean when the standard Docker profile is already forbidden by backend-api guardrail responses; it restarts the candidate service to clear the held browser owner and stops before Project Source add/full validation.


## Active repair slice — v0.1.103.10.55

`v0.1.103.10.55 — release-live bootstrap and ask use one continuous browser session` preserves the Docker-only live-profile and guardrail repairs through v0.1.103.10.53, then adds a fast pytest-backed replay harness for release-control run-all orchestration. The replay covers the success path and terminal live bootstrap 429/backend guardrail behavior before ask_live, reducing long live validation loops for shell/control-flow repairs.


## v0.1.103.10.59 — extract live preflight warmup URL from login-check url field

Repair candidate chatgpt_claudecode_workflow-2_v0.1.103.10.59.zip wires `pb test release-live-continuous` into the real CLI dispatcher while preserving the continuous release-live design from 10.55.

## v0.1.103.10.59

- Added trusted conversation warmup for `release-live-continuous`: the continuous live session starts from the conversation URL proven by `live_profile_preflight` instead of bare `https://chatgpt.com/`.
- Preserves all-in-Docker, explicit slot profile, no host-CDP/session-manager, and no copied-profile trust.

## v0.1.103.10.59

Active candidate: v0.1.103.10.59

Artifact: chatgpt_claudecode_workflow-2_v0.1.103.10.59.zip

Slice: v0.1.103.10.59 — extract live preflight warmup URL from login-check url field

Scope: release-live-continuous starts the initial auth/warmup check from the trusted conversation URL proven by live_profile_preflight instead of bare https://chatgpt.com/.


## v0.1.103.10.59 — extract live preflight warmup URL from login-check url field

Candidate adds extraction of top-level `url` from live preflight login-check output when it is a `/c/...` conversation URL, and fails fast with `live_preflight_warmup_url_missing` instead of starting release-live-continuous at `https://chatgpt.com/`.


## v0.1.103.10.61 — classify Docker live preflight challenge as external live challenge and stop browser-repair loop

Repair candidate `chatgpt_claudecode_workflow-2_v0.1.103.10.61.zip` configures the Docker live-slot service with a trusted `/g/.../c/...` conversation URL before live preflight, while preserving the Docker-routed release-live-continuous design.

## v0.1.103.10.65 candidate

`--run-all-tests` now separates deterministic product validation from explicit external ChatGPT live probes. By default, release-control does not call `POST /v1/login-check`; live rows are marked `external_live_not_requested` and import/artifact guard still run.


## v0.1.103.10.65

Artifact: `chatgpt_claudecode_workflow-2_v0.1.103.10.65.zip`

Slice: v0.1.103.10.65 — classify release-live-continuous first-ask Cloudflare challenge as LIVE_BLOCKED

Default `--run-all-tests` no longer calls `POST /v1/login-check`; external ChatGPT live probes are explicit and default live rows are `external_live_not_requested`.

## v0.1.103.10.65 candidate status

`v0.1.103.10.65` repairs the observed live-only failure from `chatgpt_claudecode_workflow-2_session_20260706_133417_319786.log`: `release-live-continuous` successfully opened a trusted project conversation with `composer_visible=True`, `logged_in=True`, and `challenge_detected=False`, then navigated to `https://chatgpt.com/` for root project discovery and lost the page/context. The repair keeps the trusted `/g/.../c/...` conversation as the active surface, derives the project home URL from it, and skips project create/discover/delete behavior in that path.

Baseline note: `v0.1.103.10.62` is the accepted/current product-validation baseline unless later adoption evidence proves otherwise. This candidate is built from the `v0.1.103.10.63` repair candidate plus this narrow flow fix.

Control-surface active slice token: v0.1.103.10.65 — release-live-continuous direct conversation mode navigates to trusted conversation before held-page send guard


## v0.1.103.10.65 candidate status

`v0.1.103.10.65` repairs the next direct-conversation ordering bug observed after `v0.1.103.10.64`: the flow trusted the `/g/.../c/...` warmup conversation identity and skipped root discovery, but the browser page remained `about:blank`, so the held-page send guard refused to submit. This candidate explicitly navigates to the trusted conversation URL and verifies current URL scope, composer visibility, login state, and no challenge before bootstrap/ask.

Control-surface active slice token: v0.1.103.10.65 — release-live-continuous direct conversation mode navigates to trusted conversation before held-page send guard


## v0.1.103.10.66

Active repair candidate: `v0.1.103.10.66 — release-live-continuous handles page/context close during composer submit as explicit browser-lifetime failure`.

Scope remains repair-only: preserve direct trusted conversation mode, skip root project discovery, add explicit `browser_context_closed_during_submit` handling, and do not add Cloudflare workarounds, host-CDP/session-manager, copied-profile trust, or project deletion.


## v0.1.103.10.66 repair note

Candidate artifact: `chatgpt_claudecode_workflow-2_v0.1.103.10.66.zip`.

Active candidate version: `v0.1.103.10.66`.

Active repair slice: `v0.1.103.10.66 — release-live-continuous handles page/context close during composer submit as explicit browser-lifetime failure`.

This remains repair-only and does not advance the normal horizon. It keeps trusted conversation direct mode and adds structured `browser_context_closed_during_submit` evidence for live browser page/context close during composer submit.

## v0.1.103.10.67 repair note

Candidate artifact: `chatgpt_claudecode_workflow-2_v0.1.103.10.67.zip`.

Active candidate version: `v0.1.103.10.67`.

Active repair slice: `v0.1.103.10.67 — composer wait target-close is classified as browser_context_closed_during_submit`.

`v0.1.103.10.67` keeps the `v0.1.103.10.66` trusted direct-conversation flow and fixes the earlier composer selector wait edge case: if the page/context closes while waiting for the chat input, Promptbranch must stop selector iteration and return structured `browser_context_closed_during_submit` with `submit_subphase=composer_wait`, not `ResponseTimeoutError: Chat input did not become visible`.

Control-surface active slice token: v0.1.103.10.67 — composer wait target-close is classified as browser_context_closed_during_submit

## v0.1.103.10.68 repair note

Candidate artifact: `chatgpt_claudecode_workflow-2_v0.1.103.10.68.zip`.

Active candidate version: `v0.1.103.10.68`.

Active repair slice: `v0.1.103.10.68 — release-live-continuous marks completed bootstrap/ask sentinel run as ok`.

`v0.1.103.10.68` keeps the `v0.1.103.10.67` trusted direct-conversation flow and fixes the final aggregation predicate: when project ensure succeeds, bootstrap returns `status=completed` with the exact bootstrap sentinel, and ask returns `status=completed` with the exact ask sentinel, the top-level result is `ok=true`, `contains_expected_sentinel=true`, and no `failed_phase` is emitted. Browser action audit warnings remain preserved.

Control-surface active slice token: v0.1.103.10.68 — release-live-continuous marks completed bootstrap/ask sentinel run as ok

## v0.1.103.10.69 repair note

Candidate artifact: `chatgpt_claudecode_workflow-2_v0.1.103.10.69.zip`.

Active candidate version: `v0.1.103.10.69`.

Active repair slice: `v0.1.103.10.69 — add install.sh strict all-all release gate`.

`v0.1.103.10.69` adds repo-root `install.sh` as the strict all-all release gate for new ZIP releases. The script installs the exact candidate ZIP, runs default product validation, runs explicit external ChatGPT live validation, requires live validation to pass, adopts only if all validation is `GO`, and writes `pb artifact current --all --json` evidence after adoption.

Control-surface active slice token: v0.1.103.10.69 — add install.sh strict all-all release gate



## v0.1.103.10.70 repair note

Candidate artifact: `chatgpt_claudecode_workflow-2_v0.1.103.10.70.zip`.

Active repair slice: `v0.1.103.10.70 — classify release-live-continuous bootstrap guardrail as external live blocked`.

`v0.1.103.10.70` keeps the `v0.1.103.10.69` strict `install.sh` all-all gate and changes only release-control final classification: `live_bootstrap_guardrail` plus skipped downstream live statuses are external-live blockage evidence, so all-all adoption remains blocked but the final verdict becomes `LIVE_BLOCKED`, not product `FIX`.

Out of scope: Cloudflare/rate-limit bypass, host-CDP/session-manager, copied-profile trust, ChatGPT Project deletion, and release adoption claims.


## v0.1.103.10.71 repair note

Candidate artifact: `chatgpt_claudecode_workflow-2_v0.1.103.10.71.zip`.

Active repair slice: `v0.1.103.10.71 — final verdict aggregation maps live_bootstrap_guardrail cascade to LIVE_BLOCKED`.

`v0.1.103.10.71` keeps the `v0.1.103.10.69` strict `install.sh` all-all gate and the `v0.1.103.10.70` status vocabulary. It fixes the actual all-tests final summary aggregation path: if the mixed `live_project_ensure` log contains terminal `live_bootstrap_guardrail` evidence, the failed live cascade is classified as external `LIVE_BLOCKED`, not product `FIX`, while preserving failed live steps, `artifact_guard` evidence, and adoption refusal.

Out of scope: Cloudflare/rate-limit bypass, host-CDP/session-manager, copied-profile trust, ChatGPT Project deletion, and release adoption claims.


## v0.1.103.10.78 repair note

Candidate artifact: `chatgpt_claudecode_workflow-2_v0.1.103.10.78.zip`.

Active repair slice: `v0.1.103.10.78 — make pb src add exact-name idempotent and block suffix-renamed Project Source uploads`.

`v0.1.103.10.78` keeps the `v0.1.103.10.69` strict `install.sh` all-all gate and the `v0.1.103.10.71` live bootstrap guardrail cascade normalization. It updates the project control surface so the active candidate, next-normal metadata, plan-state horizon, and Markdown current-baseline blocks agree. It also tightens final verdict aggregation: product validation failures keep the final verdict `FIX`, while `LIVE_BLOCKED` is reserved for otherwise-clean product validation with external-live guardrail/challenge blockage.

## v0.1.103.10.78 repair note

Candidate artifact: `chatgpt_claudecode_workflow-2_v0.1.103.10.78.zip`.

Active repair slice: `v0.1.103.10.78 — make pb src add exact-name idempotent and block suffix-renamed Project Source uploads`.

`v0.1.103.10.78` keeps the strict all-all install gate, product-clean `LIVE_BLOCKED` classification, and precise `bootstrap_sentinel_missing_after_ask_success` status. It changes only release-live sentinel validation so known visible thinking preambles are normalized before exact single-token matching. Arbitrary extra text remains a failure.

## v0.1.103.10.78 repair note

Candidate artifact: `chatgpt_claudecode_workflow-2_v0.1.103.10.78.zip`.

Active repair slice: `v0.1.103.10.78 — make pb src add exact-name idempotent and block suffix-renamed Project Source uploads`.

This repair requires exact canonical file names for normal `pb src add` / `pbsa`, blocks visible suffix-renamed collisions before upload, and reports backend-created suffixes as `backend_renamed_source` instead of accepting them as success.


## v0.1.103.10.79 repair note

Candidate artifact: `chatgpt_claudecode_workflow-2_v0.1.103.10.79.zip`.

Active repair slice: `v0.1.103.10.79 — require stable Project Sources preflight and fail fast on backend-assigned suffix names`.

`v0.1.103.10.79` keeps the strict all-all install gate, release-live sentinel normalization, and exact canonical Project Source naming. Before a file upload, it requires either an explicit empty Project Sources state or multiple stable non-empty snapshots. Zero cards without an explicit empty state are classified as `source_preflight_not_authoritative` and no upload occurs. After a committed upload, a newly visible suffix-renamed source is classified immediately as `backend_renamed_source`, rolled back when uniquely identifiable, and returned before the exact-name persistence retry loop. Source-add read timeouts include the configured timeout and active-operation details.

## v0.1.103.10.80 repair note

Candidate artifact: `chatgpt_claudecode_workflow-2_v0.1.103.10.80.zip`.

Active repair slice: `v0.1.103.10.84 — restore normal file add and replace existing Project Sources by identity`.

`v0.1.103.10.80` keeps the strict all-all gate, sentinel normalization, and authoritative Project Sources preflight. Pre-source-add auth bootstrap reuses the exact verified candidate service with `--no-recreate`; stable Docker dependency layers precede release metadata, browser automation versions are pinned, and exhausted Chrome transport downloads are classified as `docker_browser_dependency_download_failed`.



## v0.1.103.10.90 current diagnostic status

The visible Library exact-ID deletion route was unavailable in v0.1.103.10.89. This repair instruments the complete fetch/XHR surface, discovers backend inventory and exact soft/hard delete mutations from controlled disposable data, verifies exact-ID absence, and only then tests canonical reupload.


## v0.1.103.10.91 current diagnostic status

`v0.1.103.10.90` proved that upload identity capture can succeed while immediate Library DOM search remains empty. `v0.1.103.10.91` therefore separates three authorities: exact upload identity, exact backend inventory visibility, and UI selectability. The diagnostic accepts `/backend-api/files/library/nodes` as the active inventory surface, polls the captured `libfile_...` identity, exports the complete sanitized fetch/XHR trace, and returns before deletion or canonical reupload whenever any gate is not authoritative.


## v0.1.103.10.92 current diagnostic status

`v0.1.103.10.92` keeps captured authentication headers private in memory and replays the exact Library inventory request with that context. The already captured exact-ID `200` counts as observation one; a second authenticated exact-`libfile_...` observation is mandatory before the UI deletion-discovery phase. `401`/`403` returns immediately as `backend_inventory_replay_unauthorized`. No deletion, canonical reupload, release-source upload, or adoption is permitted without the inventory proof.


## v0.1.103.10.93 current diagnostic status

`v0.1.103.10.93` preserves authenticated exact-ID inventory proof from `v0.1.103.10.92` and repairs the remaining Library UI parsing boundary. It reconstructs the exact expected basename from stable attributes or contiguous rendered filename fragments, rejects suffix siblings and partial matches, binds one exact UI card to the unique backend-proven `libfile_...`, and returns fail closed before any delete or reupload when the binding is absent or ambiguous.


## v0.1.103.10.94 diagnostic candidate

Candidate artifact: `chatgpt_claudecode_workflow-2_v0.1.103.10.94.zip`.

Active candidate version: `v0.1.103.10.94`.

Active slice: `v0.1.103.10.94 — bind Library filenames only to actionable file rows`.

Accepted/current remains `v0.1.103.10.68`. `v0.1.103.10.94` repairs the `10.93` DOM-scope ambiguity by admitting only structurally actionable file rows and binding menu interaction to the unique exact row. No Project Source release upload or adoption is performed.

## v0.1.103.10.100 diagnostic repair status

`v0.1.103.10.100` bounds generic Fetch/XHR response capture, omits streaming bodies from the generic trace, classifies and cancels unresolved trace tasks, and guarantees structured JSON with `fetch_xhr_protocol_watch_settle_timeout`. Accepted/current remains `v0.1.103.10.68`; canonical release `pbsa` and adoption remain blocked.

## v0.1.103.10.101 diagnostic repair status

`v0.1.103.10.101` adds dedicated, bounded terminal processing-stream identity capture to the disposable visible-Library upload. Exact mutation identity comes only from the dedicated stream result; generic Fetch/XHR trace bodies remain stream-safe and non-authoritative. Accepted/current remains `v0.1.103.10.68`; canonical release `pbsa` and adoption remain blocked.


## v0.1.103.10.102 diagnostic repair status

`v0.1.103.10.102` freezes an authoritative request-sequence boundary before the exact row-scoped Library Delete click and snapshots request phase immutably at request start. Soft-delete protocol discovery now uses paired successful post-boundary mutation traffic as authority, reports sanitized candidates when exact identity is missing, reconciles the visible upload after terminal/backend/UI proof, and suppresses duplicate unchanged settlement history. Accepted/current remains `v0.1.103.10.68`; canonical release `pbsa` and adoption remain blocked.


## v0.1.103.10.103 diagnostic repair status

`v0.1.103.10.103` waits for one unique asynchronous Library delete confirmation inside a visible dialog, alertdialog, or native dialog. The row-menu action alone can no longer produce `delete_triggered`; a no-confirmation path is accepted only after exact post-boundary backend mutation proof. Accepted/current remains `v0.1.103.10.68`; canonical release `pbsa` and adoption remain blocked.

Current active repair: `v0.1.104.5 — hermetic release-validation profile isolation`.

## v0.1.111.1 repair candidate

`v0.1.111` failed before Project Source publication because the pipx-installed CLI could not import `promptbranch_release_engine`. `v0.1.111.1` packages that module and makes release control verify the installed CLI and read-only contract planner before browser bootstrap or Project Source mutation. Accepted/current remains `v0.1.109.1.1`.
