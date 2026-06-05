# Release v0.1.37 — threshold handoff and Promptbranch class diagram

## Scope

`v0.1.37` is a small focused-development threshold handoff slice built from `v0.1.36`.

It keeps runtime/source/adoption behavior unchanged and adds:

- read-only `threshold_handoff` payload in `pb release status-guide --json`;
- read-only `threshold_handoff` payload in `pb release checkpoint --json`;
- plain-text threshold handoff markers for operator logs;
- editable Promptbranch class diagram at `docs/design/promptbranch-class-diagram.drawio`;
- living-design documentation linking the class diagram and threshold handoff.

## Behavior

When the current candidate has reached the configured full-test/adoption threshold, the handoff reports:

```text
threshold_handoff.status = full_test_adoption_checkpoint_required
threshold_handoff.operator_action = run_full_release_control_for_current_candidate
threshold_handoff.full_test_recommended_now = true
threshold_handoff.full_test_command = ./chatgpt_claudecode_workflow_release_control.sh ... --run-tests ...
threshold_handoff.adopt_current_after_green_full_test = ./chatgpt_claudecode_workflow_release_control.sh ... --adopt-current ...
```

The handoff remains read-only. It does not run tests, adopt artifacts, upload Project Sources, sync policy, or mutate Git.

## Class diagram

New source:

```text
docs/design/promptbranch-class-diagram.drawio
```

The diagram shows the main Promptbranch runtime/design classes:

- `PromptbranchCLI`
- `ConversationStateStore`
- `WorkspaceState`
- `TaskState`
- `ArtifactState`
- `ArtifactRegistry`
- `ReleaseStatusGuide`
- `ReleaseCheckpoint`
- `ReleaseInstallPlan`
- `ThresholdHandoff`
- `ReleaseControlScript`
- `ProjectSourceClient`
- `PromptbranchMcpHost`
- `PromptbranchMcpServer`
- `SkillRegistry`

## Validation performed before packaging

```text
python3 -m py_compile promptbranch_cli.py tests/test_promptbranch_cli.py
pytest -q tests/test_promptbranch_cli.py -k 'release_status_guide or release_checkpoint or full_test_countdown'
python3 -m compileall -q .
python3 promptbranch_cli.py test smoke --json --path .
python3 promptbranch_cli.py release docs-status --version v0.1.37 --json
python3 promptbranch_cli.py release config --json
python3 promptbranch_cli.py artifact verify /mnt/data/chatgpt_claudecode_workflow-2_v0.1.37.zip --json
release install --plan against packaged v0.1.37
release lifecycle --plan against packaged v0.1.37
ZIP CRC / VERSION / hygiene verification
```

## Operator handoff

Install and inspect:

```bash
./chatgpt_claudecode_workflow_release_control.sh \
  --version v0.1.37 \
  --install-from-zip ~/Downloads/chatgpt_claudecode_workflow-2_v0.1.37.zip \
  --skip-source-add \
  --skip-tests \
  --prune-release-logs \
  --release-log-keep 12

pb release status-guide \
  --artifact ./chatgpt_claudecode_workflow-2_v0.1.37.zip \
  --version v0.1.37 \
  --target-version v0.1.37 \
  --json | python3 -m json.tool

pb release checkpoint \
  --artifact ./chatgpt_claudecode_workflow-2_v0.1.37.zip \
  --version v0.1.37 \
  --target-version v0.1.37 \
  --mode continue \
  --json | python3 -m json.tool

pb test smoke --json
```

Then run full release-control and adopt only if green:

```bash
./chatgpt_claudecode_workflow_release_control.sh \
  --version v0.1.37 \
  --install-from-zip ~/Downloads/chatgpt_claudecode_workflow-2_v0.1.37.zip \
  --skip-source-add \
  --run-tests \
  --prune-release-logs \
  --release-log-keep 12

./chatgpt_claudecode_workflow_release_control.sh \
  --version v0.1.37 \
  --skip-tests \
  --adopt-current \
  --skip-docker-logs \
  --prune-release-logs \
  --release-log-keep 12
```
