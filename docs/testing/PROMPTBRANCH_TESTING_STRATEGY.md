# Promptbranch Testing Strategy and Test Expansion Plan

## 1. Purpose

This document defines the Promptbranch testing strategy after the `v0.0.278.65` ask-flow repair.

The immediate goal is to make testing explicit across three execution surfaces:

```text
1. direct/local Promptbranch execution
2. localhost Docker service execution
3. headed local debug-browser execution
```

The longer-term goal is to make release-control validate the real operator workflows:

```text
pb ask
pb ask --prompt-file
pb ask --file
pb ask requesting a ChatGPT-generated ZIP artifact
artifact link extraction
artifact download
ZIP verification
```

This document is a planning and verification artifact. It should guide the next implementation releases; it does not define a behavior change by itself.

## 2. Current release-control behavior

The current release-control command:

```bash
./chatgpt_claudecode_workflow_release_control.sh --run-tests
```

primarily delegates validation to:

```bash
pb test full --json
pb test report <full_log> --json
```

The release-control script also performs version and service checks around that flow, including Docker service startup and `/healthz` version verification when the service is used.

Important distinction:

```text
--run-tests does not yet mean “run all operator workflow tests”.
It means “run the current Promptbranch full test profile and report parser”.
```

## 3. Existing coverage

### 3.1 Browser/live ChatGPT profile

The current `pb test full` browser profile already covers broad ChatGPT Project behavior:

```text
- login check
- project resolve before create
- project ensure create/reuse
- project ensure idempotency
- project resolve after ensure
- Project Source capability detection
- Project Source add link
- Project Source add text
- Project Source add file
- Project Source overwrite file
- ask_question smoke expecting INTEGRATION_OK
- task message flow expecting TASK_MESSAGE_OK
- task listing / visibility after ask
- task get / transcript readback
- Project Source remove link/text/file
- project cleanup
```

This means Project Source upload is already tested.

It does **not** prove that `pb ask --file` attaches a file to the same user prompt turn.

### 3.2 Agent/local control-plane profile

The current full profile also covers local Promptbranch behavior:

```text
- MCP host smoke
- MCP filesystem.read VERSION through stdio
- deterministic pb agent run "read VERSION and git status"
- skill list/show/validate
- repo-inspection skill run
- controlled test.smoke tool call
- write/risk rejection behavior
- path escape rejection
- version consistency
- package import metadata
- package import smoke
- src sync dry-run plan
- source upload preflight plan
- package hygiene
```

This validates the Promptbranch local control-plane independently from ChatGPT browser state.

## 4. Known coverage gaps

The following workflows are not yet sufficiently covered by release-control:

```text
1. pb ask against the active pbs project/task conversation
2. pb ask --debug-browser --profile-dir ./.pb_profile_local_debug
3. no-profile login bootstrap as a formal gate
4. pb ask --prompt-file
5. pb ask --file
6. pb ask --prompt-file combined with --file
7. repeated ask stale-answer regression in the same conversation
8. ChatGPT-generated ZIP artifact creation
9. artifact link extraction from assistant answer
10. authenticated artifact download
11. ZIP verification after download
12. explicit localhost service transport test
```

## 5. Execution surfaces

Testing must distinguish these surfaces.

### 5.1 Direct execution

Direct execution imports and runs Promptbranch code locally.

Example:

```bash
pb test full --json
```

Purpose:

```text
- fast development feedback
- direct browser automation path
- unit/integration coverage
- local agent/MCP/skill validation
```

### 5.2 Localhost service execution

Localhost execution runs through the Docker service API.

Example:

```bash
CHATGPT_SERVICE_BASE_URL=http://127.0.0.1:8000 \
  pb test full --json
```

Purpose:

```text
- prove the installed Docker service behaves like direct execution
- validate service API wiring
- validate /healthz version consistency
- catch packaging/runtime environment mismatches
```

### 5.3 Headed debug-browser execution

Headed debug-browser execution runs Patchright Chrome visibly with a profile directory.

Example:

