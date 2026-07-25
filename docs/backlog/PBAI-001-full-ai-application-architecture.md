# PBAI-001: validate full AI application architecture in Promptbranch and PB modules

## Goal

Define and enforce `PBAI-001 — Full AI application architecture` across
Promptbranch and every PB-related module.

A full AI application must explicitly define or integrate:

1. instructions and policy;
2. runtime agents or controlled reasoning actors;
3. versioned skills with ordered English procedures;
4. bounded tools;
5. fail-closed step and result validators;
6. authoritative knowledge and project context;
7. typed state and contracts;
8. evidence and execution records;
9. controller and authority boundaries;
10. lifecycle integration and recovery.

Completion requires all steps and validators to pass, required evidence to
exist, output contracts to validate, authority to be respected, and the
resulting state transition to be verified. An agent, LLM, script, or tool saying
“done” is not sufficient.

## Ownership

- Promptbranch is the full generic AI application/runtime: generic agent
  execution, skill execution, tool dispatch, validation orchestration,
  evidence/SkillRun ledgers, project-state transitions, correction, release,
  publication, adoption, and verification.
- PB domain modules are full AI application modules: they provide domain
  instructions, AgentSpecs, SkillSpecs, ToolSpecs/adapters, ValidatorSpecs,
  knowledge, contracts, evidence requirements, authority boundaries, and
  lifecycle hooks while delegating generic execution to Promptbranch.

```text
Promptbranch = generic runtime application
promptbranch-method = Juval Löwy Method domain module
Promptbranch + promptbranch-method = operational Method AI application
```

## Tracked declaration

Introduce a strict tracked declaration, provisionally `.promptbranch-ai.json`,
supporting:

- `runtime_application` and `domain_module`;
- sole version authority;
- runtime provider and contract version;
- paths for instructions, agents, skills, tools, validators, knowledge,
  contracts, evidence, controller/authority, and lifecycle;
- explicit delegation of generic runtime capabilities;
- project-local validation commands.

Reject unknown fields, missing or empty layers, absolute paths, path traversal,
ambiguous ownership, and self-granted mutation/release/adoption authority.

## Validation levels

1. **Declaration** — supported tracked declaration and version source.
2. **Structural** — all ten required layers are present/non-empty and
   delegation is coherent.
3. **Registry** — Agent/Skill/Tool/Validator/state/evidence contracts validate;
   IDs and references resolve; authority is bounded.
4. **Executable** — PB executes ordered skill steps with bounded tools,
   validators, and valid SkillRun evidence.
5. **Operational** — a real PB-managed project proves correction, lifecycle,
   Project Source publication, adoption, accepted/current verification, and
   recovery.

A project must report only the highest level actually proven.

Conceptual commands:

```bash
pb application architecture plan --repo-path . --json
pb application architecture validate --repo-path . --level structural --json
pb application architecture validate --repo-path . --level registry --json
pb application architecture validate --repo-path . --level executable --json
pb application architecture evidence --repo-path . --json
```

## Integration

- Add PBAI-001 and the declaration to PB project templates,
  `PROJECT_SETTINGS.md`, and `AGENTS.md`.
- Make architecture validation a required release gate.
- Integrate operational proof with the global release lifecycle from issue #1.
- Preserve `.pb_profile/` and tracked `.promptbranch-repo.json` during
  validation and lifecycle operations.
- Keep validation read-only until explicit controlled PB execution is
  requested.

## Proving projects

- `spikkie/promptbranch-method`: first `domain_module` proof. Its new minor
  release includes a reference declaration and structural validator.
- `spikkie/promptbranch`: first `runtime_application` proof.

The local `promptbranch-method` validator remains reference-only until
differential validation proves the PB implementation equivalent or stronger.

## Acceptance criteria

- [ ] PBAI-001 is a Promptbranch-wide invariant.
- [ ] Strict declaration schema supports runtime applications and domain
      modules.
- [ ] Structural validation fails closed on missing layers, empty assets,
      invalid paths, unknown fields, and delegation conflicts.
- [ ] Registry validation resolves all AI object references and authority.
- [ ] Executable validation proves ordered skills, bounded tools, validators,
      and SkillRun evidence.
- [ ] Operational validation integrates with issue #1 lifecycle evidence.
- [ ] PB templates include PBAI-001 and the tracked declaration.
- [ ] `promptbranch-method` passes as a domain module.
- [ ] Promptbranch passes as a runtime application.
- [ ] Validation output never overclaims its proof level.
- [ ] Existing PB projects receive explicit migration reports rather than
      silent breakage.

## Non-goals

- No requirement for one autonomous LLM agent per skill.
- Domain modules do not duplicate the generic PB runtime.
- Documentation, a corpus, prompts, or tools alone are not full AI
  applications.
- Existing project-local validators remain until PB equivalence is proven.
