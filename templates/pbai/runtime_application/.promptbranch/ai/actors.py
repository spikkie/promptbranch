from __future__ import annotations


def domain_architecture_actor() -> dict[str, object]:
    """Return the bounded domain actor contract without executing generic runtime work."""
    return {
        "application_id": 'example-runtime',
        "owned_capabilities": ['agent_execution', 'skill_execution', 'tool_dispatch', 'validation_orchestration', 'evidence_ledger', 'project_state_transition', 'correction', 'release', 'publication', 'adoption', 'verification'],
        "delegates_generic_runtime_to": "promptbranch",
        "read_only": True,
    }
