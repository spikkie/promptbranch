# v0.1.128.2.4 — Accepted-baseline exact-byte self-healing repair

Baseline: `v0.1.128.1.1.1.1.1` / `dd9ed8949990b1b143e7930a2357adbebaccb935744a5bc30342942dbccdcdbd`.

Live startup of `v0.1.128.2.3` proved the project-scoped registry authority path but then failed with `accepted_baseline_artifact_invalid`. The remaining defect was physical-location brittleness: recovery treated the registry record `path` as the only possible copy of already-authoritative accepted bytes.

This repair separates logical authority from byte location. The adopted/current record must still prove exact repo, version and SHA. PB then verifies accepted bytes using transport integrity + exact SHA + embedded VERSION, searches only bounded canonical/PB-owned/local cache locations for the exact canonical filename, rejects every non-matching SHA, restores the SHA-addressed canonical object when an exact copy is found, and continues the same lifecycle command. If no exact accepted bytes exist, recovery fails closed. Current candidate hygiene policy is not re-applied retroactively to an already accepted immutable baseline.

The v0.1.128.2 learning/onboarding solution, automatic smoke-timeout recovery, accepted-runtime reconstruction, and project-scoped registry authority remain unchanged.
