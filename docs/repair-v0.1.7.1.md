# Repair v0.1.7.1 — Docker service stale-version rebuild fallback

Base release: `chatgpt_claudecode_workflow-2_v0.1.7.zip`  
Repair version: `v0.1.7.1`

## Reason

Installing `v0.1.7` could fail during service verification after the Docker service recreated but `/healthz` still reported the previous runtime version, for example:

```text
service version mismatch: expected 0.1.7, got '0.1.6'
```

The packaged version surfaces in `v0.1.7` were correct, so this repair treats the failure as a Docker rebuild/recreate freshness defect rather than a feature-scope issue.

## Files changed

```text
VERSION
pyproject.toml
promptbranch_version.py
docker-compose.chatgpt-service.yml
chatgpt_claudecode_workflow_release_control.sh
docs/repair-v0.1.7.1.md
```

## Change

`chatgpt_claudecode_workflow_release_control.sh` now retries Docker service recreation with a no-cache image rebuild when the normal rebuild/recreate path fails service version verification. The fallback is only reached after the normal deterministic rebuild path fails, so normal installs do not always pay the no-cache cost.

## Validation performed

```text
bash -n chatgpt_claudecode_workflow_release_control.sh
python3 -m compileall -q .
python3 scripts/orchestration/validate_examples.py
python3 -m pytest -q tests/orchestration/test_orchestration_examples.py
python3 -m pytest -q tests/test_promptbranch_cli.py -k 'release_checkpoint or release_dev_status or release_install_plan or release_lifecycle_plan or release_config or release_doctor'
python3 -m pytest -q tests/test_cli_parser.py -k 'release_checkpoint or release_dev_status or release_install or release_lifecycle or release_config'
release-control --import-plan
ZIP reopen / CRC / hygiene / root-layout verification
```

## Slice/line confirmation

No slice or line was advanced. This is a repair-only release for install/runtime version verification freshness.
