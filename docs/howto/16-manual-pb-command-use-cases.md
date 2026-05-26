# Manual Promptbranch command use cases

## Purpose

This document is a hands-on operator manual for running the Promptbranch workflow by typing `pb` or `promptbranch` commands manually.

It is intentionally command-first. Use it when you want to understand or reproduce what the lifecycle scripts do without hiding the work behind one wrapper.

The canonical command groups are:

```text
pb ws ...          workspace / ChatGPT Project scope
pb task ...        task / chat scope
pb src ...         project source files, links, and text
pb ask ...         prompt execution and protocol ask/reply
pb artifact ...    release ZIP, candidate, intake, adoption state
pb release ...     native release lifecycle diagnostics and guarded steps
pb test ...        smoke/browser/agent/full validation profiles
pb agent ...       read-only local MCP/agent operations
pb mcp ...         MCP tool surface and stdio server helpers
pb skill ...       local skill registry
pb debug ...       diagnostic artifacts for brittle UI/backend surfaces
pb doctor          cheap local health checks
```

Use `promptbranch` instead of `pb` when a shell alias/function prints extra text before command output. This matters when piping JSON into `python3 -m json.tool`, `jq`, or another parser.

## Critical safety assessment

### What may fail

- Commands that touch ChatGPT Projects can fail because of login state, bearer-token state, browser profile locks, rate limits, UI changes, or backend changes.
- `pb src add`, `pb src sync --upload`, artifact adoption from Project Sources, and lifecycle execution are mutations. They must be verified after the command returns.
- `pb ask --protocol --parse-reply` can submit successfully but fail reply parsing when the assistant answer is missing, delayed, malformed, or contains more than one protocol envelope.
- `pb artifact intake --download --verify --migrate` depends on a previously parsed protocol reply and an accessible artifact link.
- `pb test full --json` can be long-running and environment-dependent.
- `pb release lifecycle` without `--plan` and `pb release git-sync --commit` / `--push` are high-risk compared with read-only diagnostics.

### Invariants

- Workspace, task, and artifact state are separate scopes.
- Reads should be backend-first when the implementation supports it.
- Mutations are not accepted by trust; they must be re-read and verified.
- A ZIP candidate is not an accepted baseline until tests/adoption/current-state verification say so.
- Local runtime version, `VERSION`, Project Source state, and artifact current state can diverge during a lifecycle; diagnose before assuming.

## 0. Command hygiene

Check which executable you are using:

```bash
command -v pb || true
command -v promptbranch
pb version
promptbranch version
```

Prefer clean JSON output for automation:

```bash
promptbranch version
promptbranch doctor --json | python3 -m json.tool
```

Load environment explicitly when needed:

```bash
set -a
. ./.env
set +a
promptbranch doctor --json | python3 -m json.tool
```

Common environment facts to verify:

```bash
printf 'CHATGPT_SERVICE_TOKEN=%s\n' "${CHATGPT_SERVICE_TOKEN:+set}"
printf 'CHATGPT_SERVICE_URL=%s\n' "${CHATGPT_SERVICE_URL:-unset}"
printf 'CHATGPT_CLI_CONFIG=%s\n' "${CHATGPT_CLI_CONFIG:-unset}"
```

## 1. Local health and login use cases

### 1.1 Show version

```bash
pb version
```

Expected result:

```text
promptbranch 0.0.276.3
```

### 1.2 Run cheap local doctor

```bash
pb doctor --json | python3 -m json.tool
```

Use this before browser- or project-dependent commands.

### 1.3 Verify ChatGPT login/browser profile

```bash
pb login-check --keep-open
```

Use this when project, task, or source commands fail with browser/login symptoms.

## 2. Workspace / project use cases

A workspace is the active ChatGPT Project.

### 2.1 List workspaces

```bash
pb ws list
pb ws list --json | python3 -m json.tool
```

### 2.2 Select a workspace by name

```bash
pb ws use "Claude Code workflow in Chatgpt"
```

JSON form:

```bash
pb ws use "Claude Code workflow in Chatgpt" --json | python3 -m json.tool
```

### 2.3 Select a workspace by URL

```bash
pb ws use 'https://chatgpt.com/g/g-p-.../project/...'
```

### 2.4 Select interactively from visible projects

```bash
pb ws use --pick
```

