# Repair v0.1.78.2 — Project deletion safety freeze

## Baseline

```text
chatgpt_claudecode_workflow-2_v0.1.78.1.zip candidate
```

## Problem

The v0.1.78.1 live service log proved that Promptbranch can execute real ChatGPT project deletion through `/v1/projects/remove` and browser UI confirmation. Even when the observed deletion targeted an integration-test project, the exposed destructive path is too dangerous for the current automation model.

## Decision

Project deletion is frozen. Promptbranch must not delete ChatGPT Projects until a separately designed secure delete protocol exists.

## Scope

In scope:

- Add a canonical `project_delete_disabled` payload.
- Block `/v1/projects/remove` before service resolution or browser context creation.
- Block automation service/wrapper/browser-client public `remove_project` calls before browser launch.
- Preserve Project Source add/remove behavior; this repair does not disable source removal.
- Let full integration cleanup treat the delete-disabled payload as an intentional retained-temporary-project cleanup outcome.
- Add focused regression tests proving no browser/service call is made.

Out of scope:

- Designing the future secure delete protocol.
- Any ChatGPT Project deletion.
- Normal AG-001 behavior changes.
- Artifact Guardian build/heal/agent/lifecycle integration.
- Adoption/current mutation.

## Safety invariant

```text
No public Promptbranch remove_project path may open a browser context or click a ChatGPT delete UI while project deletion is frozen.
```

## Validation performed

```text
pending in generated package; see final response for commands and results
```

## Adoption rule

This ZIP is a repair candidate only. It is not accepted/current until `pb artifact current --json` / `--all --json` adoption evidence proves runtime, state artifact, state source, registry current, and consistency alignment.
