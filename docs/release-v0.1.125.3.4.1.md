# Release v0.1.125.3.4.1

## Purpose

Repair the live candidate-test retry boundary exposed by repeated `v0.1.125.3.4` browser failures, while retaining the authoritative runtime promotion and final-convergence contract from `.3.4`.

## Baseline evidence

The accepted/current control-plane baseline remains `v0.1.125.3.3`. The unaccepted `.3.4` candidate reached `RUNTIME_PREPARED` twice. The first full test failed at `browser.task_message_flow.ask` with a 300-second `ReadTimeout`; the retry reused the same already-mutated integration project and later failed at `browser.project_source_add_text` after the Save click emitted zero relevant backend requests. No rate-limit evidence was observed and production promotion never ran.

## Repair contract

1. Every `TESTED_GREEN` execution gets a unique `test_run_id`, monotonically increasing retry number, and fresh integration project name bound to artifact SHA and retry identity.
2. Candidate image/container/runtime checkpoint are reused across retryable test failures; mutated browser-test project state is never reused.
3. Every test attempt persists project identity, timestamps, report/stdout/stderr hashes, failed step, forensic-retention status, and supersession linkage.
4. Candidate-test stdout/stderr/report files are unique per retry and cannot overwrite prior forensic evidence.
5. A source-add failure where Save emitted zero relevant requests first reconciles the authoritative source surface. A matching late-visible source is accepted as recovered success; an empty surface permits exactly one controlled retry; an unrelated or unreadable surface remains fail-closed.
6. ReadTimeout remains retryable and evidence-rich.
7. The `.3.4` production-promotion contract is retained: promote the exact tested image to canonical port `8000`, verify live version/SHA/attempt labels, rollback on failed promotion, clean superseded isolated candidate runtimes, and require live authoritative runtime identity for `FINAL_VERIFIED`.

## Canonical live command

```text
pb release run --artifact chatgpt_claudecode_workflow-2_v0.1.125.3.4.1.zip --version v0.1.125.3.4.1 --baseline-version v0.1.125.3.3 --release-type repair --profile full --test-timeout 3600 --until final-verified --adopt --json
```

No Git commit, push, or Project Source publication is implied.
