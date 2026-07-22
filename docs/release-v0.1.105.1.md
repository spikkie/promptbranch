# Release v0.1.105.1

`v0.1.105.1 — target-anchored promotion-readiness repository resolution`

This repair makes `pb loop promotion-readiness` location-independent for absolute targets. The command accepts optional `--repo-root`; without it, repository authority is derived from the target path using authoritative repository markers. Wrong or ambiguous roots fail closed as `blocked` before any evidence run.

The command still grants no repository, deployment, Kubernetes, Project Source, artifact-adoption, or Project-deletion authority. `v0.1.106` remains the earliest slice permitted to record a GO/NO-GO promotion decision.
