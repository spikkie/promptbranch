# Repair v0.1.88.1 — project-source-add-text timeout diagnostics/recovery repair

## Base release

`v0.1.88` candidate.

Accepted/current before this repair remains `chatgpt_claudecode_workflow-2_v0.1.87.1.zip` until operator adoption/current evidence proves otherwise.

## Repair version

`v0.1.88.1`

## Reason

The `v0.1.88` run-tests/adoption gate failed in `project_source_add_text` with a client-side `ReadTimeout` after roughly 300 seconds. A focused retry against an existing retained Project reproduced the same `project_source_add_text` timeout while rate-limit telemetry remained clean.

The timeout was not a loop-planner defect and did not disprove the incremental validation-evidence reuse design. It blocked adoption before the `--run-all-tests` reuse proof could be run.

## Root cause hypothesis

The full integration Docker-service adapter had a source-mutation timeout budget helper, but source add requests did not pass that extended request timeout to the service client. Source add operations therefore used the general 300-second client timeout even though Project Source mutations can legitimately take longer when the ChatGPT Project Sources UI is slow or post-save persistence verification is delayed.

## Files changed

- `promptbranch_full_integration_test.py`
- `tests/test_full_integration_harness.py`
- `VERSION`
- `pyproject.toml`
- `promptbranch_version.py`
- `tests/test_promptbranch_version.py`
- `docs/project/status.md`
- `docs/project/release-status.md`
- `docs/project/definition-of-done.md`
- `docs/project/decisions.md`
- `docs/project/migration.md`

## Repair details

- Docker-service source add calls now pass the extended source-mutation timeout to `ChatGPTServiceClient.add_project_source(...)` via `request_timeout_seconds`.
- If a source add still reaches a client-side `ReadTimeout`, the adapter returns a structured fail-closed payload instead of an opaque exception.
- The structured timeout payload includes timeout dimensions, release-blocking status, Project URL, source kind, and operator recovery guidance.
- The post-failure Project Source list diagnostic now also runs for structured source-mutation timeout failures, so operators can inspect whether the source became late-visible before retrying.

## Validation performed

Focused validation passed locally for:

- Docker-service extended source mutation timeout contract.
- Structured source-add timeout failure payload.
- Source-add timeout post-failure source-list diagnostic.
- Existing post-commit diagnostic behavior.
- Loop regressions.
- CLI loop regressions.
- Version surface.
- Project control surface.
- `compileall` for touched runtime modules.
- Shell syntax for release-control.
- Artifact Guardian.
- Artifact verification and ZIP hygiene.

## Explicit non-advancement

This repair does not advance the `v0.1.88` evidence-reuse slice. It does not change loop behavior, adoption semantics, Project Source mutation authority, Project deletion policy, deployment behavior, Kubernetes behavior, or `--run-all-tests` reuse scope.
