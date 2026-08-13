# v0.1.128.2.6 — External-repository skill sync installation repair

## Purpose

Make introducing or updating Promptbranch skills in an external application repository a first-class deterministic Promptbranch operation.

## Canonical command

```sh
pb skill sync \
  --path "$HOME/git/chatgpt_claudecode_workflow-2" \
  --target "$HOME/git/my_vault" \
  promptbranch-learning \
  promptbranch-operator \
  promptbranch-tool-authoring \
  --json
```

Skill names are optional; omitting them selects all three portable PB skills.

## Authority and safety contract

- `--path` identifies the Promptbranch control-plane repository only so its tracked `.promptbranch-repo.json` can resolve Project/repository authority.
- Skill content comes exclusively from the exact project-scoped `adopted/current` artifact and registered SHA-256, never from the mutable source worktree.
- Each portable bundle is exported from that exact artifact and verified before target mutation.
- The target must be a Git repository root.
- Existing unmanaged same-name skill directories fail closed unless `--force` is explicit.
- Existing managed skill trees are digest-bound by `.promptbranch/promptbranch-skills.json`; local drift fails closed unless `--force` is explicit.
- Target updates are staged on the same filesystem, directory replacements are atomic, and any post-install validation failure rolls the requested skills and provenance back.
- `--dry-run` resolves authority and proves bundles without mutating the target.
- The command validates each installed skill and reports target Git status. It never commits or pushes the target repository.

## Preserved behavior

All v0.1.128.2 learning/operator/tool-authoring contracts and v0.1.128.2.1–.5 lifecycle resilience remain unchanged. `v0.1.129 — External application pilot bootstrap` remains the next normal slice.
