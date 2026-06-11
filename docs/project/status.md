# Project Status

## Current baseline

```text
pinned development baseline: chatgpt_claudecode_workflow-2_v0.1.73.zip
accepted/current baseline with adoption evidence: chatgpt_claudecode_workflow-2_v0.1.72.zip
accepted checksum for v0.1.72: de4dfec45d53bc1d05f129e2796e51b86468b00e911e8e9e9566d166b4f6acc1
next repair target: chatgpt_claudecode_workflow-2_v0.1.73.1.zip
```

## Current MVP state

```text
MVP status: active, not complete
DoD status: DOD-001..DOD-023 done where evidence is listed; adoption-specific rows remain dependent on operator evidence per release
active plan slice: v0.1.73.1 repair — Canonical artifact adoption diagnostics and external-repo status semantics
last completed normal slice with adoption evidence: v0.1.72 — Project registry adoption/import ergonomics
latest field-proven normal candidate: v0.1.73 — Canonical artifact naming and adopt compatibility
next planned slice: install/test/adopt v0.1.73.1, then continue normal development from the latest adopted v0.1.73 repair
```

## Current release state

```text
latest created ZIP: chatgpt_claudecode_workflow-2_v0.1.73.1.zip candidate once packaged
latest installed ZIP: unknown until operator lifecycle evidence
latest accepted/current ZIP: chatgpt_claudecode_workflow-2_v0.1.72.zip based on provided adoption evidence
release status: v0.1.73.1 repair candidate, not accepted/current
```

## Current risks

- v0.1.73.1 intentionally repairs v0.1.73 reporting/diagnostic semantics without advancing normal slice scope.
- External repo baselines intentionally differ from the Promptbranch runtime version; payloads must distinguish this from a runtime/source mismatch.
- `.promptbranch-repo.json` is allowed in ZIPs only as portable identity metadata and must not carry local state or secrets.
- Full test suite has not been run for this repair candidate by the assistant.

## Current blockers

- v0.1.73.1 requires local release-control install/test/adoption evidence before it can become accepted/current.

## Current unknowns

- Whether the operator will accept v0.1.73 first or adopt v0.1.73.1 directly as the repair candidate.
- Whether `candlecast-src_v0.19.5.92.2.zip` remains the intended baseline or will later be replaced by `v0.19.5.94.1`.

## Next safe action

```text
Package chatgpt_claudecode_workflow-2_v0.1.73.1.zip and run focused release-control validation. Do not mark it accepted/current until pb artifact current --json confirms runtime, state artifact, state source, registry current, and consistency alignment.
```

## Last updated

```text
v0.1.73.1 repair candidate
```
