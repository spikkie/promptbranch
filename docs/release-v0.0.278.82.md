# Release v0.0.278.82

Normal release built from `chatgpt_claudecode_workflow_v0.0.278.81.zip`.

## Reason

`pb test visual-artifact-roundtrip` can fail after creating the temporary ChatGPT Project. In v0.0.278.81, early failure paths emitted the JSON payload before the temporary-project cleanup in `finally` ran. This could report `cleanup_failed` even when the project was removed immediately afterward.

## Changes

- Made visual-artifact-roundtrip failure emission cleanup-aware.
- Failure payloads now attempt temporary-project removal before printing the final JSON status.
- The `finally` cleanup path now skips duplicate removal when failure emission already removed the project.
- No artifact-intake validation was relaxed.
- No adoption, source, or release-state behavior was changed.

## Validation

- Python compileall.
- Focused CLI parser and visual-artifact-roundtrip tests.
- ZIP hygiene verification.
