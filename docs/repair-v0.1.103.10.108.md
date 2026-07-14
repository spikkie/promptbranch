# Repair v0.1.103.10.108 — singleton Project Source family replacement

## Problem

`v0.1.103.10.107` correctly uploaded and verified the next backend-assigned indexed source, but returned success while the previous family member remained visible. A second add therefore produced both `platform-gitops_v0.0.6.6(16).zip` and `platform-gitops_v0.0.6.6(17).zip`.

## Repair

- Keep the single escaped canonical/indexed filename-family matcher.
- Upload exactly once and verify the processing-stream assigned source first.
- Treat every other visible family member as an older replacement target.
- Remove older members one by one using exact Project Source identity.
- Refresh the authoritative Project Sources surface after cleanup.
- Return success only when exactly one family member remains and it is the newly assigned source.
- Return `source_replaced` plus removal and final-family diagnostics on success.
- Fail closed when cleanup fails, the assigned source is duplicated, or residual family members remain.
- With `--no-overwrite`, refuse an existing indexed family instead of creating a second family member.

## Transaction order

```text
observe old family
→ upload once
→ verify exact assigned source
→ remove all non-assigned family members
→ verify authoritative singleton family
→ success
```

The new source is never removed before it has been proven. If cleanup fails, the operation reports a release-blocking failure instead of silently claiming success.

## Preserved boundaries

- Accepted/current remains `v0.1.103.10.68`.
- `v0.1.103.10.105` clean-break registry semantics remain unchanged.
- `v0.1.103.10.107` assigned-name fast verification remains unchanged.
- No live `pb src add`, canonical release `pbsa`, adoption, Project deletion, commit, or push is performed while building this candidate.