```bash
pb ask --debug-browser \
  --profile-dir ./.pb_profile_local_debug \
  'print echo 444'
```

Purpose:

```text
- diagnose UI changes
- validate login bootstrap
- validate real project conversation routing
- inspect failures visually
```

This should not be the default release gate, but it should be available as an explicit live smoke.

## 6. Proposed test transport model

Add release-control support for explicit test transport selection:

```bash
--test-transport direct|localhost|both
--localhost-base-url http://127.0.0.1:8000
```

### 6.1 Direct mode

```bash
./chatgpt_claudecode_workflow_release_control.sh \
  --version v0.0.278.67 \
  --run-tests \
  --test-transport direct
```

Runs:

```bash
pb test full --json
pb test report <direct-log> --json
```

### 6.2 Localhost mode

```bash
./chatgpt_claudecode_workflow_release_control.sh \
  --version v0.0.278.67 \
  --run-tests \
  --test-transport localhost \
  --localhost-base-url http://127.0.0.1:8000
```

Runs:

```bash
CHATGPT_SERVICE_BASE_URL=http://127.0.0.1:8000 \
  pb test full --json

pb test report <localhost-log> --json
```

### 6.3 Both mode

```bash
./chatgpt_claudecode_workflow_release_control.sh \
  --version v0.0.278.67 \
  --run-tests \
  --test-transport both
```

Runs both direct and localhost profiles.

Release-control should fail if either profile fails.

## 7. Required log layout

Release-control should write transport-specific logs:

```text
.pb_profile/release_logs/<version>/
  pb_test.full.direct.<version>.log
  pb_test.full.direct.<version>.report.json
  pb_test.full.localhost.<version>.log
  pb_test.full.localhost.<version>.report.json
```

This prevents confusion between direct and localhost results.

## 8. Proposed new test profiles

### 8.1 `pb test ask-live --json`

Status:

```text
Implemented in v0.0.278.68 as an explicit visible/local operator workflow profile.
Updated in v0.0.278.69 to create an isolated temporary ChatGPT Project by default and remove it after the run.
```

Purpose:

```text
Validate the actual operator ask workflow repaired in v0.0.278.64 and v0.0.278.65.
```

Scope:

```text
- temporary test project creation and cleanup
- explicit project isolation for each ask-live step
- response conversation belongs to the temporary project
- basic ask
- repeated ask stale guard
- prompt file
- file attachment
- prompt file plus file attachment
- multiline JSON prompt
```

Implemented default subtests:

```text
plain
repeated_stale_first
repeated_stale_second
prompt_file
file_attachment
prompt_file_with_attachment
```

Example command:

```bash
pb test ask-live --json \
  --profile-dir ./.pb_profile_local_debug \
  2>&1 | tee pb_test.ask_live.<version>.log
```

Narrowed command:

```bash
pb test ask-live --json --only plain,prompt_file
```

Expected behavior:

```text
- a temporary ChatGPT Project is created unless --conversation-url is explicitly supplied
- each ask step is targeted at that temporary project
- each response conversation URL resolves back to the temporary project
- the temporary project is removed unless --keep-project is supplied
- the operator's remembered workspace/task state is restored after cleanup
- each response is bound to the current submitted prompt
- no stale assistant answer is returned
- prompt-file content is preserved
- file attachment is visible to the assistant
- JSON output remains parseable
```

### 8.2 `pb test artifact-download-live --json`

Purpose:

```text
Validate the next critical workflow:
ChatGPT-generated artifact -> Promptbranch download -> ZIP verification.
```

Scope:

```text
1. ask ChatGPT to create a tiny ZIP
2. wait for assistant answer/artifact link
3. extract artifact candidate
4. download artifact through authenticated context
5. verify ZIP structure and contents
```

Suggested prompt:

```text
Create a downloadable ZIP named pb_zip_smoke.zip containing one file hello.txt with content ZIP_SMOKE_OK. Return the download link.
```

Expected verification:

```text
- ZIP opens successfully
- no wrapper folder
- exactly one root file: hello.txt
- hello.txt content equals ZIP_SMOKE_OK
- sha256 recorded
- size_bytes recorded
```

