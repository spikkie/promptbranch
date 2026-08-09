from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Iterable


SOURCE_PRESERVE_ROOTS: frozenset[str] = frozenset({
    ".git", ".env", ".generated", ".pb_profile", ".pb_profile_local_debug",
    ".pb_profile_local_debug_pools", "profile", "debug_artifacts",
})
SOURCE_TRANSIENT_PARTS: frozenset[str] = frozenset({
    "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    "build", "dist", ".eggs",
})
SOURCE_TRANSIENT_SUFFIXES: frozenset[str] = frozenset({".pyc", ".pyo", ".log", ".zip"})


def iter_release_source_files(root: str | Path) -> Iterable[Path]:
    """Yield the canonical immutable release-source surface in deterministic order."""
    base = Path(root).expanduser().resolve()
    for candidate in sorted(base.rglob("*"), key=lambda p: p.relative_to(base).as_posix()):
        rel = candidate.relative_to(base)
        parts = rel.parts
        if not parts:
            continue
        if parts[0] in SOURCE_PRESERVE_ROOTS or any(
            part in SOURCE_TRANSIENT_PARTS or part.endswith(".egg-info") for part in parts
        ):
            continue
        if candidate.is_dir() or candidate.is_symlink():
            continue
        if candidate.suffix in SOURCE_TRANSIENT_SUFFIXES or candidate.name.endswith(".trace.zip"):
            continue
        yield candidate


def source_fingerprint(root: str | Path) -> str:
    """Fingerprint the complete canonical release source surface.

    Identity binds relative path, executable bit and file-content SHA-256. Runtime,
    profile, VCS and generated/transient state are intentionally excluded.
    """
    base = Path(root).expanduser().resolve()
    digest = hashlib.sha256()
    for candidate in iter_release_source_files(base):
        rel = candidate.relative_to(base)
        digest.update(rel.as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(b"x" if (candidate.stat().st_mode & 0o111) else b"-")
        digest.update(b"\0")
        digest.update(hashlib.sha256(candidate.read_bytes()).digest())
        digest.update(b"\0")
    return digest.hexdigest()
