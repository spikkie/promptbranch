# Release v0.1.73

Type: normal candidate

## Slice

Canonical artifact naming and adopt compatibility.

## Baseline

```text
chatgpt_claudecode_workflow-2_v0.1.72.zip
```

## Goal

Define and enforce one Promptbranch artifact filename convention so multi-repo project baselines can be adopted predictably with `pb artifact adopt`.

## Canonical convention

```text
<repo_id>_<version>.zip
```

Where `version` is a `v`-prefixed dot-separated numeric token with at least three components.

Examples:

```text
architecture-process_v0.29.0.zip
ib_forex_trading_v0.248.3.1.zip
candlecast-src_v0.19.5.94.1.zip
```

## In scope

- Enforce canonical artifact names in `pb artifact adopt`.
- Normalize bare ZIP `VERSION` values against `v`-prefixed filename versions.
- Add explicit `--local-only` adoption mode for operator-seeded local baselines without Project Source verification.
- Keep `--from-project-source` for Project Source verified adoption.
- Add tests for canonical architecture-process, IB Forex, and Candlecast artifact names.
- Reject non-canonical legacy filenames with the expected canonical filename when inferable.
- Update multi-repo and artifact naming documentation.

## Out of scope

- Rewriting historical release ZIPs.
- Automatic Project Source upload.
- Release-set orchestration.
- Cross-repo dependency solving.
- Runtime, Docker, or deployment behavior changes.

## Validation

Focused validation was run before packaging. Full release-control lifecycle must still be run by the operator before adoption.
