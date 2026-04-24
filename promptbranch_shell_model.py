"""Promptbranch Claude-Code-like shell object model.

This module intentionally contains no browser/UI automation.  It defines the
stable local model used by the CLI, state store, future MCP tools, and tests.
The model keeps Workspace, Task, and Artifact as independent scopes and treats
messages/answers as task subresources.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping, Optional

SHELL_STATE_SCHEMA_VERSION = 2


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class ScopeKind(str, Enum):
    WORKSPACE = "workspace"
    TASK = "task"
    ARTIFACT = "artifact"


class ToolRisk(str, Enum):
    READ = "read"
    WRITE = "write"
    DESTRUCTIVE = "destructive"
    EXTERNAL_PROCESS = "external_process"


class MutationStatus(str, Enum):
    VERIFIED = "verified"
    ALREADY_EXISTS = "already_exists"
    ALREADY_ABSENT = "already_absent"
    EXPECTED_SKIP = "expected_skip"
    EXPECTED_UNSUPPORTED = "expected_unsupported"
    TRIGGERED_NOT_VERIFIED = "triggered_not_verified"
    BACKEND_MISMATCH = "backend_mismatch"
    RATE_LIMITED = "rate_limited"
    UI_CHANGED = "ui_changed"
    COLLATERAL_CHANGE_DETECTED = "collateral_change_detected"
    TIMEOUT_UNVERIFIED = "timeout_unverified"


@dataclass(frozen=True)
class WorkspaceRef:
    """Active ChatGPT Project scope."""

    project_home_url: Optional[str] = None
    project_name: Optional[str] = None
    project_slug: Optional[str] = None

    @property
    def selected(self) -> bool:
        return bool(self.project_home_url)


@dataclass(frozen=True)
class TaskRef:
    """Active chat/conversation scope inside a workspace."""

    conversation_url: Optional[str] = None
    conversation_id: Optional[str] = None
    title: Optional[str] = None

    @property
    def selected(self) -> bool:
        return bool(self.conversation_url or self.conversation_id)


@dataclass(frozen=True)
class ArtifactRef:
    """Active repo/source/release artifact scope."""

    artifact_ref: Optional[str] = None
    artifact_version: Optional[str] = None
    source_ref: Optional[str] = None
    source_version: Optional[str] = None

    @property
    def selected(self) -> bool:
        return bool(self.artifact_ref or self.source_ref)


@dataclass(frozen=True)
class UserMessage:
    id: Optional[str]
    text: str
    created_at: Optional[str] = None
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AssistantAnswer:
    id: Optional[str]
    text: str
    status: str = "complete"
    created_at: Optional[str] = None
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Turn:
    index: int
    user_message: UserMessage
    assistant_answers: tuple[AssistantAnswer, ...] = ()
    status: str = "complete"
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @property
    def answered(self) -> bool:
        return bool(self.assistant_answers)


@dataclass(frozen=True)
class PromptbranchShellState:
    """Normalized shell state surfaced by `.pb_profile/.promptbranch_state.json`."""

    schema_version: int
    workspace: WorkspaceRef = field(default_factory=WorkspaceRef)
    task: TaskRef = field(default_factory=TaskRef)
    artifact: ArtifactRef = field(default_factory=ArtifactRef)
    updated_at: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class MutationResult:
    """Structured result contract for all verified write operations."""

    ok: bool
    action: str
    requested: Mapping[str, Any] = field(default_factory=dict)
    triggered: bool = False
    committed: bool = False
    verified: bool = False
    state_updated: bool = False
    status: MutationStatus = MutationStatus.TRIGGERED_NOT_VERIFIED
    risk: ToolRisk = ToolRisk.WRITE
    workspace: Optional[WorkspaceRef] = None
    task: Optional[TaskRef] = None
    artifact: Optional[ArtifactRef] = None
    warnings: tuple[str, ...] = ()
    error: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["status"] = self.status.value
        payload["risk"] = self.risk.value
        return payload


def mutation_result(
    *,
    action: str,
    requested: Optional[Mapping[str, Any]] = None,
    status: MutationStatus | str = MutationStatus.TRIGGERED_NOT_VERIFIED,
    risk: ToolRisk | str = ToolRisk.WRITE,
    triggered: bool = False,
    committed: bool = False,
    verified: bool = False,
    state_updated: bool = False,
    workspace: Optional[WorkspaceRef] = None,
    task: Optional[TaskRef] = None,
    artifact: Optional[ArtifactRef] = None,
    warnings: tuple[str, ...] = (),
    error: Optional[str] = None,
) -> MutationResult:
    status_enum = status if isinstance(status, MutationStatus) else MutationStatus(status)
    risk_enum = risk if isinstance(risk, ToolRisk) else ToolRisk(risk)
    ok = status_enum in {
        MutationStatus.VERIFIED,
        MutationStatus.ALREADY_EXISTS,
        MutationStatus.ALREADY_ABSENT,
        MutationStatus.EXPECTED_SKIP,
    }
    return MutationResult(
        ok=ok,
        action=action,
        requested=requested or {},
        triggered=triggered,
        committed=committed,
        verified=verified,
        state_updated=state_updated,
        status=status_enum,
        risk=risk_enum,
        workspace=workspace,
        task=task,
        artifact=artifact,
        warnings=warnings,
        error=error,
    )


TOOL_RISK_BY_ACTION: dict[str, ToolRisk] = {
    "ws_list": ToolRisk.READ,
    "ws_current": ToolRisk.READ,
    "task_list": ToolRisk.READ,
    "task_current": ToolRisk.READ,
    "task_show": ToolRisk.READ,
    "src_list": ToolRisk.READ,
    "artifact_list": ToolRisk.READ,
    "artifact_current": ToolRisk.READ,
    "debug_dump_state": ToolRisk.READ,
    "ask": ToolRisk.WRITE,
    "ws_use": ToolRisk.WRITE,
    "task_use": ToolRisk.WRITE,
    "task_leave": ToolRisk.WRITE,
    "src_add": ToolRisk.WRITE,
    "src_sync": ToolRisk.WRITE,
    "artifact_release": ToolRisk.WRITE,
    "test_smoke": ToolRisk.EXTERNAL_PROCESS,
    "src_rm": ToolRisk.DESTRUCTIVE,
    "ws_rm": ToolRisk.DESTRUCTIVE,
}


REQUIRED_PRECHECKS_BY_RISK: dict[ToolRisk, tuple[str, ...]] = {
    ToolRisk.READ: (),
    ToolRisk.WRITE: ("workspace_known", "transactional_verification"),
    ToolRisk.EXTERNAL_PROCESS: ("workspace_known", "bounded_command"),
    ToolRisk.DESTRUCTIVE: (
        "workspace_known",
        "snapshot_before_mutation",
        "transactional_verification",
        "collateral_change_detection",
    ),
}


def risk_for_action(action: str) -> ToolRisk:
    return TOOL_RISK_BY_ACTION.get(action, ToolRisk.WRITE)


def required_prechecks_for_action(action: str) -> tuple[str, ...]:
    return REQUIRED_PRECHECKS_BY_RISK[risk_for_action(action)]


def normalize_shell_state_snapshot(snapshot: Mapping[str, Any]) -> PromptbranchShellState:
    workspace = WorkspaceRef(
        project_home_url=_optional_str(snapshot.get("resolved_project_home_url") or snapshot.get("current_project_home_url")),
        project_name=_optional_str(snapshot.get("project_name")),
        project_slug=_optional_str(snapshot.get("project_slug")),
    )
    task = TaskRef(
        conversation_url=_optional_str(snapshot.get("conversation_url") or snapshot.get("current_conversation_url")),
        conversation_id=_optional_str(snapshot.get("conversation_id")),
        title=_optional_str(snapshot.get("conversation_title") or snapshot.get("task_title")),
    )
    artifact = ArtifactRef(
        artifact_ref=_optional_str(snapshot.get("artifact_ref")),
        artifact_version=_optional_str(snapshot.get("artifact_version")),
        source_ref=_optional_str(snapshot.get("source_ref")),
        source_version=_optional_str(snapshot.get("source_version")),
    )
    return PromptbranchShellState(
        schema_version=int(snapshot.get("schema_version") or SHELL_STATE_SCHEMA_VERSION),
        workspace=workspace,
        task=task,
        artifact=artifact,
        updated_at=_optional_str(snapshot.get("updated_at")),
    )


def _optional_str(value: Any) -> Optional[str]:
    return value if isinstance(value, str) and value != "" else None
