# Promptbranch documentation site operation

Release: `v0.1.65`

This page defines the source-only documentation site policy for Promptbranch. The site is a Material for MkDocs source scaffold; rendered output is generated material and must not be committed or packaged into release ZIPs.

## Source-only policy

The authoritative documentation inputs are repository files such as `mkdocs.yml`, `docs/index.md`, `docs/design/index.md`, `docs/releases/index.md`, and the linked design/release documents. The generated `site/` directory is not source. It must stay outside Git, outside Project Sources, and outside release ZIP artifacts.

## Local preview

Use this command when Material for MkDocs is installed locally:

```bash
mkdocs serve
```

This is an operator convenience command. It is not required for normal release validation because the release guard must not depend on external documentation packages being installed.

## Local build

Use this command when a local static preview/export is needed:

```bash
mkdocs build
```

The build may create `site/`, but that output remains generated. Remove it before packaging or adoption.

## Release validation

The release-checkable guard is:

```bash
pb release docs-status --version v0.1.65 --json
```

The guard verifies that:

- `mkdocs.yml` exists and declares the intended Material for MkDocs theme.
- The documentation entrypoints are present.
- MkDocs navigation targets resolve to repo-local files.
- Markdown links from the documentation entrypoints resolve to repo-local files.
- The build-readiness policy documents `mkdocs serve`, `mkdocs build`, and the generated `site/` exclusion rule.
- `site/` output is not committed or packaged.

## Related documentation

- [Documentation home](index.md)
- [Design overview](design/index.md)
- [Release overview](releases/index.md)
- [v0.1.65 release note](release-v0.1.65.md)
- [v0.1.64 release note](release-v0.1.64.md)
- [Promptbranch living-design overview](design/promptbranch-living-design-overview.md)


## Release lifecycle config guard

The documentation site remains source-only, and release lifecycle policy is now also source-only and repo-local. Validate `.promptbranch-release.yml` with:

```bash
pb release config --json
```

This command must parse and validate configuration only. It must not run lifecycle hooks, install a candidate ZIP, upload Project Sources, adopt an artifact, update artifact/source state, commit, or push.
