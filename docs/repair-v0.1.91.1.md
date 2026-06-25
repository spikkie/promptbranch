# Repair v0.1.91.1 — Ask-live first-turn retry recovery and run-all step aggregation repair

## Base release

`v0.1.91` accepted/current.

## Repair version

`v0.1.91.1`

## Reason

The `v0.1.91 --run-all-tests --adopt-after-validation` proof failed after the direct evidence reuse and localhost matrix portions succeeded. The real functional failure was the first `ask_live` `plain` step returning ChatGPT's generic transient Retry answer with no `conversation_url` or Project identity. Later ask-live steps passed. The all-tests summary also listed `live_project_ensure`, `visual_artifact_roundtrip`, and `release_live` as failed even though their embedded command payloads were successful, showing a step-result aggregation/ranking defect.

## Files changed

- `promptbranch_cli.py`
- `chatgpt_claudecode_workflow_release_control.sh`
- `tests/test_promptbranch_cli.py`
- `tests/test_promptbranch_shell_scripts.py`
- `VERSION`
- `pyproject.toml`
- `promptbranch_version.py`
- `tests/test_promptbranch_version.py`
- project control-surface docs

## Behavior changes

- `pb test ask-live` retries the first plain step once only when the response is the specific null-project generic Retry response: no conversation URL, no response Project id/home, no expected sentinel, and answer text containing ChatGPT's generic retry wording.
- Real wrong-Project answers with a concrete response Project identity remain release-blocking and are not retried as transient.
- Ask-live step payloads record retry attempt metadata for operator audit.
- `--run-all-tests` summary JSON ranking now prefers live command result payloads for project ensure, ask-live, visual-artifact-roundtrip, and release-live over nested helper/schema objects discovered later in verbose logs.

## Scope not advanced

This repair does not advance the `v0.1.91` normal slice. It preserves evidence reuse, localhost cooldown audit, adoption/current semantics, Project Source behavior, Project deletion freeze, loop behavior, and deployment/Kubernetes boundaries.

## Validation performed

Focused validation covered first-turn ask-live transient retry, real wrong-project no-retry behavior, existing ask-live rate-limit/streaming behavior, run-all summary payload ranking, version consistency, project-control surface, compileall, shell syntax, Artifact Guardian, artifact verify, and ZIP hygiene.
