# Repair v0.1.103.10.107 — exact assigned Project Source fast verification

## Problem

After a successful upload, ChatGPT can assign the next indexed Project Source filename, for example `(15)`, while Promptbranch continues polling for the canonical unsuffixed filename. That unnecessary canonical retry loop can add roughly three minutes after the processing stream has already supplied exact file, libfile, and assigned-name identity.

## Repair

- Use one escaped canonical/indexed-family regex everywhere.
- Capture all pre-upload family members and the highest numeric suffix.
- Treat the prior highest suffix as diagnostic evidence, not as a reuse target.
- Upload exactly once.
- Read `assigned_filename` from terminal processing-stream identity.
- Verify exactly that assigned Project Source card immediately.
- Skip generic canonical-name persistence retries once assigned identity is known.
- Return previous maximum, expected next, assigned index, delta, and expected-next classification.
- Fail closed when the assigned name is outside the requested family or when the exact assigned card is duplicated.

## Preserved boundaries

- Accepted/current remains `v0.1.103.10.68`.
- `v0.1.103.10.105` clean-break registry semantics remain unchanged.
- Artifact adoption behavior from `v0.1.103.10.106` remains unchanged.
- No live `pb src add`, canonical release `pbsa`, adoption, Project deletion, commit, or push is performed while building this candidate.
