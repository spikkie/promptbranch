# PBAI-001: validate full AI application architecture in Promptbranch and PB modules

- Status: `in_progress`
- Started in: `v0.1.112`
- Current phase: tracked registry validation and reference resolution

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

- [x] PBAI-001 is a Promptbranch-wide invariant for the Promptbranch runtime and release gate.
- [x] Strict declaration schema supports runtime applications and domain
      modules.
- [x] Structural validation fails closed on missing layers, empty assets,
      invalid paths, unknown fields, and delegation conflicts.
- [x] Registry validation resolves all AI object references and authority.
- [ ] Executable validation proves ordered skills, bounded tools, validators,
      and SkillRun evidence.
- [ ] Operational validation integrates with issue #1 lifecycle evidence.
- [ ] PB templates include PBAI-001 and the tracked declaration.
- [ ] `promptbranch-method` passes as a domain module.
- [x] Promptbranch passes as a runtime application at registry proof level.
- [x] Validation output never overclaims its proof level.
- [ ] Existing PB projects receive explicit migration reports rather than
      silent breakage.

## Non-goals

- No requirement for one autonomous LLM agent per skill.
- Domain modules do not duplicate the generic PB runtime.
- Documentation, a corpus, prompts, or tools alone are not full AI
  applications.
- Existing project-local validators remain until PB equivalence is proven.

## v0.1.112 implementation phase

`v0.1.112` implements only declaration and structural proof:

- `.promptbranch-ai.json` and schema version `1.0`;
- strict parsing for runtime applications and domain modules;
- ten required non-empty architecture layers;
- sole version authority and bounded project-local validation commands;
- coherent generic-runtime ownership/delegation;
- fail-closed authority boundaries;
- read-only plan and structural validation commands;
- a required release-validation gate.

Registry, executable, operational, template migration, and `promptbranch-method` proof remain open. PBAI-001 therefore remains `in_progress`.


## v0.1.113 implementation phase

`v0.1.113` adds registry proof without executing registered behavior:

- `.promptbranch/ai-registry.json` and packaged schema version `1.0`;
- declaration schema version `1.1` with explicit registry authority;
- stable Agent, Skill, Tool, Validator, state, evidence, and controller identities;
- exact cross-reference, Python-symbol, Skill frontmatter, and MCP manifest resolution;
- exact application capability coverage and bounded authority-controller resolution;
- read-only registry validation and a required release gate.

Executable, operational, template migration, and the first domain-module proof remain open.

## v0.1.114 implementation phase

`v0.1.114` adds executable proof while preserving the operational boundary:

- declaration schema `1.2` and registry schema `1.1`;
- one tracked portable proof skill with exact ordered read-only tools, validators, maximum steps, timeout, and evidence contract;
- real execution through Promptbranch MCP stdio;
- `promptbranch.ai.skill_run` schema `1.0` with full step results, per-step digests, validator outcomes, safety flags, run identity, and canonical evidence hash;
- `pb application architecture evidence --json`;
- required `application_architecture_executable` release gate;
- fail-closed operational proof at `proven_level=executable`.

Operational lifecycle proof, template migration, and the first domain-module proof remain open. PBAI-001 remains `in_progress`.