This profile should be explicit and optional at first.

It should not become part of default `--run-tests` until stable.

### 8.3 `pb test login-bootstrap-live --json`

Purpose:

```text
Validate empty-profile login bootstrap.
```

Scope:

```text
- remove or use temporary clean profile directory
- navigate to project conversation
- detect /auth/login
- resolve credentials
- click Continue with Google
- fill email/password when allowed
- detect authenticated ChatGPT session
- return explicit auth_challenge_required if blocked by 2FA/CAPTCHA/passkey
```

Expected statuses:

```text
verified
auth_challenge_required
auth_credentials_missing
auth_login_surface_changed
auth_timeout
```

This test must never silently wait for manual login.

## 9. Proposed release-control flags

Add optional flags:

```bash
--run-ask-live-tests
--run-artifact-download-live-tests
--run-login-bootstrap-live-tests
```

Keep default behavior stable:

```text
--run-tests = current full test profile only
```

Expanded release-control examples:

### 9.1 Current stable gate

```bash
./chatgpt_claudecode_workflow_release_control.sh \
  --version v0.0.278.67 \
  --run-tests \
  --test-transport direct \
  --skip-docker-logs \
  --prune-release-logs \
  --release-log-keep 12
```

### 9.2 Direct plus localhost gate

```bash
./chatgpt_claudecode_workflow_release_control.sh \
  --version v0.0.278.67 \
  --run-tests \
  --test-transport both \
  --skip-docker-logs \
  --prune-release-logs \
  --release-log-keep 12
```

### 9.3 Operator ask-flow gate

```bash
./chatgpt_claudecode_workflow_release_control.sh \
  --version v0.0.278.67 \
  --run-tests \
  --test-transport both \
  --run-ask-live-tests \
  --skip-docker-logs \
  --prune-release-logs \
  --release-log-keep 12
```

### 9.4 Artifact download gate

```bash
./chatgpt_claudecode_workflow_release_control.sh \
  --version v0.0.278.67 \
  --run-artifact-download-live-tests \
  --skip-docker-logs \
  --prune-release-logs \
  --release-log-keep 12
```

Artifact download tests should remain opt-in until proven stable.

## 10. Test data layout

Add repo-relative test fixtures:

```text
.pb_test/
  prompts/
    json_prompt.md
    read_attachment.md
    multiline_prompt.md
  fixtures/
    sentinel.txt
    sentinel.json
    small_log.txt
```

Example `sentinel.txt`:

```text
PB_FILE_ATTACHMENT_SENTINEL_123
```

Example `json_prompt.md`:

```text
Return exactly this JSON object:
{"ok": true, "sentinel": "PROMPT_FILE_OK", "finished": "finished"}

No extra text.
```

Example `read_attachment.md`:

```text
Read the attached file and return only the sentinel value.
```

## 11. Pass/fail rules

### 11.1 Ask-live pass rules

A test passes only if:

```text
- submit is confirmed by network marker or DOM-delta
- user turn is bound to the current prompt
- answer is from the assistant turn after the current user turn
- expected sentinel appears in the answer
- stale previous answers are not accepted
```

### 11.2 File attachment pass rules

A file-attachment test passes only if:

```text
- file upload/attachment is confirmed
- prompt submit is confirmed after attachment
- assistant answer proves file content was read
- failure is explicit if attachment is missing
```

### 11.3 Prompt-file pass rules

A prompt-file test passes only if:

```text
- multiline text is preserved
- quotes and JSON braces survive
- response is bound to the prompt-file turn
```

### 11.4 Artifact-download pass rules

An artifact-download test passes only if:

```text
- assistant answer contains an artifact candidate
- artifact is downloaded through a valid authenticated path
- ZIP opens
- ZIP root has expected layout
- ZIP contents match expected fixture
- sha256 and size are recorded
```

## 12. Proposed implementation plan

### Phase 1 — Documentation only

Add this document:

```text
docs/testing/PROMPTBRANCH_TESTING_STRATEGY.md
```

No behavior change.

