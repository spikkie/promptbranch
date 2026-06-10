# Decisions

| ID | Date | Decision | Reason | Consequence |
|---|---|---|---|---|
| ADR-PROJ-001 | 2026-06-10 | Adopt `docs/project/` as the canonical continuation control surface | MVP, DoD, plan, status, release state, decisions, and migration evidence were scattered across multiple historical documents | Future slices and ZIP responses must refer to `docs/project/` |
| ADR-PROJ-002 | 2026-06-10 | Treat accepted `pb artifact current --json` evidence as baseline authority | Older documents contain stale baseline references from prior lines | Current accepted baseline is v0.1.66 until v0.1.67 adoption evidence exists |
| ADR-PROJ-003 | 2026-06-10 | Preserve historical planning/status documents during migration | Old documents contain durable decisions, context, and release evidence | `docs/project/migration.md` records mappings instead of deleting or rewriting old docs |
| ADR-PROJ-004 | 2026-06-10 | Keep v0.1.67 documentation-only except release metadata and focused validator | The slice is intended to create a control surface without widening behavior | Runtime, deployment, source mutation, adoption, and lifecycle automation remain out of scope |
| ADR-PROJ-005 | 2026-06-10 | Require focused control-surface validation before packaging | Prompt-only enforcement is insufficient | `tests/test_project_control_surface.py` guards required files/tables/headings |
| ADR-PROJ-006 | 2026-06-10 | Add browser-idle barrier after successful Project Source mutations | my_awx 0.0.199 showed adoption/source-list verification can race the shared browser profile after `pb src add` | v0.1.69 adds `pb browser wait-idle`, automatic post-source-add wait, and structured busy retry guidance |
| ADR-PROJ-007 | 2026-06-10 | Scope artifact current-state by repo id | Multi-repo ChatGPT Projects need independent accepted baselines per repository; global current state can silently point future work at the wrong repo | v0.1.70 adds `repo_id`, repo-scoped state, `pb artifact current --repo`, `pb artifact current --all`, and ambiguous unscoped-current failure |
