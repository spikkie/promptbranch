# Release v0.0.248 — Read-only release install planning

Built from accepted baseline `chatgpt_claudecode_workflow_v0.0.247.1.zip`.

## Scope

This release adds the read-only planning surface for the next native lifecycle stage:

```bash
pb release install --artifact ZIP --version VERSION --plan --json
```

The command validates the lifecycle config, inspects the candidate ZIP, checks filename/version alignment, enumerates installable entries, verifies configured preserved paths, and emits a deterministic install contract.

## Safety boundary

`v0.0.248` does not install files, upload Project Sources, update artifact state, adopt candidates, commit, or push. Omitting `--plan` is blocked because controlled mutation is intentionally deferred to a later release.

## Validation

- `py_compile` for modified Python files
- focused parser and release install plan tests
- release config/doctor regression tests
- selected container/API/MCP/version tests
- ZIP hygiene and root-layout verification
