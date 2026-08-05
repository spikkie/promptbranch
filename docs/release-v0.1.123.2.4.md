# v0.1.123.2.4 — Baseline-derived ZIP creation and real attachment enforcement

`v0.1.123.2.4` is a repair-only release from accepted/current `v0.1.123.2.3`. Formal MVP proof remains `0/2`; `v0.1.124` and `v0.1.125` remain normal proof cycles 1 and 2.

## Defect

The `ask-release` protocol envelope described the expected candidate ZIP, but the generated user prompt did not force artifact execution before envelope generation. ChatGPT could therefore emit a successful JSON envelope containing a textual `sandbox:/mnt/data/...` path without a rendered attachment. Promptbranch correctly rejected that result as `artifact_declared_but_not_attached`.

## Repair

- Name the exact accepted/current ZIP and version as the actual source baseline.
- Require extraction or inspection of that exact baseline.
- Require a brand-new target ZIP for the exact request ID; earlier or failed-answer artifacts cannot be reused or renamed.
- Require physical ZIP creation before the Promptbranch reply envelope is written.
- Require the ZIP to be attached to the exact assistant answer as a real downloadable ChatGPT attachment.
- State that a filename in JSON, a textual sandbox path, or a claim that a file exists is insufficient.
- Permit `status=completed` only after the exact attachment is materialized.
- Require observed SHA-256, byte size, and ZIP entry count from the created file.
- Require `status=failed`, `result_type=release_candidate`, and `artifacts=[]` when physical creation or attachment fails.

## Scope

No timeout behavior, reply parsing, artifact validation, adoption, Project Source mutation, Git commit, or Git push semantics are changed. This repair cannot count toward the two consecutive normal MVP proof cycles.