### Phase 2 — Release-control transport support

Status: implemented in `v0.0.278.67`.

Add:

```text
--test-transport direct|localhost|both
--localhost-base-url
```

Acceptance:

```text
- direct mode preserves current behavior
- localhost mode sets CHATGPT_SERVICE_BASE_URL
- both mode runs both profiles
- logs and reports are transport-specific
```

### Phase 3 — Ask-live test profile

Status:

```text
Implemented in v0.0.278.68 and isolated to a temporary project by default in v0.0.278.69.
```

Command:

```bash
pb test ask-live --json
```

Acceptance:

```text
- creates a temporary ChatGPT Project by default
- removes the temporary project unless --keep-project is supplied
- verifies each response conversation belongs to the temporary project
- tests plain ask
- tests repeated stale guard
- tests prompt-file
- tests file attachment
- tests prompt-file plus attachment
- produces structured JSON report
```

### Phase 4 — Login-bootstrap live test profile

Add:

```bash
pb test login-bootstrap-live --json
```

Acceptance:

```text
- uses temporary clean profile
- verifies automatic login bootstrap or explicit auth_challenge_required
- no silent manual-login wait
```

### Phase 5 — Artifact-download live test profile

Add:

```bash
pb test artifact-download-live --json
```

Acceptance:

```text
- asks ChatGPT to create ZIP
- extracts candidate link
- downloads artifact
- verifies ZIP
- remains opt-in initially
```

### Phase 6 — Release-control integration

Add flags:

```text
--run-ask-live-tests
--run-login-bootstrap-live-tests
--run-artifact-download-live-tests
```

Acceptance:

```text
- each profile has separate logs
- release-control fails if requested profile fails
- artifact-download profile remains opt-in
```

## 13. Release sequence status

Completed planning release:

```text
v0.0.278.66
```

Scope:

```text
- add docs/testing/PROMPTBRANCH_TESTING_STRATEGY.md
- no code behavior changes
```

Completed transport release:

```text
v0.0.278.67
```

Scope:

```text
- implement --test-transport direct|localhost|both
- add transport-specific logs/reports
```

Completed ask-live release:

```text
v0.0.278.68
```

Scope:

```text
- add pb test ask-live --json
```

Completed ask-live isolation repair:

```text
v0.0.278.69
```

Scope:

```text
- make pb test ask-live create and remove a temporary test project by default
- fail ask-live if a response conversation does not belong to the expected test project
```

## 14. Definition of done

The testing expansion is complete when this command is reliable:

```bash
./chatgpt_claudecode_workflow_release_control.sh \
  --version <version> \
  --run-tests \
  --test-transport both \
  --run-ask-live-tests \
  --skip-docker-logs \
  --prune-release-logs \
  --release-log-keep 12
```

And this optional command works when explicitly requested:

```bash
./chatgpt_claudecode_workflow_release_control.sh \
  --version <version> \
  --run-artifact-download-live-tests \
  --skip-docker-logs \
  --prune-release-logs \
  --release-log-keep 12
```

The final state should prove:

```text
- current full suite still passes
- localhost service transport passes
- real operator pb ask workflow passes
- prompt-file workflow passes
- file attachment workflow passes
- stale-answer guard passes
- artifact download workflow can be tested explicitly
```

## 15. Open issues to verify

```text
[ ] Does CHATGPT_SERVICE_BASE_URL=http://127.0.0.1:8000 pb test full --json pass cleanly?
[ ] Does pb ask --prompt-file preserve multiline JSON prompts?
[ ] Does pb ask --file attach files to the current prompt turn?
[ ] Does pb ask --prompt-file --file work in one turn?
[ ] Does repeated pb ask return only current answers?
[ ] Can Promptbranch extract artifact links from ChatGPT answers?
[ ] Can Promptbranch download ChatGPT-generated artifacts through authenticated browser/session?
[ ] Does ZIP verification reject wrapper folders and hygiene violations?
[ ] Does fresh-profile login bootstrap remain stable across sessions?
[ ] Does Docker/headless ask path behave like local debug-browser path?
```
