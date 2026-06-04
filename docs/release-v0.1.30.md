# Release v0.1.30 — baseline-status development checkpoint artifact selection

## Purpose

`v0.1.30` fixes a read-only operator guidance issue discovered while inspecting a full-test-green but not-yet-adopted development candidate.

When `pb release baseline-status --version <candidate> --json` was run before adoption and no explicit `--artifact` was supplied, the command correctly reported that `baseline-status` is post-adoption only, but the suggested development checkpoint command could combine the candidate version with the previously accepted artifact path.

## Scope

This release keeps all behavior read-only except normal version metadata updates. It changes only the command guidance produced by `baseline-status` in development-candidate context.

## Behavior

If `baseline-status` detects an installed development candidate and a matching local candidate ZIP exists in the repo root, it now emits:

```text
pb release checkpoint --artifact ./<candidate-zip> --version <candidate-version> --target-version <candidate-version> --mode continue --json
```

instead of falling back to the accepted baseline artifact path.

The payload also exposes:

```text
development_checkpoint_artifact
development_checkpoint_artifact_source
```

so operators and smoke/focused tests can see whether the checkpoint artifact came from an explicit argument, a local development candidate, or the accepted-baseline fallback.

## Non-goals

This release does not change:

- adoption semantics
- Project Source upload/add behavior
- ZIP import/install behavior
- full-test execution
- structured post-release validation summary generation
- ChatGPT browser automation

## Validation target

Focused validation should include:

```text
python3 -m compileall -q .
python3 -m pytest -q tests/test_promptbranch_cli.py::test_release_baseline_status_uses_local_dev_candidate_for_checkpoint_without_explicit_artifact
python3 -m pytest -q tests/test_promptbranch_cli.py::test_release_baseline_status_guides_dev_candidate_to_checkpoint
pb test smoke --json --path .
pb release docs-status --version v0.1.30 --json
pb release install --artifact ./chatgpt_claudecode_workflow-2_v0.1.30.zip --version v0.1.30 --target-version v0.1.30 --plan --json
pb release lifecycle --artifact ./chatgpt_claudecode_workflow-2_v0.1.30.zip --version v0.1.30 --target-version v0.1.30 --plan --json
```
