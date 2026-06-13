# Project Status

## Current baseline

```text
accepted/current baseline with adoption evidence: chatgpt_claudecode_workflow-2_v0.1.74.3.zip
accepted checksum: operator-pinned baseline; checksum evidence not present in this package build context
next normal target: chatgpt_claudecode_workflow-2_v0.1.75.zip
release line: v0.1.x JSON orchestration / Promptbranch workflow control-plane hardening
```

## Current MVP state

```text
MVP status: active, not complete
DoD status: DOD-001..DOD-031 done where evidence is listed; DOD-011 remains release-specific/open until each candidate is adopted
active plan slice: v0.1.75 normal — KISS project/repo management command model rebased on v0.1.74.3
last completed slice: v0.1.74.3 accepted/current by operator baseline instruction
next planned slice: install/test v0.1.75, then adopt only after release-control and pb artifact current evidence are green
```

## Current release state

```text
latest created ZIP: chatgpt_claudecode_workflow-2_v0.1.75.zip candidate once packaged
latest installed ZIP: chatgpt_claudecode_workflow-2_v0.1.74.3.zip
latest accepted/current ZIP: chatgpt_claudecode_workflow-2_v0.1.74.3.zip
release status: v0.1.75 candidate rebased from v0.1.74.3; not accepted/current
```

## Current risks

- Single-repo and multi-repo command shapes can drift again if future code adds special-case single-repo paths.
- Existing scripts that consumed legacy single-repo `pb artifact current --json` in joined projects may need to handle the repo-loop payload shape.
- Candidate ZIPs must not be treated as accepted/current until adoption evidence confirms alignment.

## Current blockers

- v0.1.75 requires full release-control install/test evidence before it can become accepted/current.

## Current unknowns

- Whether local ChatGPT/backend rate limits will affect the live browser portion of the v0.1.75 release-control run.
- Whether any local operator scripts still assume legacy single-repo `artifact current` JSON for joined projects.

## Next safe action

```text
Run release-control for chatgpt_claudecode_workflow-2_v0.1.75.zip, then adopt only after pb artifact current --all --json confirms alignment.
```

## Last updated

```text
v0.1.75 candidate rebased on v0.1.74.3
```
