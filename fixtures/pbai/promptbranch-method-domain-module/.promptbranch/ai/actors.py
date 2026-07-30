from __future__ import annotations


def domain_architecture_actor() -> dict[str, object]:
    """Return the bounded domain actor contract without executing generic runtime work."""
    return {
        "application_id": 'promptbranch-method',
        "owned_capabilities": ['domain_instructions', 'domain_actors', 'domain_skills', 'domain_tools', 'domain_validators', 'domain_knowledge', 'domain_contracts', 'domain_evidence', 'domain_authority_hooks', 'domain_lifecycle_hooks'],
        "delegates_generic_runtime_to": "promptbranch",
        "read_only": True,
    }
