# Project Status

## Current baseline

```text
accepted/current baseline with adoption evidence: chatgpt_claudecode_workflow-2_v0.1.73.4.zip
accepted checksum: a76aa4292bb8aba31c8223ae5342b6e9a731b4aef3a5505581d719d263fa1858
next normal target: chatgpt_claudecode_workflow-2_v0.1.74.zip; current repair candidate: chatgpt_claudecode_workflow-2_v0.1.74.3.zip
release line: v0.1.x JSON orchestration / Promptbranch workflow control-plane hardening
```

## Current MVP state

```text
MVP status: active, not complete
DoD status: DOD-001..DOD-028 done where evidence is listed; DOD-011 remains release-specific/open until each candidate is adopted
active plan slice: v0.1.74.3 repair — full integration source-mutation wait alignment
last completed slice: v0.1.73.4 repair accepted/current
next planned slice: build/install/test v0.1.74.3, then adopt only after release-control and pb artifact current evidence are green
```

## Current release state

```text
latest created ZIP: chatgpt_claudecode_workflow-2_v0.1.74.3.zip candidate once packaged
latest installed ZIP: chatgpt_claudecode_workflow-2_v0.1.73.4.zip
latest accepted/current ZIP: chatgpt_claudecode_workflow-2_v0.1.73.4.zip
release status: v0.1.74 failed release-control; v0.1.74.1 failed release-control; v0.1.74.2 failed release-control; v0.1.74.3 repair candidate in progress; not accepted/current
```

## Current risks

- Release-control can fail if repo validation groups accidentally use the installed CLI runtime interpreter instead of the repo/operator Python.
- Release-control can look green while focused regression groups are skipped unless the full-test report declares required validation groups.
- Running all required focused pytest groups inside `pb test full` increases release validation duration.
- Full-test group reporting must distinguish missing/skipped required groups from passed groups.
- Candidate ZIPs must not be treated as accepted/current until adoption evidence confirms alignment.

## Current blockers

- v0.1.74.3 requires full release-control install/test evidence before it can become accepted/current.

## Current unknowns

- Whether local ChatGPT/backend rate limits will affect the live browser portion of the v0.1.74 release-control run.
- Whether the added release-validation groups materially increase operator runtime beyond acceptable bounds.

## Next safe action

```text
Package chatgpt_claudecode_workflow-2_v0.1.74.3.zip as a repair of v0.1.74.2, run focused validation and release-control, then adopt only after pb artifact current --json confirms alignment.
```

## Last updated

```text
v0.1.74.3 repair candidate
```
