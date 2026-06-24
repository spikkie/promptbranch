# Loop target schema contract — v0.1.87

Promptbranch loop targets describe bounded problems that PB may plan against.

## Required schema

```json
{
  "schema": "promptbranch.loop.target",
  "schema_version": "1.0",
  "target_id": "example-target",
  "goal": "Describe the bounded problem.",
  "allowed_paths": ["examples/**"],
  "forbidden_actions": ["project_delete", "kubernetes_apply"],
  "validation": {"commands": ["pytest -q tests/test_example.py"]},
  "human_required_when": ["requirements_conflict"],
  "deployment": {"requested": false, "allowed": false},
  "max_iterations": 1
}
```

## v0.1.87 execution boundary

`v0.1.87` validates and plans only. It must not execute validation commands, mutate files, deploy, mutate Project Sources, adopt artifacts, or delete ChatGPT Projects.
