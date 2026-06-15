# Project Status

## Current baseline

```text
accepted/current baseline with adoption evidence: chatgpt_claudecode_workflow-2_v0.1.76.zip
accepted checksum: 27030674c5af1b1d9d5199e638b55c2d3beed4b7df36175082e107992721d96f
next normal target: v0.1.78 after v0.1.77 repair line is accepted/current
active repair target: chatgpt_claudecode_workflow-2_v0.1.77.11.zip
```

## Current MVP state

```text
MVP status: active
DoD status: in_progress
active plan slice: v0.1.77.11 repair — name-only non-anchor project cleanup fallback
last completed slice: v0.1.76 KISS repo-loop consumer cleanup accepted/current
next planned slice: install/test v0.1.77.11, then adopt only after release-control and pb artifact current evidence are green
```

## Current release state

```text
latest created ZIP: chatgpt_claudecode_workflow-2_v0.1.77.11.zip candidate once packaged
latest installed ZIP: v0.1.77.7 installed/tested_failed
latest accepted/current ZIP: chatgpt_claudecode_workflow-2_v0.1.76.zip
release status: v0.1.77 repair line in progress; v0.1.77.11 candidate once packaged; not accepted/current
```

## Current risks

- Full release-control and live browser validation still required for v0.1.77.11.
- Already leaked temporary `itest-*` projects may need cleanup if ChatGPT project-menu automation cannot remove them.

## Current blockers

- v0.1.77.11 must pass release-control.
- v0.1.77.11 must not be adopted/current without `pb artifact current --all --json` alignment evidence.

## Current unknowns

- Whether ChatGPT now exposes the temporary project row through a non-anchor sidebar/menu candidate that cleanup can remove.

## Next safe action

```text
Run release-control for chatgpt_claudecode_workflow-2_v0.1.77.11.zip. Adopt only after pb artifact current --all --json confirms alignment.
```

## Last updated

```text
v0.1.77.11 repair candidate
```
## Current repair note — v0.1.77.9

```text
v0.1.77.8 full release-control failed before adoption because text Project Source add treated stale inflight after commit as a hard timeout before post-refresh persistence verification, and cleanup still lacked a project-name fallback through the removal request stack. v0.1.77.9 repairs only those validation defects and remains candidate until full release-control and adoption evidence pass.
```


## Repair status — v0.1.77.10

```text
v0.1.77.9 release-control failed before full browser tests because Docker service recreation kept reporting stale service version `0.1.77.8` while `v0.1.77.9` was expected. v0.1.77.10 pins the Compose service image to the release-derived image reference unless `PROMPTBRANCH_ALLOW_SERVICE_IMAGE_OVERRIDE=1` is explicitly set. v0.1.77.10 remains candidate until full release-control and adoption evidence pass.
```


## Repair status — v0.1.77.11

```text
v0.1.77.10 release-control failed at project_remove_cleanup: the exact temporary project was still resolvable by name, but the browser removal path could not find it in the sidebar. v0.1.77.11 widens the cleanup DOM lookup to name-matched non-anchor sidebar/menu project rows while preserving fail-closed cleanup semantics. v0.1.77.11 remains candidate until full release-control and adoption evidence pass.
```
