# Release v0.1.128.2.1 — Release smoke timeout auto-recovery repair

Accepted/current baseline: `v0.1.128.1.1.1.1.1`, SHA-256 `dd9ed8949990b1b143e7930a2357adbebaccb935744a5bc30342942dbccdcdbd`.
Construction predecessor: exact `v0.1.128.2` learning/skills artifact.

## Purpose

Make the first canonical release lifecycle invocation resilient to supported transient ChatGPT/browser ask timeouts so an operator does not need a second repair/retry command after `candidate_test_ask_timeout` or equivalent service/assistant-response timeout evidence.

## Scope

- preserve the entire v0.1.128.2 learning/onboarding and portable skill-bundle implementation unchanged;
- run canonical `ask_question` and `task_message_flow.ask` through one bounded release-smoke recovery policy;
- use a short 90-second per-attempt ask budget and at most three total attempts by default;
- after a transient timeout, observe the correlated conversation backend first and accept the already-completed expected token without resubmitting;
- if the submitted prompt is present but unresolved, retry against the same recovered conversation when possible;
- for new-project task/message asks, discover the correlated newly-created conversation by the unique smoke prompt before retrying;
- preserve the exact pinned conversation route for baseline `ask_question`;
- emit `promptbranch.release_ask_recovery` attempt/recovery evidence in the single normal test step;
- never auto-retry or hide authentication/challenge, 429/cooldown, permission, route mismatch, or ambiguous submit-causality failures.

## Non-goals

- no generic user `pb ask` retry semantics are broadened;
- no timeout is converted into unconditional success;
- no accepted/current, Project Source, artifact registry, or external application authority is changed by construction;
- no compatibility alias or legacy fallback is introduced.

## Acceptance

Construction closes only when the exact artifact passes the canonical 17 release-validation groups, deterministic rebuild, ZIP CRC, Artifact Guardian, and focused timeout-recovery regressions. Release closure additionally requires one fresh canonical repair lifecycle from accepted/current `v0.1.128.1.1.1.1.1` to independently verified FINAL_VERIFIED/current `v0.1.128.2.1`, after which `v0.1.129` becomes active and `v0.1.130` becomes planned-after-acceptance.
