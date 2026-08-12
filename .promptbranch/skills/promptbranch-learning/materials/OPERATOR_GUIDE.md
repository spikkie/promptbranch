# Promptbranch operator guide

The operator's job is to make state transitions explicit, bounded and independently verifiable.

## Read before write

Before a stateful action, resolve the identities that the action will affect: repository, project/workspace, task/conversation, version and artifact SHA as applicable. Inspect the current state and working tree. Determine whether the action is read-only, controlled external process, write or destructive.

## Before execution

State the exact target, preconditions, expected evidence and failure conditions. Use PB's canonical command/control path. Do not substitute an old alias or a historical execution path because it appears to work.

## After execution

Verify the intended transition independently. For source operations, verify persistence/absence and collateral changes. For browser asks, verify causal submission and fresh-answer correlation. For releases, verify the immutable artifact, candidate runtime, tests, acceptance, adoption/current and control projection.

## Release discipline

A release is not current because a ZIP exists or a service reports a version. The adopted project-scoped artifact SHA, runtime identity and tracked current projection must converge. If a lifecycle step fails retryably, resume only through the canonical state machine; do not recreate a different artifact under the same version.

## Failure discipline

Distinguish route mismatch, service/browser timeout, rate limit/cooldown, validation failure, authority mismatch and deterministic product defects. Do not transform uncertainty into success.
