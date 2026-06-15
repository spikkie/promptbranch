# Project Status

## Current baseline

```text
accepted/current baseline with adoption evidence: chatgpt_claudecode_workflow-2_v0.1.76.zip
accepted checksum: 27030674c5af1b1d9d5199e638b55c2d3beed4b7df36175082e107992721d96f
next normal target: v0.1.78 after v0.1.77 repair line is accepted/current
active repair target: chatgpt_claudecode_workflow-2_v0.1.77.7.zip
```

## Current MVP state

```text
MVP status: active
DoD status: in_progress
active plan slice: v0.1.77.7 repair — explicit resolved-project-url cleanup retry
last completed slice: v0.1.76 KISS repo-loop consumer cleanup accepted/current
next planned slice: install/test v0.1.77.7, then adopt only after release-control and pb artifact current evidence are green
```

## Current release state

```text
latest created ZIP: chatgpt_claudecode_workflow-2_v0.1.77.7.zip candidate once packaged
latest installed ZIP: v0.1.77.6 installed/tested_failed
latest accepted/current ZIP: chatgpt_claudecode_workflow-2_v0.1.76.zip
release status: v0.1.77 repair line in progress; v0.1.77.7 candidate once packaged; not accepted/current
```

## Current risks

- Full release-control and live browser validation still required for v0.1.77.7.
- Already leaked temporary `itest-*` projects may need cleanup if ChatGPT project-menu automation cannot remove them.

## Current blockers

- v0.1.77.7 must pass release-control.
- v0.1.77.7 must not be adopted/current without `pb artifact current --all --json` alignment evidence.

## Current unknowns

- Whether explicitly passing the resolved project URL lets the cleanup removal path reach the correct temporary project in the next full run.

## Next safe action

```text
Run release-control for chatgpt_claudecode_workflow-2_v0.1.77.7.zip. Adopt only after pb artifact current --all --json confirms alignment.
```

## Last updated

```text
v0.1.77.7 repair candidate
```
