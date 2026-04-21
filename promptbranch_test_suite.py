from __future__ import annotations

import argparse
import asyncio
from typing import Any, Optional, Sequence

from promptbranch_full_integration_test import make_parser as make_integration_parser, run_integration


DEFAULT_ONLY: tuple[str, ...] = ()
DEFAULT_SKIP: tuple[str, ...] = ()


def build_test_suite_namespace(
    *,
    project_url: Optional[str] = None,
    email: Optional[str] = None,
    password: Optional[str] = None,
    password_file: Optional[str] = None,
    profile_dir: Optional[str] = None,
    headless: Optional[bool] = None,
    use_playwright: Optional[bool] = None,
    browser_channel: Optional[str] = None,
    enable_fedcm: Optional[bool] = None,
    keep_no_sandbox: Optional[bool] = None,
    max_retries: Optional[int] = None,
    retry_backoff_seconds: Optional[float] = None,
    debug: Optional[bool] = None,
    keep_open: Optional[bool] = None,
    keep_project: bool = False,
    step_delay_seconds: Optional[float] = None,
    skip: Sequence[str] = DEFAULT_SKIP,
    only: Sequence[str] = DEFAULT_ONLY,
    strict_remove_ui: bool = False,
    project_name: Optional[str] = None,
    project_name_prefix: Optional[str] = None,
    run_id: Optional[str] = None,
    memory_mode: Optional[str] = None,
    link_url: Optional[str] = None,
    ask_prompt: Optional[str] = None,
    json_out: Optional[str] = None,
    project_list_debug_scroll_rounds: Optional[int] = None,
    project_list_debug_wait_ms: Optional[int] = None,
    project_list_debug_manual_pause: bool = False,
    service_base_url: Optional[str] = None,
    service_token: Optional[str] = None,
    service_timeout_seconds: Optional[float] = None,
    clear_singleton_locks: Optional[bool] = None,
) -> argparse.Namespace:
    parser = make_integration_parser()
    args = parser.parse_args([])
    overrides = {
        'project_url': project_url,
        'email': email,
        'password': password,
        'password_file': password_file,
        'profile_dir': profile_dir,
        'headless': headless,
        'use_playwright': use_playwright,
        'browser_channel': browser_channel,
        'enable_fedcm': enable_fedcm,
        'keep_no_sandbox': keep_no_sandbox,
        'max_retries': max_retries,
        'retry_backoff_seconds': retry_backoff_seconds,
        'debug': debug,
        'keep_open': keep_open,
        'keep_project': keep_project,
        'step_delay_seconds': step_delay_seconds,
        'skip': list(skip),
        'only': list(only),
        'strict_remove_ui': strict_remove_ui,
        'project_name': project_name,
        'project_name_prefix': project_name_prefix,
        'run_id': run_id,
        'memory_mode': memory_mode,
        'link_url': link_url,
        'ask_prompt': ask_prompt,
        'json_out': json_out,
        'project_list_debug_scroll_rounds': project_list_debug_scroll_rounds,
        'project_list_debug_wait_ms': project_list_debug_wait_ms,
        'project_list_debug_manual_pause': project_list_debug_manual_pause,
        'service_base_url': service_base_url,
        'service_token': service_token,
        'service_timeout_seconds': service_timeout_seconds,
        'clear_singleton_locks': clear_singleton_locks,
    }
    for key, value in overrides.items():
        if value is not None:
            setattr(args, key, value)
    return args


async def run_test_suite_async(**kwargs: Any) -> dict[str, Any]:
    args = build_test_suite_namespace(**kwargs)
    return await run_integration(args)


def run_test_suite_sync(**kwargs: Any) -> dict[str, Any]:
    return asyncio.run(run_test_suite_async(**kwargs))
