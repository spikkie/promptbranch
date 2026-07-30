from __future__ import annotations


def controlled_execution_adapter() -> dict[str, object]:
    return {"controller": "promptbranch.controlled_execution", "delegated": True, "self_grant": False}


def release_lifecycle_adapter() -> dict[str, object]:
    return {"controller": "promptbranch.release.lifecycle", "delegated": True, "self_grant": False}


def publication_adapter() -> dict[str, object]:
    return {"controller": "promptbranch.release.publication", "delegated": True, "self_grant": False}


def artifact_registry_adapter() -> dict[str, object]:
    return {"controller": "promptbranch.artifact.registry", "delegated": True, "self_grant": False}
