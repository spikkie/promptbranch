# LLM Provider Policy — JSON Orchestration State MVP

## Decision

The critical orchestration/grilling path uses ChatGPT only.

```text
provider.kind = chatgpt
provider.role = primary_grill
```

## Exclusion

Ollama is excluded from the v0.1.1 critical path.

Reason:

```text
The local larger-model Ollama bakeoff failed the configured validation threshold.
```

## Allowed provider kinds

For v0.1.1:

```text
chatgpt        = allowed for real grill proposals
manual_fixture = allowed only for tests/examples
```

Rejected:

```text
ollama
local_llm
unknown
```

## Authority boundary

```text
LLM proposes.
Promptbranch validates.
Only Promptbranch accepted events become trusted workflow state.
```

No provider may:

```text
execute tools
adopt artifacts
mutate source
deploy
select accepted baselines as authority
override Promptbranch validation
```

## Reintroduction rule

A local LLM may be reconsidered only after:

```text
1. It passes the same automated validation threshold.
2. A new ADR accepts it.
3. Provider policy is updated.
4. Tests prove unapproved providers still fail closed.
```
