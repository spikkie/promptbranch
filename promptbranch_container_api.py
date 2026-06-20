from __future__ import annotations

import asyncio
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
from promptbranch_version import PACKAGE_VERSION as SERVICE_VERSION
from promptbranch_project_delete_safety import project_delete_disabled_result
from promptbranch_browser_auth.client import get_latest_ask_progress
from promptbranch_browser_auth.exceptions import (
    AuthenticationError,
    BotChallengeError,
    BrowserContextUnavailableError,
    BrowserProfileBusyError,
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


def _unique_temp_upload_name(raw_name: Optional[str], used_names: set[str], *, default: str) -> str:
    name = _normalized_upload_filename(raw_name, default=default)
    if name not in used_names:
        used_names.add(name)
        return name
    stem = Path(name).stem or "attachment"
    suffix = Path(name).suffix
    counter = 2
    while True:
        candidate = f"{stem}-{counter}{suffix}"
        if candidate not in used_names:
            used_names.add(candidate)
            return candidate
        counter += 1


async def _persist_uploads_to_named_temp_paths(files: list[UploadFile], *, default_filename: str = "attachment.bin") -> tuple[Path, list[Path]]:
    temp_dir = Path(tempfile.mkdtemp(prefix="promptbranch-upload-"))
    paths: list[Path] = []
    used_names: set[str] = set()
    for index, upload in enumerate(files, start=1):
        name = _unique_temp_upload_name(
            upload.filename,
            used_names,
            default=default_filename if index == 1 else f"attachment-{index}.bin",
        )
        temp_path = temp_dir / name
        temp_path.write_bytes(await upload.read())
        paths.append(temp_path)
    return temp_dir, paths


async def _persist_upload_to_named_temp_path(file: UploadFile, *, default_filename: str = "attachment.bin") -> tuple[Path, Path]:
    temp_dir, paths = await _persist_uploads_to_named_temp_paths([file], default_filename=default_filename)
    return temp_dir, paths[0]


def _cleanup_temp_uploads(temp_paths: list[Path], temp_dir: Optional[Path]) -> None:
    for temp_path in temp_paths:
        temp_path.unlink(missing_ok=True)
    if temp_dir is not None:
        temp_dir.rmdir()


def _cleanup_temp_upload(temp_path: Optional[Path], temp_dir: Optional[Path]) -> None:
    _cleanup_temp_uploads([temp_path] if temp_path is not None else [], temp_dir)


def _env_flag(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class LoginCheckRequest(BaseModel):
    keep_open: bool = False


class AskResponse(BaseModel):
    ok: bool = True
    answer: object = None
    conversation_url: Optional[str] = None
    submit_evidence: Optional[dict] = None
    status: Optional[str] = None
    error: Optional[str] = None
    error_type: Optional[str] = None
    timeout_layer: Optional[str] = None
    partial_result: bool = False
    response_timeout_ms: Optional[int] = None
    debug_artifacts: Optional[list[str]] = None
    backend_answer_diagnostics: Optional[dict] = None
    ask_phase_timings: Optional[dict] = None
    service_timeout_seconds: Optional[float] = None
    service_internal_timeout_seconds: Optional[float] = None
    progress_status: Optional[str] = None
    progress_updated_at_monotonic: Optional[float] = None
    submit_method: Optional[str] = None
    prefer_button_submit: Optional[bool] = None
    submit_button_visible: Optional[bool] = None
    submit_button_enabled: Optional[bool] = None
    submit_prepare_request_observed: Optional[bool] = None
    submit_prepare_response_observed: Optional[bool] = None
    submit_message_request_observed: Optional[bool] = None
    submit_backend_commit_confirmed: Optional[bool] = None
    post_submit_user_turn_visibility_status: Optional[str] = None
    submit_dom_delta_status: Optional[str] = None
    answer_text: Optional[str] = None
    answer_text_length: Optional[int] = None


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
    project_name: Optional[str] = None
    profile_lock_wait_seconds: Optional[float] = None


class ProjectSourceRemoveRequest(BaseModel):
    source_name: str = Field(..., min_length=1)
    exact: bool = False
    keep_open: bool = False
    project_url: Optional[str] = None
    profile_lock_wait_seconds: Optional[float] = None


class ChatGetRequest(BaseModel):
    conversation_url: str = Field(..., min_length=1)
    keep_open: bool = False
    project_url: Optional[str] = None


class ChatArtifactDownloadRequest(BaseModel):
    conversation_url: str = Field(..., min_length=1)
    artifact_url: Optional[str] = None
    filename: str = Field(..., min_length=1)
    target_path: str = Field(..., min_length=1)
    timeout_seconds: float = 120.0
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
    profile: str = "browser"
    path: str = "."
    package_zip: Optional[str] = None


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
            clear_singleton_locks=_env_flag("CHATGPT_CLEAR_PROFILE_SINGLETON_LOCKS", False),
            profile_lock_wait_seconds=float(os.getenv("PROMPTBRANCH_BROWSER_PROFILE_LOCK_WAIT_SECONDS", os.getenv("CHATGPT_BROWSER_PROFILE_LOCK_WAIT_SECONDS", "600.0"))),
            profile_stale_lock_seconds=float(os.getenv("PROMPTBRANCH_BROWSER_PROFILE_STALE_LOCK_SECONDS", os.getenv("CHATGPT_BROWSER_PROFILE_STALE_LOCK_SECONDS", "300.0"))),
            slow_mo_ms=int(os.getenv("CHATGPT_SLOW_MO_MS", "0")),
            debug=_env_flag("CHATGPT_DEBUG_BROWSER", _env_flag("CHATGPT_DEBUG", False)),
            debug_artifact_dir=os.getenv("CHATGPT_DEBUG_ARTIFACT_DIR", "debug_artifacts"),
            dom_diagnostic_mode=os.getenv("CHATGPT_DOM_DIAGNOSTIC_MODE", "light"),
            pause_before_fill=_env_flag("CHATGPT_PAUSE_BEFORE_FILL", False),
            pause_after_fill=_env_flag("CHATGPT_PAUSE_AFTER_FILL", False),
            pause_before_submit=_env_flag("CHATGPT_PAUSE_BEFORE_SUBMIT", False),
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
    if isinstance(exc, BrowserProfileBusyError):
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail=exc.to_payload()) from exc
    if isinstance(exc, BrowserContextUnavailableError):
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
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




@protected.get("/browser/status", dependencies=[Depends(require_service_token)])
async def browser_status(project_url: Optional[str] = None) -> dict:
    return _service_for(project_url).browser_status()

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
    service_timeout_seconds: Optional[float] = Form(default=None),
    prefer_button_submit: bool = Form(False),
    project_url: Optional[str] = Form(default=None),
    conversation_url: Optional[str] = Form(default=None),
    file: Optional[UploadFile] = File(default=None),
    attachments: Optional[list[UploadFile]] = File(default=None),
) -> AskResponse:
    temp_paths: list[Path] = []
    temp_dir: Optional[Path] = None
    try:
        upload_files: list[UploadFile] = []
        if file is not None:
            upload_files.append(file)
        upload_files.extend(attachments or [])
        if upload_files:
            temp_dir, temp_paths = await _persist_uploads_to_named_temp_paths(upload_files)

        ask_kwargs = {
            "prompt": prompt,
            "conversation_url": conversation_url,
            "expect_json": expect_json,
            "keep_open": keep_open,
            "retries": retries,
        }
        if prefer_button_submit:
            ask_kwargs["prefer_button_submit"] = True
        if service_timeout_seconds is not None:
            ask_kwargs["service_timeout_seconds"] = service_timeout_seconds
        if len(temp_paths) == 1:
            ask_kwargs["file_path"] = str(temp_paths[0])
        elif temp_paths:
            ask_kwargs["attachment_paths"] = [str(path) for path in temp_paths]

        service = _service_for(project_url)
        if service_timeout_seconds is not None:
            try:
                outer_timeout = max(1.0, float(service_timeout_seconds))
            except (TypeError, ValueError):
                outer_timeout = 0.0
        else:
            outer_timeout = 0.0
        if outer_timeout > 0:
            # Keep the HTTP handler inside the client contract even if the
            # browser operation wedges in a slow DOM/backend probe.  The browser
            # client still owns richer submit/answer timeout evidence when it
            # returns normally; this endpoint guard is the final fail-closed
            # boundary that prevents service_client_read_timeout.
            internal_timeout = max(1.0, outer_timeout - 8.0)
            try:
                result = await asyncio.wait_for(service.ask_question_result(**ask_kwargs), timeout=internal_timeout)
            except asyncio.TimeoutError:
                progress = get_latest_ask_progress()
                submit_evidence = progress.get("submit_evidence") if isinstance(progress.get("submit_evidence"), dict) else None
                ask_phase_timings = progress.get("ask_phase_timings") if isinstance(progress.get("ask_phase_timings"), dict) else None
                status = "service_internal_deadline_timeout"
                error = "browser service internal deadline reached before client timeout"
                timeout_layer = "service"
                if submit_evidence and submit_evidence.get("submit_backend_confirmed_but_user_turn_not_visible"):
                    status = "submit_confirmed_backend_only_ui_not_hydrated"
                    error = "submit was backend-confirmed but the submitted user turn was not visible before the service internal deadline"
                    timeout_layer = "submit_visibility"
                result = {
                    "ok": False,
                    "action": "ask",
                    "status": status,
                    "error": error,
                    "error_type": status if status != "service_internal_deadline_timeout" else "ServiceInternalDeadlineTimeout",
                    "timeout_layer": timeout_layer,
                    "partial_result": True,
                    "service_timeout_seconds": outer_timeout,
                    "service_internal_timeout_seconds": internal_timeout,
                    "operator_action": "inspect preserved submit evidence before retrying",
                    "conversation_url": progress.get("conversation_url"),
                    "submit_evidence": submit_evidence,
                    "ask_phase_timings": ask_phase_timings,
                    "progress_status": progress.get("status"),
                    "progress_updated_at_monotonic": progress.get("updated_at_monotonic"),
                }
        else:
            result = await service.ask_question_result(**ask_kwargs)
        return AskResponse(
            ok=bool(result.get("ok", True)) if isinstance(result, dict) else True,
            answer=result.get("answer") if isinstance(result, dict) else None,
            conversation_url=result.get("conversation_url") if isinstance(result, dict) else None,
            submit_evidence=result.get("submit_evidence") if isinstance(result, dict) else None,
            status=result.get("status") if isinstance(result, dict) else None,
            error=result.get("error") if isinstance(result, dict) else None,
            error_type=result.get("error_type") if isinstance(result, dict) else None,
            timeout_layer=result.get("timeout_layer") if isinstance(result, dict) else None,
            partial_result=bool(result.get("partial_result", False)) if isinstance(result, dict) else False,
            response_timeout_ms=result.get("response_timeout_ms") if isinstance(result, dict) else None,
            debug_artifacts=result.get("debug_artifacts") if isinstance(result, dict) and isinstance(result.get("debug_artifacts"), list) else None,
            backend_answer_diagnostics=result.get("backend_answer_diagnostics") if isinstance(result, dict) and isinstance(result.get("backend_answer_diagnostics"), dict) else None,
            ask_phase_timings=result.get("ask_phase_timings") if isinstance(result, dict) and isinstance(result.get("ask_phase_timings"), dict) else None,
            service_timeout_seconds=result.get("service_timeout_seconds") if isinstance(result, dict) else None,
            service_internal_timeout_seconds=result.get("service_internal_timeout_seconds") if isinstance(result, dict) else None,
            progress_status=result.get("progress_status") if isinstance(result, dict) else None,
            progress_updated_at_monotonic=result.get("progress_updated_at_monotonic") if isinstance(result, dict) else None,
            submit_method=result.get("submit_method") if isinstance(result, dict) else None,
            prefer_button_submit=result.get("prefer_button_submit") if isinstance(result, dict) else None,
            submit_button_visible=result.get("submit_button_visible") if isinstance(result, dict) else None,
            submit_button_enabled=result.get("submit_button_enabled") if isinstance(result, dict) else None,
            submit_prepare_request_observed=result.get("submit_prepare_request_observed") if isinstance(result, dict) else None,
            submit_prepare_response_observed=result.get("submit_prepare_response_observed") if isinstance(result, dict) else None,
            submit_message_request_observed=result.get("submit_message_request_observed") if isinstance(result, dict) else None,
            submit_backend_commit_confirmed=result.get("submit_backend_commit_confirmed") if isinstance(result, dict) else None,
            post_submit_user_turn_visibility_status=result.get("post_submit_user_turn_visibility_status") if isinstance(result, dict) else None,
            submit_dom_delta_status=result.get("submit_dom_delta_status") if isinstance(result, dict) else None,
            answer_text=result.get("answer_text") if isinstance(result, dict) else None,
            answer_text_length=result.get("answer_text_length") if isinstance(result, dict) else None,
        )
    except Exception as exc:  # pragma: no cover - exercised by live runs
        _raise_http_error(exc)
    finally:
        _cleanup_temp_uploads(temp_paths, temp_dir)


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


