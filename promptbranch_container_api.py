from __future__ import annotations

import logging
import os
import secrets
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, FastAPI, File, Form, Header, HTTPException, UploadFile, status
from pydantic import BaseModel, Field

from promptbranch_automation import ChatGPTAutomationService, ChatGPTAutomationSettings
from promptbranch_browser_auth.exceptions import (
    AuthenticationError,
    BotChallengeError,
    ManualLoginRequiredError,
    ResponseTimeoutError,
    UnsupportedOperationError,
)

logger = logging.getLogger(__name__)


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


SERVICE_VERSION = "0.0.81"
_SERVICE_TOKEN = os.getenv("CHATGPT_SERVICE_TOKEN") or os.getenv("CHATGPT_API_TOKEN")
_DEFAULT_PROJECT_URL = os.getenv("CHATGPT_PROJECT_URL", "https://chatgpt.com/")


def _build_service(*, project_url_override: Optional[str] = None) -> ChatGPTAutomationService:
    return ChatGPTAutomationService(
        ChatGPTAutomationSettings(
            project_url=project_url_override or _DEFAULT_PROJECT_URL,
            email=os.getenv("CHATGPT_EMAIL") or os.getenv("EMAIL"),
            password=os.getenv("CHATGPT_PASSWORD") or os.getenv("PASSWORD"),
            profile_dir=os.getenv("CHATGPT_PROFILE_DIR", "/app/profile"),
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
app = FastAPI(
    title="ChatGPT Docker Service",
    version=SERVICE_VERSION,
    description="Reusable Docker-first service for browser-driven ChatGPT automation.",
)
protected = APIRouter(prefix="/v1")


def _service_for(project_url: Optional[str]) -> ChatGPTAutomationService:
    if not project_url or project_url == service.settings.project_url:
        return service
    return _build_service(project_url_override=project_url)


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
    try:
        if file is not None:
            suffix = Path(file.filename or "attachment.bin").suffix
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as handle:
                handle.write(await file.read())
                temp_path = Path(handle.name)

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
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


@protected.get("/projects", dependencies=[Depends(require_service_token)])
async def list_projects(keep_open: bool = False, project_url: Optional[str] = None) -> dict:
    try:
        return await _service_for(project_url).list_projects(keep_open=keep_open)
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
    try:
        if source_kind == "file":
            if file is None:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="file is required when type=file")
            suffix = Path(file.filename or "attachment.bin").suffix
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as handle:
                handle.write(await file.read())
                temp_path = Path(handle.name)
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
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


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
