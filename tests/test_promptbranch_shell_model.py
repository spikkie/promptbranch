from __future__ import annotations

import json

from promptbranch_shell_model import (
    ArtifactRef,
    AssistantAnswer,
    MutationStatus,
    ToolRisk,
    Turn,
    UserMessage,
    mutation_result,
    required_prechecks_for_action,
    risk_for_action,
)
from promptbranch_state import ConversationStateStore


def test_shell_turn_allows_zero_or_more_answers() -> None:
    pending = Turn(index=0, user_message=UserMessage(id="u1", text="hello"))
    answered = Turn(
        index=1,
        user_message=UserMessage(id="u2", text="continue"),
        assistant_answers=(
            AssistantAnswer(id="a1", text="first answer"),
            AssistantAnswer(id="a2", text="regenerated answer"),
        ),
    )

    assert pending.answered is False
    assert answered.answered is True
    assert len(answered.assistant_answers) == 2


def test_mutation_result_verified_contract_is_json_ready() -> None:
    result = mutation_result(
        action="src_add",
        requested={"file": "repo.zip"},
        status=MutationStatus.VERIFIED,
        risk=ToolRisk.WRITE,
        triggered=True,
        committed=True,
        verified=True,
        state_updated=True,
        artifact=ArtifactRef(source_ref="repo.zip", source_version="v0.0.129"),
    )

    payload = result.to_dict()
    assert payload["ok"] is True
    assert payload["status"] == "verified"
    assert payload["risk"] == "write"
    assert payload["artifact"]["source_ref"] == "repo.zip"
    json.dumps(payload)


def test_risk_policy_requires_stronger_prechecks_for_destructive_actions() -> None:
    assert risk_for_action("ws_current") == ToolRisk.READ
    assert required_prechecks_for_action("ws_current") == ()

    assert risk_for_action("src_rm") == ToolRisk.DESTRUCTIVE
    assert "snapshot_before_mutation" in required_prechecks_for_action("src_rm")
    assert "collateral_change_detection" in required_prechecks_for_action("src_rm")


def test_state_store_tracks_workspace_task_and_artifact_independently(tmp_path) -> None:
    store = ConversationStateStore(str(tmp_path))
    project_url = "https://chatgpt.com/g/g-p-demo-my-project/project"
    conversation_url = "https://chatgpt.com/g/g-p-demo-my-project/c/12345678-1234-1234-1234-1234567890ab"

    store.remember_project(project_url, project_name="my-project")
    store.remember(project_url, conversation_url, project_name="my-project")
    store.remember_artifact(
        project_url=project_url,
        artifact_ref="chatgpt_claudecode_workflow_v0.0.129.zip",
        artifact_version="v0.0.129",
        source_ref="chatgpt_claudecode_workflow_v0.0.129.zip",
        source_version="v0.0.129",
    )

    snapshot = store.snapshot(project_url)
    assert snapshot["schema_version"] == 2
    assert snapshot["workspace"]["project_home_url"] == project_url
    assert snapshot["task"]["conversation_id"] == "12345678-1234-1234-1234-1234567890ab"
    assert snapshot["artifact"]["artifact_version"] == "v0.0.129"
    assert snapshot["artifact"]["source_ref"] == "chatgpt_claudecode_workflow_v0.0.129.zip"

    on_disk = json.loads((tmp_path / ".promptbranch_state.json").read_text(encoding="utf-8"))
    assert on_disk["schema_version"] == 2
    assert on_disk["current"]["artifact_ref"] == "chatgpt_claudecode_workflow_v0.0.129.zip"
