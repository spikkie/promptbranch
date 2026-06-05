from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


PROFILE_REGISTRY_SCHEMA = "promptbranch.profile.registry"
PROFILE_REGISTRY_SCHEMA_VERSION = "1.0"


@dataclass(frozen=True)
class ProfilePoolDefinition:
    name: str
    size: int
    purpose: str
    lease_timeout_seconds: float
    lease_ttl_seconds: float
    notes: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ProfileDefinition:
    name: str
    kind: str
    seed_dir: str | None
    service_id: str | None
    service_base_url: str | None
    status: str
    pools: tuple[ProfilePoolDefinition, ...]
    notes: str

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["pools"] = [pool.to_dict() for pool in self.pools]
        return payload


def _env_or(*names: str, default: str | None = None) -> str | None:
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    return default


def _resolve_seed(seed_dir: str | None, repo_path: str | Path) -> str | None:
    if not seed_dir:
        return None
    path = Path(seed_dir).expanduser()
    if not path.is_absolute():
        path = Path(repo_path).expanduser().resolve() / path
    return str(path)


def _profile_status(kind: str, seed_dir: str | None) -> str:
    if kind == "service_browser":
        return "metadata_only"
    if not seed_dir:
        return "seed_missing"
    return "seed_available" if Path(seed_dir).exists() else "seed_missing"


def _pool_from_mapping(name: str, raw: dict[str, Any]) -> ProfilePoolDefinition:
    return ProfilePoolDefinition(
        name=name,
        size=int(raw.get("size", 1)),
        purpose=str(raw.get("purpose") or raw.get("notes") or "browser operation pool"),
        lease_timeout_seconds=float(raw.get("lease_timeout_seconds", 0.0)),
        lease_ttl_seconds=float(raw.get("lease_ttl_seconds", 24 * 60 * 60.0)),
        notes=str(raw.get("notes") or ""),
    )


def _profile_from_mapping(raw: dict[str, Any], repo_path: str | Path) -> ProfileDefinition:
    name = str(raw.get("name") or "unnamed")
    kind = str(raw.get("kind") or "local_browser")
    seed_dir = _resolve_seed(raw.get("seed_dir"), repo_path)
    pools_raw = raw.get("pools") or {}
    pools: list[ProfilePoolDefinition] = []
    if isinstance(pools_raw, dict):
        for pool_name, pool_raw in sorted(pools_raw.items()):
            if isinstance(pool_raw, dict):
                pools.append(_pool_from_mapping(str(pool_name), pool_raw))
    elif isinstance(pools_raw, list):
        for item in pools_raw:
            if isinstance(item, dict):
                pools.append(_pool_from_mapping(str(item.get("name") or "default"), item))
    return ProfileDefinition(
        name=name,
        kind=kind,
        seed_dir=seed_dir,
        service_id=raw.get("service_id"),
        service_base_url=raw.get("service_base_url"),
        status=_profile_status(kind, seed_dir),
        pools=tuple(pools),
        notes=str(raw.get("notes") or ""),
    )


def builtin_profiles(repo_path: str | Path = ".") -> list[ProfileDefinition]:
    local_seed = _resolve_seed(_env_or("PROMPTBRANCH_LOCAL_DEBUG_PROFILE_DIR", default=".pb_profile_local_debug"), repo_path)
    service_seed = _env_or("PROMPTBRANCH_SERVICE_PROFILE_DIR", default="/app/.pb_profile")
    service_base = _env_or("CHATGPT_SERVICE_BASE_URL", "CHATGPT_API_BASE_URL", default="http://localhost:8000")
    return [
        ProfileDefinition(
            name="local-debug",
            kind="local_browser",
            seed_dir=local_seed,
            service_id=None,
            service_base_url=None,
            status=_profile_status("local_browser", local_seed),
            pools=(
                ProfilePoolDefinition(
                    name="tasks",
                    size=4,
                    purpose="parallel read-only task list/show/message reads through cloned local browser slots",
                    lease_timeout_seconds=0.0,
                    lease_ttl_seconds=24 * 60 * 60.0,
                    notes="Use for browser-backed task reads when backend-first data is unavailable.",
                ),
                ProfilePoolDefinition(
                    name="ask",
                    size=2,
                    purpose="future parallel asks across different conversations",
                    lease_timeout_seconds=0.0,
                    lease_ttl_seconds=24 * 60 * 60.0,
                    notes="Same conversation must still serialize even when ask pool has multiple slots.",
                ),
            ),
            notes="Built-in local profile seeded from ./.pb_profile_local_debug or PROMPTBRANCH_LOCAL_DEBUG_PROFILE_DIR.",
        ),
        ProfileDefinition(
            name="service-default",
            kind="service_browser",
            seed_dir=service_seed,
            service_id="default",
            service_base_url=service_base,
            status="metadata_only",
            pools=(
                ProfilePoolDefinition(
                    name="sources",
                    size=1,
                    purpose="serialized Project Source mutations through the service browser profile",
                    lease_timeout_seconds=600.0,
                    lease_ttl_seconds=24 * 60 * 60.0,
                    notes="Metadata only in v0.1.42; service queue implementation follows in later slices.",
                ),
                ProfilePoolDefinition(
                    name="tasks",
                    size=3,
                    purpose="future service-backed task reads after service profile cloning/queue support exists",
                    lease_timeout_seconds=30.0,
                    lease_ttl_seconds=24 * 60 * 60.0,
                    notes="Do not assume service browser parallelism until the service queue/profile slice implements it.",
                ),
            ),
            notes="Built-in service profile metadata for /app/.pb_profile; not cloned by this slice.",
        ),
    ]


