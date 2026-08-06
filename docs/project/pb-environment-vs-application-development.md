# Promptbranch environment versus application development

Documentation release: `PB-DOC-2026-08-06.1`  
Evidence checkpoint: accepted/current artifact `v0.1.124`  
Installed Promptbranch runtime observed during proof: `v0.1.123.2.6`

## Purpose

This document makes one boundary explicit:

```text
System A — Promptbranch environment / control plane
System B — an external application or tool developed using Promptbranch
```

The work through `v0.1.124` primarily built and tested **System A**. It proved that Promptbranch can manage its own state, browser integration, artifact intake, candidate testing, and local acceptance lifecycle. It did not yet prove that Promptbranch can safely design, modify, test, release, and deploy **System B**.

## System A — the PB environment we have been developing

The Promptbranch environment contains the deterministic authority and workflow machinery:

- CLI command grammar and repository/project identity;
- Workspace, Task, Source, Artifact, candidate, and accepted/current state;
- ChatGPT Project/conversation integration;
- structured ask/reply request and response contracts;
- exact request/message/answer/artifact correlation;
- authenticated browser operations and transactional Project Source mutation;
- ZIP download, verification, migration, candidate registry, testing, and acceptance;
- release evidence, architecture validation, safety checks, and recovery gates;
- read-only MCP tools, skills, and bounded registered execution surfaces.

The successful `v0.1.124` path demonstrated:

```text
release request
→ real rendered ZIP
→ exact reply correlation
→ verified artifact inbox
→ candidate migration
→ focused browser proof
→ full direct candidate test
→ explicit acceptance
→ artifact-current verification
→ candidate_mvp_complete
```

That is a meaningful PB control-plane milestone.

## System B — the application/tool that PB will develop

An external application has its own independent product and release authority:

- separate repository and repository identity;
- product target, users, non-goals, and acceptance criteria;
- application architecture and bounded contexts;
- application source code and configuration;
- application-specific unit, integration, acceptance, and security tests;
- application candidate artifact and accepted/current baseline;
- optional deployment environment and post-deployment evidence.

The external application must not share or inherit Promptbranch's runtime version, candidate registry, accepted artifact, or release evidence merely because PB itself is green.

## The critical difference

| Concern | PB environment | Application developed with PB |
|---|---|---|
| Primary purpose | Orchestrate and govern work | Deliver user/business functionality |
| Repository | `chatgpt_claudecode_workflow-2` | Separate application repository |
| Tests | PB CLI/browser/protocol/release tests | Application unit/integration/acceptance tests |
| Artifact | Promptbranch runtime/release ZIP | Application package/container/chart/binary/ZIP |
| Candidate registry | PB release candidates | Application release candidates |
| Accepted/current | PB control-plane baseline | Application baseline |
| Mutation authority | PB policy and operator | App execution envelope and operator |
| Deployment | PB runtime/service operations | Application deployment target |
| Completion evidence | PB workflow and safety evidence | Functional application behavior and release evidence |

## Current maturity statement

```text
PB candidate/artifact lifecycle MVP: complete for the local accepted-artifact path
PB environment final proof repetition: next at v0.1.125
PB environment hardening/freeze: planned through v0.1.128
External application-development MVP: planned from v0.1.129 through v0.1.132
External deployment proof: planned at v0.1.133
Reusable multi-repository application workflow: planned at v0.1.134
```

## Authority rule

ChatGPT may reason, question assumptions, propose architecture, and draft changes. Promptbranch validates deterministic contracts and evidence. The operator authorizes source mutation, candidate acceptance, publication, and deployment. A passing PB environment test never grants automatic authority over an application repository.
