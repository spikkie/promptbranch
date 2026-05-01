from __future__ import annotations

import logging
import os
import secrets
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, FastAPI, File, Form, Header, HTTPException, UploadFile, status
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel, Field

from promptbranch_automation import ChatGPTAutomationService, ChatGPTAutomationSettings
from promptbranch_test_suite import run_test_suite_async
from promptbranch_browser_auth.exceptions import (
    AuthenticationError,
    BotChallengeError,
    ManualLoginRequiredError,
    ResponseTimeoutError,
    UnsupportedOperationError,
)

logger = logging.getLogger(__name__)


def _normalized_upload_filename(filename: Optional[str], *, default: str = "attachment.bin") -> str:
    candidate = Path((filename or "").strip() or default).name
    if candidate in {"", ".", ".."}:
        return default
    return candidate


async def _persist_upload_to_named_temp_path(file: UploadFile, *, default_filename: str = "attachment.bin") -> tuple[Path, Path]:
    temp_dir = Path(tempfile.mkdtemp(prefix="promptbranch-upload-"))
    temp_path = temp_dir / _normalized_upload_filename(file.filename, default=default_filename)
    temp_path.write_bytes(await file.read())
    return temp_dir, temp_path


def _cleanup_temp_upload(temp_path: Optional[Path], temp_dir: Optional[Path]) -> None:
    if temp_path is not None:
        temp_path.unlink(missing_ok=True)
    if temp_dir is not None:
        temp_dir.rmdir()


