#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import time
from pathlib import Path
from typing import Any

from promptbranch_automation import ChatGPTAutomation


PROJECT_ID_RE = re.compile(r"/g/(g-p-[^/]+)/project")


def _env_flag(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _now_tag() -> str:
    return time.strftime("%Y%m%d_%H%M%S")


def _slugify(text: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9._-]+", "-", text.strip())
    return value.strip("-")[:80] or "item"


def _save_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def _save_text(path: Path, payload: str) -> None:
    path.write_text(payload, encoding="utf-8")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Promptbranch-native local diagnostic for project-list popup/debug investigation (no Docker service).",
    )
    parser.add_argument("--project-url", default=os.getenv("CHATGPT_PROJECT_URL", "https://chatgpt.com/"))
    parser.add_argument("--email", default=os.getenv("CHATGPT_EMAIL"))
    parser.add_argument("--password", default=os.getenv("CHATGPT_PASSWORD"))
    parser.add_argument("--password-file", default=os.getenv("CHATGPT_PASSWORD_FILE"))
    parser.add_argument("--profile-dir", default=os.getenv("PROMPTBRANCH_PROFILE_DIR") or os.getenv("CHATGPT_PROFILE_DIR", "./.pb_profile"))
    parser.add_argument("--headless", action="store_true", default=_env_flag("CHATGPT_HEADLESS", False))
    parser.add_argument("--use-playwright", action="store_true", default=not _env_flag("CHATGPT_USE_PATCHRIGHT", True))
    parser.add_argument("--browser-channel", default=os.getenv("CHATGPT_BROWSER_CHANNEL", "chrome"))
    parser.add_argument("--debug", action="store_true", default=_env_flag("CHATGPT_DEBUG", True))
    parser.add_argument("--debug-artifact-dir", default=os.getenv("CHATGPT_DEBUG_ARTIFACT_DIR", "debug_artifacts"))
    parser.add_argument("--scroll-rounds", type=int, default=12)
    parser.add_argument("--wait-ms", type=int, default=350)
    parser.add_argument("--manual", action="store_true", help="Pause between phases so you can inspect the headed browser.")
    parser.add_argument("--keep-open", action="store_true", help="Keep browser open at the end until Enter is pressed.")
    return parser.parse_args()


async def _find_project_links(page: Any) -> list[dict[str, Any]]:
    js = r"""
    () => {
      const anchors = Array.from(document.querySelectorAll('a[href*="/g/g-p-"][href$="/project"]'));
      return anchors.map((a, idx) => {
        const href = a.href || a.getAttribute("href") || "";
        const text = (a.innerText || a.textContent || "").replace(/\s+/g, " ").trim();
        const rect = a.getBoundingClientRect();
        const style = getComputedStyle(a);
        return {
          index: idx,
          href,
          text,
          visible: !!(rect.width && rect.height && style.visibility !== "hidden" && style.display !== "none"),
          top: rect.top,
          left: rect.left,
          width: rect.width,
          height: rect.height,
          outer_html: a.outerHTML.slice(0, 800),
        };
      });
    }
    """
    links = await page.evaluate(js)
    dedup: dict[str, dict[str, Any]] = {}
    for item in links:
        href = str(item.get("href") or "")
        match = PROJECT_ID_RE.search(href)
        item["project_id"] = match.group(1) if match else None
        dedup[href] = item
    return sorted(dedup.values(), key=lambda x: (x.get("top", 0), x.get("left", 0), x.get("text", ""), x.get("href", "")))


async def _find_dialog_nodes(page: Any) -> list[dict[str, Any]]:
    js = r"""
    () => {
      const sels = ['[role="dialog"]', '[role="menu"]', '[role="listbox"]', '[data-radix-popper-content-wrapper]', '[data-radix-menu-content]'];
      const out = [];
      for (const sel of sels) {
        for (const el of document.querySelectorAll(sel)) {
          const rect = el.getBoundingClientRect();
          if (!(rect.width && rect.height)) continue;
          out.push({
            selector: sel,
            tag: el.tagName.toLowerCase(),
            role: el.getAttribute("role"),
            aria_label: el.getAttribute("aria-label"),
            top: rect.top,
            left: rect.left,
            width: rect.width,
            height: rect.height,
            text_preview: (el.innerText || "").replace(/\s+/g, " ").trim().slice(0, 240),
            outer_html: el.outerHTML.slice(0, 1500),
          });
        }
      }
      return out;
    }
    """
    return await page.evaluate(js)


