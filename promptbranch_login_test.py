import argparse
import asyncio
import json
import os
import traceback

from promptbranch_automation import ChatGPTAutomation


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run a ChatGPT login check with the default backend library."
    )
    parser.add_argument(
        "--url",
        default=os.getenv("CHATGPT_PROJECT_URL"),
        help="ChatGPT project or chat URL. Defaults to CHATGPT_PROJECT_URL.",
    )
    parser.add_argument(
        "--email",
        default=os.getenv("EMAIL"),
        help="Google account email. Defaults to EMAIL.",
    )
    parser.add_argument(
        "--password",
        default=None,
        help="Google account password. Optional; if omitted, the script will read from an external password file.",
    )
    parser.add_argument(
        "--profile-dir",
        default=os.getenv("CHATGPT_PROFILE_DIR", "/app/profile"),
        help="Persistent browser profile directory.",
    )
    parser.add_argument(
        "--debug-dir",
        default=os.getenv("CHATGPT_DEBUG_ARTIFACT_DIR", "debug_artifacts"),
        help="Directory for traces, screenshots, html dumps, and failure reports.",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--headed", action="store_true", help="Use a visible browser.")
    mode.add_argument("--headless", action="store_true", help="Use a headless browser.")
    parser.add_argument(
        "--playwright",
        action="store_true",
        help="Use Playwright instead of Patchright.",
    )
    parser.add_argument(
        "--channel",
        default=os.getenv("CHATGPT_BROWSER_CHANNEL"),
        help="Browser channel to launch, e.g. chrome. Defaults to CHATGPT_BROWSER_CHANNEL.",
    )
    fedcm = parser.add_mutually_exclusive_group()
    fedcm.add_argument(
        "--disable-fedcm",
        dest="disable_fedcm",
        action="store_true",
        default=None,
        help="Disable Chromium FedCM browser-mediated sign-in UI. Enabled by default via CHATGPT_DISABLE_FEDCM or built-in default.",
    )
    fedcm.add_argument(
        "--allow-fedcm",
        dest="disable_fedcm",
        action="store_false",
        help="Allow Chromium FedCM browser-mediated sign-in UI.",
    )
    sandbox = parser.add_mutually_exclusive_group()
    sandbox.add_argument(
        "--filter-no-sandbox",
        dest="filter_no_sandbox",
        action="store_true",
        default=None,
        help="Filter Playwright/Patchright default --no-sandbox flags. Enabled by default via CHATGPT_FILTER_NO_SANDBOX or built-in default.",
    )
    sandbox.add_argument(
        "--keep-no-sandbox",
        dest="filter_no_sandbox",
        action="store_false",
        help="Keep Playwright/Patchright default --no-sandbox flags.",
    )
    parser.add_argument(
        "--keep-open",
        action="store_true",
        help="Keep the headed browser open until Enter is pressed.",
    )
    parser.add_argument(
        "--no-debug",
        action="store_true",
        help="Disable verbose browser diagnostics and artifact capture.",
    )
    parser.add_argument(
        "--no-trace",
        action="store_true",
        help="Disable Playwright trace capture.",
    )
    parser.add_argument(
        "--no-html",
        action="store_true",
        help="Disable HTML snapshot capture on failure.",
    )
    parser.add_argument(
        "--no-screenshot",
        action="store_true",
        help="Disable screenshot capture on failure.",
    )
    return parser


async def main() -> int:
    args = build_parser().parse_args()
    if not args.url:
        raise SystemExit("Missing --url or CHATGPT_PROJECT_URL")

    bot = ChatGPTAutomation(
        project_url=args.url,
        email=args.email,
        password=args.password,
        profile_dir=args.profile_dir,
        headless=bool(args.headless),
        use_patchright=not bool(args.playwright),
        browser_channel=args.channel,
        debug=not bool(args.no_debug),
        debug_artifact_dir=args.debug_dir,
        save_trace=not bool(args.no_trace),
        save_html=not bool(args.no_html),
        save_screenshot=not bool(args.no_screenshot),
        disable_fedcm=args.disable_fedcm,
        filter_no_sandbox=args.filter_no_sandbox,
    )

    config_summary = {
        "url": args.url,
        "email": args.email,
        "profile_dir": args.profile_dir,
        "debug_dir": args.debug_dir,
        "headless": bool(args.headless),
        "use_patchright": not bool(args.playwright),
        "channel": bot.browser_channel,
        "debug": not bool(args.no_debug),
        "save_trace": not bool(args.no_trace),
        "save_html": not bool(args.no_html),
        "save_screenshot": not bool(args.no_screenshot),
        "disable_fedcm": bot.disable_fedcm,
        "filter_no_sandbox": bot.filter_no_sandbox,
        "no_viewport": True if bot.use_patchright else None,
        "password_source": bot.password_source,
    }
    print("[cli] starting promptbranch login test", flush=True)
    print(json.dumps(config_summary, indent=2), flush=True)

    try:
        result = await bot.run_login_check(keep_open=bool(args.keep_open))
    except Exception as exc:
        print("[cli] login test failed", flush=True)
        print(f"[cli] error_type={type(exc).__name__}", flush=True)
        print(f"[cli] error={exc}", flush=True)
        traceback.print_exc()
        return 1

    print("[cli] login test succeeded", flush=True)
    print(json.dumps(result, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