### 2.5 Show current workspace

```bash
pb ws current
pb ws current --json | python3 -m json.tool
```

### 2.6 Leave workspace and task state

```bash
pb ws leave
```

This clears both workspace and task state.

## 3. Task / chat use cases

A task is the active chat/conversation inside the workspace.

### 3.1 List tasks for the current workspace

```bash
pb task list
pb task list --json | python3 -m json.tool
```

Use deep history only when normal project-scoped listing is insufficient:

```bash
pb task list --deep-history --json | python3 -m json.tool
```

### 3.2 Select a task by index

```bash
pb task use 1
```

### 3.3 Select a task by id, prefix, title, or URL

```bash
pb task use '6a118728-cc88-83eb-a2fd-12f7d9d5a69c'
pb task use 'Architecture canvas'
pb task use 'https://chatgpt.com/c/...'
```

### 3.4 Show current task

```bash
pb task current
pb task current --json | python3 -m json.tool
```

### 3.5 Show transcript

```bash
pb task show
pb task show --json | python3 -m json.tool
```

Show a different task without selecting it:

```bash
pb task show 3
```

### 3.6 List user messages and assistant answers

```bash
pb task messages list
pb task messages list --json | python3 -m json.tool
```

### 3.7 Show one user message

```bash
pb task message show 1
pb task message show 1 --json | python3 -m json.tool
```

### 3.8 Show assistant answer for one message

```bash
pb task message answer 1
pb task message answer 1 --json | python3 -m json.tool
```

### 3.9 Leave current task but keep workspace

```bash
pb task leave
pb task leave --json | python3 -m json.tool
```

## 4. Ask use cases

### 4.1 Plain ask in current workspace/task

```bash
pb ask 'Reply with exactly the single token INTEGRATION_OK and nothing else.'
```

### 4.2 Continue a specific conversation URL

```bash
pb ask 'Continue from the previous context.' \
  --conversation-url 'https://chatgpt.com/c/...'
```

### 4.3 Ask with a file attached to the message

This attaches a file to one chat message. It does not add it as a persistent Project Source.

```bash
pb ask 'Analyze this log and give root cause.' \
  --attach ./session.log
```

Multiple attachments:

```bash
pb ask 'Compare these two logs.' \
  --attach ./before.log \
  --attach ./after.log
```

### 4.4 Ask from a prompt file

```bash
pb ask --prompt-file ./prompt.txt
```

Combine inline text and a prompt file:

```bash
pb ask 'Use this extra instruction.' \
  --prompt-file ./prompt.txt
```

### 4.5 Print a protocol request without sending it

```bash
pb ask 'Implement the next documentation-only repair.' \
  --protocol \
  --from-current-baseline \
  --target-version v0.0.276.3 \
  --release-type repair \
  --print-request-json \
  | python3 -m json.tool
```

### 4.6 Submit a protocol ask and parse the reply

```bash
pb ask 'Implement the next documentation-only repair.' \
  --protocol \
  --from-current-baseline \
  --target-version v0.0.276.3 \
  --release-type repair \
  --parse-reply \
  --json \
  | python3 -m json.tool
```

### 4.7 Parse the latest answer after a protocol ask

```bash
pb task answer parse --latest --json | python3 -m json.tool
```

Parse a specific answer:

```bash
pb task answer parse \
  --message-index 2 \
  --answer-index 1 \
  --json \
  | python3 -m json.tool
```

### 4.8 Strict release-candidate ask

Use this when you expect exactly one ZIP candidate.

```bash
pb ask-release \
  --target-version v0.0.277 \
  --release-type normal \
  --expect-artifact chatgpt_claudecode_workflow_v0.0.277.zip \
  --expect-version v0.0.277 \
  --json \
  'Build the next release candidate from the current accepted baseline.' \
  | python3 -m json.tool
```

Dry-run the request envelope first:

```bash
pb ask-release \
  --target-version v0.0.277 \
  --expect-artifact chatgpt_claudecode_workflow_v0.0.277.zip \
  --print-request-json \
  | python3 -m json.tool
```

## 5. Project source use cases

Project Sources are persistent context attached to the ChatGPT Project. Do not confuse them with one-message attachments.

### 5.1 List sources

```bash
pb src list
pb src list --json | python3 -m json.tool
```

### 5.2 Add a file source

