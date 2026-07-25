# Promptbranch behavioral surface inventory

Version: `v0.1.109.1`

Schema: `promptbranch.project.behavioral_surface`

The authoritative machine-readable inventory is `docs/project/promptbranch-behavioral-surface-v0.1.109.1.json`. Validation is static, read-only, and performs no Project Source, registry, Git, or ChatGPT Project mutation.

## Inventory summary

- Instructions: stable project policy, repository-agent policy, MCP safety boundary, operator-instruction families, protocol envelope rules, and release adoption gating.
- Skills: `repo-inspection`, `release-readiness`, and `promptbranch-final-mvp`. File-backed skills are authoritative; embedded skill documents are validated projections.
- Agents: deterministic request planning, deterministic read-only execution, and optional Ollama read-only tool selection.
- Tools: nine read-only MCP tools, one explicitly enabled controlled process tool, and two blocked write intents.
- Prompts: Ollama summaries/tool selection, integration and task-message exact-token probes, continuous release-live probes, visual-artifact roundtrip prompts, correction retry, and protocol reply-envelope prompts.

## Review commands

```bash
pb project behavioral-surface show --repo-path . --json | jq
pb project behavioral-surface show --repo-path . --kind prompt --json | jq
pb project behavioral-surface show --repo-path . --kind tool --json | jq
pb project behavioral-surface validate --repo-path . --json | jq
```

## Validation contracts

Validation fails closed when a stable ID is duplicated, an owner path or symbol is missing, a skill references an unknown tool, file-backed and embedded skill definitions drift, the tool registry disagrees with the MCP manifests, a blocked tool is exposed, a tool schema is absent, or a prompt lacks recipient, role, output contract, parser, retry behavior, owner, or tests.

The inventory intentionally groups repeated `operator_instruction` payloads by authoritative owner file while reporting discovered occurrence counts. Historical prose, generated logs, and third-party dependency internals are outside the executable behavioral surface.
