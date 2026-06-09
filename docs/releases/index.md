# Promptbranch release documentation

Release: `v0.1.63`

This index provides a compact path into the current documentation-governance release line.

## Current documentation-governance releases

- [v0.1.63 — docs-site link-integrity / navigation validation guard](../release-v0.1.63.md)
- [v0.1.62 — documentation site scaffold / navigation guard](../release-v0.1.62.md)
- [v0.1.61 — living-design HTML overview integration](../release-v0.1.61.md)
- [v0.1.60 — release baseline evidence semantics](../release-v0.1.60.md)
- [v0.1.59 — PB application design docs-status guard](../release-v0.1.59.md)

## Release rules

Every normal release continues from the latest accepted Promptbranch baseline. Candidate ZIPs, transient sandbox ZIPs, installed ZIPs, locally accepted artifacts, Project Source baselines, and runtime package versions must remain distinguishable in the release evidence model.


## Link-integrity policy

Release documentation referenced from the MkDocs navigation or release index must resolve to repo-local Markdown files. Rendered `site/` output remains generated output and must not be committed.