@protected.get("/debug/rate-limit", dependencies=[Depends(require_service_token)])
async def debug_rate_limit(
    keep_open: bool = False,
    project_url: Optional[str] = None,
    probe_backend: bool = False,
    wait_ms: int = 750,
) -> dict:
    try:
        return await _service_for(project_url).debug_rate_limit(
            keep_open=keep_open,
            probe_backend=probe_backend,
            wait_ms=wait_ms,
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


@protected.post("/chats/download-artifact", dependencies=[Depends(require_service_token)])
async def download_chat_artifact(payload: ChatArtifactDownloadRequest) -> dict:
    try:
        return await _service_for(payload.project_url).download_chat_artifact(
            conversation_url=payload.conversation_url,
            artifact_url=payload.artifact_url,
            filename=payload.filename,
            target_path=payload.target_path,
            timeout_seconds=payload.timeout_seconds,
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
    # v0.1.78.2 safety repair: project deletion is frozen at the HTTP
    # boundary.  The service must not open a browser context or click any
    # ChatGPT deletion affordance from this endpoint.
    return project_delete_disabled_result(
        project_url=payload.project_url,
        project_name=payload.project_name,
        blocked_at_layer="container_api",
    )


@protected.post("/project-sources", dependencies=[Depends(require_service_token)])
async def add_project_source(
    source_kind: str = Form(..., alias="type"),
    value: Optional[str] = Form(default=None),
    display_name: Optional[str] = Form(default=None, alias="name"),
    keep_open: bool = Form(False),
    overwrite_existing: bool = Form(True),
    profile_lock_wait_seconds: Optional[float] = Form(default=None),
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

        call_kwargs = {
            "source_kind": source_kind,
            "value": value,
            "file_path": (str(temp_path) if temp_path is not None else None),
            "display_name": display_name,
            "keep_open": keep_open,
            "overwrite_existing": overwrite_existing,
        }
        if profile_lock_wait_seconds is not None:
            call_kwargs["profile_lock_wait_seconds"] = profile_lock_wait_seconds
        return await _service_for(project_url).add_project_source(**call_kwargs)
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
            profile_lock_wait_seconds=payload.profile_lock_wait_seconds,
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
