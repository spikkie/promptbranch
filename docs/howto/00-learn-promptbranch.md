# Learn Promptbranch

This is the canonical human entry point for learning Promptbranch.

Promptbranch now ships a portable, verified learning system rather than requiring a newcomer to reconstruct PB from release notes and scattered how-to documents.

## Canonical order

1. Validate the tracked curriculum:

   ```sh
   pb skill learning-validate --path . --json
   pb skill operator-validate --path . --json
   ```

2. Read `.promptbranch/skills/promptbranch-learning/SKILL.md`.
3. Follow its `PROMPTBRANCH_OVERVIEW`, `AUTHORITY_MODEL`, `LEARNING_PATH`, `QUICKSTART`, operator/developer guides, exercises and glossary.
4. Use `.promptbranch/skills/promptbranch-operator/SKILL.md` when moving from learning to operator reasoning.
5. Use `.promptbranch/skills/promptbranch-tool-authoring/SKILL.md` when learning to design deterministic PB tools.

## Portable bootstrap

A complete learning bundle can be exported for a human, ChatGPT Project, Claude/coding agent or another PB-aware agent:

```sh
pb skill export promptbranch-learning --path . --output /tmp/promptbranch-learning.zip --json
pb skill verify-bundle /tmp/promptbranch-learning.zip --json
```

The bundle contains audience-specific entry points while preserving one canonical PB contract:

- `LEARNING_PATH.md` — human learning path;
- `PROJECT_SOURCE.md` — self-contained ChatGPT Project Source;
- `AGENTS.md` — generic coding-agent bootstrap;
- `CLAUDE.md` — Claude-oriented bootstrap;
- `SKILL.md` + `manifest.json` — PB-aware agent bootstrap;
- embedded related PB skills — operator, repo inspection, final-MVP inspection, application-architecture proof and tool authoring.

The bundle is deterministic and digest-bound. Verification rejects missing/extra/tampered content and authority escalation.

## Important boundary

Learning does not grant execution authority. A valid skill, a valid learning bundle, or a correct explanation of PB does not authorize repository/browser/Project Source mutation, publication, acceptance, adoption, deployment, Git commit or Git push.