def load_profile_config(path: str | Path | None, repo_path: str | Path = ".") -> list[ProfileDefinition]:
    if not path:
        return []
    config_path = Path(path).expanduser()
    if not config_path.is_absolute():
        config_path = Path(repo_path).expanduser().resolve() / config_path
    if not config_path.exists():
        return []
    data = json.loads(config_path.read_text(encoding="utf-8"))
    raw_profiles = data.get("profiles", []) if isinstance(data, dict) else []
    profiles: list[ProfileDefinition] = []
    for item in raw_profiles:
        if isinstance(item, dict):
            profiles.append(_profile_from_mapping(item, repo_path))
    return profiles


def profile_registry(repo_path: str | Path = ".", config_path: str | Path | None = None) -> dict[str, Any]:
    repo = Path(repo_path).expanduser().resolve()
    profiles = builtin_profiles(repo)
    profiles.extend(load_profile_config(config_path, repo))
    return {
        "ok": True,
        "action": "profile_registry",
        "status": "listed",
        "schema": PROFILE_REGISTRY_SCHEMA,
        "schema_version": PROFILE_REGISTRY_SCHEMA_VERSION,
        "repo_path": str(repo),
        "profile_count": len(profiles),
        "profiles": [profile.to_dict() for profile in profiles],
    }


def profile_pools(repo_path: str | Path = ".", config_path: str | Path | None = None, profile_name: str | None = None) -> dict[str, Any]:
    registry = profile_registry(repo_path=repo_path, config_path=config_path)
    profiles = registry["profiles"]
    if profile_name:
        profiles = [profile for profile in profiles if profile.get("name") == profile_name]
        if not profiles:
            return {
                "ok": False,
                "action": "profile_pools",
                "status": "profile_not_found",
                "schema": "promptbranch.profile.pools",
                "schema_version": PROFILE_REGISTRY_SCHEMA_VERSION,
                "profile": profile_name,
                "known_profiles": [profile.get("name") for profile in registry["profiles"]],
            }
    pool_entries: list[dict[str, Any]] = []
    for profile in profiles:
        for pool in profile.get("pools", []):
            pool_entries.append(
                {
                    "profile": profile.get("name"),
                    "kind": profile.get("kind"),
                    "profile_status": profile.get("status"),
                    "seed_dir": profile.get("seed_dir"),
                    "service_id": profile.get("service_id"),
                    "service_base_url": profile.get("service_base_url"),
                    **pool,
                }
            )
    return {
        "ok": True,
        "action": "profile_pools",
        "status": "listed",
        "schema": "promptbranch.profile.pools",
        "schema_version": PROFILE_REGISTRY_SCHEMA_VERSION,
        "repo_path": registry["repo_path"],
        "profile": profile_name,
        "pool_count": len(pool_entries),
        "pools": pool_entries,
    }


def profile_show(name: str, repo_path: str | Path = ".", config_path: str | Path | None = None) -> dict[str, Any]:
    registry = profile_registry(repo_path=repo_path, config_path=config_path)
    for profile in registry["profiles"]:
        if profile.get("name") == name:
            return {
                "ok": True,
                "action": "profile_show",
                "status": "found",
                "schema": "promptbranch.profile.definition",
                "schema_version": PROFILE_REGISTRY_SCHEMA_VERSION,
                "profile": profile,
            }
    return {
        "ok": False,
        "action": "profile_show",
        "status": "profile_not_found",
        "schema": "promptbranch.profile.definition",
        "schema_version": PROFILE_REGISTRY_SCHEMA_VERSION,
        "profile": name,
        "known_profiles": [profile.get("name") for profile in registry["profiles"]],
    }
