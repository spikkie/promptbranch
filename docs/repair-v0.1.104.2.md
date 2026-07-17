# Repair v0.1.104.2 — bounded post-bootstrap conversation-idle recovery

## Baseline

- Accepted/current: `v0.1.103.10.116`
- Repaired candidate: unadopted `v0.1.104.1`
- `v0.1.104.1` proved fresh direct, independent localhost, and all 13 sandbox gates, but external-live reproduced `target_conversation_busy` because `interrupted_answer_state` persisted after a completed bootstrap.

## Scope

1. Preserve the complete sandbox gate and ten-step release manifest unchanged.
2. Preserve fresh direct and independent localhost execution.
3. Probe composer readiness after bootstrap and before ask fill.
4. Recover only when `interrupted_answer_state` is the sole blocker.
5. Reload the same trusted conversation exactly once using the same page, browser context, and physical profile.
6. Do not resubmit bootstrap and do not create another conversation.
7. Reverify the bootstrap sentinel after reload.
8. Require no stop, thinking, running, or interrupted state before ask submission.
9. Fail closed as `target_conversation_busy` after one unsuccessful recovery.
10. Preserve structured rate-limit and Cloudflare classification rules.

## Out of scope

General retries, source lifecycle changes, sandbox changes, deployment, repository mutation, Project deletion, and scope advancement.
