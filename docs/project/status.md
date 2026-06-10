# Project Status

## Current baseline

```text
accepted/current baseline with adoption evidence: chatgpt_claudecode_workflow-2_v0.1.69.zip
accepted checksum: 2132bec14263f3418cec5707211bd0931dd4d9928c7e8ae50bcb3e9fc3997b56
next normal target: chatgpt_claudecode_workflow-2_v0.1.70.zip
```

## Current MVP state

```text
MVP status: active, not complete
DoD status: project-control-surface rows done; source-add diagnostics done; browser-idle barrier done; multi-repo artifact current-state row pending candidate validation/adoption
active plan slice: Multi-repo artifact registry state
last completed slice with adoption evidence: v0.1.69 Browser-profile busy retry and source-add idle barrier
next planned slice: choose after v0.1.70 validation/adoption evidence
```

## Current release state

```text
latest created ZIP: chatgpt_claudecode_workflow-2_v0.1.70.zip candidate after this slice is packaged
latest installed ZIP: unknown until operator lifecycle evidence
latest accepted/current ZIP: chatgpt_claudecode_workflow-2_v0.1.69.zip
release status: v0.1.70 candidate, not accepted/current
```

## Current risks

- A ChatGPT Project can contain multiple repo ZIPs; a single global artifact current pointer can silently point future work at the wrong repository baseline.
- Local artifact state historically stored one artifact/source pair per project, so adopting a second repo ZIP could overwrite the visible baseline for the first repo.
- Some existing lifecycle commands still call unscoped `pb artifact current --json`; v0.1.70 must preserve single-repo compatibility while failing closed when multiple repo scopes exist.

## Current blockers

- None for the v0.1.70 candidate build.

## Current unknowns

- Whether every downstream repo-local lifecycle script will immediately pass `--repo`; the candidate provides `--all` and ambiguous-scope guidance to make this migration observable.
- Whether release-set dependency orchestration should become a later slice; it is intentionally out of scope for v0.1.70.

## Next safe action

```text
Install/test chatgpt_claudecode_workflow-2_v0.1.70.zip as a candidate. Operator should verify `pb artifact current --repo <repo> --json`, `pb artifact current --all --json`, and unscoped ambiguous-scope behavior before adoption, then provide `pb artifact current --repo chatgpt_claudecode_workflow-2 --json` or equivalent adoption evidence.
```

## Last updated

```text
v0.1.70 candidate
```
