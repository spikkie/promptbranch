# Release v0.1.104.3

Repair candidate for current-turn-scoped interrupted-state readiness.

## Preserved

- Accepted/current baseline `v0.1.103.10.116`.
- Complete 13-gate sandbox mutation, validation, rollback, repository immutability, and workspace deletion proof.
- Ten-step strict release manifest.
- Fresh `full_direct` and independent `full_localhost` evidence.
- One bounded same-conversation post-bootstrap reload.
- Existing Project Source, Artifact Guardian, adoption, and assigned-source verification behavior.

## Changed

- Historical Retry controls no longer block an otherwise idle composer.
- Pre-bootstrap readiness is separate from post-bootstrap recovery.
- Post-bootstrap recovery requires a completed exact bootstrap sentinel.
- Reload recovery waits boundedly for conversation hydration before sentinel and readiness verification.
- Wrong or incomplete bootstrap results stop before ask submission.

## Standalone first check

```bash
python3 scripts/verify-sandbox-mutation-rollback-release-gate.py --repo .
```
