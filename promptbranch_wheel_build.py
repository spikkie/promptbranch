from __future__ import annotations

import argparse
import importlib
from importlib import metadata
import json
import contextlib
import io
import os
from pathlib import Path
import re
import subprocess
import sys
import tomllib
from typing import Any

_BUILD_REQ_NAME_RE = re.compile(r"^\s*([A-Za-z0-9_.-]+)")


def _requirement_name(requirement: str) -> str:
    match = _BUILD_REQ_NAME_RE.match(requirement)
    return match.group(1) if match else requirement.strip()


def inspect_build_backend(root: Path) -> dict[str, Any]:
    pyproject_path = root / "pyproject.toml"
    if not pyproject_path.is_file():
        return {
            "ok": False,
            "status": "build_backend_config_missing",
            "root": str(root),
            "pyproject": str(pyproject_path),
        }
    data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    build_system = data.get("build-system") or {}
    backend = str(build_system.get("build-backend") or "").strip()
    requires = [str(item).strip() for item in build_system.get("requires") or []]
    if not backend:
        return {
            "ok": False,
            "status": "build_backend_config_missing",
            "root": str(root),
            "pyproject": str(pyproject_path),
            "build_backend": backend,
            "build_requires": requires,
        }

    missing_requirements: list[str] = []
    requirement_resolution: dict[str, str] = {}
    installed_distributions: dict[str, str] = {}
    vendor_path: str | None = None
    for requirement in requires:
        name = _requirement_name(requirement)
        module_name = name.replace("-", "_")
        try:
            installed_distributions[name] = metadata.version(name)
            importlib.import_module(module_name)
            requirement_resolution[name] = "installed_distribution"
            continue
        except (metadata.PackageNotFoundError, ImportError, ModuleNotFoundError):
            pass
        if name == "wheel":
            try:
                setuptools_module = importlib.import_module("setuptools")
                candidate = Path(setuptools_module.__file__).resolve().parent / "_vendor"
                if (candidate / "wheel" / "wheelfile.py").is_file():
                    vendor_path = str(candidate)
                    requirement_resolution[name] = "setuptools_vendored_wheel"
                    continue
            except Exception:
                pass
        missing_requirements.append(name)
        requirement_resolution[name] = "missing"

    backend_error: str | None = None
    try:
        importlib.import_module(backend)
    except Exception as exc:
        backend_error = f"{type(exc).__name__}: {exc}"

    ok = not missing_requirements and backend_error is None
    return {
        "ok": ok,
        "status": "build_backend_available" if ok else "build_backend_unavailable",
        "root": str(root),
        "pyproject": str(pyproject_path),
        "build_backend": backend,
        "build_requires": requires,
        "installed_distributions": installed_distributions,
        "requirement_resolution": requirement_resolution,
        "missing_requirements": missing_requirements,
        "backend_import_error": backend_error,
        "setuptools_vendor_path": vendor_path,
    }


def build_wheel(
    root: Path,
    wheel_dir: Path,
    *,
    python_executable: str = sys.executable,
) -> dict[str, Any]:
    root = root.resolve()
    wheel_dir = wheel_dir.resolve()
    preflight = inspect_build_backend(root)
    if not preflight.get("ok"):
        return {
            "ok": False,
            "status": "build_backend_unavailable",
            "root": str(root),
            "wheel_dir": str(wheel_dir),
            "python": python_executable,
            "preflight": preflight,
            "command": None,
            "returncode": None,
        }

    wheel_dir.mkdir(parents=True, exist_ok=True)
    backend_name = str(preflight["build_backend"])
    try:
        backend = importlib.import_module(backend_name)
        build_hook = getattr(backend, "build_wheel")
    except Exception as exc:
        return {
            "ok": False,
            "status": "build_backend_unavailable",
            "root": str(root),
            "wheel_dir": str(wheel_dir),
            "python": python_executable,
            "preflight": preflight,
            "backend_error": f"{type(exc).__name__}: {exc}",
            "returncode": None,
        }

    previous_cwd = Path.cwd()
    vendor_path = preflight.get("setuptools_vendor_path")
    vendor_inserted = False
    if vendor_path and vendor_path not in sys.path:
        sys.path.insert(0, str(vendor_path))
        vendor_inserted = True
    previous_no_index = os.environ.get("PIP_NO_INDEX")
    previous_disable_check = os.environ.get("PIP_DISABLE_PIP_VERSION_CHECK")
    backend_stdout_buffer = io.StringIO()
    backend_stderr_buffer = io.StringIO()
    try:
        os.environ["PIP_NO_INDEX"] = "1"
        os.environ["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
        os.chdir(root)
        with contextlib.redirect_stdout(backend_stdout_buffer), contextlib.redirect_stderr(backend_stderr_buffer):
            wheel_name = str(build_hook(str(wheel_dir)))
        backend_error = None
    except Exception as exc:
        wheel_name = ""
        backend_error = f"{type(exc).__name__}: {exc}"
    finally:
        os.chdir(previous_cwd)
        if previous_no_index is None:
            os.environ.pop("PIP_NO_INDEX", None)
        else:
            os.environ["PIP_NO_INDEX"] = previous_no_index
        if previous_disable_check is None:
            os.environ.pop("PIP_DISABLE_PIP_VERSION_CHECK", None)
        else:
            os.environ["PIP_DISABLE_PIP_VERSION_CHECK"] = previous_disable_check
        if vendor_inserted:
            try:
                sys.path.remove(str(vendor_path))
            except ValueError:
                pass

    wheels = sorted(path.name for path in wheel_dir.glob("*.whl"))
    ok = backend_error is None and wheel_name in wheels and len(wheels) == 1
    return {
        "ok": ok,
        "status": "wheel_built" if ok else "wheel_build_failed",
        "root": str(root),
        "wheel_dir": str(wheel_dir),
        "python": python_executable,
        "preflight": preflight,
        "backend_hook": f"{backend_name}.build_wheel",
        "wheel_name": wheel_name or None,
        "backend_error": backend_error,
        "backend_stdout": backend_stdout_buffer.getvalue(),
        "backend_stderr": backend_stderr_buffer.getvalue(),
        "returncode": 0 if ok else 1,
        "wheels": wheels,
        "network_policy": "offline_no_index",
        "build_isolation": False,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a Promptbranch wheel with the declared backend in an offline deterministic environment.")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--wheel-dir", type=Path, required=True)
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    payload = build_wheel(args.root, args.wheel_dir, python_executable=args.python)
    if args.json:
        print(json.dumps(payload, sort_keys=True))
    else:
        print(payload["status"])
        if not payload["ok"]:
            print(json.dumps(payload, indent=2, sort_keys=True), file=sys.stderr)
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
