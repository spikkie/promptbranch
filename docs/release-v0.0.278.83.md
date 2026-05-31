# chatgpt_claudecode_workflow v0.0.278.83

## Purpose

Normal release from v0.0.278.82 to fix the visual artifact roundtrip smoke-content expectation.

## Reason

The v0.0.278.81 live log showed that project creation, project-scoped ask, browser-context artifact download, and temporary-project cleanup all succeeded, but smoke verification failed because Promptbranch expected `output.txt` to include a trailing newline while the assistant-created ZIP contained the exact token without the newline.

## Changes

- Removed the implicit trailing newline from the default visual-roundtrip input token.
- Removed the implicit trailing newline from the default visual-roundtrip expected output token.
- Kept artifact-intake ZIP verification strict: downloaded bytes must still match the expected content exactly.
- Did not change source upload, adoption, release state, or migration behavior.

## Validation

- `python3 -m compileall promptbranch_cli.py promptbranch_service.py promptbranch_version.py`
- Focused CLI/parser/response tests.
- Packaged ZIP hygiene and version-surface verification.
