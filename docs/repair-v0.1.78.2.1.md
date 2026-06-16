# Repair v0.1.78.2.1 — Package delete-safety helper module

## Problem

`v0.1.78.2` correctly added the public ChatGPT Project deletion safety freeze, but release-control from the installed ZIP failed before running tests:

```text
ModuleNotFoundError: No module named 'promptbranch_project_delete_safety'
```

The file `promptbranch_project_delete_safety.py` existed in the ZIP but was not listed in `[tool.setuptools].py-modules`, so pipx installation did not install it as an importable module.

## Scope

- Add `promptbranch_project_delete_safety` to `pyproject.toml` `py-modules`.
- Bump version surfaces to `v0.1.78.2.1`.
- Preserve the `v0.1.78.2` deletion freeze behavior unchanged.

## Out of scope

- No secure project delete protocol.
- No re-enabling ChatGPT Project deletion.
- No Project Source removal behavior change.
- No AG-001 behavior change.
- No adoption/current mutation.

## Validation expectation

Run focused import/package tests and release-control from ZIP. Adoption is only valid after operator-side `pb artifact current --json` / `--all --json` evidence confirms current alignment.