```bash
pb src add ./chatgpt_claudecode_workflow_v0.0.276.3.zip
```

Explicit form:

```bash
pb src add --type file --file ./chatgpt_claudecode_workflow_v0.0.276.3.zip
```

Do not overwrite an existing same-name source:

```bash
pb src add ./chatgpt_claudecode_workflow_v0.0.276.3.zip --no-overwrite
```

### 5.3 Add a text source

```bash
pb src add \
  --type text \
  --name 'operator note' \
  --value 'This is a short project-source text note.'
```

### 5.4 Add a link source

```bash
pb src add \
  --type link \
  --value 'https://example.com/' \
  --name 'example reference'
```

### 5.5 Remove a source

```bash
pb src rm 'chatgpt_claudecode_workflow_v0.0.276.2.zip'
```

Require exact matching:

```bash
pb src rm 'chatgpt_claudecode_workflow_v0.0.276.2.zip' --exact
```

### 5.6 Package and source-sync a repo snapshot

Plan without creating or uploading anything:

```bash
pb src sync . --plan --json | python3 -m json.tool
```

Create/register the ZIP locally but do not upload:

```bash
pb src sync . --no-upload --json | python3 -m json.tool
```

Choose output directory and filename:

```bash
pb src sync . \
  --output-dir .pb_profile/artifacts \
  --filename chatgpt_claudecode_workflow_v0.0.276.3.zip \
  --no-upload \
  --json \
  | python3 -m json.tool
```

Request a live upload preflight. Review the returned confirmation command before executing it:

```bash
pb src sync . --upload --json | tee src_sync_upload_preflight.json
```

Confirm the reviewed upload transaction:

```bash
pb src sync . \
  --confirm-upload \
  --confirm-transaction-id '<transaction-id-from-preflight>' \
  --json \
  | python3 -m json.tool
```

## 6. Artifact state and ZIP use cases

Artifacts are local repo snapshots, release ZIPs, candidate ZIPs, and accepted baselines.

### 6.1 Show current artifact/source baseline

```bash
pb artifact current
pb artifact current --json | python3 -m json.tool
```

### 6.2 List local artifacts

```bash
pb artifact list
pb artifact list --json | python3 -m json.tool
```

### 6.3 Verify a ZIP

```bash
pb artifact verify ./chatgpt_claudecode_workflow_v0.0.276.3.zip --json \
  | python3 -m json.tool
```

Manual ZIP checks without `pb`:

```bash
unzip -p chatgpt_claudecode_workflow_v0.0.276.3.zip VERSION
python3 - <<'PY'
import zipfile
from pathlib import Path
zip_path = Path('chatgpt_claudecode_workflow_v0.0.276.3.zip')
with zipfile.ZipFile(zip_path) as zf:
    names = [n for n in zf.namelist() if n.strip('/')]
roots = sorted({n.split('/')[0] for n in names})
wrapper = len(roots) == 1 and all('/' in n for n in names)
print({'entry_count': len(names), 'wrapper_folder': wrapper, 'sample_roots': roots[:20]})
PY
```

### 6.4 Create a release ZIP

Use the current repository as input:

```bash
pb artifact release . --json | python3 -m json.tool
```

Create/register through the source-sync transaction workflow without upload:

```bash
pb artifact release . --sync-source --no-upload --json | python3 -m json.tool
```

Request a live source upload preflight. Review the returned confirmation command before executing it:

```bash
pb artifact release . --sync-source --upload --json \
  | tee artifact_release_upload_preflight.json
```

Confirm the reviewed upload transaction:

```bash
pb artifact release . \
  --sync-source \
  --confirm-upload \
  --confirm-transaction-id '<transaction-id-from-preflight>' \
  --json \
  | python3 -m json.tool
```

### 6.5 Adopt an existing Project Source ZIP as current baseline

Only do this after the ZIP is visible in Project Sources and validation is green.

```bash
pb artifact adopt chatgpt_claudecode_workflow_v0.0.276.3.zip \
  --from-project-source \
  --json \
  | python3 -m json.tool
```

With local path evidence:

```bash
pb artifact adopt chatgpt_claudecode_workflow_v0.0.276.3.zip \
  --from-project-source \
  --local-path ./chatgpt_claudecode_workflow_v0.0.276.3.zip \
  --json \
  | python3 -m json.tool
```

