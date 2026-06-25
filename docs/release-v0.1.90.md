# Release v0.1.90 — Conversation-history/backend-api 429 pressure reduction

## Baseline

```text
chatgpt_claudecode_workflow-2_v0.1.89.zip
```

## Goal

Reduce live validation cooldown pressure before repeated broad `--run-all-tests` runs by shielding non-essential global conversation-history auto-requests from the rate-limit-sensitive `/backend-api/conversations` surface.

## Scope

This release adds a conservative browser request shield:

- Global `GET /backend-api/conversations` frontend auto-requests are fulfilled with an empty Promptbranch-marked JSON payload.
- Explicit Promptbranch conversation-history fetches are allowed through while the controlled fetch is in progress.
- Project-scoped `/backend-api/gizmos/{project_id}/conversations` calls are not intercepted.
- Telemetry now reports shield enabled/mode, shielded request count, explicit-fetch allowed count, and recent shield events.
- `pb test report` rate-limit summaries include the shield state and shielded request count.

## Safety boundaries

The shield does not change:

- Project Source mutation semantics.
- Artifact adoption/current semantics.
- ChatGPT Project deletion safety.
- Kubernetes/deployment behavior.
- Loop behavior.
- Functional validation requirements.

A shielded request is not proof of success. It is only a pressure-reduction mechanism for non-essential global history auto-requests.

## Validation performed before handoff

Focused validation only:

- conversation-history request shield route tests
- explicit Promptbranch history fetch allow-through test
- project-scoped endpoint non-interception test
- test-report shield summary test
- browser action/click audit regressions
- loop regressions
- version tests
- project-control tests
- compileall
- shell syntax
- Artifact Guardian
- artifact verify
- ZIP hygiene

## Validation not performed before handoff

- install in operator environment
- release-control `--run-tests`
- release-control `--run-all-tests`
- Project Source add/verify
- adoption/current verification
