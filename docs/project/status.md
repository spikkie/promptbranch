# Project Status

## Current baseline

```text
accepted/current baseline: chatgpt_claudecode_workflow-2_v0.1.66.zip
accepted checksum: 2b05556677346aa2f9e1d7449bb1c70fc0c54b8d7cd130f22b6e7083960ec8a3
next normal target: chatgpt_claudecode_workflow-2_v0.1.67.zip
```

## Current MVP state

```text
MVP status: active, not complete
DoD status: project-control-surface rows in progress for v0.1.67; adoption rows remain open
active plan slice: Project MVP / DoD / Plan control surface migration
last completed slice: v0.1.66 release doctor config-aware candidate ZIP precheck
next planned slice: choose after v0.1.67 adoption evidence
```

## Current release state

```text
latest created ZIP: chatgpt_claudecode_workflow-2_v0.1.67.zip candidate after this slice is packaged
latest installed ZIP: unknown until operator lifecycle evidence
latest accepted/current ZIP: chatgpt_claudecode_workflow-2_v0.1.66.zip
release status: v0.1.67 candidate, not accepted/current
```

## Current risks

- Existing MVP, plan, and status information is scattered across older root-level, `docs/`, and `docs/design/orchestration/` documents.
- Older documents reference earlier artifact names and baselines; accepted v0.1.66 evidence is the current authority.
- Native release lifecycle work remains partially repo-local and partially Promptbranch-native; future slices must stay narrow.
- A candidate ZIP can be mistaken for accepted/current if adoption evidence is not required.

## Current blockers

- No blocker for the documentation-control-surface migration slice.
- Full test evidence for this slice is not available unless the operator runs the full suite.
- Adoption cannot be claimed until `pb artifact current --json` aligns on v0.1.67.

## Current unknowns

- Whether the operator's Git working tree is clean and pushed after v0.1.66 adoption.
- Whether all historical status files have exact one-to-one mappings; this migration records the initial mapping and leaves old docs in place.
- Which post-v0.1.67 implementation slice should be selected after adoption.

## Next safe action

```text
Install/test/adopt the v0.1.67 candidate only after focused validation and ZIP hygiene checks pass, then provide pb artifact current --json. Do not continue to v0.1.68 until v0.1.67 is accepted/current or explicitly rejected.
```

## Last updated

```text
v0.1.67 candidate
```
