from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

import httpx


class ChatGPTServiceClient:
    """Thin sync client for the Dockerized ChatGPT browser service."""

    def __init__(
        self,
        base_url: str,
        *,
        token: Optional[str] = None,
        timeout: float = 300.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._token = token
        self._client = httpx.Client(
            base_url=self.base_url,
            timeout=timeout,
            headers=self._build_headers(),
            transport=transport,
        )

    def _build_headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "ChatGPTServiceClient":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def _json(self, response: httpx.Response) -> Any:
        response.raise_for_status()
        return response.json()

    def healthz(self) -> dict[str, Any]:
        return self._json(self._client.get("/healthz"))

    def login_check(self, *, keep_open: bool = False) -> dict[str, Any]:
        return self._json(self._client.post("/v1/login-check", json={"keep_open": keep_open}))

    def ask(
        self,
        prompt: str,
        *,
        file_path: Optional[str] = None,
        expect_json: bool = False,
        keep_open: bool = False,
        retries: Optional[int] = None,
        project_url: Optional[str] = None,
    ) -> Any:
        data: dict[str, Any] = {
            "prompt": prompt,
            "expect_json": str(expect_json).lower(),
            "keep_open": str(keep_open).lower(),
        }
        if retries is not None:
            data["retries"] = str(retries)
        if project_url:
            data["project_url"] = project_url

        if file_path:
            path = Path(file_path)
            with path.open("rb") as handle:
                response = self._client.post(
                    "/v1/ask",
                    data=data,
                    files={"file": (path.name, handle, "application/octet-stream")},
                )
        else:
            response = self._client.post("/v1/ask", data=data)
        payload = self._json(response)
        return payload.get("answer")

    def discover_project_source_capabilities(
        self,
        *,
        keep_open: bool = False,
        project_url: Optional[str] = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"keep_open": keep_open}
        if project_url:
            params["project_url"] = project_url
        return self._json(self._client.get("/v1/project-source-capabilities", params=params))


    def resolve_project(
        self,
        name: str,
        *,
        keep_open: bool = False,
        project_url: Optional[str] = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "name": name,
            "keep_open": keep_open,
        }
        if project_url:
            payload["project_url"] = project_url
        return self._json(self._client.post("/v1/projects/resolve", json=payload))

    def ensure_project(
        self,
        name: str,
        *,
        icon: Optional[str] = None,
        color: Optional[str] = None,
        memory_mode: str = "default",
        keep_open: bool = False,
        project_url: Optional[str] = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "name": name,
            "icon": icon,
            "color": color,
            "memory_mode": memory_mode,
            "keep_open": keep_open,
        }
        if project_url:
            payload["project_url"] = project_url
        return self._json(self._client.post("/v1/projects/ensure", json=payload))

    def remove_project(
        self,
        *,
        keep_open: bool = False,
        project_url: Optional[str] = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"keep_open": keep_open}
        if project_url:
            payload["project_url"] = project_url
        return self._json(self._client.post("/v1/projects/remove", json=payload))

    def add_project_source(
        self,
        *,
        source_kind: str,
        value: Optional[str] = None,
        file_path: Optional[str] = None,
        display_name: Optional[str] = None,
        keep_open: bool = False,
        project_url: Optional[str] = None,
    ) -> dict[str, Any]:
        data = {
            "type": source_kind,
            "keep_open": str(keep_open).lower(),
        }
        if value is not None:
            data["value"] = value
        if display_name is not None:
            data["name"] = display_name
        if project_url:
            data["project_url"] = project_url

        if file_path:
            path = Path(file_path)
            with path.open("rb") as handle:
                response = self._client.post(
                    "/v1/project-sources",
                    data=data,
                    files={"file": (path.name, handle, "application/octet-stream")},
                )
        else:
            response = self._client.post("/v1/project-sources", data=data)
        return self._json(response)

    def remove_project_source(
        self,
        source_name: str,
        *,
        exact: bool = False,
        keep_open: bool = False,
        project_url: Optional[str] = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "source_name": source_name,
            "exact": exact,
            "keep_open": keep_open,
        }
        if project_url:
            payload["project_url"] = project_url
        return self._json(self._client.post("/v1/project-sources/remove", json=payload))
