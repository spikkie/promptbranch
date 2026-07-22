# Promptbranch documentation

Release: `v0.1.105.1`

- [v0.1.105.1 release note](release-v0.1.105.1.md)
- [v0.1.105 release note](release-v0.1.105.md)
- [Promptbranch plan at v0.1.105](project/promptbranch-plan-v0.1.105.md)

This documentation entrypoint makes the Promptbranch (`pb`) architecture and release-control material discoverable from one place. It is intentionally a source scaffold for **Material for MkDocs** and does not commit rendered `site/` output.

## Start here

- [v0.1.104.4 repair note](repair-v0.1.104.4.md)
- [v0.1.104.4 release note](release-v0.1.104.4.md)

- [v0.1.104.2 repair note](repair-v0.1.104.2.md)
- [v0.1.104.2 release note](release-v0.1.104.2.md)

- [Promptbranch plan at v0.1.104](project/promptbranch-plan-v0.1.104.md)
- [v0.1.104.1 repair note](repair-v0.1.104.1.md)
- [v0.1.104.1 release note](release-v0.1.104.1.md)
- [v0.1.104 release note](release-v0.1.104.md)

- [Documentation site operation](site.md)
- [Design overview](design/index.md)
- [Promptbranch living-design overview](design/promptbranch-living-design-overview.md)
- [Promptbranch living-design HTML](design/promptbranch-living-design-overview.html)
- [Promptbranch application design](design/promptbranch-application-design.md)
- [Release baseline evidence](design/promptbranch-release-baseline-evidence.md)
- [MVP living design](design/promptbranch-mvp-living-design.md)
- [MVP gap analysis](design/promptbranch-mvp-gap-analysis.md)
- [Orchestration current status](design/orchestration/docs/current_status.md)
- [Release overview](releases/index.md)
- [v0.1.66 release note](release-v0.1.66.md)
- [v0.1.65 release note](release-v0.1.65.md)
- [v0.1.64 release note](release-v0.1.64.md)
- [v0.1.63 release note](release-v0.1.63.md)

## Authority model

Promptbranch is the deterministic control plane. ChatGPT is the reasoning and execution surface. The documentation site must preserve the Workspace / Task / Artifact scope model, backend-first reads, transactional writes, ask/reply protocol, artifact baseline semantics, MCP/agent layer, and release lifecycle documentation.

## Site-source rule

`mkdocs.yml` is a navigation scaffold. Rendered `site/` output is a generated artifact and must not be committed or packaged as source.

## Release-checkable repo-relative references

The docs-status guard intentionally checks these repo-relative source paths:

- `docs/site.md`
- `docs/design/promptbranch-living-design-overview.html`
- `docs/design/promptbranch-living-design-overview.md`
- `docs/design/promptbranch-application-design.md`
- `docs/design/promptbranch-release-baseline-evidence.md`
- `docs/design/promptbranch-mvp-living-design.md`
- `docs/design/promptbranch-mvp-gap-analysis.md`
- `docs/design/orchestration/docs/current_status.md`
- `docs/release-v0.1.66.md`
- `docs/release-v0.1.65.md`
- `docs/release-v0.1.64.md`
- `docs/release-v0.1.63.md`
- `docs/release-v0.1.62.md`


## v0.1.63 link-integrity guard

The docs-site guard now checks that `mkdocs.yml` navigation entries and Markdown links from the documentation index pages resolve to repo-local files. This prevents broken navigation from silently entering a release candidate.


## v0.1.64 build-readiness guard

The docs-site guard now verifies that the source tree documents local preview and build commands, keeps generated `site/` output forbidden from committed source, and reports `docs_site.build_readiness.ok=true` from `pb release docs-status --version v0.1.66 --json`.


## v0.1.65 release lifecycle config guard

The release-config guard now validates `.promptbranch-release.yml` as a repo-local, machine-readable lifecycle policy. `pb release config --json` is read-only: it parses artifact naming, preserved local paths, unsafe Git paths, and hook command templates without installing artifacts, uploading Project Sources, adopting baselines, committing, or pushing.


## v0.1.66 release doctor candidate precheck

The release doctor now has a config-aware candidate ZIP precheck. `pb release doctor --artifact ZIP --version VERSION --json` reports `release_config` and `candidate_artifact` sections without running lifecycle hooks or mutating artifact/source/Git state.

- [Bonnetjes Cloudflare one-shot validation](bonnetjes-cloudflare-one-shot-validation.md)
