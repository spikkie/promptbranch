from __future__ import annotations


def validate_domain_result(value: object) -> bool:
    """Fail closed unless the proof result is an explicit successful object."""
    return isinstance(value, dict) and value.get("ok") is True