## 7. Ask/reply artifact-intake use cases

These commands process a ZIP candidate returned by a protocol reply.

### 7.1 Inspect candidate from latest answer, no mutation

```bash
pb artifact intake --from-last-answer --json | python3 -m json.tool
```

### 7.2 Download candidate into artifact inbox

```bash
pb artifact intake \
  --from-last-answer \
  --download \
  --json \
  | python3 -m json.tool
```

### 7.3 Download and verify candidate

```bash
pb artifact intake \
  --from-last-answer \
  --download \
  --verify \
  --json \
  | python3 -m json.tool
```

### 7.4 Download, verify, and migrate candidate to repo root

```bash
pb artifact intake \
  --from-last-answer \
  --download \
  --verify \
  --migrate \
  --json \
  | python3 -m json.tool
```

### 7.5 Check migrated candidate status

```bash
pb artifact candidate-status --json | python3 -m json.tool
```

### 7.6 Ask for the next candidate action

```bash
pb artifact candidate-next --json | python3 -m json.tool
```

### 7.7 Execute one allowlisted candidate step

```bash
pb artifact candidate-run --json | python3 -m json.tool
```

Execute until blocked or complete:

```bash
pb artifact candidate-run \
  --execute-until-blocked \
  --max-steps 4 \
  --step-timeout 3600 \
  --json \
  | python3 -m json.tool
```

Require completion:

```bash
pb artifact candidate-run \
  --execute-until-blocked \
  --require-complete \
  --json \
  | python3 -m json.tool
```

### 7.8 Test a migrated candidate without adoption

```bash
pb artifact candidate-test \
  --version v0.0.276.3 \
  --json \
  | python3 -m json.tool
```

### 7.9 Accept a migrated candidate after green candidate-test

```bash
pb artifact accept-candidate \
  --version v0.0.276.3 \
  --adopt-if-green \
  --json \
  | python3 -m json.tool
```

### 7.10 Show Artifact Intake MVP cockpit

```bash
pb artifact mvp-status --json | python3 -m json.tool
```

### 7.11 Show MVP definition-of-done visibility

```bash
pb artifact mvp-dod --json | python3 -m json.tool
```

## 8. Release lifecycle use cases

`pb release ...` is the native lifecycle direction. Prefer read-only commands first.

### 8.1 Read lifecycle status cockpit

```bash
pb release lifecycle-status \
  --version v0.0.276.3 \
  --target-version v0.0.277 \
  --repo-path . \
  --json \
  | python3 -m json.tool
```

### 8.2 Run release doctor

```bash
pb release doctor \
  --version v0.0.276.3 \
  --target-version v0.0.277 \
  --json \
  | python3 -m json.tool
```

Include candidate artifact inspection:

```bash
pb release doctor \
  --version v0.0.276.3 \
  --target-version v0.0.277 \
  --artifact ./chatgpt_claudecode_workflow_v0.0.276.3.zip \
  --json \
  | python3 -m json.tool
```

### 8.3 Validate release config

```bash
pb release config --json | python3 -m json.tool
```

### 8.4 Plan install of a candidate ZIP

```bash
pb release install \
  --version v0.0.276.3 \
  --artifact ./chatgpt_claudecode_workflow_v0.0.276.3.zip \
  --plan \
  --json \
  | python3 -m json.tool
```

### 8.5 Execute install of a candidate ZIP

Only after the plan is understood:

```bash
pb release install \
  --version v0.0.276.3 \
  --artifact ./chatgpt_claudecode_workflow_v0.0.276.3.zip \
  --json \
  | python3 -m json.tool
```

### 8.6 Run acceptance hooks

```bash
pb release test \
  --version v0.0.276.3 \
  --artifact ./chatgpt_claudecode_workflow_v0.0.276.3.zip \
  --json \
  | python3 -m json.tool
```

### 8.7 Adopt through native release command

Only after acceptance is green and the ZIP is a Project Source:

```bash
pb release adopt \
  --version v0.0.276.3 \
  --artifact ./chatgpt_claudecode_workflow_v0.0.276.3.zip \
  --json \
  | python3 -m json.tool
```

### 8.8 Sync local policy after adoption

