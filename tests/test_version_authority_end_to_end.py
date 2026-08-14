from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def _tree_digest(root: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        if any(part in {".git", ".pb_profile", "__pycache__", ".pytest_cache", "build", "dist"} or part.endswith(".egg-info") for part in rel.parts):
            continue
        if path.suffix in {".pyc", ".pyo", ".zip"}:
            continue
        result[rel.as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def test_changing_only_version_updates_core_derived_version_surfaces(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    shutil.copytree(
        ROOT,
        repo,
        ignore=shutil.ignore_patterns(".git", ".pb_profile", "__pycache__", ".pytest_cache", "*.pyc", "*.zip", "build", "dist", "*.egg-info"),
    )
    before = _tree_digest(repo)
    sentinel_tag = "v9.8.7.654321"
    sentinel = sentinel_tag.removeprefix("v")
    (repo / "VERSION").write_text(sentinel_tag + "\n", encoding="utf-8")
    after = _tree_digest(repo)
    changed = sorted(path for path in set(before) | set(after) if before.get(path) != after.get(path))
    assert changed == ["VERSION"]

    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo)
    probe = subprocess.run(
        [
            sys.executable,
            "-c",
            "import json,promptbranch_cli,promptbranch_version; "
            "print(json.dumps({'package':promptbranch_version.PACKAGE_VERSION,'tag':promptbranch_version.VERSION_TAG,'cli':promptbranch_cli.CLI_VERSION}))",
        ],
        cwd=repo,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert probe.returncode == 0, probe.stderr
    payload = json.loads(probe.stdout.strip().splitlines()[-1])
    assert payload == {"package": sentinel, "tag": sentinel_tag, "cli": sentinel}

    docker_contract = subprocess.run(
        [
            sys.executable,
            "-m",
            "promptbranch_docker_build_contract",
            "--root",
            str(repo),
            "--expected-version",
            sentinel_tag,
            "--json",
        ],
        cwd=repo,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert docker_contract.returncode == 0, docker_contract.stderr
    docker_payload = json.loads(docker_contract.stdout.strip().splitlines()[-1])
    assert docker_payload["ok"] is True
    assert docker_payload["version_file"] == sentinel
    assert docker_payload["package_version"] == sentinel
    assert all(docker_payload["checks"].values())

    wheel_dir = tmp_path / "wheel"
    wheel_dir.mkdir()
    build = subprocess.run(
        [
            sys.executable,
            "-m",
            "promptbranch_wheel_build",
            "--root",
            str(repo),
            "--wheel-dir",
            str(wheel_dir),
            "--json",
        ],
        cwd=tmp_path,
        env={**env, "PIP_NO_INDEX": "1", "PIP_INDEX_URL": "http://127.0.0.1:9/unreachable"},
        text=True,
        capture_output=True,
        check=False,
    )
    assert build.returncode == 0, build.stdout + "\n" + build.stderr
    build_payload = json.loads(build.stdout)
    assert build_payload["ok"] is True
    assert build_payload["status"] == "wheel_built"
    assert build_payload["network_policy"] == "offline_no_index"
    assert build_payload["build_isolation"] is False
    assert build_payload["backend_hook"] == "setuptools.build_meta.build_wheel"
    assert build_payload["backend_error"] is None
    wheels = list(wheel_dir.glob("promptbranch-*.whl"))
    assert len(wheels) == 1
    with zipfile.ZipFile(wheels[0]) as archive:
        metadata_names = [name for name in archive.namelist() if name.endswith(".dist-info/METADATA")]
        assert len(metadata_names) == 1
        metadata = archive.read(metadata_names[0]).decode("utf-8")
    assert f"Version: {sentinel}\n" in metadata


def test_wheel_build_backend_preflight_fails_with_promptbranch_status(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "pyproject.toml").write_text(
        '[build-system]\nrequires = ["definitely-missing-promptbranch-build-backend"]\nbuild-backend = "definitely_missing_promptbranch_backend"\n',
        encoding="utf-8",
    )
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "promptbranch_wheel_build",
            "--root",
            str(repo),
            "--wheel-dir",
            str(tmp_path / "wheel"),
            "--json",
        ],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["status"] == "build_backend_unavailable"
    assert payload["preflight"]["status"] == "build_backend_unavailable"


def test_release_validation_tests_do_not_invoke_raw_pip_wheel() -> None:
    import ast

    offenders: list[str] = []
    for path in (ROOT / "tests").glob("test_*.py"):
        if path == Path(__file__).resolve():
            source = path.read_text(encoding="utf-8")
        else:
            source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, (ast.List, ast.Tuple)):
                continue
            values = [item.value for item in node.elts if isinstance(item, ast.Constant) and isinstance(item.value, str)]
            if "-m" in values and "pip" in values and "wheel" in values:
                offenders.append(path.relative_to(ROOT).as_posix())
                break
    assert offenders == []
