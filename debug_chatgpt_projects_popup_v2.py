#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import tempfile
import time
from pathlib import Path
from typing import Any

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright


PROJECT_ID_RE = re.compile(r"/g/(g-p-[^/]+)/project")
LOCK_NAMES = {"SingletonCookie", "SingletonLock", "SingletonSocket", "lockfile", ".org.chromium.Chromium"}


def ts() -> str:
    return time.strftime("%Y%m%d-%H%M%S")


def slugify(text: str) -> str:
    text = re.sub(r"[^a-zA-Z0-9._-]+", "-", text.strip())
    return text.strip("-")[:80] or "item"


def save_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def save_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def default_profile_dir() -> str:
    env = os.getenv("PROMPTBRANCH_PROFILE_DIR")
    if env:
        return env
    local = Path("./.pb_profile")
    if local.exists():
        return str(local.resolve())
    return str(Path.home() / ".config" / "promptbranch" / "profile")


def ignore_profile_junk(_dir: str, names: list[str]) -> set[str]:
    ignored = set()
    for name in names:
        if name in LOCK_NAMES or name.startswith("Singleton"):
            ignored.add(name)
        if name.endswith(".lock"):
            ignored.add(name)
    return ignored


def clone_profile(src: Path) -> Path:
    dst = Path(tempfile.mkdtemp(prefix="promptbranch-debug-profile-"))
    if src.exists():
        shutil.copytree(src, dst, dirs_exist_ok=True, ignore=ignore_profile_junk)
    return dst


def launch_context(pw, profile_dir: Path, browser_channel: str, use_persistent: bool = True):
    common = dict(
        headless=False,
        viewport={"width": 1280, "height": 1100},
        args=["--disable-crash-reporter", "--disable-crashpad", "--no-sandbox"],
    )
    if use_persistent:
        return pw.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            channel=browser_channel,
            **common,
        )
    browser = pw.chromium.launch(channel=browser_channel, headless=False, args=common["args"])
    context = browser.new_context(viewport=common["viewport"])
    return context


def open_browser_context(pw, profile_dir: Path, browser_channel: str, out_dir: Path):
    attempts = []
    for channel in [browser_channel, "chrome", "msedge", "chromium"]:
        if channel in attempts:
            continue
        attempts.append(channel)
        try:
            ctx = launch_context(pw, profile_dir, channel, use_persistent=True)
            return ctx, {"profile_dir": str(profile_dir), "channel": channel, "mode": "persistent"}
        except Exception as e:
            save_text(out_dir / f"launch-error-{slugify(channel)}.txt", repr(e))

    copied = clone_profile(profile_dir)
    for channel in [browser_channel, "chrome", "msedge", "chromium"]:
        if channel in attempts:
            continue
        attempts.append(channel)
        try:
            ctx = launch_context(pw, copied, channel, use_persistent=True)
            return ctx, {"profile_dir": str(copied), "channel": channel, "mode": "persistent-cloned"}
        except Exception as e:
            save_text(out_dir / f"launch-error-cloned-{slugify(channel)}.txt", repr(e))

    # last fallback: non-persistent fresh browser
    for channel in [browser_channel, "chrome", "msedge", "chromium"]:
        try:
            ctx = launch_context(pw, copied, channel, use_persistent=False)
            return ctx, {"profile_dir": None, "channel": channel, "mode": "non-persistent"}
        except Exception as e:
            save_text(out_dir / f"launch-error-nonpersistent-{slugify(channel)}.txt", repr(e))

    raise RuntimeError(
        "Could not launch a headed browser. Try closing other browsers using the same profile, "
        "or rerun with --browser-channel chrome."
    )


def find_project_links(page, scope=None) -> list[dict[str, Any]]:
    js = r"""
    (root) => {
      const scope = root || document;
      const anchors = Array.from(scope.querySelectorAll('a[href*="/g/g-p-"][href$="/project"]'));
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
          outer_html: a.outerHTML.slice(0, 1000),
        };
      });
    }
    """
    links = page.evaluate(js, scope)
    for item in links:
        m = PROJECT_ID_RE.search(item["href"])
        item["project_id"] = m.group(1) if m else None
    dedup = {}
    for item in links:
        dedup[item["href"]] = item
    return sorted(dedup.values(), key=lambda x: (x["top"], x["left"], x["text"], x["href"]))


