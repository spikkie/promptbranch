from __future__ import annotations

PACKAGE_VERSION = "0.0.189"
VERSION_TAG = f"v{PACKAGE_VERSION}"


def normalize_version(value: object) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    if text.lower().startswith("v"):
        text = text[1:]
    return text


def version_tag(value: object = PACKAGE_VERSION) -> str:
    normalized = normalize_version(value) or ""
    return f"v{normalized}" if normalized else ""
