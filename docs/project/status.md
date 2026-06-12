# Project Status

## Current baseline

```text
accepted/current baseline with adoption evidence: chatgpt_claudecode_workflow-2_v0.1.73.1.zip
accepted checksum: 3a032f2470a74903f6f61f9dbdf63dbf98e3154e2fd146e6ea9a757cf7941554
failed/superseded repair candidate: chatgpt_claudecode_workflow-2_v0.1.73.2.zip
next repair target: chatgpt_claudecode_workflow-2_v0.1.73.3.zip
next normal target after accepted repair: chatgpt_claudecode_workflow-2_v0.1.74.zip
```

## Current MVP state

```text
MVP status: active, not complete
DoD status: DOD-001..DOD-023 done where evidence is listed; DOD-024 from v0.1.73.2 is superseded by DOD-025; adoption-specific rows remain release-specific
active plan slice: v0.1.73.3 repair — Universal browser-operation scheduler coverage for source/project lifecycle paths
last accepted/current repair: v0.1.73.1
failed repair candidate: v0.1.73.2 release-control failed with browser_profile_busy during source/project cleanup
next planned slice: build/install/test v0.1.73.3, then adopt only after release-control and pb artifact current evidence are green
```

## Current release state

```text
latest created ZIP: chatgpt_claudecode_workflow-2_v0.1.73.3.zip candidate once packaged
latest installed ZIP: chatgpt_claudecode_workflow-2_v0.1.73.2.zip failed release-control in provided log
latest accepted/current ZIP: chatgpt_claudecode_workflow-2_v0.1.73.1.zip
release status: v0.1.73.3 repair planned/candidate; not accepted/current
```

## Current risks

- Browser-backed source/project lifecycle operations must use one scheduler/lease path, otherwise full release-control can race list/add/remove/cleanup against the same profile.
- v0.1.73.2 repaired JSON/reporting regressions but failed live release-control; v0.1.73.3 must supersede it without advancing normal scope.
- Increasing a timeout alone is not sufficient; the advertised scheduler model and actual lock wait defaults must align.
- Full release-control evidence is required before adoption.

## Current blockers

- v0.1.73.3 requires local release-control install/test evidence before it can become accepted/current.

## Current unknowns

- Whether release-control will still encounter external ChatGPT/backend rate limits after the scheduler coverage repair.
- Whether all live browser paths in full-test mode are now scheduler-mediated through the service path.

## Next safe action

```text
Package chatgpt_claudecode_workflow-2_v0.1.73.3.zip from accepted/current v0.1.73.1, run focused scheduler/JSON-contract tests, then run full release-control. Do not mark accepted/current until pb artifact current --json confirms alignment.
```

## Last updated

```text
v0.1.73.3 repair candidate
```
