# Repair v0.1.103.10.82

## Goal

Restore the existing `pbsa <file>` same-name overwrite contract without changing the command surface.

## Behavior

- `pbsa <file>` still delegates to `promptbranch src add <file>`.
- Project Sources are read only after an authoritative stable preflight.
- Existing exact canonical and numeric-suffix family source associations are removed by exact identity.
- ChatGPT Library records are reconciled only by exact backing file ID.
- Exact attributable records are deleted from Library and then permanently removed from Recently deleted.
- Files referenced by another project, files without an exact ID, or files lacking Promptbranch provenance fail closed as `library_collision_ambiguous`.
- A canonical upload succeeds only when exactly one canonical source exists and no numeric suffix source exists.
- A newly backend-renamed source is removed, its exact backing Library file is reconciled, and the operation returns `library_collision_not_cleared` rather than success.

## Acceptance command

```bash
cd /home/spikkie/git/platform-gitops
pbsa platform-gitops_v0.0.6.6.zip
```

Required result:

```text
ok=true
persistence_verified=true
backend_assigned_name=platform-gitops_v0.0.6.6.zip
exact_canonical_source_count=1
duplicate_suffix_source_count=0
```

The candidate remains unadopted until the strict all-all gate reaches `GO` and the unchanged legacy command above succeeds against the polluted Kubernetes project.