```bash
pb release policy-sync \
  --version v0.0.276.3 \
  --artifact chatgpt_claudecode_workflow_v0.0.276.3.zip \
  --json \
  | python3 -m json.tool
```

### 8.9 Plan guarded Git sync

```bash
pb release git-sync \
  --version v0.0.276.3 \
  --artifact chatgpt_claudecode_workflow_v0.0.276.3.zip \
  --plan \
  --json \
  | python3 -m json.tool
```

### 8.10 Execute guarded Git commit/push

Only after reviewing the plan. Use `--commit`; add `--push` only when the same-run guarded commit succeeded and upstream prechecks are acceptable:

```bash
pb release git-sync \
  --version v0.0.276.3 \
  --artifact chatgpt_claudecode_workflow_v0.0.276.3.zip \
  --commit \
  --json \
  | python3 -m json.tool
```

```bash
pb release git-sync \
  --version v0.0.276.3 \
  --artifact chatgpt_claudecode_workflow_v0.0.276.3.zip \
  --commit \
  --push \
  --json \
  | python3 -m json.tool
```

### 8.11 Plan full native lifecycle

```bash
pb release lifecycle \
  --version v0.0.276.3 \
  --artifact ./chatgpt_claudecode_workflow_v0.0.276.3.zip \
  --plan \
  --json \
  | python3 -m json.tool
```

### 8.12 Execute full native lifecycle

High-risk. Run only when the plan is clean and you intend mutation. Execution is the default when `--plan` is omitted. Add `--commit` or `--push` only when you intentionally want guarded Git sync as part of the lifecycle.

```bash
pb release lifecycle \
  --version v0.0.276.3 \
  --artifact ./chatgpt_claudecode_workflow_v0.0.276.3.zip \
  --json \
  | python3 -m json.tool
```

With guarded commit but no push:

```bash
pb release lifecycle \
  --version v0.0.276.3 \
  --artifact ./chatgpt_claudecode_workflow_v0.0.276.3.zip \
  --commit \
  --json \
  | python3 -m json.tool
```

## 9. Final Artifact Intake MVP finalizer use case

The finalizer wraps `scripts/post-release-validation.sh` with strict finalization flags.

### 9.1 Run preflight manually

```bash
cat VERSION
pb version
pb artifact current --json | python3 -m json.tool
pb src list --json | python3 -m json.tool
pb artifact verify ./chatgpt_claudecode_workflow_v0.0.276.3.zip --json | python3 -m json.tool
```

### 9.2 Run finalizer

```bash
scripts/finalize-artifact-intake-mvp.sh \
  --version v0.0.276.3 \
  --target-version v0.0.277 \
  --pb-cmd promptbranch \
  --test-timeout 900
```

### 9.3 Run finalizer with strict real-candidate requirement

From `v0.0.276.6`, this strict form asks ChatGPT for an artifact-producing release candidate by running `pb ask-release` for `--target-version` before full tests/adoption, then runs artifact intake with `--download --verify` before candidate-run proof is accepted.

```bash
scripts/finalize-artifact-intake-mvp.sh \
  --version v0.0.276.6 \
  --target-version v0.0.277 \
  --pb-cmd promptbranch \
  --require-real-candidate-mvp \
  --candidate-mvp-max-steps 4 \
  --candidate-run-step-timeout 3600 \
  --test-timeout 900
```

Inspect strict download proof:

```bash
python3 -m json.tool .pb_profile/release_logs/v0.0.276.6/pb_ask_protocol_smoke.v0.0.276.6.json
python3 -m json.tool .pb_profile/release_logs/v0.0.276.6/pb_artifact_intake_dry_run.v0.0.276.6.json
```

Required fields in the intake evidence:

```text
download_performed: true
verification_performed: true
```

### 9.4 Inspect finalizer evidence

```bash
ls -l .pb_profile/release_logs/v0.0.276.3/
python3 -m json.tool \
  .pb_profile/release_logs/v0.0.276.3/post_release_validation.v0.0.276.3.summary.json
```

## 10. Test use cases

### 10.1 Run smoke tests

```bash
pb test smoke --json | tee pb_test.smoke.v0.0.276.3.log
```

### 10.2 Run browser/project/source/task tests

```bash
pb test browser --json | tee pb_test.browser.v0.0.276.3.log
```

### 10.3 Run local MCP/agent/skill tests

