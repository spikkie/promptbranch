# v0.1.128.2.3 — Project-scoped baseline registry authority repair

Baseline: `v0.1.128.1.1.1.1.1` / `dd9ed8949990b1b143e7930a2357adbebaccb935744a5bc30342942dbccdcdbd`.

This repair corrects the release-start recovery authority path. `v0.1.128.2.2` reconstructed the accepted runtime from an adopted artifact but mistakenly looked for that artifact in the browser/session profile registry. `v0.1.128.2.3` resolves `.promptbranch-repo.json`, verifies the configured repo/project binding, and reads adopted/current only from the canonical project-scoped artifact registry.

The v0.1.128.2 learning/onboarding capability, v0.1.128.2.1 automatic smoke-timeout recovery, and v0.1.128.2.2 runtime reconstruction remain unchanged. No manual registry fix, runtime repair, pre-install, or timeout retry is part of the normal lifecycle.
