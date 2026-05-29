# Release v0.0.278.62

Repair release for the ChatGPT ask path.

## Scope

- Build from the latest v0.0.278.61 candidate.
- Keep the JSON-default and stale-answer fail-closed behavior from v0.0.278.60/v0.0.278.61.
- Fix the pre-fill composer readiness gate so an empty composer is accepted even when the send button is disabled.
- Keep stop-button, visible thinking, and interrupted-answer state as pre-fill blockers.
- Add an opt-in local headed browser debug mode for visual DOM/composer inspection.
- Keep Docker/headless service operation as the release target.

## Operator usage

Normal Docker/service target:

```bash
pb ask 'print echo 111'
```

Local headed debug mode:

```bash
pb ask --debug-browser --pause-after-fill 'print echo 111'
```

Additional pause flags:

```bash
pb ask --debug-browser --pause-before-fill 'prompt'
pb ask --debug-browser --pause-before-submit 'prompt'
```

## Validation

- Python compile validation.
- Focused unit tests for composer readiness, CLI parser debug flags, service metadata, and ask-path behavior.
- ZIP hygiene verification.
