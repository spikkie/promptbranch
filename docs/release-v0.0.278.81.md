# Release v0.0.278.81 — Visual artifact roundtrip project-home conversation recovery

## Base content

```text
chatgpt_claudecode_workflow_v0.0.278.80.zip
```

## Target artifact

```text
chatgpt_claudecode_workflow_v0.0.278.81.zip
```

## Reason

The previous repair candidate used an unsupported five-component version shape. Current release tooling does not support that release-name shape yet, so this normal release carries the same intended visual-roundtrip fix forward under the supported next normal version `v0.0.278.81`.

## Scope

This release keeps the v0.0.278.80 visual-artifact-roundtrip project-isolation design and adds the project-home conversation recovery fix:

- `pb test visual-artifact-roundtrip` still creates an isolated temporary ChatGPT Project by default.
- The visual ZIP ask still runs inside that project.
- Artifact intake validation is not relaxed.
- When the ask starts from a project home URL and the browser later navigates into a new `/c/...` conversation, the attachment-visible-answer fallback can wait for and return that project-scoped conversation URL.
- The visual-roundtrip wrapper no longer misclassifies a missing ask-level `conversation_url` as `WrongProject` before attempting recovery diagnostics.
- If ask submission/recovery still fails, the test reports `ask_failed` with diagnostics instead of a misleading project-mismatch classification.

## Validation

The release was validated from a clean extracted ZIP with:

```text
python3 -m compileall -q .
pytest -q tests/test_response_completion.py tests/test_cli_parser.py
pytest -q selected visual-artifact-roundtrip focused CLI tests
static version consistency checks
ZIP hygiene verification
```

## Notes

No artifact-intake policy was weakened. No adoption state is advanced by this release.
