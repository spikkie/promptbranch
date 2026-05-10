# Repair v0.0.201.1

Base release: v0.0.201
Repair version: v0.0.201.1

## Reason

`v0.0.201` introduced `promptbranch_ask_protocol.py` and imported it from `promptbranch_cli.py`, but the new module was not listed in `pyproject.toml` under `tool.setuptools.py-modules`. After pipx installation, `pb` failed before tests with:

```text
ModuleNotFoundError: No module named 'promptbranch_ask_protocol'
```

The protocol data directory also lacked package metadata for installed schema/example/prompt files.

## Files changed

- `pyproject.toml`
- `promptbranch_protocol/__init__.py`
- version metadata files
- `docs/repair-v0.0.201.1.md`

## Validation performed

- Python syntax compilation for core modules
- Focused ask protocol tests
- Package metadata/import checks
- Temporary venv install with `pip install --no-deps .` and `import promptbranch_cli`
- ZIP CRC/testzip check
- Artifact hygiene verification

## Scope confirmation

No MVP slice, feature line, schema semantics, artifact-intake behavior, ZIP download, ZIP migration, Project Source mutation, or adoption automation was advanced. This repair fixes packaging/installability defects only.
