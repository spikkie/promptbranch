# v0.1.103.10.105 — fail-closed project registry clean break

## Scope

- Keep accepted/current at `v0.1.103.10.68`.
- Require `.promptbranch-repo.json` and configured project membership for all artifact-state reads and mutations.
- Use only `~/.local/state/promptbranch/projects/<project-id>/promptbranch_artifacts.json` as the artifact registry.
- Remove repo-local registry fallback and remove `pb project import-current-registry`.
- Classify missing, invalid, unreadable, unresolved, and valid-empty registry state explicitly.
- Ignore `--profile-dir` for artifact registry routing.
- Make `pb repo doctor` fail when configured repositories have missing/mismatched identities or stray repo-local artifact registries.
- Do not migrate, reconcile, infer, or automatically adopt legacy state.
- Do not run canonical release `pbsa` or adoption.

## Clean initialization

A repository joins the new dataset explicitly with `pb project join`. That command writes the repository identity, records configured membership, and initializes the project registry. Reads never create a registry implicitly.

## Validation intent

Prove fail-closed behavior for missing identity, missing/invalid/unreadable registry, missing membership, repo-root mismatch, explicit profile override attempts, and stray repo-local registries. Prove a deliberately initialized empty project registry remains a valid empty dataset.
