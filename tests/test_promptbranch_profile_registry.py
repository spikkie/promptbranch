from __future__ import annotations

import json
from pathlib import Path

from promptbranch_profiles import profile_pools, profile_registry, profile_show


def test_profile_registry_includes_builtin_local_and_service_profiles(tmp_path: Path) -> None:
    seed = tmp_path / ".pb_profile_local_debug"
    seed.mkdir()

    payload = profile_registry(repo_path=tmp_path)

    assert payload["ok"] is True
    assert payload["schema"] == "promptbranch.profile.registry"
    profiles = {profile["name"]: profile for profile in payload["profiles"]}
    assert {"local-debug", "service-default"}.issubset(profiles)
    assert profiles["local-debug"]["kind"] == "local_browser"
    assert profiles["local-debug"]["status"] == "seed_available"
    assert profiles["local-debug"]["seed_dir"] == str(seed)
    assert profiles["service-default"]["kind"] == "service_browser"
    assert profiles["service-default"]["status"] == "metadata_only"


def test_profile_registry_reports_missing_local_seed_without_failing(tmp_path: Path) -> None:
    payload = profile_registry(repo_path=tmp_path)
    profiles = {profile["name"]: profile for profile in payload["profiles"]}

    assert payload["ok"] is True
    assert profiles["local-debug"]["status"] == "seed_missing"
    assert profiles["local-debug"]["seed_dir"] == str(tmp_path / ".pb_profile_local_debug")


def test_profile_pools_flatten_pool_definitions(tmp_path: Path) -> None:
    payload = profile_pools(repo_path=tmp_path)

    assert payload["ok"] is True
    pools = {(pool["profile"], pool["name"]): pool for pool in payload["pools"]}
    assert ("local-debug", "tasks") in pools
    assert ("local-debug", "ask") in pools
    assert ("service-default", "sources") in pools
    assert pools[("local-debug", "tasks")]["size"] == 4
    assert pools[("service-default", "sources")]["size"] == 1


def test_profile_pools_can_filter_by_profile(tmp_path: Path) -> None:
    payload = profile_pools(repo_path=tmp_path, profile_name="service-default")

    assert payload["ok"] is True
    assert payload["profile"] == "service-default"
    assert {pool["profile"] for pool in payload["pools"]} == {"service-default"}


def test_profile_show_rejects_unknown_profile(tmp_path: Path) -> None:
    payload = profile_show("missing", repo_path=tmp_path)

    assert payload["ok"] is False
    assert payload["status"] == "profile_not_found"
    assert "local-debug" in payload["known_profiles"]


def test_profile_registry_loads_optional_json_config(tmp_path: Path) -> None:
    custom_seed = tmp_path / "profiles" / "custom"
    custom_seed.mkdir(parents=True)
    config = tmp_path / "profiles.json"
    config.write_text(
        json.dumps(
            {
                "profiles": [
                    {
                        "name": "custom-local",
                        "kind": "local_browser",
                        "seed_dir": "profiles/custom",
                        "pools": {"tasks": {"size": 2, "purpose": "custom task reads"}},
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    payload = profile_registry(repo_path=tmp_path, config_path=config)
    profiles = {profile["name"]: profile for profile in payload["profiles"]}

    assert profiles["custom-local"]["status"] == "seed_available"
    assert profiles["custom-local"]["seed_dir"] == str(custom_seed)
    assert profiles["custom-local"]["pools"][0]["size"] == 2
