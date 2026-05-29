# Release v0.0.278.42

## Purpose

Restore the v0.0.278.40 submit order while shortening the failed raw-Enter prepare-only wait.

## Baseline

Built from `chatgpt_claudecode_workflow_v0.0.278.40.zip` as the last known green behavioral baseline.  The v0.0.278.41 trusted-refill-primary ordering is intentionally not preserved because it regressed to prepare-only/no-commit.

## Changes

- Preserve v0.0.278.40 ordering:
  - raw Enter remains the primary keyboard submit dispatch;
  - trusted-refill + Enter remains the retry path;
  - v0.0.278.40 fast latest-turn answer promotion remains unchanged.
- Add a bounded prepare-only fast-fail path for the raw Enter primary attempt.
- When raw Enter produces `/conversation/prepare` with a conduit token but no marker-bound message submit, classify it quickly so the existing trusted-refill retry can start sooner.
- Keep exact-current-sentinel submit causality and answer freshness gates unchanged.

## Non-goals

- Does not make trusted-refill + Enter primary.
- Does not weaken exact marker/sentinel validation.
- Does not change answer extraction semantics from v0.0.278.40.
