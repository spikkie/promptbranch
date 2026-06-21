# Release v0.1.81 — Accepted-event dry-run promotion foundation

## Status

```text
candidate only
```

`v0.1.81` is a focused working candidate built from the `v0.1.80` working candidate context. Accepted/current remains `v0.1.79` until a later promotion/adoption gate proves alignment with `pb artifact current --json`.

## Slice goal

Add a read-only dry-run authority bridge after accepted-event validation:

```text
pb orchestration accept-event --dry-run --json
```

The command previews whether validated accepted-event fixtures would be acceptable for a future ledger write, without writing any accepted state, mutating Project Source, adopting artifacts, deploying anything, or allowing model execution.

## In scope

- Add `pb orchestration accept-event --dry-run --json`.
- Default to committed accepted-event examples when no explicit paths are passed.
- Reuse the installed-module accepted-event validator from `promptbranch_orchestration.py`.
- Return a deterministic `accepted_event_preview` for validated fixtures.
- Fail closed when accepted-event validation fails.
- Preserve no-mutation authority flags.
- Add focused tests for valid dry-run and rejected dry-run cases.

## Out of scope

- Accepted-event ledger writes.
- `accept-event --write`.
- Proposal promotion from event-intake JSON.
- Runtime orchestration engine.
- k8s-game implementation or deployment.
- Project Source mutation behavior changes.
- Artifact adoption/current behavior changes.
- ChatGPT Project deletion behavior.

## Validation performed in artifact preparation

- `python3 promptbranch_cli.py orchestration validate-accepted-event --json`
- `python3 promptbranch_cli.py orchestration accept-event --dry-run --json`
- `python3 promptbranch_cli.py orchestration validate-event --json`
- Focused pytest for orchestration and CLI parser surfaces.
- `python3 -m compileall -q .`
- `bash -n chatgpt_claudecode_workflow_release_control.sh`

Full release-control, live browser tests, Project Source add, adoption/current verification, and Git push were not performed in artifact preparation.
