#!/usr/bin/env python3
from __future__ import annotations

import argparse
import fnmatch
import os
import stat
import zipfile
from pathlib import Path

FIXED_ZIP_TIMESTAMP = (2020, 1, 1, 0, 0, 0)


def _patterns(repo: Path) -> list[str]:
    values = [
        ".git/",
        "__pycache__/",
        "*.pyc",
        "*.pyo",
        ".pytest_cache/",
        ".mypy_cache/",
        ".ruff_cache/",
        "node_modules/",
        "dist/",
        "build/",
        "coverage/",
        ".venv/",
        "venv/",
        "env/",
        ".env",
        ".env.*",
        "*.zip",
        "*.tar.gz",
        "*.log",
        ".pb_profile/",
        "profile/",
        "debug_artifacts/",
        ".DS_Store",
    ]
    ignore = repo / ".not_to_zip"
    if ignore.is_file():
        for raw in ignore.read_text(encoding="utf-8", errors="replace").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or line.startswith("!"):
                continue
            if line.startswith("./"):
                line = line[2:]
            values.append(line)
    return values


def _match(rel: str, pattern: str, *, is_dir: bool) -> bool:
    rel = rel.strip("/")
    pattern = pattern.strip()
    if not pattern:
        return False
    directory_only = pattern.endswith("/")
    pattern = pattern.strip("/")
    if directory_only and not is_dir and not rel.startswith(pattern + "/"):
        return False
    candidates = {rel, Path(rel).name}
    if is_dir:
        candidates.add(rel + "/")
    return (
        any(fnmatch.fnmatch(candidate, pattern) for candidate in candidates)
        or fnmatch.fnmatch(rel, pattern)
        or rel.startswith(pattern + "/")
    )


def _excluded(repo: Path, path: Path, patterns: list[str], output: Path) -> bool:
    try:
        rel = path.relative_to(repo).as_posix()
    except ValueError:
        return path == output
    if path == output:
        return True
    if any(part in {".git", "__pycache__", ".pytest_cache"} for part in rel.split("/")):
        return True
    if path.suffix in {".pyc", ".pyo"}:
        return True
    parts = rel.split("/")
    for index in range(1, len(parts) + 1):
        candidate = "/".join(parts[:index])
        candidate_path = repo / candidate
        is_dir = index < len(parts) or candidate_path.is_dir()
        if any(_match(candidate, pattern, is_dir=is_dir) for pattern in patterns):
            return True
    return False


def _files(repo: Path, output: Path) -> list[Path]:
    patterns = _patterns(repo)
    files: list[Path] = []
    for current, dirs, filenames in os.walk(repo):
        current_path = Path(current)
        dirs[:] = [name for name in sorted(dirs) if not _excluded(repo, current_path / name, patterns, output)]
        for filename in sorted(filenames):
            path = current_path / filename
            if not _excluded(repo, path, patterns, output):
                files.append(path)
    return sorted(files, key=lambda item: item.relative_to(repo).as_posix())


def build(repo: Path, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    files = _files(repo, output)
    if output.exists():
        output.unlink()
    # ZIP_STORED is intentional: it removes zlib implementation/version variance
    # from the canonical release identity while keeping ordering and metadata fixed.
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_STORED, strict_timestamps=True) as archive:
        archive.comment = b""
        for path in files:
            rel = path.relative_to(repo).as_posix()
            info = zipfile.ZipInfo(rel, date_time=FIXED_ZIP_TIMESTAMP)
            info.create_system = 3
            info.create_version = 20
            info.extract_version = 20
            info.flag_bits = 0
            info.internal_attr = 0
            mode = stat.S_IFREG | (0o755 if (path.stat().st_mode & 0o111) else 0o644)
            info.external_attr = mode << 16
            info.compress_type = zipfile.ZIP_STORED
            info.extra = b""
            info.comment = b""
            archive.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_STORED)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a byte-deterministic Promptbranch release ZIP")
    parser.add_argument("--repo", default=".")
    parser.add_argument("--output")
    args = parser.parse_args()
    repo = Path(args.repo).resolve()
    if args.output:
        output_arg = Path(args.output).expanduser()
    else:
        version = (repo / "VERSION").read_text(encoding="utf-8").strip()
        if not version.startswith("v"):
            raise SystemExit(f"VERSION must be v-prefixed: {version!r}")
        output_arg = Path(f"{repo.name}_{version}.zip")
    output = output_arg.resolve() if output_arg.is_absolute() else (repo / output_arg).resolve()
    build(repo, output)
    print(f"created {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
