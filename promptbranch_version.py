from __future__ import annotations

PACKAGE_VERSION = "0.1.73.2"


def normalize_version(value: object) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    while text.lower().startswith("v"):
        text = text[1:]
    return text or None


def version_tag(value: object = PACKAGE_VERSION) -> str:
    normalized = normalize_version(value) or ""
    return f"v{normalized}" if normalized else ""


VERSION_TAG = version_tag(PACKAGE_VERSION)
