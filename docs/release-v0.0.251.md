# Release v0.0.251 — Native release acceptance hook runner

Base release: `chatgpt_claudecode_workflow_v0.0.250.1.zip`

## Scope

This release adds the next native release-lifecycle MVP slice: `pb release test`.

The command runs configured release acceptance hooks from `.promptbranch-release.yml`, captures structured hook evidence, and writes a release acceptance report under `.pb_profile/release_acceptance/<version>/`.

## Added command

```bash
pb release test \
  --artifact chatgpt_claudecode_workflow_v0.0.251.zip \
  --version v0.0.251 \
  --target-version v0.0.252 \
  --repo-path . \
  --json
```

Optional read-only plan:

```bash
pb release test \
  --artifact chatgpt_claudecode_workflow_v0.0.251.zip \
  --version v0.0.251 \
  --target-version v0.0.252 \
  --repo-path . \
  --plan \
  --json
```

## Lifecycle boundary

`pb release test` may execute configured project hook commands, but the Promptbranch command itself does not:

- adopt artifacts
- update artifact/source state
- update the artifact registry
- mutate Project Sources
- commit Git state
- push Git state

The output is an evidence report for a later adoption gate.

## Structured report

Reports use schema:

```text
promptbranch.release.acceptance_report / 1.0
```

They include:

- candidate version
- target version
- artifact inspection
- hook commands
- hook return codes
- stdout/stderr tails
- accepted/rejected status
- explicit confirmation that adoption/state/git/source mutation were not performed

## Validation

Focused validation performed before packaging:

```bash
python3 -m py_compile promptbranch_cli.py promptbranch_version.py
pytest -q tests/test_promptbranch_cli.py tests/test_cli_parser.py
pytest -q tests/test_chatgpt_container_api.py tests/test_promptbranch_container_api.py tests/test_promptbranch_mcp.py tests/test_project_source_capabilities.py tests/test_promptbranch_automation_service.py
```
