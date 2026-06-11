# Project Status

## Current baseline

```text
accepted/current baseline with adoption evidence: chatgpt_claudecode_workflow-2_v0.1.72.zip
accepted checksum: de4dfec45d53bc1d05f129e2796e51b86468b00e911e8e9e9566d166b4f6acc1
next normal target: chatgpt_claudecode_workflow-2_v0.1.73.zip
```

## Current MVP state

```text
MVP status: active, not complete
DoD status: DOD-001..DOD-022 done where evidence is listed; adoption-specific rows remain dependent on operator evidence per release
active plan slice: v0.1.73 normal — Canonical artifact naming and adopt compatibility
last completed normal slice with adoption evidence: v0.1.72 — Project registry adoption/import ergonomics
next planned slice: install/test/adopt v0.1.73, then re-check multi-repo current artifacts for candlecast project
```

## Current release state

```text
latest created ZIP: chatgpt_claudecode_workflow-2_v0.1.73.zip candidate
latest installed ZIP: unknown until operator lifecycle evidence
latest accepted/current ZIP: chatgpt_claudecode_workflow-2_v0.1.72.zip
release status: v0.1.73 candidate, not accepted/current
```

## Current risks

- v0.1.73 changes adoption semantics by adding explicit `--local-only`; this must remain opt-in and fail closed when mixed with `--from-project-source`.
- Non-canonical historical artifacts must be copied or renamed to canonical filenames before adoption.
- Full test suite has not been run for this candidate by the assistant.

## Current blockers

- v0.1.73 requires local release-control install/test/adoption evidence before it can become accepted/current.

## Current unknowns

- Whether all external repos already expose a `VERSION` file matching the target canonical artifact version after normalization.
- Whether future release-set orchestration should depend on only adopted current records or also version compatibility manifests.

## Next safe action

```text
Install/test chatgpt_claudecode_workflow-2_v0.1.73.zip with release-control. Then copy legacy repo ZIP filenames to canonical names and run pb artifact adopt --local-only --repo ... for architecture-process, ib_forex_trading, and candlecast-src.
```

## Last updated

```text
v0.1.73 candidate
```
