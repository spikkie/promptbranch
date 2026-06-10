# Promptbranch Living Design Overview HTML

Release: `v0.1.66`

This page publishes the standalone HTML overview for the editable Promptbranch living-design source:

- HTML overview: [docs/design/promptbranch-living-design-overview.html](promptbranch-living-design-overview.html)
- Editable draw.io source: [docs/design/promptbranch-mvp-living-design.drawio](promptbranch-mvp-living-design.drawio)
- Living design Markdown: [docs/design/promptbranch-mvp-living-design.md](promptbranch-mvp-living-design.md)

The HTML overview explains Promptbranch (`pb`) as the deterministic control plane around ChatGPT Projects. It documents the PB authority model: ChatGPT proposes, reasons, and produces conversation output; Promptbranch validates, records state, verifies artifacts, and controls release/adoption evidence.

Keep this HTML page, the editable draw.io source, and the living design Markdown aligned after design-documentation slices.


## v0.1.62 site navigation

This overview is now linked from `docs/index.md`, `docs/design/index.md`, and `mkdocs.yml`. The HTML remains a source-controlled documentation artifact; generated MkDocs `site/` output must stay outside the release ZIP.


## v0.1.63 link-integrity guard

This bridge page is now included in docs-site link-integrity validation. Its links to the HTML overview, editable draw.io source, and living-design Markdown must remain repo-local and present.


## v0.1.64 build-readiness guard

The living-design overview remains source-controlled documentation. It is linked from `mkdocs.yml`, `docs/index.md`, and `docs/site.md`; generated `site/` output remains forbidden from release ZIPs.


## v0.1.65 release config guard

Release `v0.1.65` validates `.promptbranch-release.yml` as a source-only lifecycle policy. `pb release config --json` is a read-only guard and does not execute hooks or mutate Promptbranch state.


## v0.1.66 release doctor candidate precheck

Release `v0.1.66` makes `pb release doctor --artifact ZIP --version VERSION --json` consume `.promptbranch-release.yml` for read-only candidate ZIP prechecks. It reports `release_config` and `candidate_artifact` evidence for filename/config matching, VERSION consistency, ZIP layout, hygiene, and accepted-baseline continuity without installing, uploading, adopting, committing, or pushing.
