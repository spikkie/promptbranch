# Repair v0.1.77.7 — Retargeted temporary project cleanup uses resolved project URL

## Repair identity

```text
base accepted release: chatgpt_claudecode_workflow-2_v0.1.76.zip
failed intended release: chatgpt_claudecode_workflow-2_v0.1.77.zip
failed repair candidate: chatgpt_claudecode_workflow-2_v0.1.77.6.zip
repair version: v0.1.77.7
artifact: chatgpt_claudecode_workflow-2_v0.1.77.7.zip
```

## Reason

`v0.1.77.6` still failed full release-control in `project_remove_cleanup`.
The cleanup verifier resolved the exact temporary project by name, but retry removal still called the service without passing the resolved project URL as a `project_url` request field. Setting a dynamic `project_service.project_url` attribute was not sufficient for `ChatGPTServiceClient`, because that client only forwards an explicitly supplied `project_url` argument.

## Files changed

```text
promptbranch_full_integration_test.py
tests/test_full_integration_harness.py
VERSION
pyproject.toml
promptbranch_version.py
tests/test_promptbranch_version.py
docs/project/definition-of-done.md
docs/project/plan.md
docs/project/status.md
docs/project/release-status.md
docs/project/decisions.md
docs/project/migration.md
```

## Validation performed

```text
focused cleanup retarget regression tests
project control-surface tests
version tests
compileall
bash syntax checks
ZIP hygiene checks
clean extraction validation
```

## Scope control

```text
No normal slice advanced.
No release line advanced.
No repo-loop semantics changed.
No registry/adoption semantics changed.
No Project Source upload behavior changed.
```
