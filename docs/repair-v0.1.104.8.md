# Repair v0.1.104.8 — auth readiness and browser challenge debug repair

Base candidate: `chatgpt_claudecode_workflow-2_v0.1.104.7.zip`

This is a repair-only candidate for the `v0.1.104` normal slice. It preserves the sandbox mutation verification and rollback evidence gate and the `v0.1.104.1` project-remove frozen scheduler timeout repair. It does not advance to `v0.1.105`.

## Reason

Live validation showed that the first blocking layer is no longer Project Sources selector behavior. The browser reaches ChatGPT through Patchright but can be held on auth/challenge surfaces such as Cloudflare human verification, `/api/auth/error`, or Turnstile/private-access-token flows before Project Sources can render.

## Changes

- Add a machine-readable auth-readiness snapshot with URL, title, visible text preview, driver, profile directory, FedCM mode, and challenge flags.
- Detect auth/challenge blockers from visible text as well as URL/title.
- When Project Sources cannot be opened and the auth-readiness snapshot is blocked, fail closed with `auth_challenge_blocking_before_project_sources`.
- Preserve `project_source_mutated=false` and `persistence_verified=false` for this failure class.
- Surface structured service error detail through the CLI source-add failure payload when available.

## Out of scope

- No Cloudflare bypass.
- No Project Source selector workaround.
- No isolated release-test mode.
- No sandbox correction promotion readiness.
- No repository-wide correction workflow.
- No ChatGPT Project deletion.

## Validation

Focused validation should include auth-readiness snapshot tests, Project Sources preflight failure classification, control-surface validation, Artifact Guardian, and artifact verify. Full release-control remains required before adoption/current.