```bash
pb test agent --json | tee pb_test.agent.v0.0.276.3.log
```

### 10.4 Run full test profile

```bash
timeout 900s pb test full --json | tee pb_test.full.v0.0.276.3.log
```

### 10.5 Summarize a test log

```bash
pb test report pb_test.full.v0.0.276.3.log --json \
  | tee pb_test.full.v0.0.276.3.report.json
```

### 10.6 Show last known full status

```bash
pb test status --json | python3 -m json.tool
```

### 10.7 Verify installed imports outside the source tree

```bash
pb test import-smoke --json | python3 -m json.tool
```

### 10.8 Legacy daily suite

```bash
pb test-suite --json | tee pb_test_suite.v0.0.276.3.log
```

Run a single suite selector:

```bash
pb test-suite --only mcp_smoke --json | tee pb_test_suite.mcp_smoke.v0.0.276.3.log
```

Skip a selector:

```bash
pb test-suite --skip source_remove --json | tee pb_test_suite.no_source_remove.v0.0.276.3.log
```

## 11. Local agent / MCP / skill use cases

These are intended to be read-only unless a command explicitly says otherwise.

### 11.1 Inspect local repo through agent surface

```bash
pb agent inspect --path . --json | python3 -m json.tool
```

### 11.2 Run agent doctor

```bash
pb agent doctor --path . --json | python3 -m json.tool
```

### 11.3 Plan without executing

```bash
pb agent plan 'read VERSION and git status' --path . --json \
  | python3 -m json.tool
```

### 11.4 Run deterministic read-only request

```bash
pb agent run 'read VERSION and git status' --path . --json \
  | python3 -m json.tool
```

Legacy equivalent:

```bash
pb agent ask 'read VERSION and git status' --path . --json \
  | python3 -m json.tool
```

### 11.5 Run host/client smoke

```bash
pb agent host-smoke --path . --json | python3 -m json.tool
```

### 11.6 Call one MCP tool through stdio boundary

```bash
pb agent mcp-call filesystem.read '{"path":"VERSION"}' \
  --path . \
  --json \
  | python3 -m json.tool
```

### 11.7 Call one read-only tool through deterministic executor

```bash
pb agent tool-call git.status '{}' --path . --json \
  | python3 -m json.tool
```

### 11.8 Use Ollama only as proposal/summarizer

List models:

```bash
pb agent models --json | python3 -m json.tool
```

Ask for a proposed read-only tool call:

```bash
pb agent ollama-propose 'read VERSION' \
  --model llama3.2:3b \
  --json \
  | python3 -m json.tool
```

Run diagnostic LLM-proposed MCP smoke:

```bash
pb agent mcp-llm-smoke 'read VERSION' \
  --path . \
  --model llama3.2:3b \
  --json \
  | python3 -m json.tool
```

Summarize a repo-bounded log:

```bash
pb agent summarize-log pb_test.full.v0.0.276.3.log \
  --path . \
  --model llama3.2:3b \
  --json \
  | python3 -m json.tool
```

### 11.9 Run release-readiness skill

```bash
pb agent release-readiness --path . --json | python3 -m json.tool
```

### 11.10 List, show, and validate skills

```bash
pb skill list --json | python3 -m json.tool
pb skill show repo-inspection --json | python3 -m json.tool
pb skill validate repo-inspection --json | python3 -m json.tool
```

Validate a local skill path:

```bash
pb skill validate .promptbranch/skills/repo-inspection --json \
  | python3 -m json.tool
```

### 11.11 MCP manifest and server helpers

```bash
pb mcp manifest --json | python3 -m json.tool
pb mcp config --path . --json | python3 -m json.tool
pb mcp host-smoke --path . --json | python3 -m json.tool
```

Run the server manually for an MCP host:

```bash
pb mcp serve --path .
```

## 12. Debug and troubleshooting use cases

### 12.1 Debug task/chat enumeration

```bash
pb debug chats --json | python3 -m json.tool
```

Use this when `pb task list` misses a visible chat or returns stale data.

### 12.2 Show shell prompt state

```bash
pb prompt
pb state
```

### 12.3 Clear remembered state

```bash
pb state-clear
```

### 12.4 Emit shell completion

```bash
pb completion bash > /tmp/promptbranch.bash
pb completion zsh > /tmp/_promptbranch
pb completion fish > /tmp/promptbranch.fish
```

