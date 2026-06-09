# Promptbranch design documentation

Release: `v0.1.62`

This index groups the PB design surfaces that should be read together when continuing the architecture, documentation, or release-control line.

## Human-facing overview

- [Promptbranch living-design overview](promptbranch-living-design-overview.md)
- [Promptbranch living-design HTML](promptbranch-living-design-overview.html)
- [Editable draw.io source](promptbranch-mvp-living-design.drawio)

## Design and authority model

- [Promptbranch application design](promptbranch-application-design.md)
- [Release baseline evidence](promptbranch-release-baseline-evidence.md)
- [MVP living design](promptbranch-mvp-living-design.md)
- [MVP gap analysis](promptbranch-mvp-gap-analysis.md)
- [Orchestration current status](orchestration/docs/current_status.md)

## Required invariants

- Promptbranch is the deterministic control plane.
- ChatGPT is the reasoning and execution surface.
- Workspace / Task / Artifact scopes stay separate.
- Reads are backend-first where possible.
- Writes are transactional and verified before state changes.
- Candidate, installed, and adopted artifacts remain distinct.
- Rendered documentation output belongs outside source control.
