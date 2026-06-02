# Release v0.1.6

## Scope

Read-only CI-style release checkpoint planning on top of the v0.1.5 development head.

This release adds:

- `pb release checkpoint --artifact ZIP --version VERSION --mode continue --json`
- `pb release checkpoint --artifact ZIP --version VERSION --mode adopt --json`
- a structured checkpoint decision separating:
  - continuing focused development,
  - running one full release-control test,
  - adopting only after green validation.

## Non-goals

This release does not:

- install a candidate into the repository;
- upload or mutate Project Sources;
- run full browser/service tests;
- adopt an artifact;
- update the artifact registry;
- sync release policy;
- commit or push Git state.

## Validation

Focused validation performed during artifact creation:

- `python3 -m pytest -q tests/test_promptbranch_cli.py -k 'release_checkpoint or release_dev_status or release_install_plan or release_lifecycle_plan or release_config or release_doctor'`
- `python3 -m pytest -q tests/test_cli_parser.py -k 'release_checkpoint or release_dev_status or release_install or release_lifecycle or release_config'`
- `python3 scripts/orchestration/validate_examples.py`
- `python3 -m pytest -q tests/orchestration/test_orchestration_examples.py`
- `python3 -m compileall -q .`
- `python3 promptbranch_cli.py release checkpoint --artifact /mnt/data/chatgpt_claudecode_workflow-2_v0.1.6.zip --version v0.1.6 --target-version v0.1.6 --mode continue --json`
- release-control import-plan against the generated ZIP.
