from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse, urlunparse

DEFAULT_PROJECT_URL = "https://chatgpt.com/"
PROFILE_DIR_NAME = ".pb_profile"
LEGACY_PROFILE_DIR_NAME = "profile"
PROFILE_DIR_ENV = "PROMPTBRANCH_PROFILE_DIR"
LEGACY_PROFILE_DIR_ENV = "CHATGPT_PROFILE_DIR"
STATE_FILE_NAME = ".promptbranch_state.json"
LEGACY_STATE_FILE_NAME = ".chatgpt_cli_state.json"
GLOBAL_PROJECT_CACHE_FILE_NAME = "project-list-cache.json"
GLOBAL_PROJECT_CACHE_ENV = "PROMPTBRANCH_PROJECT_CACHE_PATH"
LEGACY_GLOBAL_PROJECT_CACHE_ENV = "CHATGPT_PROJECT_CACHE_PATH"




def resolve_profile_dir(profile_dir: Optional[str] = None, *, cwd: Optional[str] = None) -> Path:
    if profile_dir:
        return Path(profile_dir).expanduser().resolve()
    env_path = os.getenv(PROFILE_DIR_ENV) or os.getenv(LEGACY_PROFILE_DIR_ENV)
    if env_path:
        return Path(env_path).expanduser().resolve()
    start = Path(cwd).expanduser().resolve() if cwd else Path.cwd().resolve()
    for current in (start, *start.parents):
        candidate = current / PROFILE_DIR_NAME
        if candidate.is_dir():
            return candidate
    for current in (start, *start.parents):
        candidate = current / LEGACY_PROFILE_DIR_NAME
        if candidate.is_dir():
            return candidate
    return (start / PROFILE_DIR_NAME).resolve()

def global_project_cache_path(path: Optional[str] = None) -> Path:
    if path:
        return Path(path).expanduser()
    env_path = os.getenv(GLOBAL_PROJECT_CACHE_ENV) or os.getenv(LEGACY_GLOBAL_PROJECT_CACHE_ENV)
    if env_path:
        return Path(env_path).expanduser()
    xdg_config_home = os.getenv("XDG_CONFIG_HOME")
    config_root = Path(xdg_config_home).expanduser() if xdg_config_home else Path("~/.config").expanduser()
    return config_root / "promptbranch" / GLOBAL_PROJECT_CACHE_FILE_NAME


def project_home_url_from_url(url: Optional[str]) -> Optional[str]:
    if not url:
        return None
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        return None
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) < 2 or parts[0] != "g":
        return None
    slug = parts[1]
    if len(parts) == 2:
        return urlunparse(parsed._replace(path=f"/g/{slug}/project", query="", fragment=""))
    if parts[2] == "project":
        return urlunparse(parsed._replace(path=f"/g/{slug}/project", query="", fragment=""))
    if parts[2] == "c" and len(parts) >= 4:
        return urlunparse(parsed._replace(path=f"/g/{slug}/project", query="", fragment=""))
    return None


def is_project_conversation_url(url: Optional[str]) -> bool:
    if not url:
        return False
    parsed = urlparse(url)
    parts = [part for part in parsed.path.split("/") if part]
    return len(parts) >= 4 and parts[0] == "g" and parts[2] == "c"


def conversation_id_from_url(url: Optional[str]) -> Optional[str]:
    if not url:
        return None
    parsed = urlparse(url)
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) >= 4 and parts[0] == "g" and parts[2] == "c":
        return parts[3]
    return None


def project_slug_from_url(url: Optional[str]) -> Optional[str]:
    if not url:
        return None
    parsed = urlparse(url)
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) >= 2 and parts[0] == "g":
        return parts[1]
    return None


def project_name_from_url(url: Optional[str]) -> Optional[str]:
    slug = project_slug_from_url(url)
    if not slug:
        return None
    if "-" not in slug:
        return slug
    pieces = slug.split("-")
    if len(pieces) >= 4 and pieces[0] == "g" and pieces[1] == "p":
        name = "-".join(pieces[3:])
        return name or slug
    return slug


