# Release v0.1.100 — First controlled read-only validation command execution

## Baseline

- Accepted/current baseline: `chatgpt_claudecode_workflow-2_v0.1.99.1.zip`
- Candidate: `chatgpt_claudecode_workflow-2_v0.1.100.zip`
- Release mode: normal
- Active MVP: MVP-1 loop-based problem-solving engine

## Scope

This slice introduces the first real loop command execution after the read-only evidence report and evidence gate line.

Allowed command class:

```text
python3 -m json.tool <repo-relative-json-file>
```

The command may run only when all of the following are true:

- `--read-only-execution --evidence-gate --execute-read-only-validation` is explicitly requested.
- The existing read-only evidence gate passes.
- The command exactly matches the allowlisted JSON syntax validation shape.
- The command target is a literal repo-relative `.json` file.
- The command target is covered by `target.allowed_paths`.
- Before/after evidence proves the command input file was not modified.

## Out of scope

- broad shell execution
- pytest execution from loop targets
- correction planning
- file writes or generated patches
- deployment
- Kubernetes mutation
- Project Source mutation from loop execution
- artifact adoption from loop execution
- ChatGPT Project deletion

## Added fixture

`examples/loop-targets/read-only-validation-command-target.json` defines the first command-execution fixture. It intentionally targets itself with `python3 -m json.tool` so validation remains deterministic, repo-local, and low risk.

## Validation focus

Focused tests prove:

- the allowlisted JSON command executes once;
- stdout/stderr/exit code/duration and before/after file hash evidence are captured;
- non-allowlisted commands are blocked before execution;
- allowlisted commands outside `allowed_paths` are blocked before execution;
- CLI requires `--read-only-execution --evidence-gate` before command execution;
- Project control surface now points from accepted/current `v0.1.99.1` to candidate `v0.1.100`, with `v0.1.101` as the next planned slice.
