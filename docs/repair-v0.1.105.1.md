# Repair v0.1.105.1

## Target-anchored promotion-readiness repository resolution

`v0.1.105` proved the readiness evidence model from the repository root, but its standalone command bound repository authority to `Path.cwd()`. An absolute target invoked from another repository therefore searched that unrelated repository for the sandbox fixture and returned completed `not_ready` evidence instead of blocking repository-resolution failure.

`v0.1.105.1` changes only repository resolution:

- add optional `--repo-root`;
- otherwise derive one repository root from the resolved target path using authoritative Promptbranch markers;
- require the target to be contained in that root;
- block before evidence execution when root resolution is missing, ambiguous, marker-invalid, or non-containing;
- resolve fixtures, allowed paths, and validation commands relative to the resolved root.

The readiness evidence schema, sandbox mutation/rollback implementation, authority restrictions, fresh direct/localhost policy, and ten release gates remain unchanged.
