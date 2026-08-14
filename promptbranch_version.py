from __future__ import annotations

from importlib import metadata
from pathlib import Path


def normalize_version(value: object) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    while text.lower().startswith("v"):
        text = text[1:]
    return text or None


def _version_from_authority() -> str:
    authority = Path(__file__).resolve().with_name("VERSION")
    if authority.is_file():
        value = normalize_version(authority.read_text(encoding="utf-8"))
        if value:
            return value
        raise RuntimeError(f"VERSION authority is empty or invalid: {authority}")
    try:
        value = normalize_version(metadata.version("promptbranch"))
    except metadata.PackageNotFoundError as exc:
        raise RuntimeError("VERSION authority is unavailable and installed package metadata is missing") from exc
    if not value:
        raise RuntimeError("installed promptbranch package metadata has no version")
    return value


PACKAGE_VERSION = _version_from_authority()


def version_tag(value: object = PACKAGE_VERSION) -> str:
    normalized = normalize_version(value) or ""
    return f"v{normalized}" if normalized else ""


VERSION_TAG = version_tag(PACKAGE_VERSION)
