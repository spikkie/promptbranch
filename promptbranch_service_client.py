from __future__ import annotations

import json
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
        timeout: float = 900.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._token = token
        self._timeout = float(timeout)
        self._client = httpx.Client(
            base_url=self.base_url,
            timeout=self._timeout,
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
        if response.is_error:
            detail: str | None = None
            try:
                payload = response.json()
                if isinstance(payload, dict):
                    detail_value = payload.get("detail") or payload.get("error")
                    if detail_value is not None:
                        if isinstance(detail_value, (dict, list)):
                            detail = json.dumps(detail_value, ensure_ascii=False)
                        else:
                            detail = str(detail_value)
            except Exception:
                detail = None
            if not detail:
                body = response.text.strip()
                detail = body[:500] if body else None
            message = f"{response.status_code} error for {response.request.method} {response.request.url}"
            if detail:
                message += f": {detail}"
            raise httpx.HTTPStatusError(message, request=response.request, response=response)
        return response.json()

    def healthz(self) -> dict[str, Any]:
        return self._json(self._client.get("/healthz"))

    def run_test_suite(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._json(self._client.post("/v1/test-suite/run", json=payload))

    def login_check(self, *, keep_open: bool = False) -> dict[str, Any]:
        return self._json(self._client.post("/v1/login-check", json={"keep_open": keep_open}))

    def ask(
        self,
        prompt: str,
        *,
        file_path: Optional[str] = None,
        conversation_url: str | None = None,
        expect_json: bool = False,
        keep_open: bool = False,
        retries: Optional[int] = None,
        project_url: Optional[str] = None,
    ) -> Any:
        payload = self.ask_result(
            prompt,
            file_path=file_path,
            conversation_url=conversation_url,
            expect_json=expect_json,
            keep_open=keep_open,
            retries=retries,
            project_url=project_url,
        )
        return payload.get("answer")

    def ask_result(
        self,
        prompt: str,
        *,
        file_path: Optional[str] = None,
        conversation_url: str | None = None,
        expect_json: bool = False,
        keep_open: bool = False,
        retries: Optional[int] = None,
        project_url: Optional[str] = None,
    ) -> dict[str, Any]:
        data: dict[str, Any] = {
            "prompt": prompt,
            "expect_json": str(expect_json).lower(),
            "keep_open": str(keep_open).lower(),
        }
        if retries is not None:
            data["retries"] = str(retries)
        if project_url:
            data["project_url"] = project_url
        if conversation_url:
            data["conversation_url"] = conversation_url

        if file_path:
            path = Path(file_path)
            with path.open("rb") as handle:
                response = self._client.post(
                    "/v1/ask",
                    data=data,
                    files={"file": (path.name, handle, "application/octet-stream")},
                    timeout=max(self._timeout, 900.0),
                )
        else:
            response = self._client.post("/v1/ask", data=data, timeout=max(self._timeout, 900.0))
        return self._json(response)

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



    def list_projects(
        self,
        *,
        keep_open: bool = False,
        project_url: Optional[str] = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"keep_open": keep_open}
        if project_url:
            params["project_url"] = project_url
        return self._json(self._client.get("/v1/projects", params=params))

    def list_project_chats(
        self,
        *,
        keep_open: bool = False,
        project_url: Optional[str] = None,
        include_history_fallback: bool = True,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "keep_open": keep_open,
            "include_history_fallback": include_history_fallback,
        }
        if project_url:
            params["project_url"] = project_url
        return self._json(self._client.get("/v1/chats", params=params))

    def debug_project_chats(
        self,
        *,
        keep_open: bool = False,
        project_url: Optional[str] = None,
        scroll_rounds: int = 20,
        wait_ms: int = 600,
        include_history: bool = True,
        history_max_pages: int = 5,
        history_max_detail_probes: int = 80,
        manual_pause: bool = False,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "keep_open": keep_open,
            "scroll_rounds": scroll_rounds,
            "wait_ms": wait_ms,
            "include_history": include_history,
            "history_max_pages": history_max_pages,
            "history_max_detail_probes": history_max_detail_probes,
            "manual_pause": manual_pause,
        }
        if project_url:
            params["project_url"] = project_url
        return self._json(self._client.get("/v1/chats/debug", params=params))

    def list_project_sources(
        self,
        *,
        keep_open: bool = False,
        project_url: Optional[str] = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"keep_open": keep_open}
        if project_url:
            params["project_url"] = project_url
        return self._json(self._client.get("/v1/project-sources", params=params))

    def get_chat(
        self,
        conversation_url: str,
        *,
        keep_open: bool = False,
        project_url: Optional[str] = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"conversation_url": conversation_url, "keep_open": keep_open}
        if project_url:
            payload["project_url"] = project_url
        return self._json(self._client.post("/v1/chats/get", json=payload))

    def create_project(
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
        return self._json(self._client.post("/v1/projects/create", json=payload))

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
        overwrite_existing: bool = True,
        project_url: Optional[str] = None,
    ) -> dict[str, Any]:
        normalized_display_name = Path(display_name).name if display_name else None
        data = {
            "type": source_kind,
            "keep_open": str(keep_open).lower(),
            "overwrite_existing": str(overwrite_existing).lower(),
        }
        if value is not None:
            data["value"] = value
        if normalized_display_name is not None:
            data["name"] = normalized_display_name
        elif source_kind == "file" and file_path:
            data["name"] = Path(file_path).name
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
