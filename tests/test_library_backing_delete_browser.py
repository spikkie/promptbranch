from __future__ import annotations
import asyncio
from pathlib import Path
from promptbranch_browser_auth.client import ChatGPTBrowserClient
from promptbranch_browser_auth.config import ChatGPTBrowserConfig

class Page:
    async def wait_for_timeout(self, _ms: int): return None


def client(tmp_path: Path) -> ChatGPTBrowserClient:
    return ChatGPTBrowserClient(ChatGPTBrowserConfig(project_url="https://chatgpt.com/", profile_dir=str(tmp_path / "profile"), debug=False))


def test_exact_id_candidates_include_libfile_file_and_raw_uuid(tmp_path: Path) -> None:
    c = client(tmp_path)
    ids = c._library_exact_id_candidates(
        processed_file_id="file_00000000a7cc71f48c35989259e6dc33",
        library_metadata_object_id="libfile_8b26b82651e88191a9e965b267290f5b",
    )
    assert ids == [
        "libfile_8b26b82651e88191a9e965b267290f5b",
        "file_00000000a7cc71f48c35989259e6dc33",
        "00000000-a7cc-71f4-8c35-989259e6dc33",
    ]


def test_delete_operation_fails_closed_when_exact_id_not_exposed(tmp_path: Path) -> None:
    c = client(tmp_path); page = Page(); context = object()
    async def logged_in(_page, _context): return True
    async def goto(*_args, **_kwargs): return None
    async def search(*_args, **_kwargs): return None
    async def surface(*_args, **_kwargs): return {"ok": True, "authoritative": True}
    async def presence(*_args, **_kwargs): return {"present": False, "locator_id": None, "matching_cards": []}
    c.ensure_logged_in = logged_in  # type: ignore
    c._goto = goto  # type: ignore
    c._library_search_exact_family = search  # type: ignore
    c._wait_for_authoritative_library_family_surface = surface  # type: ignore
    c._exact_library_backing_presence = presence  # type: ignore
    result = asyncio.run(c._delete_library_backing_object_diagnostic_operation(
        context=context, page=page,
        processed_file_id="file_00000000a7cc71f48c35989259e6dc33",
        library_metadata_object_id="libfile_8b26b82651e88191a9e965b267290f5b",
        filename="demo.txt",
    ))
    assert result["status"] == "exact_library_backing_delete_not_supported"
    assert result["filename_fallback_allowed"] is False
    assert result["exact_object_absent_verified"] is False


def test_delete_operation_requires_stable_absence_after_hard_delete(tmp_path: Path) -> None:
    c = client(tmp_path); page = Page(); context = object(); presence_calls = {"count": 0}; deletes = []
    async def logged_in(_page, _context): return True
    async def goto(*_args, **_kwargs): return None
    async def search(*_args, **_kwargs): return None
    async def surface(*_args, **_kwargs): return {"ok": True, "authoritative": True}
    async def open_deleted(_page): return True
    async def presence(*_args, **_kwargs):
        presence_calls["count"] += 1
        if presence_calls["count"] <= 2:
            return {"present": True, "locator_id": "libfile_target", "matching_cards": []}
        return {"present": False, "locator_id": None, "matching_cards": []}
    async def delete(_page, *, file_id, filename, delete_forever):
        deletes.append((file_id, filename, delete_forever)); return {"ok": True, "status": "delete_triggered"}
    c.ensure_logged_in = logged_in  # type: ignore
    c._goto = goto  # type: ignore
    c._library_search_exact_family = search  # type: ignore
    c._wait_for_authoritative_library_family_surface = surface  # type: ignore
    c._open_library_recently_deleted = open_deleted  # type: ignore
    c._exact_library_backing_presence = presence  # type: ignore
    c._delete_library_file_record_via_ui = delete  # type: ignore
    result = asyncio.run(c._delete_library_backing_object_diagnostic_operation(
        context=context, page=page,
        processed_file_id="file_00000000a7cc71f48c35989259e6dc33",
        library_metadata_object_id="libfile_8b26b82651e88191a9e965b267290f5b",
        filename="demo.txt",
    ))
    assert result["ok"] is True
    assert result["status"] == "exact_library_backing_object_deleted"
    assert result["exact_object_absent_verified"] is True
    assert deletes == [("libfile_target", "demo.txt", False), ("libfile_target", "demo.txt", True)]
    assert result["verification"][-1]["stable_absent"] == 2