async def _find_scrollables(page: Any) -> list[dict[str, Any]]:
    js = r"""
    () => {
      const nodes = Array.from(document.querySelectorAll('*'));
      const out = [];
      for (const el of nodes) {
        const style = getComputedStyle(el);
        const rect = el.getBoundingClientRect();
        const scrollable = el.scrollHeight > el.clientHeight + 20 || el.scrollWidth > el.clientWidth + 20;
        const overflowY = style.overflowY;
        const overflowX = style.overflowX;
        if (!scrollable && !["auto", "scroll"].includes(overflowY) && !["auto", "scroll"].includes(overflowX)) {
          continue;
        }
        out.push({
          tag: el.tagName.toLowerCase(),
          id: el.id || null,
          cls: (el.className && String(el.className)) || null,
          role: el.getAttribute("role"),
          aria_label: el.getAttribute("aria-label"),
          clientHeight: el.clientHeight,
          scrollHeight: el.scrollHeight,
          scrollTop: el.scrollTop,
          clientWidth: el.clientWidth,
          scrollWidth: el.scrollWidth,
          top: rect.top,
          left: rect.left,
          width: rect.width,
          height: rect.height,
          text_preview: (el.innerText || "").replace(/\s+/g, " ").trim().slice(0, 240),
          outer_html: el.outerHTML.slice(0, 1000),
        });
      }
      out.sort((a, b) => {
        const diff = (b.scrollHeight - b.clientHeight) - (a.scrollHeight - a.clientHeight);
        if (diff !== 0) return diff;
        return (b.height * b.width) - (a.height * a.width);
      });
      return out.slice(0, 25);
    }
    """
    return await page.evaluate(js)


async def _find_more_candidates(page: Any) -> list[dict[str, Any]]:
    js = r"""
    () => {
      const matches = [];
      const nodes = Array.from(document.querySelectorAll('button, [role="button"], a, div, span, summary'));
      for (const el of nodes) {
        const text = (el.innerText || el.textContent || "").replace(/\s+/g, " ").trim();
        if (!/\bmore\b/i.test(text)) continue;
        const rect = el.getBoundingClientRect();
        if (!(rect.width && rect.height)) continue;
        matches.push({
          text,
          tag: el.tagName.toLowerCase(),
          role: el.getAttribute("role"),
          aria_label: el.getAttribute("aria-label"),
          top: rect.top,
          left: rect.left,
          width: rect.width,
          height: rect.height,
          outer_html: el.outerHTML.slice(0, 1000),
        });
      }
      matches.sort((a, b) => a.top - b.top || a.left - b.left);
      return matches;
    }
    """
    return await page.evaluate(js)


async def _capture_state(page: Any, out_dir: Path, label: str) -> dict[str, Any]:
    safe = _slugify(label)
    await page.screenshot(path=str(out_dir / f"{safe}.png"), full_page=True)
    _save_text(out_dir / f"{safe}.html", await page.content())
    payload = {
        "label": label,
        "url": page.url,
        "title": await page.title(),
        "project_links": await _find_project_links(page),
        "dialog_like_nodes": await _find_dialog_nodes(page),
        "candidate_scrollables": await _find_scrollables(page),
        "more_candidates": await _find_more_candidates(page),
    }
    _save_json(out_dir / f"{safe}.json", payload)
    return payload


async def _pause(message: str) -> None:
    await asyncio.to_thread(input, message)


