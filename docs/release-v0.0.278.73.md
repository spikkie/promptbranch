# Release v0.0.278.74

Repair release after v0.0.278.72 packaging defect.

## Reason

v0.0.278.72 omitted `.gitignore` from the release ZIP.

## Scope

- Restore `.gitignore` at ZIP root.
- Preserve v0.0.278.72 file_attachment submit-readiness changes.
- Do not advance functional scope.

## Validation required

- ZIP must contain `.gitignore`.
- ZIP root must contain repository contents directly.
- ZIP hygiene must pass.
- ask-live attachment test should be rerun after install.