def _env_flag(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class LoginCheckRequest(BaseModel):
    keep_open: bool = False


class AskResponse(BaseModel):
    ok: bool = True
    answer: object
    conversation_url: Optional[str] = None


class ProjectResolveRequest(BaseModel):
    name: str = Field(..., min_length=1)
    keep_open: bool = False
    project_url: Optional[str] = None


class ProjectEnsureRequest(BaseModel):
    name: str = Field(..., min_length=1)
    icon: Optional[str] = None
    color: Optional[str] = None
    memory_mode: str = "default"
    keep_open: bool = False
    project_url: Optional[str] = None


class ProjectRemoveRequest(BaseModel):
    keep_open: bool = False
    project_url: Optional[str] = None


class ProjectSourceRemoveRequest(BaseModel):
    source_name: str = Field(..., min_length=1)
    exact: bool = False
    keep_open: bool = False
    project_url: Optional[str] = None


class ChatGetRequest(BaseModel):
    conversation_url: str = Field(..., min_length=1)
    keep_open: bool = False
    project_url: Optional[str] = None


class TestSuiteRunRequest(BaseModel):
    project_url: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None
    password_file: Optional[str] = None
    profile_dir: Optional[str] = None
    headless: Optional[bool] = None
    use_playwright: Optional[bool] = None
    browser_channel: Optional[str] = None
    enable_fedcm: Optional[bool] = None
    keep_no_sandbox: Optional[bool] = None
    max_retries: Optional[int] = None
    retry_backoff_seconds: Optional[float] = None
    debug: Optional[bool] = None
    keep_open: Optional[bool] = None
    keep_project: bool = False
    step_delay_seconds: Optional[float] = None
    post_ask_delay_seconds: Optional[float] = None
    skip: list[str] = Field(default_factory=list)
    only: list[str] = Field(default_factory=list)
    strict_remove_ui: bool = False
    project_name: Optional[str] = None
    project_name_prefix: Optional[str] = None
    run_id: Optional[str] = None
    memory_mode: Optional[str] = None
    link_url: Optional[str] = None
    ask_prompt: Optional[str] = None
    json_out: Optional[str] = None
    project_list_debug_scroll_rounds: Optional[int] = None
    project_list_debug_wait_ms: Optional[int] = None
    project_list_debug_manual_pause: bool = False
    service_base_url: Optional[str] = None
    service_token: Optional[str] = None
    service_timeout_seconds: Optional[float] = None
    clear_singleton_locks: Optional[bool] = None


class ServiceInfo(BaseModel):
    ok: bool = True
    service: str
    version: str
    profile_dir: str
    project_url: str
    headless: bool
    use_patchright: bool
    browser_channel: Optional[str] = None
    auth_required: bool


SERVICE_VERSION = "0.0.135"
_SERVICE_TOKEN = os.getenv("CHATGPT_SERVICE_TOKEN") or os.getenv("CHATGPT_API_TOKEN")
_DEFAULT_PROJECT_URL = os.getenv("CHATGPT_PROJECT_URL", "https://chatgpt.com/")


def _build_service(*, project_url_override: Optional[str] = None) -> ChatGPTAutomationService:
    return ChatGPTAutomationService(
        ChatGPTAutomationSettings(
            project_url=project_url_override or _DEFAULT_PROJECT_URL,
            email=os.getenv("CHATGPT_EMAIL") or os.getenv("EMAIL"),
            password=os.getenv("CHATGPT_PASSWORD") or os.getenv("PASSWORD"),
            profile_dir=os.getenv("PROMPTBRANCH_PROFILE_DIR", "/app/.pb_profile"),
            headless=_env_flag("CHATGPT_HEADLESS", False),
            use_patchright=_env_flag("CHATGPT_USE_PATCHRIGHT", True),
            browser_channel=os.getenv("CHATGPT_BROWSER_CHANNEL", "chrome"),
            password_file=os.getenv("CHATGPT_PASSWORD_FILE"),
            disable_fedcm=_env_flag("CHATGPT_DISABLE_FEDCM", True),
            filter_no_sandbox=_env_flag("CHATGPT_FILTER_NO_SANDBOX", False),
            max_retries=int(os.getenv("CHATGPT_MAX_RETRIES", "2")),
            retry_backoff_seconds=float(os.getenv("CHATGPT_RETRY_BACKOFF_SECONDS", "2.0")),
            clear_singleton_locks=_env_flag("CHATGPT_CLEAR_PROFILE_SINGLETON_LOCKS", True),
        )
    )


service = _build_service()
_project_services: dict[str, ChatGPTAutomationService] = {}
app = FastAPI(
    title="ChatGPT Docker Service",
    version=SERVICE_VERSION,
    description="Reusable Docker-first service for browser-driven ChatGPT automation.",
)
protected = APIRouter(prefix="/v1")


def _test_suite_frontend_html() -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>promptbranch test suite</title>
  <style>
    body {{ font-family: system-ui, sans-serif; margin: 2rem; max-width: 1100px; }}
    textarea {{ width: 100%; min-height: 22rem; font-family: ui-monospace, monospace; }}
    input, button, select {{ font: inherit; padding: 0.45rem 0.6rem; margin: 0.2rem 0; }}
    .grid {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 1rem; }}
    .card {{ border: 1px solid #ddd; border-radius: 10px; padding: 1rem; }}
    .muted {{ color: #666; }}
    code {{ background: #f4f4f4; padding: 0.1rem 0.3rem; border-radius: 4px; }}
  </style>
</head>
<body>
  <h1>promptbranch test suite</h1>
  <p class="muted">Run the end-to-end smoke suite from localhost. This page works both when the service runs locally and when it runs in Docker on <code>http://localhost:8000</code>.</p>
  <div class="grid">
    <div class="card">
      <h2>Run</h2>
      <label>Bearer token (optional)<br><input id="token" type="password" placeholder="Only needed when CHATGPT_SERVICE_TOKEN is set"></label><br>
      <label>Project URL<br><input id="project_url" type="text" value="{_DEFAULT_PROJECT_URL}"></label><br>
      <label>Profile dir<br><input id="profile_dir" type="text" placeholder="Use server default when blank"></label><br>
      <label>Email<br><input id="email" type="text" placeholder="Optional override"></label><br>
      <label>Password file<br><input id="password_file" type="text" placeholder="Optional override"></label><br>
      <label><input id="headless" type="checkbox"> Headless</label><br>
      <label><input id="use_playwright" type="checkbox"> Use Playwright instead of Patchright</label><br>
      <label><input id="keep_project" type="checkbox"> Keep project after run</label><br>
      <label><input id="project_list_debug" type="checkbox"> Include project_list_debug step</label><br>
      <button id="run">Run test suite</button>
      <p class="muted">Recommended for daily validation: leave <code>keep project</code> off and run against your normal profile.</p>
    </div>
    <div class="card">
      <h2>How to use</h2>
      <p>Local frontend:</p>
      <pre>promptbranch-ui</pre>
      <p>Docker frontend:</p>
      <pre>./run_chatgpt_service.sh
open http://localhost:8000/ui/test-suite</pre>
      <p>CLI daily run:</p>
      <pre>promptbranch test-suite --json</pre>
    </div>
  </div>
  <h2>Result</h2>
  <textarea id="result" spellcheck="false" placeholder="JSON result will appear here"></textarea>
  <script>
    const $ = (id) => document.getElementById(id);
    $('run').addEventListener('click', async () => {{
      $('result').value = 'Running test suite...';
      const payload = {{
        project_url: $('project_url').value || undefined,
        profile_dir: $('profile_dir').value || undefined,
        email: $('email').value || undefined,
        password_file: $('password_file').value || undefined,
        headless: $('headless').checked,
        use_playwright: $('use_playwright').checked,
        keep_project: $('keep_project').checked,
        only: $('project_list_debug').checked ? ['project_list_debug'] : [],
      }};
      const headers = {{ 'Content-Type': 'application/json' }};
      if ($('token').value) headers['Authorization'] = 'Bearer ' + $('token').value;
      try {{
        const response = await fetch('/v1/test-suite/run', {{ method: 'POST', headers, body: JSON.stringify(payload) }});
        const text = await response.text();
        try {{ $('result').value = JSON.stringify(JSON.parse(text), null, 2); }} catch {{ $('result').value = text; }}
      }} catch (error) {{
        $('result').value = String(error);
      }}
    }});
  </script>
</body>
</html>"""


def _service_for(project_url: Optional[str]) -> ChatGPTAutomationService:
    if not project_url or project_url == service.settings.project_url:
        return service
    cached = _project_services.get(project_url)
    if cached is None:
        cached = _build_service(project_url_override=project_url)
        _project_services[project_url] = cached
    return cached


def _raise_http_error(exc: Exception) -> None:
    if isinstance(exc, AuthenticationError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    if isinstance(exc, ManualLoginRequiredError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if isinstance(exc, BotChallengeError):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(exc)) from exc
    if isinstance(exc, UnsupportedOperationError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if isinstance(exc, ResponseTimeoutError):
        raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail=str(exc)) from exc
    logger.exception("Unhandled ChatGPT Docker service error", exc_info=exc)
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"{type(exc).__name__}: {exc}",
    ) from exc


async def require_service_token(authorization: Optional[str] = Header(default=None)) -> None:
    if not _SERVICE_TOKEN:
        return
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
        )
    presented = authorization.split(" ", 1)[1].strip()
    if not secrets.compare_digest(presented, _SERVICE_TOKEN):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid bearer token",
        )


@app.get("/", include_in_schema=False)
async def root_redirect() -> RedirectResponse:
    return RedirectResponse(url="/ui/test-suite")


@app.get("/ui/test-suite", response_class=HTMLResponse, include_in_schema=False)
async def test_suite_frontend() -> HTMLResponse:
    return HTMLResponse(_test_suite_frontend_html())


@app.get("/healthz", response_model=ServiceInfo)
async def healthz() -> ServiceInfo:
    settings = service.settings
    return ServiceInfo(
        service="promptbranch-service",
        version=SERVICE_VERSION,
        profile_dir=settings.profile_dir,
        project_url=settings.project_url,
        headless=settings.headless,
        use_patchright=settings.use_patchright,
        browser_channel=settings.browser_channel,
        auth_required=bool(_SERVICE_TOKEN),
    )


@protected.post("/login-check", dependencies=[Depends(require_service_token)])
async def login_check(payload: LoginCheckRequest) -> dict:
    try:
        return await service.run_login_check(keep_open=payload.keep_open)
    except Exception as exc:  # pragma: no cover - exercised by live runs
        _raise_http_error(exc)


@protected.post("/ask", response_model=AskResponse, dependencies=[Depends(require_service_token)])
async def ask(
    prompt: str = Form(...),
    expect_json: bool = Form(False),
    keep_open: bool = Form(False),
    retries: Optional[int] = Form(None),
    project_url: Optional[str] = Form(default=None),
    conversation_url: Optional[str] = Form(default=None),
    file: Optional[UploadFile] = File(default=None),
) -> AskResponse:
    temp_path: Optional[Path] = None
    temp_dir: Optional[Path] = None
    try:
        if file is not None:
            temp_dir, temp_path = await _persist_upload_to_named_temp_path(file)

        result = await _service_for(project_url).ask_question_result(
            prompt=prompt,
            file_path=(str(temp_path) if temp_path is not None else None),
            conversation_url=conversation_url,
            expect_json=expect_json,
            keep_open=keep_open,
            retries=retries,
        )
        return AskResponse(
            answer=result["answer"],
            conversation_url=result.get("conversation_url"),
        )
    except Exception as exc:  # pragma: no cover - exercised by live runs
        _raise_http_error(exc)
    finally:
        _cleanup_temp_upload(temp_path, temp_dir)


@protected.get("/projects", dependencies=[Depends(require_service_token)])
async def list_projects(keep_open: bool = False, project_url: Optional[str] = None) -> dict:
    try:
        return await _service_for(project_url).list_projects(keep_open=keep_open)
    except Exception as exc:  # pragma: no cover - exercised by live runs
        _raise_http_error(exc)


@protected.get("/chats", dependencies=[Depends(require_service_token)])
async def list_project_chats(
    keep_open: bool = False,
    project_url: Optional[str] = None,
    include_history_fallback: bool = True,
) -> dict:
    try:
        return await _service_for(project_url).list_project_chats(
            keep_open=keep_open,
            include_history_fallback=include_history_fallback,
        )
    except Exception as exc:  # pragma: no cover - exercised by live runs
        _raise_http_error(exc)


@protected.get("/chats/debug", dependencies=[Depends(require_service_token)])
async def debug_project_chats(
    keep_open: bool = False,
    project_url: Optional[str] = None,
    scroll_rounds: int = 20,
    wait_ms: int = 600,
    include_history: bool = True,
    history_max_pages: int = 5,
    history_max_detail_probes: int = 80,
    manual_pause: bool = False,
) -> dict:
    try:
        return await _service_for(project_url).debug_project_chats(
            keep_open=keep_open,
            scroll_rounds=scroll_rounds,
            wait_ms=wait_ms,
            include_history=include_history,
            history_max_pages=history_max_pages,
            history_max_detail_probes=history_max_detail_probes,
            manual_pause=manual_pause,
        )
    except Exception as exc:  # pragma: no cover - exercised by live runs
        _raise_http_error(exc)


@protected.get("/project-sources", dependencies=[Depends(require_service_token)])
async def list_project_sources(keep_open: bool = False, project_url: Optional[str] = None) -> dict:
    try:
        return await _service_for(project_url).list_project_sources(keep_open=keep_open)
    except Exception as exc:  # pragma: no cover - exercised by live runs
        _raise_http_error(exc)


@protected.post("/chats/get", dependencies=[Depends(require_service_token)])
async def get_chat(payload: ChatGetRequest) -> dict:
    try:
        return await _service_for(payload.project_url).get_chat(
            conversation_url=payload.conversation_url,
            keep_open=payload.keep_open,
        )
    except Exception as exc:  # pragma: no cover - exercised by live runs
        _raise_http_error(exc)


@protected.post("/test-suite/run", dependencies=[Depends(require_service_token)])
async def run_test_suite(payload: TestSuiteRunRequest) -> dict:
    try:
        return await run_test_suite_async(**payload.model_dump())
    except Exception as exc:  # pragma: no cover - exercised by live runs
        _raise_http_error(exc)


@protected.get("/project-source-capabilities", dependencies=[Depends(require_service_token)])
async def project_source_capabilities(keep_open: bool = False, project_url: Optional[str] = None) -> dict:
    try:
        return await _service_for(project_url).discover_project_source_capabilities(keep_open=keep_open)
    except Exception as exc:  # pragma: no cover - exercised by live runs
        _raise_http_error(exc)


@protected.post("/projects/create", dependencies=[Depends(require_service_token)])
async def create_project(payload: ProjectEnsureRequest) -> dict:
    try:
        return await _service_for(payload.project_url).create_project(
            name=payload.name,
            icon=payload.icon,
            color=payload.color,
            memory_mode=payload.memory_mode,
            keep_open=payload.keep_open,
        )
    except Exception as exc:  # pragma: no cover - exercised by live runs
        _raise_http_error(exc)


@protected.post("/projects/resolve", dependencies=[Depends(require_service_token)])
async def resolve_project(payload: ProjectResolveRequest) -> dict:
    try:
        return await _service_for(payload.project_url).resolve_project(
            name=payload.name,
            keep_open=payload.keep_open,
        )
    except Exception as exc:  # pragma: no cover - exercised by live runs
        _raise_http_error(exc)


@protected.post("/projects/ensure", dependencies=[Depends(require_service_token)])
async def ensure_project(payload: ProjectEnsureRequest) -> dict:
    try:
        return await _service_for(payload.project_url).ensure_project(
            name=payload.name,
            icon=payload.icon,
            color=payload.color,
            memory_mode=payload.memory_mode,
            keep_open=payload.keep_open,
        )
    except Exception as exc:  # pragma: no cover - exercised by live runs
        _raise_http_error(exc)


@protected.post("/projects/remove", dependencies=[Depends(require_service_token)])
async def remove_project(payload: ProjectRemoveRequest) -> dict:
    try:
        return await _service_for(payload.project_url).remove_project(keep_open=payload.keep_open)
    except Exception as exc:  # pragma: no cover - exercised by live runs
        _raise_http_error(exc)


@protected.post("/project-sources", dependencies=[Depends(require_service_token)])
async def add_project_source(
    source_kind: str = Form(..., alias="type"),
    value: Optional[str] = Form(default=None),
    display_name: Optional[str] = Form(default=None, alias="name"),
    keep_open: bool = Form(False),
    project_url: Optional[str] = Form(default=None),
    conversation_url: Optional[str] = Form(default=None),
    file: Optional[UploadFile] = File(default=None),
) -> dict:
    temp_path: Optional[Path] = None
    temp_dir: Optional[Path] = None
    try:
        if source_kind == "file":
            if file is None:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="file is required when type=file")
            temp_dir, temp_path = await _persist_upload_to_named_temp_path(file)
            if display_name:
                display_name = _normalized_upload_filename(display_name)
            else:
                display_name = _normalized_upload_filename(file.filename)
        elif source_kind in {"text", "link"} and not value:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"value is required when type={source_kind}")

        return await _service_for(project_url).add_project_source(
            source_kind=source_kind,
            value=value,
            file_path=(str(temp_path) if temp_path is not None else None),
            display_name=display_name,
            keep_open=keep_open,
        )
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - exercised by live runs
        _raise_http_error(exc)
    finally:
        _cleanup_temp_upload(temp_path, temp_dir)


@protected.post("/project-sources/remove", dependencies=[Depends(require_service_token)])
async def remove_project_source(payload: ProjectSourceRemoveRequest) -> dict:
    try:
        return await _service_for(payload.project_url).remove_project_source(
            source_name=payload.source_name,
            exact=payload.exact,
            keep_open=payload.keep_open,
        )
    except Exception as exc:  # pragma: no cover - exercised by live runs
        _raise_http_error(exc)


app.include_router(protected)


def main() -> int:
    import uvicorn

    host = os.getenv("PROMPTBRANCH_UI_HOST", os.getenv("CHATGPT_SERVICE_HOST", "127.0.0.1"))
    port = int(os.getenv("PROMPTBRANCH_UI_PORT", os.getenv("CHATGPT_SERVICE_PORT", "8000")))
    uvicorn.run("promptbranch_container_api:app", host=host, port=port, reload=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