def find_dialog_like_nodes(page) -> list[dict[str, Any]]:
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
            text_preview: (el.innerText || "").replace(/\s+/g, " ").trim().slice(0, 200),
            outer_html: el.outerHTML.slice(0, 1500),
          });
        }
      }
      return out;
    }
    """
    return page.evaluate(js)


def find_candidate_scrollables(page) -> list[dict[str, Any]]:
    js = r"""
    () => {
      const nodes = Array.from(document.querySelectorAll('*'));
      const out = [];
      for (const el of nodes) {
        const style = getComputedStyle(el);
        const rect = el.getBoundingClientRect();
        const isScrollable = el.scrollHeight > el.clientHeight + 20 || el.scrollWidth > el.clientWidth + 20;
        const overflowY = style.overflowY;
        const overflowX = style.overflowX;
        if (!isScrollable && !["auto", "scroll"].includes(overflowY) && !["auto", "scroll"].includes(overflowX)) continue;
        const text = (el.innerText || "").replace(/\s+/g, " ").trim();
        out.push({
          tag: el.tagName.toLowerCase(),
          id: el.id || null,
          cls: (el.className && String(el.className)) || null,
          role: el.getAttribute("role"),
          aria_label: el.getAttribute("aria-label"),
          clientHeight: el.clientHeight,
          scrollHeight: el.scrollHeight,
          scrollTop: el.scrollTop,
          top: rect.top,
          left: rect.left,
          width: rect.width,
          height: rect.height,
          text_preview: text[:180],
          outer_html: el.outerHTML.slice(0, 800),
        });
      }
      out.sort((a, b) => {
        const diff = (b.scrollHeight - b.clientHeight) - (a.scrollHeight - a.clientHeight);
        if (diff !== 0) return diff;
        return (b.height * b.width) - (a.height * a.width);
      });
      return out.slice(0, 30);
    }
    """
    return page.evaluate(js)


def find_more_candidates(page) -> list[dict[str, Any]]:
    js = r"""
    () => {
      const matches = [];
      const nodes = Array.from(document.querySelectorAll('button, [role="button"], a, div, span'));
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
    return page.evaluate(js)


def capture_state(page, out_dir: Path, label: str) -> dict[str, Any]:
    safe = slugify(label)
    page.screenshot(path=str(out_dir / f"{safe}.png"), full_page=True)
    save_text(out_dir / f"{safe}.html", page.content())
    data = {
        "label": label,
        "url": page.url,
        "title": page.title(),
        "project_links": find_project_links(page),
        "dialog_like_nodes": find_dialog_like_nodes(page),
        "candidate_scrollables": find_candidate_scrollables(page),
        "more_candidates": find_more_candidates(page),
    }
    save_json(out_dir / f"{safe}.json", data)
    return data


def open_more(page) -> bool:
    candidates = [
        page.get_by_role("button", name=re.compile(r"^\s*More\s*$", re.I)),
        page.get_by_role("menuitem", name=re.compile(r"^\s*More\s*$", re.I)),
        page.get_by_text(re.compile(r"^\s*More\s*$", re.I)),
        page.locator("button:has-text('More')"),
        page.locator("[role='button']:has-text('More')"),
    ]
    for loc in candidates:
        try:
            if loc.count() > 0:
                loc.first.click(timeout=3000)
                return True
        except Exception:
            pass
    return False


def scroll_best_container(page, rounds: int, out_dir: Path) -> list[dict[str, Any]]:
    metrics = []
    scroll_js = r"""
    (step) => {
      const nodes = Array.from(document.querySelectorAll('*'));
      let best = null;
      let bestScore = -1;
      for (const el of nodes) {
        const rect = el.getBoundingClientRect();
        if (!(rect.width > 100 && rect.height > 120)) continue;
        const text = (el.innerText || "").replace(/\s+/g, " ").trim();
        const containsProjects = /Candlecast2|Demo Project|Project|Ubuntu|React|Natalie|VPN|CV|Google Drive/i.test(text);
        const scrollable = el.scrollHeight > el.clientHeight + 40;
        if (!scrollable) continue;
        const score = (containsProjects ? 100000 : 0) + (el.scrollHeight - el.clientHeight) + rect.height - Math.abs(rect.left - 550);
        if (score > bestScore) {
          bestScore = score;
          best = el;
        }
      }
      if (!best) return null;
      const before = best.scrollTop;
      best.scrollTop = Math.min(best.scrollTop + step, best.scrollHeight);
      const after = best.scrollTop;
      const rect = best.getBoundingClientRect();
      return {
        tag: best.tagName.toLowerCase(),
        id: best.id || null,
        cls: (best.className && String(best.className)) || null,
        role: best.getAttribute("role"),
        aria_label: best.getAttribute("aria-label"),
        clientHeight: best.clientHeight,
        scrollHeight: best.scrollHeight,
        before,
        after,
        moved: after > before,
        top: rect.top,
        left: rect.left,
        width: rect.width,
        height: rect.height,
        text_preview: (best.innerText || "").replace(/\s+/g, " ").trim().slice(0, 200),
      };
    }
    """
    for i in range(rounds):
        result = page.evaluate(scroll_js, 700)
        metrics.append({"round": i + 1, "result": result})
        page.wait_for_timeout(700)
        capture_state(page, out_dir, f"after-scroll-{i+1}")
        if not result or not result.get("moved"):
            break
    return metrics


def main() -> int:
    ap = argparse.ArgumentParser(description="Debug ChatGPT 'More' project list popup outside Docker in a headed browser.")
    ap.add_argument("--url", default="https://chatgpt.com/", help="Start URL.")
    ap.add_argument("--profile-dir", default=default_profile_dir(), help="Persistent browser profile dir to reuse your signed-in session.")
    ap.add_argument("--browser-channel", default="chrome", help="Preferred browser channel: chrome, msedge, chromium.")
    ap.add_argument("--manual", action="store_true", help="Pause for manual interaction before each capture phase.")
    ap.add_argument("--scroll-rounds", type=int, default=8, help="How many popup scroll rounds to try.")
    ap.add_argument("--out-dir", default=f"./debug_projects_popup_{ts()}", help="Where to write screenshots/HTML/JSON.")
    args = ap.parse_args()

    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    network_events: list[dict[str, Any]] = []
    console_events: list[dict[str, Any]] = []

    with sync_playwright() as pw:
        context, launch_info = open_browser_context(
            pw,
            Path(args.profile_dir).expanduser().resolve(),
            args.browser_channel,
            out_dir,
        )
        page = context.pages[0] if context.pages else context.new_page()

        def on_request(req):
            if req.resource_type in {"fetch", "xhr"}:
                network_events.append({
                    "type": "request",
                    "method": req.method,
                    "resource_type": req.resource_type,
                    "url": req.url,
                    "post_data": req.post_data,
                    "ts": time.time(),
                })

        def on_response(resp):
            try:
                req = resp.request
                if req.resource_type in {"fetch", "xhr"}:
                    network_events.append({
                        "type": "response",
                        "method": req.method,
                        "resource_type": req.resource_type,
                        "url": req.url,
                        "status": resp.status,
                        "ts": time.time(),
                    })
            except Exception:
                pass

        def on_console(msg):
            console_events.append({
                "type": msg.type,
                "text": msg.text,
                "ts": time.time(),
            })

        page.on("request", on_request)
        page.on("response", on_response)
        page.on("console", on_console)

        print(f"Launch mode:      {launch_info['mode']}")
        print(f"Browser channel:  {launch_info['channel']}")
        print(f"Profile dir used: {launch_info['profile_dir']}")
        print(f"Artifacts dir:    {out_dir}")
        print(f"Navigating to:    {args.url}")

        page.goto(args.url, wait_until="domcontentloaded", timeout=120000)
        page.wait_for_timeout(2500)

        if args.manual:
            input("Browser is open. Put ChatGPT in the state you want, then press Enter to capture BEFORE clicking More... ")

        before = capture_state(page, out_dir, "before-more")

        opened = open_more(page)
        page.wait_for_timeout(1500)

        if args.manual:
            print(f"Auto-click More success: {opened}")
            input("If needed, click More manually now, then press Enter to capture AFTER clicking More... ")

        after_click = capture_state(page, out_dir, "after-more-click")
        scroll_metrics = scroll_best_container(page, args.scroll_rounds, out_dir)

        if args.manual:
            input("Optionally interact more with the popup, then press Enter for FINAL capture... ")

        final = capture_state(page, out_dir, "final")

        summary = {
            "launch_info": launch_info,
            "start_url": args.url,
            "end_url": page.url,
            "auto_clicked_more": opened,
            "before_more_project_count": len(before["project_links"]),
            "after_more_click_project_count": len(after_click["project_links"]),
            "final_project_count": len(final["project_links"]),
            "scroll_metrics": scroll_metrics,
            "before_more_projects": [{"text": x["text"], "href": x["href"]} for x in before["project_links"]],
            "after_more_click_projects": [{"text": x["text"], "href": x["href"]} for x in after_click["project_links"]],
            "final_projects": [{"text": x["text"], "href": x["href"]} for x in final["project_links"]],
            "dialog_like_after_click": after_click["dialog_like_nodes"],
            "candidate_scrollables_after_click": after_click["candidate_scrollables"][:10],
            "more_candidates_after_click": after_click["more_candidates"],
            "network_events": network_events,
            "console_events": console_events,
        }
        save_json(out_dir / "summary.json", summary)

        print("\nSummary")
        print(f"- before more project links: {len(before['project_links'])}")
        print(f"- after click project links: {len(after_click['project_links'])}")
        print(f"- final project links:      {len(final['project_links'])}")
        print(f"- network events captured:  {len(network_events)}")
        print(f"- artifacts dir:            {out_dir}")
        print("\nMost useful files:")
        print(f"  {out_dir / 'summary.json'}")
        print(f"  {out_dir / 'before-more.png'}")
        print(f"  {out_dir / 'after-more-click.png'}")
        print(f"  {out_dir / 'final.png'}")

        input("\nPress Enter to close the browser...")
        context.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
