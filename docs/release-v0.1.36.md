# Release v0.1.36 — pre-threshold planning notice alignment

`v0.1.36` is a focused read-only operator-guidance slice.

## Scope

- Align `checkpoint_threshold.threshold_notice.active` with the already-active `full_test_countdown.active` planning window.
- Keep `full_test_recommended_now=false` until the configured threshold is actually reached.
- Keep full release-control and adoption commands optional during the pre-threshold countdown.
- Keep the expected-next-release warning limited to the one-release-away threshold case.

## Non-goals

- No install behavior changes.
- No Project Source mutation changes.
- No adoption behavior changes.
- No full-test execution changes.
- No browser automation changes.

## Validation

Focused validation should include:

```bash
pytest -q tests/test_promptbranch_cli.py -k 'release_status_guide or release_checkpoint or full_test_countdown'
python3 promptbranch_cli.py test smoke --json --path .
python3 promptbranch_cli.py release docs-status --version v0.1.36 --json
python3 promptbranch_cli.py release config --json
python3 promptbranch_cli.py artifact verify chatgpt_claudecode_workflow-2_v0.1.36.zip --json
```

Expected post-install proof:

```text
full_test_countdown.active=true
checkpoint_threshold.threshold_notice.active=true
checkpoint_threshold.threshold_notice.pre_threshold_planning_active=true
checkpoint_threshold.next_release_reaches_full_test_threshold=false
full_test_recommended_now=false
next_development_version=v0.1.37
blocker_codes=[]
```
