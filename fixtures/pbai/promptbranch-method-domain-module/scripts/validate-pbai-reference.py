#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

GENERIC = {
    "agent_execution", "skill_execution", "tool_dispatch", "validation_orchestration",
    "evidence_ledger", "project_state_transition", "correction", "release",
    "publication", "adoption", "verification",
}
LAYERS = {
    "instructions_policy", "runtime_actors", "skills", "tools", "validators",
    "knowledge_context", "state_contracts", "evidence_records",
    "controller_authority", "lifecycle_recovery",
}


def validate(root: Path) -> dict[str, object]:
    errors: list[str] = []
    declaration_path = root / ".promptbranch-ai.json"
    try:
        declaration = json.loads(declaration_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"ok": False, "status": "declaration_invalid", "errors": [str(exc)]}
    allowed_top = {
        "schema", "schema_version", "application", "version_authority", "runtime",
        "registry", "layers", "delegation", "authority", "validation",
    }
    if set(declaration) != allowed_top:
        errors.append("declaration fields must match the tracked contract exactly")
    if declaration.get("schema") != "promptbranch.ai.application" or declaration.get("schema_version") != "1.3":
        errors.append("unsupported declaration identity")
    app = declaration.get("application") or {}
    if app != {"id": "promptbranch-method", "kind": "domain_module"}:
        errors.append("application identity must be promptbranch-method domain_module")
    if (root / "VERSION").read_text(encoding="utf-8").strip() != "v0.2.0":
        errors.append("VERSION must be v0.2.0")
    delegation = declaration.get("delegation") or {}
    if set(delegation.get("delegated_capabilities") or []) != GENERIC:
        errors.append("all generic runtime capabilities must be delegated")
    if GENERIC & set(delegation.get("owned_capabilities") or []):
        errors.append("domain module may not own generic runtime capabilities")
    authority = declaration.get("authority") or {}
    if authority.get("self_grant_allowed") is not False:
        errors.append("self-granted authority is prohibited")
    layers = declaration.get("layers") or {}
    if set(layers) != LAYERS:
        errors.append("all ten architecture layers are required")
    for layer in sorted(LAYERS):
        paths = layers.get(layer)
        if not isinstance(paths, list) or not paths:
            errors.append(f"layer {layer} is empty")
            continue
        for rel in paths:
            path = root / rel
            if not path.exists():
                errors.append(f"layer {layer} asset missing: {rel}")
            elif path.is_file() and path.stat().st_size == 0:
                errors.append(f"layer {layer} asset empty: {rel}")
            elif path.is_dir() and not any(item.is_file() and item.stat().st_size > 0 for item in path.rglob("*")):
                errors.append(f"layer {layer} directory empty: {rel}")
    source = root / "corpus/righting-software-method-v1/SOURCE.json"
    try:
        metadata = json.loads(source.read_text(encoding="utf-8"))
    except Exception as exc:
        errors.append(f"corpus metadata invalid: {exc}")
    else:
        if metadata.get("object_count") != 428:
            errors.append("corpus object_count must be 428")
        if metadata.get("corpus_sha256") != "7a2dd34e1892a906590165553bf7b78bde44ba26b9c789aa54134f532de5abeb":
            errors.append("corpus SHA-256 mismatch")
    return {"ok": not errors, "status": "reference_structural_validated" if not errors else "reference_structural_invalid", "errors": errors}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = validate(Path.cwd())
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    elif result["ok"]:
        print(result["status"])
    else:
        for error in result["errors"]:
            print(error)
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
