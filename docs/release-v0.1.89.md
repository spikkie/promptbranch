# Release v0.1.89 — Live validation timing visibility and click-path audit

## Baseline

Accepted/current baseline: `chatgpt_claudecode_workflow-2_v0.1.88.1.zip`.

## Scope

This release adds observability for live browser validation cost and shortest-path action review before repeated broad `--run-all-tests` runs.

## Changes

- Browser client now attaches a `browser_action_audit` payload to browser-operation results.
- Click attempts, successes, failures, fallback strategies, repeated click labels, and a cooldown-risk score are captured.
- Test reports now summarize browser action audits across browser steps so the operator can review whether Promptbranch took the shortest safe path to the goal.
- Test reports now expose a `timing_summary` with total browser-step duration and slowest steps.

## Safety

The action audit is observational. It does not authorize extra clicks or mutate Projects. Redundant/fallback clicks are flagged for review because every additional click can increase live UI cooldown and 429 exposure.

## Out of scope

- No Project deletion behavior changes.
- No Project Source mutation semantic changes.
- No artifact adoption/current behavior changes.
- No Kubernetes/deployment behavior.
- No broad live-test retry policy changes.

## Validation

Focused validation covered browser action audit aggregation, timing report aggregation, version consistency, loop regressions, project-control docs, compileall, shell syntax, Artifact Guardian, and ZIP hygiene.
