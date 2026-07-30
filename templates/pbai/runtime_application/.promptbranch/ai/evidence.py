from __future__ import annotations


def validate_domain_evidence(value: object) -> bool:
    return isinstance(value, dict) and bool(value.get("schema")) and bool(value.get("evidence_id"))
