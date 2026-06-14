# Project Status

## Current baseline

```text
accepted/current baseline with adoption evidence: chatgpt_claudecode_workflow-2_v0.1.76.zip
accepted checksum: 27030674c5af1b1d9d5199e638b55c2d3beed4b7df36175082e107992721d96f
active repair target: chatgpt_claudecode_workflow-2_v0.1.77.2.zip
next normal target after accepted repair: chatgpt_claudecode_workflow-2_v0.1.78.zip
release line: v0.1.x JSON orchestration / Promptbranch workflow control-plane hardening
```

## Current MVP state

```text
MVP status: active, not complete
DoD status: DOD-001..DOD-034 done where evidence is listed; adoption-related rows remain release-specific until adoption evidence exists
active plan slice: v0.1.77.2 repair — temporary project cleanup retry and release-validation isolation
last completed slice: v0.1.76 accepted/current KISS repo-loop consumer cleanup for operator/release scripts and release-state checks
next planned slice: install/test v0.1.77.2, then adopt only after release-control and pb artifact current evidence are green
```

## Current release state

```text
latest created ZIP: chatgpt_claudecode_workflow-2_v0.1.77.2.zip candidate once packaged
latest installed ZIP: chatgpt_claudecode_workflow-2_v0.1.77.zip failed live browser validation
latest accepted/current ZIP: chatgpt_claudecode_workflow-2_v0.1.76.zip
release status: v0.1.77 repair_required; v0.1.77.1 repair_required; v0.1.77.2 candidate once packaged; not accepted/current
```

## Current risks

- Temporary ChatGPT projects can leak if cleanup reports sidebar-not-found without proving the project is absent.
- ChatGPT create-project dialog can keep the submit button disabled after the name appears filled; this must fail clearly or recover by refilling/rechecking.
- Candidate ZIPs must not be treated as accepted/current until adoption evidence confirms alignment.

## Current blockers

- v0.1.77 failed full release-control live browser validation.
- v0.1.77.1 failed release-control due cleanup still present/unverified and release-validation group timeout.
- v0.1.77.2 repair requires full release-control install/test evidence before it can become accepted/current.

## Current unknowns

- Whether the create-project disabled-submit issue appears only under pressure or after stale modal/sidebar state.
- Whether existing leaked `itest-*` projects need manual cleanup outside this release flow.

## Next safe action

```text
Package and run release-control for chatgpt_claudecode_workflow-2_v0.1.77.2.zip. Adopt only after pb artifact current --all --json confirms alignment.
```

## Last updated

```text
v0.1.77.2 repair candidate
```
