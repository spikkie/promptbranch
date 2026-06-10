# Project Status

## Current baseline

```text
accepted/current baseline with adoption evidence: chatgpt_claudecode_workflow-2_v0.1.70.zip
accepted checksum: 99836251f6b07798d2e4c1e8bf978f001dccb0cced6fb64446dd7f098fe620e9
next repair target: chatgpt_claudecode_workflow-2_v0.1.70.1.zip
next normal target after accepted repair: chatgpt_claudecode_workflow-2_v0.1.71.zip
```

## Current MVP state

```text
MVP status: active, not complete
DoD status: project-control-surface rows done; source-add diagnostics done; browser-idle barrier done; multi-repo artifact current-state done/adopted; missing-repo fallback repair done in candidate after focused validation
active plan slice: v0.1.70.1 repair — missing repo artifact-current fallback
last completed slice with adoption evidence: v0.1.70 Multi-repo artifact registry state
next planned normal slice: choose after v0.1.70.1 validation/adoption evidence
```

## Current release state

```text
latest created ZIP: chatgpt_claudecode_workflow-2_v0.1.70.1.zip candidate after this repair is packaged
latest installed ZIP: unknown until operator lifecycle evidence
latest accepted/current ZIP: chatgpt_claudecode_workflow-2_v0.1.70.zip
release status: v0.1.70.1 repair candidate, not accepted/current
```

## Current risks

- v0.1.70 correctly supports multi-repo `--all`, valid `--repo`, and ambiguous unscoped-current behavior, but an explicit missing/typo repo lookup could leak another repo artifact state before this repair.
- The current multi-repo project model is coordinator-registry convention, not a first-class `.promptbranch-repos.json` declaration.
- Running from another repo directory uses that repo's local `.pb_profile` unless a shared/coordinator profile is explicitly selected.

## Current blockers

- None for the v0.1.70.1 repair candidate build.

## Current unknowns

- Whether a future slice should add first-class project/repo declaration commands such as `pb repo list --json` and `pb repo doctor --json`.
- Whether all operator workflows will consistently run cross-repo checks from the chosen coordinator registry or pass an explicit shared profile.

## Next safe action

```text
Install/test chatgpt_claudecode_workflow-2_v0.1.70.1.zip as a repair candidate. Verify `pb artifact current --repo does-not-exist --json` returns repo_current_not_found with state=null and registry_current=null. Also verify valid repo lookups and `pb artifact current --all --json` still work from the coordinator registry.
```

## Last updated

```text
v0.1.70.1 repair candidate
```
