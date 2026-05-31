# Release v0.0.278.77

Narrow visual artifact roundtrip prompt-sharing repair.

## Reason

`pb test visual-artifact-roundtrip` needed the same production prompt construction style used by release-candidate asks. The previous visual test prompt was hand-shaped and the test asserted prompt fragments independently, which made prompt intent less clear and easier to drift.

## Scope

- Add a shared ZIP artifact user-prompt builder used by release-candidate asks and the visual artifact roundtrip test.
- Keep the visual test from embedding a complete successful JSON envelope.
- Remove explicit placeholder/example URL literals from the visual artifact prompt.
- Update the unit test to compare the prompt sent to the backend with the production prompt builder output.

## Validation

- Compile check.
- Focused parser and visual artifact roundtrip tests.
- Reopened ZIP hygiene and version checks.

## Non-goals

- No release adoption.
- No Project Source mutation.
- No broad browser/live behavior change.