### 12.5 Interactive shell loop

```bash
pb shell
```

With default attachment:

```bash
pb shell --file ./context.txt
```

## 13. Legacy aliases and preferred replacements

Prefer the canonical command groups in new scripts.

| Legacy command | Preferred command |
|---|---|
| `pb project-list` | `pb ws list` |
| `pb use <project>` | `pb ws use <project>` |
| `pb state` | `pb ws current` / `pb task current` |
| `pb state-clear` | `pb ws leave` |
| `pb chat-list` / `pb chats` | `pb task list` |
| `pb chat-use` / `pb use-chat` | `pb task use` |
| `pb chat-leave` / `pb cq` | `pb task leave` |
| `pb chat-show` / `pb show` | `pb task show` |
| `pb chat-summarize` / `pb summarize` | legacy summary command; prefer explicit `pb task show` plus `pb ask` summary workflow |
| `pb source-list` | `pb src list` |
| `pb source-add` | `pb src add` |
| `pb source-remove` | `pb src rm` |

## 14. End-to-end manual workflows

### 14.1 Daily operator startup

```bash
pb version
pb doctor --json | python3 -m json.tool
pb ws current --json | python3 -m json.tool
pb task current --json | python3 -m json.tool
pb artifact current --json | python3 -m json.tool
pb test status --json | python3 -m json.tool
```

### 14.2 Select project, inspect task, ask, and parse answer

```bash
pb ws use "Claude Code workflow in Chatgpt" --json | python3 -m json.tool
pb task list --json | python3 -m json.tool
pb task use 1 --json | python3 -m json.tool
pb task show
pb ask 'Summarize the current task state in one paragraph.'
pb task messages list --json | python3 -m json.tool
```

### 14.3 Update project context with a fresh repo ZIP source

```bash
pb ws current --json | python3 -m json.tool
pb src sync . --filename chatgpt_claudecode_workflow_v0.0.276.3.zip --no-upload --json
pb src list --json | python3 -m json.tool
```

### 14.4 Generate a strict release request and process the answer manually

```bash
pb ask-release \
  --target-version v0.0.277 \
  --expect-artifact chatgpt_claudecode_workflow_v0.0.277.zip \
  --json \
  'Build the next release candidate from the current accepted baseline.' \
  | tee ask_release.v0.0.277.json

pb task answer parse --latest --json | tee reply_parse.v0.0.277.json
pb artifact intake --from-last-answer --json | tee intake.inspect.v0.0.277.json
pb artifact intake --from-last-answer --download --verify --migrate --json \
  | tee intake.migrate.v0.0.277.json
pb artifact candidate-status --json | python3 -m json.tool
```

### 14.5 Test and accept a migrated candidate manually

```bash
pb artifact candidate-test --version v0.0.277 --json \
  | tee candidate_test.v0.0.277.json
pb artifact accept-candidate --version v0.0.277 --adopt-if-green --json \
  | tee accept_candidate.v0.0.277.json
pb artifact current --json | python3 -m json.tool
```

### 14.6 Repair release manual path

```bash
pb artifact current --json | python3 -m json.tool
pb ask 'Create a documentation-only repair release v0.0.276.3 from v0.0.276.2. Do not change runtime behavior.' \
  --protocol \
  --from-current-baseline \
  --target-version v0.0.276.3 \
  --release-type repair \
  --parse-reply \
  --json \
  | tee ask_repair.v0.0.276.3.json
pb task answer parse --latest --json | python3 -m json.tool
```

### 14.7 Manual validation of a local candidate ZIP

```bash
unzip -p chatgpt_claudecode_workflow_v0.0.276.3.zip VERSION
pb artifact verify chatgpt_claudecode_workflow_v0.0.276.3.zip --json | python3 -m json.tool
bash -n scripts/finalize-artifact-intake-mvp.sh scripts/post-release-validation.sh chatgpt_claudecode_workflow_release_control.sh
python3 -m py_compile $(find . -path './.venv' -prune -o -name '*.py' -print)
pytest tests/test_promptbranch_shell_scripts.py -q
pytest tests/test_promptbranch_cli.py -q -k 'mvp_dod or lifecycle_status or release_doctor'
```

### 14.8 Reproduce full validation risk

