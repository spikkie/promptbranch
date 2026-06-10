# Promptbranch design documentation

Release: `v0.1.66`

This index groups the PB design surfaces that should be read together when continuing the architecture, documentation, or release-control line.

## Documentation site operation

- [Documentation site operation](../site.md)

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


## v0.1.63 link-integrity rule

Every link from this index is part of the release-checkable documentation surface. If a referenced design file is renamed or removed, `pb release docs-status --json` must block the candidate until navigation is repaired.


## v0.1.64 build-readiness rule

The documentation site is now release-checkable for build readiness. `docs/site.md` must document `mkdocs serve`, `mkdocs build`, the source-only policy, and the rule that generated `site/` output must not be committed or packaged.


## v0.1.65 release lifecycle config rule

Release lifecycle policy now has a checked repo-root contract in `.promptbranch-release.yml`. The `pb release config --json` guard validates the config shape, repo-relative paths, safe hook template placeholders, and absence of embedded absolute local machine paths without executing hooks or mutating state.
