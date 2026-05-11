# Promptbranch Ask/Reply Protocol and Artifact Intake Design

Status: Draft for v0.0.201 planning  
Scope: Promptbranch / Claude-Code-like workflow in ChatGPT  
Primary goal: make `pb ask` produce machine-readable, validated outcomes that can drive artifact intake, ZIP verification, candidate migration, test/adopt, and the next `pb ask`.

---

## Navigation

- [1. Design summary](#1-design-summary)
- [2. Problem statement](#2-problem-statement)
- [3. Design principles](#3-design-principles)
- [4. Core object model](#4-core-object-model)
- [5. Ask/Reply protocol](#5-askreply-protocol)
- [6. Host-side validation model](#6-host-side-validation-model)
- [7. Artifact intake pipeline](#7-artifact-intake-pipeline)
- [8. Command design](#8-command-design)
- [9. State and storage layout](#9-state-and-storage-layout)
- [10. Error taxonomy](#10-error-taxonomy)
- [11. Security and safety model](#11-security-and-safety-model)
- [12. MVP plan](#12-mvp-plan)
- [13. Acceptance criteria](#13-acceptance-criteria)
- [14. Open questions](#14-open-questions)

---

# 1. Design summary

Promptbranch should treat every `pb ask` as a structured protocol transaction, not as a plain text chat message.

The core loop should become:

```text
pb ask structured request
  -> ChatGPT answers with structured reply envelope
  -> Promptbranch extracts and validates reply envelope
  -> Promptbranch extracts artifact candidates
  -> Promptbranch downloads artifacts only when explicitly requested
  -> Promptbranch verifies ZIPs before migration
  -> Promptbranch migrates verified ZIPs as candidate releases
  -> Promptbranch tests/adopts only after green validation
  -> next pb ask continues from the verified/adopted baseline
```

The human-readable answer may still exist, but automation must use only the validated JSON envelope.

The MVP must close this manual gap:

```text
Current manual gap:
pb ask
  -> ChatGPT gives ZIP link
  -> operator manually downloads ZIP
  -> operator manually copies/migrates ZIP
  -> operator manually verifies/tests/adopts
  -> operator manually starts the next ask
```

Target:

```text
Target MVP loop:
pb ask --protocol
pb task answer parse --json
pb artifact intake --from-last-answer --download --verify --migrate --json
release-control --tests-only --adopt-if-green
pb ask --continue-from-current-baseline
```

---

# 2. Problem statement

Promptbranch already has a strong release/adoption workflow, but the ChatGPT answer itself is still handled too manually.

Missing capabilities:

1. `pb ask` does not yet guarantee a structured request contract.
2. ChatGPT replies are not yet required to include a machine-readable reply envelope.
3. Promptbranch does not yet parse assistant answers as protocol data.
4. ZIP links returned by ChatGPT are manually downloaded.
5. Downloaded ZIPs are manually migrated to repo root.
6. Candidate artifacts are not clearly separated from accepted baselines.
7. The next `pb ask` relies on human memory of what was adopted.

The critical missing MVP layer is therefore:

```text
Ask answer handling + artifact intake.
```

---

# 3. Design principles

## 3.1 Protocol first

Every automation-relevant ask/reply must use a protocol envelope.

Do not rely on prose such as:

```text
I created the ZIP here: ...
```

Instead require a structured reply envelope with explicit fields for:

```text
request_id
status
baseline
artifacts
validation
next_step
confidence
```

## 3.2 Human text is advisory, JSON is operational

ChatGPT may include human-readable explanation, but Promptbranch automation must ignore anything outside the validated protocol block.

Preferred extraction format:

```text
BEGIN_PROMPTBRANCH_REPLY_JSON
{ ...valid JSON... }
END_PROMPTBRANCH_REPLY_JSON
```

## 3.3 Fail closed

If the reply is missing, invalid, ambiguous, or inconsistent, Promptbranch must not download, migrate, adopt, or advance state.

## 3.4 Candidate before accepted baseline

A downloaded artifact is never immediately accepted.

State sequence:

```text
answer artifact candidate
  -> downloaded artifact
  -> verified candidate
  -> migrated candidate
  -> tested candidate
  -> adopted baseline
```

## 3.5 Host validates, LLM proposes

Both ChatGPT and the host-side LLM may understand the schema, but neither is trusted as authority.

Promptbranch validates:

```text
schema
version
filename
ZIP hygiene
baseline continuity
artifact role
candidate status
test/adopt result
```

## 3.6 Preserve Workspace / Task / Artifact separation

Promptbranch state must not conflate:

```text
Workspace = ChatGPT Project
Task      = ChatGPT conversation / chat
Artifact  = source bundle / release ZIP / adopted baseline
```

---

# 4. Core object model

## 4.1 Workspace

Represents the current ChatGPT Project.

Fields:

```json
{
  "project_home_url": "...",
  "project_name": "Claude Code workflow in ChatGPT",
  "project_slug": "claude-code-workflow-in-chatgpt"
}
```

## 4.2 Task

Represents the current chat/conversation inside the workspace.

Important invariant:

```text
A user turn can have zero, one, or multiple assistant answers.
```

So Promptbranch must track:

```json
{
  "conversation_url": "...",
  "conversation_id": "...",
  "title": "...",
  "last_user_message_id": "...",
  "last_assistant_answer_ids": ["..."]
}
```

## 4.3 Artifact

Represents repo snapshots, source bundles, release ZIPs, downloaded candidates, and adopted baselines.

Fields:

```json
{
  "artifact_ref": "chatgpt_claudecode_workflow_v0.0.200.zip",
  "artifact_version": "v0.0.200",
  "source_ref": "chatgpt_claudecode_workflow_v0.0.200.zip",
  "source_version": "v0.0.200",
  "candidate_ref": null,
  "candidate_version": null
}
```

---

# 5. Ask/Reply protocol

## 5.1 Ask request envelope

Every protocol-aware `pb ask` should send a request envelope.

Example:

```json
{
  "schema": "promptbranch.ask.request",
  "schema_version": "1.0",
  "request_id": "req_20260510_001",
  "correlation_id": "corr_20260510_001",
  "workspace": {
    "project_name": "Claude Code workflow in ChatGPT",
    "project_home_url": "https://chatgpt.com/..."
  },
  "task": {
    "conversation_id": "current",
    "turn_policy": "assistant_may_return_one_protocol_reply"
  },
  "artifact": {
    "repo": "chatgpt_claudecode_workflow",
    "current_baseline": "chatgpt_claudecode_workflow_v0.0.200.zip",
    "current_version": "v0.0.200",
    "target_version": "v0.0.201",
    "release_type": "normal"
  },
  "intent": {
    "kind": "software_release_request",
    "summary": "Implement ask/reply protocol first slice."
  },
  "constraints": {
    "preserve_baseline": true,
    "zip_root_must_be_repo_contents": true,
    "no_patch_files": true,
    "no_wrapper_folder": true,
    "no_cache_files": true,
    "no_nested_zips": true,
    "no_auto_adopt": true
  },
  "expected_reply": {
    "schema": "promptbranch.ask.reply",
    "schema_version": "1.0",
    "required_sections": [
      "status",
      "summary",
      "baseline",
      "changes",
      "artifacts",
      "validation",
      "next_step"
    ]
  }
}
```

## 5.2 Reply envelope

ChatGPT must include one valid reply envelope.

Example:

```text
BEGIN_PROMPTBRANCH_REPLY_JSON
{
  "schema": "promptbranch.ask.reply",
  "schema_version": "1.0",
  "request_id": "req_20260510_001",
  "correlation_id": "corr_20260510_001",
  "status": "completed",
  "result_type": "release_candidate",
  "summary": "Implemented ask/reply protocol schema and answer parsing.",
  "baseline": {
    "input_artifact": "chatgpt_claudecode_workflow_v0.0.200.zip",
    "input_version": "v0.0.200",
    "output_artifact": "chatgpt_claudecode_workflow_v0.0.201.zip",
    "output_version": "v0.0.201",
    "release_type": "normal"
  },
  "changes": [
    {
      "path": "promptbranch_protocol/schemas/ask.request.schema.json",
      "kind": "added",
      "summary": "Defines the ask request envelope."
    },
    {
      "path": "promptbranch_protocol/schemas/ask.reply.schema.json",
      "kind": "added",
      "summary": "Defines the ask reply envelope."
    }
  ],
  "artifacts": [
    {
      "kind": "zip",
      "filename": "chatgpt_claudecode_workflow_v0.0.201.zip",
      "version": "v0.0.201",
      "role": "candidate_release",
      "download": {
        "available": true,
        "link_text": "chatgpt_claudecode_workflow_v0.0.201.zip",
        "url": null
      }
    }
  ],
  "validation": {
    "claimed": [
      "bash -n shell scripts",
      "py_compile OK",
      "focused tests passed",
      "ZIP hygiene passed"
    ],
    "not_claimed": [
      "full browser suite",
      "local adoption"
    ]
  },
  "next_step": {
    "operator_action": "download_verify_test_adopt",
    "recommended_command": "pb artifact intake --from-last-answer --download --verify --migrate --json"
  },
  "confidence": "medium"
}
END_PROMPTBRANCH_REPLY_JSON
```

## 5.3 Reply statuses

Allowed statuses:

```text
completed
partial
blocked
needs_clarification
failed
no_artifact
invalid_request
```

## 5.4 Result types

Allowed result types:

```text
analysis_only
release_candidate
repair_candidate
test_report
diagnostic
no_change
```

---

# 6. Host-side validation model

## 6.1 Validation sequence

```text
assistant answer text
  -> extract protocol block
  -> parse JSON
  -> validate schema
  -> validate request_id / correlation_id
  -> validate baseline continuity
  -> validate artifact metadata
  -> classify artifact candidates
  -> persist parsed answer record
  -> expose result to operator
```

## 6.2 Hard rejection cases

Reject automation if:

```text
- no protocol envelope found
- multiple protocol envelopes found
- invalid JSON
- schema_version unsupported
- request_id mismatch
- baseline input does not match current adopted baseline
- output version skips expected normal version without explicit repair/override policy
- artifact filename does not match project naming convention
- artifact role is unclear
- validation claims are absent or impossible
```

## 6.3 Host-side LLM role

The host-side LLM may help summarize or classify, but it must not bypass deterministic validation.

Allowed:

```text
- summarize answer text
- explain validation failure
- propose likely artifact candidate
```

Not allowed:

```text
- accept baseline
- choose candidate when deterministic rules disagree
- override ZIP hygiene failure
- execute write tools
```

---

# 7. Artifact intake pipeline

## 7.1 Pipeline stages

```text
candidate_found
  -> downloaded
  -> verified
  -> migrated
  -> tested
  -> adopted
```

Each stage must be explicit.

## 7.2 Candidate extraction

Sources:

```text
- reply envelope artifacts[]
- markdown links in answer
- plain URLs in answer
- attached file/download links exposed by service
- known artifact filename patterns in text
```

The reply envelope is preferred. Link scraping is fallback.

## 7.3 Download target

Use a quarantine/inbox path first:

```text
.pb_profile/artifact_inbox/<workspace_id>/<task_id>/<answer_id>/
```

Example:

```text
.pb_profile/artifact_inbox/claude-code-workflow/69fd.../ans_001/chatgpt_claudecode_workflow_v0.0.201.zip
```

## 7.4 Verification checks

A downloaded ZIP must pass:

```text
- ZIP opens successfully
- no wrapper folder
- VERSION file exists
- VERSION matches filename
- project artifact name matches repo
- version is allowed from current baseline
- no .pytest_cache/
- no __pycache__/
- no *.pyc / *.pyo
- no *.log
- no nested ZIPs
- no .pb_profile/
- no local secrets
```

## 7.5 Migration

Migration copies a verified candidate to the canonical repo-root artifact path.

Example:

```text
from:
  .pb_profile/artifact_inbox/.../chatgpt_claudecode_workflow_v0.0.201.zip

to:
  ./chatgpt_claudecode_workflow_v0.0.201.zip
```

Migration registers a candidate artifact, not an accepted baseline.

## 7.6 Test/adopt

Acceptance remains guarded:

```bash
./chatgpt_claudecode_workflow_release_control.sh \
  --version v0.0.201 \
  --tests-only \
  --adopt-if-green \
  --skip-docker-logs \
  --prune-release-logs \
  --release-log-keep 12
```

---

# 8. Command design

## 8.1 Ask request generation

```bash
pb ask "Implement v0.0.201 from v0.0.200" --protocol --json
```

Dry-run / inspection:

```bash
pb ask "Implement v0.0.201 from v0.0.200" --protocol --print-request-json
```

Expected output includes:

```json
{
  "ok": true,
  "action": "ask",
  "request_id": "...",
  "conversation_id": "...",
  "answer_status": "complete",
  "latest_answer_id": "...",
  "protocol_reply_found": true,
  "artifact_candidate_count": 1
}
```

## 8.2 Answer parsing

```bash
pb task answer parse --latest --json
```

or:

```bash
pb task answer parse --answer-id <id> --json
```

Output:

```json
{
  "ok": true,
  "action": "task_answer_parse",
  "status": "valid",
  "request_id": "...",
  "answer_id": "...",
  "artifact_candidates": [...]
}
```

## 8.3 Artifact intake

Candidate only:

```bash
pb artifact intake --from-last-answer --json
```

Download:

```bash
pb artifact intake --from-last-answer --download --json
```

Download and verify:

```bash
pb artifact intake --from-last-answer --download --verify --json
```

Download, verify, migrate:

```bash
pb artifact intake --from-last-answer --download --verify --migrate --json
```

## 8.4 Future wrapper command

Not MVP-F0. Later:

```bash
pb ask-release "Implement v0.0.201" \
  --expect-artifact chatgpt_claudecode_workflow_v0.0.201.zip \
  --download \
  --verify \
  --test \
  --adopt-if-green \
  --continue
```

---

# 9. State and storage layout

## 9.1 Protocol files

```text
promptbranch_protocol/
  schemas/
    ask.request.schema.json
    ask.reply.schema.json
    artifact.candidate.schema.json
    validation.report.schema.json
  prompts/
    chatgpt_ask_contract.md
    host_llm_reply_interpreter.md
  examples/
    ask.release.request.example.json
    ask.release.reply.example.json
```

## 9.2 Runtime records

```text
.pb_profile/
  ask_records/
    <request_id>.request.json
    <request_id>.reply.raw.txt
    <request_id>.reply.parsed.json
  artifact_inbox/
    <workspace>/<task>/<answer>/
      artifact.zip
      artifact.sha256
      intake.json
  artifact_candidates.json
  promptbranch_artifacts.json
```

## 9.3 Candidate registry entry

```json
{
  "kind": "candidate_release",
  "version": "v0.0.201",
  "filename": "chatgpt_claudecode_workflow_v0.0.201.zip",
  "path": "./chatgpt_claudecode_workflow_v0.0.201.zip",
  "sha256": "...",
  "source": {
    "request_id": "...",
    "answer_id": "...",
    "downloaded_from": "assistant_reply"
  },
  "verified": true,
  "accepted": false
}
```

---

# 10. Error taxonomy

## 10.1 Ask/reply errors

```text
reply_missing
reply_timeout
reply_partial
reply_schema_missing
reply_schema_invalid
reply_schema_ambiguous
reply_request_id_mismatch
reply_correlation_mismatch
reply_multiple_answers
reply_answer_changed
```

## 10.2 Artifact intake errors

```text
artifact_candidate_missing
artifact_candidate_ambiguous
artifact_download_url_missing
artifact_download_failed
artifact_download_expired
artifact_wrong_filename
artifact_wrong_version
artifact_wrong_project
artifact_zip_invalid
artifact_wrapper_folder
artifact_hygiene_failed
artifact_nested_zip
artifact_baseline_mismatch
artifact_repair_policy_violation
```

## 10.3 Migration/adoption errors

```text
candidate_not_verified
candidate_already_exists
candidate_registry_update_failed
candidate_test_failed
candidate_adopt_failed
candidate_state_mismatch
```

---

# 11. Security and safety model

## 11.1 Trust boundaries

Untrusted:

```text
- assistant prose
- assistant-provided links
- assistant validation claims
- host-side LLM interpretation
- downloaded ZIP before verification
```

Trusted only after deterministic validation:

```text
- parsed protocol envelope
- schema validation result
- ZIP verification result
- release-control full test/report
- adopt verification result
```

## 11.2 No automatic adoption from answer

Even if ChatGPT says:

```text
Adopt this ZIP.
```

Promptbranch must not adopt until:

```text
- artifact downloaded
- artifact verified
- artifact migrated as candidate
- full test/report green
- adopt command succeeds
- current state matches expected version
```

## 11.3 No host-side LLM authority

The host-side LLM may assist, but the deterministic policy gate decides.

---

# 12. MVP plan

This section is the linked MVP plan for the design above.

Back to design: [Design summary](#1-design-summary)

## MVP-F0 — Ask/Reply Protocol

Goal:

```text
Every pb ask request and assistant reply uses a shared, validated JSON protocol.
```

Scope:

```text
- add JSON schemas
- add prompt contract
- add request envelope builder
- add reply envelope parser
- persist raw and parsed answers
- expose artifact candidates from reply envelope
- no download yet
- no migration yet
- no auto-adopt
```

Commands:

```bash
pb ask "..." --protocol --print-request-json
pb ask "..." --protocol --json
pb task answer parse --latest --json
```

Acceptance:

```text
- valid request JSON can be generated
- ChatGPT prompt includes reply contract
- reply envelope can be extracted from answer text
- invalid JSON returns reply_schema_invalid
- no envelope returns reply_schema_missing
- multiple envelopes returns reply_schema_ambiguous
- artifact candidates are listed but not downloaded
```

Recommended release:

```text
v0.0.201
```

---

## MVP-F1 — Artifact Candidate Extraction

Goal:

```text
Promptbranch can classify candidate artifacts from the parsed reply and fallback text links.
```

Scope:

```text
- extract artifacts[] from protocol reply
- fallback parse markdown/plain links
- classify ZIP candidates
- detect ambiguous multiple ZIPs
- require expected artifact name/version when possible
```

Commands:

```bash
pb artifact intake --from-last-answer --json
pb artifact intake --from-answer <answer_id> --json
```

Acceptance:

```text
- one expected ZIP candidate is detected
- no ZIP returns artifact_candidate_missing
- multiple ZIPs without expected selector returns artifact_candidate_ambiguous
- wrong filename/version returns artifact_wrong_version or artifact_wrong_project
```

Recommended release:

```text
v0.0.202
```

---

## MVP-F2 — Artifact Download

Goal:

```text
Promptbranch can download candidate artifacts into .pb_profile/artifact_inbox/ without mutating accepted artifact state.
```

Scope:

```text
- explicit --download flag
- download to artifact inbox
- calculate sha256 and size
- preserve source answer/request metadata
- handle expired/missing links
```

Commands:

```bash
pb artifact intake --from-last-answer --download --json
```

Acceptance:

```text
- downloaded file is stored under .pb_profile/artifact_inbox/
- sha256 recorded
- size recorded
- no repo-root file created yet
- no artifact state adopted
```

Recommended release:

```text
v0.0.203.1
```

---

## MVP-F3 — ZIP Verification

Goal:

```text
Downloaded artifacts are verified before migration.
```

Scope:

```text
- ZIP opens
- VERSION exists
- filename/version match
- no wrapper folder
- hygiene checks
- baseline continuity checks
- repair-version checks
```

Commands:

```bash
pb artifact intake --from-last-answer --download --verify --json
pb artifact verify .pb_profile/artifact_inbox/.../artifact.zip --json
```

Acceptance:

```text
- valid ZIP becomes verified candidate
- invalid ZIP fails closed
- hygiene failure is explicit
- wrong baseline/version is explicit
```

Recommended release:

```text
v0.0.204
```

---

## MVP-F4 — Candidate Migration

Goal:

```text
Verified artifacts can be migrated to canonical repo-root candidate ZIPs without becoming accepted baselines.
```

Scope:

```text
- explicit --migrate flag
- copy verified ZIP to repo root
- register candidate_release
- do not adopt
- do not update source_ref/artifact_ref as current baseline
```

Commands:

```bash
pb artifact intake --from-last-answer --download --verify --migrate --json
pb artifact candidates --json
```

Acceptance:

```text
- repo-root candidate ZIP exists
- candidate registry updated
- accepted baseline unchanged
- candidate source answer metadata preserved
```

Recommended release:

```text
v0.0.205
```

---

## MVP-F5 — Guarded Candidate Test/Adopt

Goal:

```text
A verified migrated candidate can be tested and adopted only if the validation report is green.
```

Scope:

```text
- connect candidate artifact to release-control test/adopt flow
- verify current state after adopt
- preserve release logs
- fail closed on test/report/adopt mismatch
```

Commands:

```bash
pb artifact accept-candidate --version v0.0.201 --test --adopt-if-green --json
```

or current bridge:

```bash
./chatgpt_claudecode_workflow_release_control.sh \
  --version v0.0.201 \
  --tests-only \
  --adopt-if-green \
  --skip-docker-logs \
  --prune-release-logs \
  --release-log-keep 12
```

Acceptance:

```text
- full test/report green required
- adopt verified required
- current state matches candidate version
- candidate becomes adopted_release only after verification
```

Recommended release:

```text
v0.0.206
```

---

## MVP-F6 — Continue Ask From Adopted Baseline

Goal:

```text
After adoption, the next pb ask automatically references the accepted baseline.
```

Scope:

```text
- request envelope reads pb artifact current
- current baseline injected automatically
- target version can be inferred or explicitly supplied
- repair release logic respected
```

Commands:

```bash
pb ask "Continue next slice" --protocol --from-current-baseline --json
```

Acceptance:

```text
- request envelope includes adopted artifact/source version
- wrong stale baseline is not used
- repair baseline continuity is preserved
```

Recommended release:

```text
v0.0.207
```

---

# 13. Acceptance criteria

The full MVP-F is complete when this works end-to-end:

```bash
pb ask "Implement v0.0.201 from current baseline" --protocol --json

pb task answer parse --latest --json

pb artifact intake --from-last-answer --download --verify --migrate --json

./chatgpt_claudecode_workflow_release_control.sh \
  --version v0.0.201 \
  --tests-only \
  --adopt-if-green \
  --skip-docker-logs \
  --prune-release-logs \
  --release-log-keep 12

pb artifact current --json

pb ask "Continue v0.0.202 from current baseline" --protocol --from-current-baseline --json
```

Expected invariants:

```text
- ask request is structured
- reply envelope is valid
- artifact candidate is found
- artifact is downloaded only explicitly
- ZIP is verified before migration
- migrated artifact is candidate_release, not adopted_release
- full tests are green before adoption
- adopted state matches runtime/source/artifact versions
- next ask uses the adopted baseline automatically
```

---

# 14. Open questions

1. Can the current service access ChatGPT artifact download links directly, or must download happen through browser context?
2. Are artifact URLs stable enough to store, or should Promptbranch store only answer IDs and re-resolve links when needed?
3. Should the reply envelope be required for all `pb ask`, or only for `pb ask --protocol` initially?
4. Should the host reject answers that contain prose but no envelope, or allow manual-only mode?
5. How should multiple assistant answers for one user message be selected?
6. Should `pb ask` infer `target_version`, or must the operator supply it?
7. How should repair releases be requested and validated in the protocol?
8. Should artifact intake support non-ZIP outputs later, such as docs or JSON reports?

---

# Final design verdict

The MVP should be extended with an Ask/Reply Protocol and Artifact Intake layer.

Without this layer, Promptbranch still depends on manual handling at the most important transition point:

```text
ChatGPT generated artifact -> local verified release candidate
```

With this layer, Promptbranch becomes a true control plane:

```text
structured ask
  -> structured reply
  -> candidate artifact
  -> verified ZIP
  -> migrated candidate
  -> guarded test/adopt
  -> next structured ask from accepted baseline
```