```bash
timeout 900s pb test full --json \
  2>&1 | tee pb_test.full.v0.0.276.3.manual.log
pb test report pb_test.full.v0.0.276.3.manual.log --json \
  | tee pb_test.full.v0.0.276.3.manual.report.json
```

## 15. Decision table

| Situation | First command | Mutation? | Follow-up |
|---|---:|---:|---|
| Need to know current project | `pb ws current --json` | No | `pb ws use ...` if wrong |
| Need to know current chat | `pb task current --json` | No | `pb task list`, then `pb task use ...` |
| Need to inspect sources | `pb src list --json` | No | `pb src add` or `pb src rm` only after review |
| Need to send one prompt | `pb ask '...'` | Yes, creates chat turn | `pb task messages list` |
| Need structured release reply | `pb ask-release ... --json` | Yes, creates chat turn | `pb task answer parse --latest` |
| Need to inspect candidate from reply | `pb artifact intake --from-last-answer --json` | No | Add `--download --verify --migrate` only when correct |
| Need to validate ZIP | `pb artifact verify ZIP --json` | No | Fix packaging if failed |
| Need to adopt baseline | `pb artifact adopt ZIP --from-project-source --json` | Yes | `pb artifact current --json` |
| Need release diagnosis | `pb release doctor --json` | No | Use status/next actions |
| Need full release lifecycle | `pb release lifecycle --plan --json` | No | Omit `--plan` only after plan review; add `--commit` / `--push` intentionally |
| Need local MCP confidence | `pb agent host-smoke --path . --json` | No | `pb agent run ...` |
| Need broad validation | `pb test full --json` | No project mutation expected, but browser/service side effects possible | `pb test report ...` |

## 16. Minimum evidence bundle after manual work

After any significant manual lifecycle run, keep these artifacts:

```text
pb artifact current --json output
pb src list --json output
pb release doctor --json output
pb release lifecycle-status --json output
pb test full log and report, when run
candidate-test / accept-candidate output, when used
post_release_validation summary, when finalizer is used
```

Recommended capture pattern:

```bash
mkdir -p .pb_profile/manual_evidence/v0.0.276.3
pb artifact current --json > .pb_profile/manual_evidence/v0.0.276.3/artifact_current.json
pb src list --json > .pb_profile/manual_evidence/v0.0.276.3/src_list.json
pb release doctor --version v0.0.276.3 --target-version v0.0.277 --json \
  > .pb_profile/manual_evidence/v0.0.276.3/release_doctor.json
pb release lifecycle-status --version v0.0.276.3 --target-version v0.0.277 --repo-path . --json \
  > .pb_profile/manual_evidence/v0.0.276.3/lifecycle_status.json
```

Do not package `.pb_profile/manual_evidence/` into a release ZIP.

### v0.0.276.7 strict artifact-materialization note

A protocol reply may declare a ZIP artifact in JSON and set `download.available=true`, but that is not sufficient real-candidate proof. If the only artifact reference is `sandbox:/mnt/data/...` inside the JSON envelope and no real ChatGPT attachment/download link is detected by the host, strict validation must fail with `artifact_declared_but_not_attached`. Use manual import only after an actual ZIP file has been downloaded to the operator machine.


### Browser-session download for ChatGPT attachment links

From `v0.0.276.8`, when the selected candidate URL is a ChatGPT `sandbox:/mnt/data/...` attachment reference, `pb artifact intake --download` first attempts a browser/session-context download instead of immediately requiring manual import.

```bash
pb artifact intake \
  --from-last-answer \
  --expect-artifact chatgpt_claudecode_workflow_v0.0.277.zip \
  --expect-version v0.0.277 \
  --expect-repo chatgpt_claudecode_workflow \
  --download \
  --verify \
  --json | tee intake.browser_download_verify.v0.0.277.json
```

If browser-assisted download fails, use the manual fallback after clicking the ChatGPT UI link yourself:

```bash
pb artifact intake \
  --from-last-answer \
  --expect-artifact chatgpt_claudecode_workflow_v0.0.277.zip \
  --expect-version v0.0.277 \
  --expect-repo chatgpt_claudecode_workflow \
  --local-file "$HOME/Downloads/chatgpt_claudecode_workflow_v0.0.277.zip" \
  --verify \
  --json | tee intake.manual_import_verify.v0.0.277.json
```
