# Repair v0.1.104.6 — Project Sources challenge/interstitial readiness repair

## Base

- Accepted/current baseline before this repair: `chatgpt_claudecode_workflow-2_v0.1.103.zip`
- Failed normal candidate: `chatgpt_claudecode_workflow-2_v0.1.104.zip`
- Failed repair candidates preserved: `v0.1.104.1`, `v0.1.104.2`, `v0.1.104.3`, `v0.1.104.4`, `v0.1.104.5`
- Repair candidate: `chatgpt_claudecode_workflow-2_v0.1.104.6.zip`

## Reason

`v0.1.104.5` failed during pre-validation Project Source ZIP add. The improved route-hydration diagnostics proved the browser was not on a usable Project Sources UI; it was showing a ChatGPT/Cloudflare challenge/interstitial with text such as `Verification successful. Waiting for chatgpt.com to respond` and `Enable JavaScript and cookies to continue`.

## Scope

This is a repair-only release. It does not advance the active normal slice and does not open `v0.1.105`.

The preserved normal slice remains:

```text
v0.1.104 — Sandbox mutation verification and rollback evidence gate
```

## Changes

- Detect Project Sources challenge/interstitial text, not only challenge URLs/titles.
- Wait briefly for challenge/interstitial state to settle before failing.
- Keep route-recovery attempts bounded.
- Fail closed with explicit `project_sources_challenge_interstitial_blocking` status when the challenge persists.
- Mark the CLI error payload as `operator_review_required` and `manual_action_required` without claiming Project Source mutation.
- Preserve the removal of `--run-isolated-release-tests`.

## Validation

Focused validation was performed for challenge/interstitial detection, CLI payload classification, control-surface consistency, version surfaces, compileability, release-control shell syntax, Artifact Guardian, artifact verification, and ZIP integrity.

## Scope advancement

No slice or line advanced. `v0.1.105` remains deferred.