class ConversationStateStore:
    def __init__(self, profile_dir: str) -> None:
        base = Path(profile_dir).expanduser()
        self._path = base / STATE_FILE_NAME
        self._legacy_path = base / LEGACY_STATE_FILE_NAME

    @property
    def path(self) -> Path:
        return self._path

    @property
    def legacy_path(self) -> Path:
        return self._legacy_path

    def resolve(self, project_url: Optional[str]) -> Optional[str]:
        if is_project_conversation_url(project_url):
            return project_url
        payload = self._load()
        if not project_url or project_url == DEFAULT_PROJECT_URL:
            current = payload.get("current") if isinstance(payload, dict) else None
            if isinstance(current, dict):
                conversation_url = current.get("conversation_url")
                if isinstance(conversation_url, str):
                    return conversation_url
                project_home_url = current.get("project_home_url")
                if isinstance(project_home_url, str):
                    return project_home_url
            return project_url
        home_url = project_home_url_from_url(project_url)
        if not home_url:
            return project_url
        entry = self._project_entry(payload, home_url)
        if not isinstance(entry, dict):
            return home_url
        conversation_url = entry.get("conversation_url")
        if not isinstance(conversation_url, str):
            return home_url
        if project_home_url_from_url(conversation_url) != home_url:
            return home_url
        return conversation_url

    def project_url_for_operations(self, project_url: Optional[str]) -> Optional[str]:
        if is_project_conversation_url(project_url):
            return project_home_url_from_url(project_url)
        if project_url and project_url != DEFAULT_PROJECT_URL:
            return project_home_url_from_url(project_url) or project_url
        payload = self._load()
        current = payload.get("current") if isinstance(payload, dict) else None
        if isinstance(current, dict):
            current_home = current.get("project_home_url")
            if isinstance(current_home, str):
                return current_home
        return project_url

    def remember(self, project_url: Optional[str], conversation_url: Optional[str], *, project_name: Optional[str] = None) -> None:
        if not conversation_url:
            return
        home_url = project_home_url_from_url(conversation_url) or project_home_url_from_url(project_url)
        if not home_url:
            return
        payload = self._load()
        entry = self._merged_entry(payload, home_url, conversation_url=conversation_url, project_name=project_name)
        self._store_entry(payload, home_url, entry)
        self._write(payload)

    def remember_project(self, project_url: Optional[str], *, project_name: Optional[str] = None) -> None:
        home_url = project_home_url_from_url(project_url)
        if not home_url:
            return
        payload = self._load()
        entry = self._merged_entry(payload, home_url, project_name=project_name)
        self._store_entry(payload, home_url, entry)
        self._write(payload)

    def forget_project(self, project_url: Optional[str]) -> None:
        home_url = project_home_url_from_url(project_url)
        if not home_url:
            return
        payload = self._load()
        projects = payload.get("projects") if isinstance(payload, dict) else None
        if isinstance(projects, dict):
            projects.pop(home_url, None)
        current = payload.get("current") if isinstance(payload, dict) else None
        if isinstance(current, dict) and current.get("project_home_url") == home_url:
            payload["current"] = {}
        self._write(payload if isinstance(payload, dict) else {})

    def forget_conversation(self, project_url: Optional[str]) -> None:
        payload = self._load()
        home_url = project_home_url_from_url(project_url)
        if not home_url and isinstance(payload, dict):
            current = payload.get("current")
            if isinstance(current, dict):
                candidate = current.get("project_home_url")
                if isinstance(candidate, str):
                    home_url = candidate
        if not home_url:
            return
        entry = self._project_entry(payload, home_url) or self._merged_entry(payload, home_url)
        entry["conversation_url"] = None
        self._store_entry(payload, home_url, entry)
        self._write(payload)

    def clear(self) -> None:
        self._write({})

    def snapshot(self, project_url: Optional[str] = None) -> dict[str, Any]:
        payload = self._load()
        current = payload.get("current") if isinstance(payload, dict) else None
        resolved_project_home_url = self.project_url_for_operations(project_url)
        entry: dict[str, Any] | None = None
        if resolved_project_home_url:
            entry = self._project_entry(payload, resolved_project_home_url)
        if not isinstance(entry, dict) and isinstance(current, dict):
            entry = current
        entry = entry if isinstance(entry, dict) else {}
        conversation_url = entry.get("conversation_url") if isinstance(entry.get("conversation_url"), str) else None
        project_name = entry.get("project_name") if isinstance(entry.get("project_name"), str) else None
        if not project_name:
            project_name = project_name_from_url(resolved_project_home_url)
        current_home = current.get("project_home_url") if isinstance(current, dict) and isinstance(current.get("project_home_url"), str) else None
        current_conversation = current.get("conversation_url") if isinstance(current, dict) and isinstance(current.get("conversation_url"), str) else None
        return {
            "state_file": str(self._path),
            "has_current": bool(current_home),
            "current_project_home_url": current_home,
            "current_conversation_url": current_conversation,
            "resolved_project_home_url": resolved_project_home_url,
            "project_name": project_name,
            "conversation_url": conversation_url,
            "conversation_id": conversation_id_from_url(conversation_url),
            "project_slug": project_slug_from_url(resolved_project_home_url),
        }

    def _load(self) -> dict[str, Any]:
        candidates = [self._path, self._legacy_path]
        for candidate in candidates:
            if not candidate.exists():
                continue
            try:
                payload = json.loads(candidate.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if isinstance(payload, dict):
                return payload
        return {}

    def _write(self, payload: dict[str, Any]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    def _project_entry(self, payload: dict[str, Any], home_url: str) -> dict[str, Any] | None:
        projects = payload.get("projects") if isinstance(payload, dict) else None
        if not isinstance(projects, dict):
            return None
        entry = projects.get(home_url)
        return entry if isinstance(entry, dict) else None

    def _merged_entry(
        self,
        payload: dict[str, Any],
        home_url: str,
        *,
        conversation_url: Optional[str] = None,
        project_name: Optional[str] = None,
    ) -> dict[str, Any]:
        existing = self._project_entry(payload, home_url) or {}
        return {
            "project_home_url": home_url,
            "project_name": project_name or existing.get("project_name") or project_name_from_url(home_url),
            "conversation_url": conversation_url or existing.get("conversation_url"),
            "updated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        }

    def _store_entry(self, payload: dict[str, Any], home_url: str, entry: dict[str, Any]) -> None:
        projects = payload.get("projects")
        if not isinstance(projects, dict):
            projects = {}
        projects[home_url] = entry
        payload["projects"] = projects
        payload["current"] = entry


class GlobalProjectCache:
    def __init__(self, path: Optional[str] = None) -> None:
        self._path = global_project_cache_path(path)

    @property
    def path(self) -> Path:
        return self._path

    def snapshot(self) -> dict[str, Any]:
        payload = self._load()
        projects = payload.get("projects") if isinstance(payload, dict) else None
        if not isinstance(projects, list):
            projects = []
        return {
            "cache_file": str(self._path),
            "updated_at": payload.get("updated_at") if isinstance(payload, dict) else None,
            "count": len(projects),
            "projects": projects,
        }

    def store_projects(self, projects: list[dict[str, Any]]) -> dict[str, Any]:
        normalized: list[dict[str, Any]] = []
        seen: set[str] = set()
        for item in projects:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or "").strip()
            url = str(item.get("url") or "").strip()
            home_url = project_home_url_from_url(url) or url
            if not home_url:
                continue
            cache_key = home_url
            if cache_key in seen:
                continue
            seen.add(cache_key)
            normalized.append({
                "name": name or project_name_from_url(home_url) or "<unnamed>",
                "url": home_url,
                "project_home_url": home_url,
                "project_slug": project_slug_from_url(home_url),
                "is_current": bool(item.get("is_current")),
            })
        normalized.sort(key=lambda item: (not bool(item.get("is_current")), str(item.get("name") or "").lower(), str(item.get("url") or "")))
        payload = {
            "schema_version": 1,
            "cache_file": str(self._path),
            "updated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "projects": normalized,
        }
        self._write(payload)
        return payload

    def resolve(self, target: str) -> dict[str, Any] | None:
        projects = self.snapshot().get("projects")
        if not isinstance(projects, list):
            return None
        needle = (target or "").strip()
        if not needle:
            return None
        home_url = project_home_url_from_url(needle) or needle
        url_matches = [item for item in projects if isinstance(item, dict) and home_url in {str(item.get("url") or ""), str(item.get("project_home_url") or "")}]
        if len(url_matches) == 1:
            return dict(url_matches[0])
        exact = [item for item in projects if isinstance(item, dict) and str(item.get("name") or "") == needle]
        if len(exact) == 1:
            return dict(exact[0])
        lowered = needle.lower()
        exact_ci = [item for item in projects if isinstance(item, dict) and str(item.get("name") or "").lower() == lowered]
        if len(exact_ci) == 1:
            return dict(exact_ci[0])
        contains = [item for item in projects if isinstance(item, dict) and lowered in str(item.get("name") or "").lower()]
        if len(contains) == 1:
            return dict(contains[0])
        return None

    def _load(self) -> dict[str, Any]:
        if not self._path.exists():
            return {}
        try:
            payload = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        return payload if isinstance(payload, dict) else {}

    def _write(self, payload: dict[str, Any]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
