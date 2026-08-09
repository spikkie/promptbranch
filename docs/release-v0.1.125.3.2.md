# Release v0.1.125.3.2

## Classification

Repair release derived from the exact `v0.1.125.3.1` candidate. Accepted/current remains `v0.1.124` until the exact candidate completes the canonical lifecycle and final convergence verification.

## Failures repaired

The live `v0.1.125.3.1` run proved isolated candidate runtime preparation and then failed in `TESTED_GREEN` for two independent reasons:

1. the state-machine parser selected the last nested JSON dictionary from the full report instead of the complete top-level test-suite report;
2. the genuine full suite exposed an unconfigured read-only smoke status and an ambiguous repository-root lookup because the clean candidate extraction lived below the accepted repository's `.pb_profile` tree.

The real report contained 53 completed units, 48 passed, 3 failed and 2 skipped. The failing units were the two smoke-agent wrappers and `validation.execution_envelope_validation_gate`.

## Candidate-test evidence contract

`v0.1.125.3.2` requires exactly one complete report whose identity is:

```text
schema=promptbranch.test_suite.report
schema_version=1.0
action=test_suite
profile=<requested profile>
version=<target version>
```

Mixed stdout is parsed as complete top-level JSON documents. Once a document is decoded, nested dictionaries inside it are not treated as independent reports.

The selected report must contain complete progress evidence. The candidate-test transition persists:

```text
completed
passed
failed
skipped
failed_group
failed_groups
failed_steps
report_schema
report_schema_version
report_sha256
stdout_sha256
stderr_sha256
```

Missing, ambiguous and malformed report evidence fails closed with distinct codes:

```text
candidate_test_report_missing
candidate_test_report_ambiguous
candidate_test_report_invalid
```

A missing report cannot claim `failed_count_zero=true`.

## Genuine full-suite repairs

The bounded smoke gate now treats `project_repo_not_configured` as an expected read-only uninitialized state only when no mutation flag is true.

The mandatory execution-envelope validation group now supplies an explicit clean-extraction repository authority:

```text
--repo-root .
```

This prevents the parent accepted repository from being misclassified as a second candidate root when the exact release is extracted below `.pb_profile/release_attempts_v2`.

## Transition evidence hygiene

Successful transition evidence no longer contains a stale or placeholder `failure_code`. Failure codes are present only when a transition is blocked or fails.

## Canonical command

```bash
pb release run \
  --artifact chatgpt_claudecode_workflow-2_v0.1.125.3.2.zip \
  --version v0.1.125.3.2 \
  --baseline-version v0.1.124 \
  --release-type repair \
  --profile full \
  --test-timeout 3600 \
  --until final-verified \
  --adopt \
  --json
```

Git commit, push and Project Source upload remain disabled unless their explicit positive flags are supplied.
