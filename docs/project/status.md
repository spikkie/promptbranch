# Project Status

## Current baseline

```text
accepted/current baseline with adoption evidence: chatgpt_claudecode_workflow-2_v0.1.77.11.zip
accepted checksum: 825e3b3a5e2d36214ddcdeb6f97ece8601a82f35322a34c96a6e3e2bab78af44
active repair candidate: chatgpt_claudecode_workflow-2_v0.1.78.2.4.zip
next normal target after accepted AG-001: chatgpt_claudecode_workflow-2_v0.1.79.zip
```

## Current MVP state

```text
MVP status: active
DoD status: in_progress
active plan slice: AG-001 — Deterministic Artifact Guardian Guard
active repair: v0.1.78.2.4 — Delete-frozen live-test profile alignment and one-command all-tests report
last completed slice: v0.1.77.11 repair line accepted/current
next planned slice: v0.1.79 — rebaselined JSON orchestration / k8s-game MVP foundation
```

## Current release state

```text
latest created ZIP: chatgpt_claudecode_workflow-2_v0.1.78.2.4.zip candidate once packaged
latest installed ZIP: chatgpt_claudecode_workflow-2_v0.1.78.zip failed release-control
latest accepted/current ZIP: chatgpt_claudecode_workflow-2_v0.1.77.11.zip
release status: v0.1.78.2 freezes ChatGPT Project deletion after v0.1.78.1 live-log delete evidence; not accepted/current
```

## Current risks

- Project deletion is now frozen because the current automation path can execute real ChatGPT project deletion; deletion must remain unavailable until a secure delete protocol exists.
- Project Source file uploads can reach commit-seen / stale-inflight / not-visible states that must remain release-blocking unless refreshed persistence is proven.
- Artifact Guardian must remain a structural ZIP guard only, not a build/heal/agent workflow.
- Guard-passed must not be confused with accepted/current adoption state.
- Project-specific ZIP requirements must remain policy-driven through `.artifact-guardian.yml`, not duplicated as hidden code constants.

## Current blockers

- v0.1.78.2.4 must pass focused live-test default alignment, release-control all-tests shell validation, and release-control from ZIP.
- v0.1.78.2.4 must not be adopted/current without `pb artifact current --all --json` alignment evidence.
- Existing leaked `itest-promptbranch-*` projects from pre-fix runs remain manual cleanup until a secure delete protocol exists.

## Current unknowns

- What secure multi-factor delete protocol, if any, is acceptable for future ChatGPT Project deletion.
- Whether live ChatGPT file-source indexing will become visible within the extended post-commit readback window in release-control.
- Whether future lifecycle scripts should delegate their install ZIP checks to `pb artifact guard` in AG-005 or an earlier slice.

## Next safe action

```text
Package chatgpt_claudecode_workflow-2_v0.1.78.2.3.zip from v0.1.78.2.2 as a repair-only artifact, run focused release-control quarantine-project validation, then run release-control before adoption.
```

## Last updated

```text
v0.1.78.2.3 repair candidate build
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
