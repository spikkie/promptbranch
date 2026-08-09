from __future__ import annotations

import json
import os
import subprocess
import urllib.request
from pathlib import Path

import pytest


def _json_url(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=10) as response:
        payload = json.loads(response.read().decode("utf-8"))
    assert isinstance(payload, dict)
    return payload


def _docker(*args: str) -> str:
    completed = subprocess.run(
        ["docker", *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=60,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    return completed.stdout.strip()


@pytest.mark.skipif(
    os.environ.get("PROMPTBRANCH_RUN_DOCKER_INTEGRATION") != "1",
    reason="executed only by the canonical exact-candidate state-machine test transition",
)
def test_live_candidate_runtime_is_isolated_identity_bound_and_preserves_accepted_service() -> None:
    version = Path("VERSION").read_text(encoding="utf-8").strip().removeprefix("v")
    artifact = Path(os.environ["PROMPTBRANCH_RELEASE_STATE_MACHINE_ARTIFACT"])
    artifact_sha = subprocess.check_output(["sha256sum", str(artifact)], text=True).split()[0]
    attempt_id = os.environ["PROMPTBRANCH_RELEASE_STATE_MACHINE_ATTEMPT_ID"]
    project = os.environ["PROMPTBRANCH_CANDIDATE_COMPOSE_PROJECT"]
    image = os.environ["PROMPTBRANCH_CANDIDATE_SERVICE_IMAGE"]
    port = int(os.environ["PROMPTBRANCH_CANDIDATE_SERVICE_PORT"])
    container_id = os.environ["PROMPTBRANCH_CANDIDATE_CONTAINER_ID"]
    service_base = os.environ["PROMPTBRANCH_CANDIDATE_SERVICE_BASE_URL"]
    accepted_before = json.loads(os.environ.get("PROMPTBRANCH_ACCEPTED_RUNTIME_BEFORE_JSON", "{}"))

    assert project
    assert project != "chatgpt_claudecode_workflow"
    assert image.startswith("promptbranch-candidate:")
    assert port != 8000
    assert container_id

    candidate_health = _json_url(service_base + "/healthz")
    assert candidate_health["ok"] is True
    assert candidate_health["version"] == version

    image_labels = json.loads(_docker("image", "inspect", image, "--format", "{{json .Config.Labels}}"))
    assert image_labels["promptbranch.version"] == version
    assert image_labels["promptbranch.artifact_sha256"] == artifact_sha
    assert image_labels["promptbranch.release_attempt_id"] == attempt_id
    assert image_labels["promptbranch.source_fingerprint"]

    container_labels = json.loads(_docker("inspect", container_id, "--format", "{{json .Config.Labels}}"))
    assert container_labels["com.docker.compose.project"] == project

    if accepted_before.get("present"):
        accepted_health = _json_url("http://127.0.0.1:8000/healthz")
        before_container = str(accepted_before.get("container", {}).get("container_id") or "")
        before_version = str(accepted_before.get("health", {}).get("version") or "")
        accepted_ids = _docker("ps", "--filter", "publish=8000", "--format", "{{.ID}}").splitlines()
        assert len(accepted_ids) == 1
        assert accepted_ids[0] == before_container
        assert accepted_health["version"] == before_version
        assert accepted_health["version"] != version