async def _run_debug(args: argparse.Namespace) -> int:
    artifact_root = Path(args.debug_artifact_dir).expanduser().resolve()
    out_dir = artifact_root / f"project_list_debug_{_now_tag()}"
    out_dir.mkdir(parents=True, exist_ok=True)

    bot = ChatGPTAutomation(
        project_url=args.project_url,
        email=args.email,
        password=args.password,
        password_file=args.password_file,
        profile_dir=args.profile_dir,
        headless=args.headless,
        use_patchright=not args.use_playwright,
        browser_channel=args.browser_channel,
        debug=args.debug,
        debug_artifact_dir=str(artifact_root),
    )
    client = bot.client

    async def operation(*, context: Any, page: Any, keep_open: bool = False) -> dict[str, Any]:
        network_events: list[dict[str, Any]] = []
        console_events: list[dict[str, Any]] = []

        async def on_request(request: Any) -> None:
            try:
                if request.resource_type in {"fetch", "xhr"}:
                    network_events.append(
                        {
                            "type": "request",
                            "method": request.method,
                            "resource_type": request.resource_type,
                            "url": request.url,
                            "post_data": request.post_data,
                            "ts": time.time(),
                        }
                    )
            except Exception:
                pass

        async def on_response(response: Any) -> None:
            try:
                request = response.request
                if request.resource_type in {"fetch", "xhr"}:
                    network_events.append(
                        {
                            "type": "response",
                            "method": request.method,
                            "resource_type": request.resource_type,
                            "url": request.url,
                            "status": response.status,
                            "ts": time.time(),
                        }
                    )
            except Exception:
                pass

        async def on_console(msg: Any) -> None:
            try:
                console_events.append(
                    {
                        "type": msg.type,
                        "text": msg.text,
                        "ts": time.time(),
                    }
                )
            except Exception:
                pass

        page.on("request", lambda req: asyncio.create_task(on_request(req)))
        page.on("response", lambda resp: asyncio.create_task(on_response(resp)))
        page.on("console", lambda msg: asyncio.create_task(on_console(msg)))

        await client.ensure_logged_in(page, context)
        await client._goto(page, client._chatgpt_home_url(), label="project-list-debug-home")
        await client._ensure_sidebar_open(page)
        before = await _capture_state(page, out_dir, "01-before-expand")

        if args.manual:
            await _pause("Inspect state before expanding Projects. Press Enter to continue... ")

        await client._expand_projects_section(page)
        await page.wait_for_timeout(args.wait_ms)
        after_expand = await _capture_state(page, out_dir, "02-after-expand")

        if args.manual:
            await _pause("Inspect state after expanding Projects. Press Enter to continue... ")

        opened_more = await client._open_more_projects_menu(page)
        await page.wait_for_timeout(args.wait_ms)
        after_more = await _capture_state(page, out_dir, "03-after-open-more")

        if args.manual:
            await _pause("Inspect state after opening More. Press Enter to start scrolling... ")

        collected: list[dict[str, str]] = []
        rounds: list[dict[str, Any]] = []
        for round_index in range(args.scroll_rounds):
            visible = await client._collect_sidebar_projects(page)
            collected = client._dedupe_projects([*collected, *visible])
            state = await _capture_state(page, out_dir, f"round-{round_index + 1:02d}")
            moved = await client._scroll_project_sidebar_step(page)
            rounds.append(
                {
                    "round": round_index + 1,
                    "visible_count": len(visible),
                    "collected_count": len(collected),
                    "moved": bool(moved),
                    "visible_projects": visible,
                    "captured_project_count": len(state["project_links"]),
                }
            )
            if not moved:
                break
            await page.wait_for_timeout(args.wait_ms)

        helper_result = await client._collect_all_sidebar_projects(page, label="project-list-debug-helper")
        final_state = await _capture_state(page, out_dir, "99-final")

        summary = {
            "ok": True,
            "action": "project_list_debug",
            "project_url": args.project_url,
            "profile_dir": str(Path(args.profile_dir).expanduser().resolve()),
            "driver": client.driver_name,
            "headless": args.headless,
            "browser_channel": args.browser_channel,
            "opened_more": opened_more,
            "before_expand_count": len(before["project_links"]),
            "after_expand_count": len(after_expand["project_links"]),
            "after_more_count": len(after_more["project_links"]),
            "manual_scroll_rounds": rounds,
            "manual_collected_projects": collected,
            "manual_collected_count": len(collected),
            "helper_collected_projects": helper_result,
            "helper_collected_count": len(helper_result),
            "final_dom_project_count": len(final_state["project_links"]),
            "final_dom_projects": final_state["project_links"],
            "dialog_like_nodes_after_more": after_more["dialog_like_nodes"],
            "candidate_scrollables_after_more": after_more["candidate_scrollables"][:10],
            "more_candidates_after_more": after_more["more_candidates"],
            "network_events": network_events,
            "console_events": console_events,
            "artifact_dir": str(out_dir),
        }
        _save_json(out_dir / "summary.json", summary)
        if keep_open and client.config.is_headed:
            await client._pause_for_keep_open("Project-list debug completed. Press Enter to close the browser... ")
        return summary

    result = await client._run_with_context(
        operation_name="project_list_debug",
        operation=operation,
        keep_open=args.keep_open,
    )

    print(json.dumps(result, indent=2, ensure_ascii=False))
    print(f"\nArtifacts: {result['artifact_dir']}")
    print("Most useful files:")
    print(f"  {Path(result['artifact_dir']) / 'summary.json'}")
    print(f"  {Path(result['artifact_dir']) / '03-after-open-more.png'}")
    print(f"  {Path(result['artifact_dir']) / '99-final.png'}")
    return 0


def main() -> int:
    args = _parse_args()
    return asyncio.run(_run_debug(args))


if __name__ == "__main__":
    raise SystemExit(main())
