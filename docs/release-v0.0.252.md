# Release v0.0.252 — Release Adopt + Verification Gate

## Scope

This release adds the native release adoption gate:

```bash
pb release adopt --artifact ZIP --version VERSION --json
```

The command advances local artifact/source baseline state only after deterministic preconditions are verified.

## Implemented behavior

`pb release adopt` now:

- verifies the candidate artifact ZIP;
- loads the latest structured acceptance report for the requested version, or an explicitly supplied report;
- requires a green `promptbranch.release.acceptance_report` with matching version, artifact filename, and artifact sha256 when present;
- verifies exactly one matching Project Source exists before adoption;
- writes an adopted release record to the artifact registry;
- updates Promptbranch artifact/source state;
- re-reads `pb artifact current` semantics and verifies the adopted artifact/source baseline.

## Safety boundaries

The command does not:

- upload Project Sources;
- run acceptance hooks;
- mutate Git state;
- commit or push;
- sync policy files.

Those remain separate lifecycle slices.

## Validation

Focused validation performed:

```text
python3 -m py_compile promptbranch_cli.py
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q \
  tests/test_cli_parser.py \
  tests/test_chatgpt_container_api.py \
  tests/test_promptbranch_container_api.py \
  tests/test_promptbranch_mcp.py \
  tests/test_promptbranch_automation_service.py

PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q \
  tests/test_promptbranch_cli.py \
  -k 'release_adopt or release_test or release_install or source_upload_verification or parser_accepts_release'
```

Result:

```text
112 passed
18 passed, 268 deselected
```

## Next step

Continue with policy sync in v0.0.253.
