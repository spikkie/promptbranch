# Release v0.1.10 — Read-only dev-line complexity checkpoint advisory

Base: `chatgpt_claudecode_workflow-2_v0.1.9.zip`

This release keeps the CI-style development flow monotonic while making checkpoint advice more explicit.

## Scope

- Extend `pb release dev-status --json` with a read-only `complexity_summary`.
- Extend `pb release checkpoint --mode continue --json` so it can recommend a full-test/adoption checkpoint when accumulated focused-development drift becomes large.
- Preserve focused-development mode: the command remains advisory and does not run tests, adopt, upload sources, mutate registries, sync policy, or touch Git.

## Complexity signals

The advisory considers:

- normal version distance between accepted baseline and candidate;
- number of local development candidates newer than the accepted baseline;
- repair releases present in the focused-development line.

When a threshold is reached, checkpoint output uses:

```text
status = full_test_checkpoint_recommended
checkpoint_decision.recommendation = consider_full_test_checkpoint
checkpoint_decision.full_test_recommended_now = true
checkpoint_decision.continue_development = true
```

The command still allows continued development, but gives the operator an explicit signal that a full release-control/adoption checkpoint is becoming useful.

## Non-goals

- No full tests are run.
- No browser/service/source mutation is performed.
- No adoption is performed.
- No policy sync or Git mutation is performed.

## Validation

Focused validation performed during artifact creation:

```text
python3 -m pytest -q tests/test_promptbranch_cli.py -k 'release_checkpoint or release_dev_status or release_install_plan or release_lifecycle_plan or release_config or release_doctor'
python3 -m pytest -q tests/test_cli_parser.py -k 'release_checkpoint or release_dev_status or release_install or release_lifecycle or release_config'
python3 scripts/orchestration/validate_examples.py
python3 -m pytest -q tests/orchestration/test_orchestration_examples.py
python3 -m compileall -q .
```

Full browser/service/source/adoption validation was intentionally deferred.
