# v0.1.123.2 — Explicit conversation pinning for integrated MVP proof lifecycle

`v0.1.123.2` is a repair-only release from accepted/current `v0.1.123.1`.
It does not count toward the two required consecutive normal MVP proof cycles.

## Operator contract

A proof cycle now requires an explicit ChatGPT Project conversation URL:

```bash
pb ask continue \
  --conversation-url 'https://chatgpt.com/g/<project>/c/<conversation-id>' \
  --target-version v0.1.124 \
  --release-type normal
```

The explicit URL is authoritative for the release-candidate Ask, exact reply correlation,
artifact intake task selection, and post-adoption continuation Ask. Promptbranch does not
fall back to remembered task state, project home, the latest conversation, or the visible
browser tab.

## Fail-closed checks

The command exits nonzero before mutation when the URL is missing, is not a Project
conversation URL, belongs to a different release-authority project, or the candidate Ask
returns a different conversation. The finalizer also requires the continuation reply to
resolve to the same conversation ID.

## Scope

No platform capability is added beyond deterministic conversation selection for the
existing integrated proof lifecycle. After acceptance, `v0.1.124` remains proof cycle 1
and `v0.1.125` remains proof cycle 2.
