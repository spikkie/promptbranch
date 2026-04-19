#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import random
import re
import string
import subprocess
import sys
import tempfile
import textwrap
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence


@dataclass
class CommandResult:
    argv: list[str]
    returncode: int
    stdout: str
    stderr: str

    @property
    def combined(self) -> str:
        return "\n".join(x for x in [self.stdout.strip(), self.stderr.strip()] if x).strip()


@dataclass
class State:
    project_name: str
    source_path: str
    project_id: str | None = None
    project_url: str | None = None
    source_id: str | None = None
    conversation_id: str | None = None
    message_id: str | None = None


class SmokeError(RuntimeError):
    pass


class Runner:
    def __init__(self, cli_path: str, python_exe: str, timeout: int, keep_project: bool = False) -> None:
        self.cli_path = cli_path
        self.python_exe = python_exe
        self.timeout = timeout
        self.keep_project = keep_project
        self.help_cache: dict[str, str] = {}
        self.results: list[tuple[str, bool, str]] = []

    def log(self, step: str, ok: bool, msg: str) -> None:
        self.results.append((step, ok, msg))
        print(f"[{'OK' if ok else 'FAIL'}] {step}: {msg}")

    def run(self, argv: Sequence[str], input_text: str | None = None) -> CommandResult:
        proc = subprocess.run(
            [self.python_exe, self.cli_path, *argv],
            input=input_text,
            text=True,
            capture_output=True,
            timeout=self.timeout,
        )
        return CommandResult(list(argv), proc.returncode, proc.stdout, proc.stderr)

    def help(self, subcommand: str) -> str:
        if subcommand not in self.help_cache:
            r = self.run([subcommand, "--help"])
            self.help_cache[subcommand] = r.combined
        return self.help_cache[subcommand]

    @staticmethod
    def option_names(help_text: str) -> set[str]:
        return set(re.findall(r"--[a-zA-Z0-9][a-zA-Z0-9-]*", help_text))

    @staticmethod
    def _try_json_objects(text: str) -> list[object]:
        text = text.strip()
        if not text:
            return []
        out: list[object] = []
        for candidate in [text, *re.findall(r"(\{.*?\}|\[.*?\])", text, flags=re.DOTALL)]:
            try:
                out.append(json.loads(candidate))
            except Exception:
                pass
        return out

    @classmethod
    def _search_key_recursive(cls, obj: object, keys: set[str]) -> str | None:
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k in keys and isinstance(v, (str, int, float)):
                    return str(v)
            for v in obj.values():
                found = cls._search_key_recursive(v, keys)
                if found is not None:
                    return found
        elif isinstance(obj, list):
            for item in obj:
                found = cls._search_key_recursive(item, keys)
                if found is not None:
                    return found
        return None

    @classmethod
    def extract(cls, text: str, keys: Iterable[str]) -> str | None:
        keys = set(keys)
        for obj in cls._try_json_objects(text):
            found = cls._search_key_recursive(obj, keys)
            if found is not None:
                return found
        for key in keys:
            patterns = [
                rf'"{re.escape(key)}"\s*:\s*"([^"]+)"',
                rf"\b{re.escape(key)}\b\s*=\s*([A-Za-z0-9_./:-]+)",
                rf"\b{re.escape(key)}\b\s*:\s*([A-Za-z0-9_./:-]+)",
            ]
            for p in patterns:
                m = re.search(p, text)
                if m:
                    return m.group(1)
        return None

    @staticmethod
    def fmt_result(prefix: str, r: CommandResult) -> str:
        parts = [prefix, f"argv: {' '.join(r.argv)}", f"returncode: {r.returncode}"]
        if r.stdout.strip():
            parts.append("stdout:\n" + r.stdout.strip())
        if r.stderr.strip():
            parts.append("stderr:\n" + r.stderr.strip())
        return "\n\n".join(parts)

    def pick_flag(self, subcommand: str, preferred: list[str]) -> str | None:
        opts = self.option_names(self.help(subcommand))
        for f in preferred:
            if f in opts:
                return f
        return None

    def refs_for_project(self, subcommand: str, s: State) -> list[list[str]]:
        opts = self.option_names(self.help(subcommand))
        refs: list[list[str]] = []
        candidates: list[tuple[list[str], str | None]] = [
            (["--project-id"], s.project_id),
            (["--id"], s.project_id),
            (["--project-url"], s.project_url),
            (["--url"], s.project_url),
            (["--project-name"], s.project_name),
            (["--name"], s.project_name),
            (["--project"], s.project_name),
        ]
        for flags, value in candidates:
            if value and flags[0] in opts:
                refs.append([flags[0], value])
        # positional fallbacks last
        if s.project_id:
            refs.append([s.project_id])
        if s.project_url:
            refs.append([s.project_url])
        refs.append([s.project_name])
        # empty only when command appears to support global --project-url or no project selector
        refs.append([])
        # dedupe
        seen: set[tuple[str, ...]] = set()
        out: list[list[str]] = []
        for ref in refs:
            t = tuple(ref)
            if t not in seen:
                seen.add(t)
                out.append(ref)
        return out

    def refs_for_source_add(self, subcommand: str, source_path: str) -> list[list[str]]:
        opts = self.option_names(self.help(subcommand))
        refs: list[list[str]] = []
        for flag in ["--path", "--file", "--source", "--source-path"]:
            if flag in opts:
                refs.append([flag, source_path])
        refs.append([source_path])
        return refs

    def refs_for_source_remove(self, subcommand: str, s: State) -> list[list[str]]:
        opts = self.option_names(self.help(subcommand))
        refs: list[list[str]] = []
        if s.source_id:
            for flag in ["--source-id", "--id", "--source"]:
                if flag in opts:
                    refs.append([flag, s.source_id])
            refs.append([s.source_id])
        for flag in ["--path", "--file", "--source", "--source-path"]:
            if flag in opts:
                refs.append([flag, s.source_path])
        refs.append([s.source_path])
        seen: set[tuple[str, ...]] = set()
        out: list[list[str]] = []
        for ref in refs:
            t = tuple(ref)
            if t not in seen:
                seen.add(t)
                out.append(ref)
        return out

    def refs_for_prompt(self, subcommand: str, prompt: str) -> list[list[str]]:
        opts = self.option_names(self.help(subcommand))
        refs: list[list[str]] = []
        for flag in ["--message", "--prompt", "--text", "--question"]:
            if flag in opts:
                refs.append([flag, prompt])
        refs.append([prompt])
        return refs

    def refs_for_conversation(self, subcommand: str, s: State) -> list[list[str]]:
        if not s.conversation_id:
            return [[]]
        opts = self.option_names(self.help(subcommand))
        refs: list[list[str]] = []
        for flag in ["--conversation-id", "--chat-id", "--thread-id", "--session-id"]:
            if flag in opts:
                refs.append([flag, s.conversation_id])
        refs.append([])
        return refs

    def refs_for_reply(self, subcommand: str, s: State) -> list[list[str]]:
        if not s.message_id:
            return [[]]
        opts = self.option_names(self.help(subcommand))
        refs: list[list[str]] = []
        for flag in ["--reply-to-message-id", "--reply-to", "--parent-message-id", "--parent-id"]:
            if flag in opts:
                refs.append([flag, s.message_id])
        refs.append([])
        return refs

    def try_variants(self, step: str, variants: Iterable[Sequence[str]], input_text: str | None = None) -> CommandResult:
        attempts: list[CommandResult] = []
        for variant in variants:
            r = self.run(list(variant), input_text=input_text)
            attempts.append(r)
            if r.returncode == 0:
                self.log(step, True, f"accepted variant: {' '.join(variant)}")
                return r
        self.log(step, False, "all variants failed")
        detail = "\n\n".join(self.fmt_result(f"Attempt {i+1}", r) for i, r in enumerate(attempts))
        raise SmokeError(detail)

    def preflight(self) -> None:
        for sub in [
            "login-check",
            "project-create",
            "project-resolve",
            "project-ensure",
            "project-remove",
            "project-source-add",
            "project-source-remove",
            "ask",
            "shell",
        ]:
            h = self.help(sub)
            opts = sorted(self.option_names(h))
            self.log(f"help.{sub}", True, ", ".join(opts) if opts else "(no options detected)")

    def login_check(self) -> None:
        self.try_variants("login-check", [["login-check"]])

    def project_create(self, s: State) -> None:
        sub = "project-create"
        opts = self.option_names(self.help(sub))
        variants: list[list[str]] = []
        for flag in ["--name", "--project-name", "--project"]:
            if flag in opts:
                variants.append([sub, flag, s.project_name])
        variants.append([sub, s.project_name])
        r = self.try_variants(sub, variants)
        combined = r.combined
        s.project_id = self.extract(combined, ["project_id", "id", "uuid"])
        s.project_url = self.extract(combined, ["project_url", "url"])
        self.log("project-create.parse", True, f"project_id={s.project_id or 'unknown'}, project_url={s.project_url or 'unknown'}")

    def project_resolve(self, s: State) -> None:
        variants = [["project-resolve", *ref] for ref in self.refs_for_project("project-resolve", s)]
        r = self.try_variants("project-resolve", variants)
        combined = r.combined
        s.project_id = self.extract(combined, ["project_id", "id", "uuid"]) or s.project_id
        s.project_url = self.extract(combined, ["project_url", "url"]) or s.project_url
        self.log("project-resolve.parse", True, f"project_id={s.project_id or 'unknown'}, project_url={s.project_url or 'unknown'}")

    def project_ensure(self, s: State) -> None:
        variants = [["project-ensure", *ref] for ref in self.refs_for_project("project-ensure", s)]
        r = self.try_variants("project-ensure", variants)
        combined = r.combined
        s.project_id = self.extract(combined, ["project_id", "id", "uuid"]) or s.project_id
        s.project_url = self.extract(combined, ["project_url", "url"]) or s.project_url
        self.log("project-ensure.parse", True, f"project_id={s.project_id or 'unknown'}, project_url={s.project_url or 'unknown'}")

    def project_source_add(self, s: State) -> None:
        variants: list[list[str]] = []
        for pref in self.refs_for_project("project-source-add", s):
            for sref in self.refs_for_source_add("project-source-add", s.source_path):
                variants.append(["project-source-add", *pref, *sref])
        r = self.try_variants("project-source-add", variants)
        s.source_id = self.extract(r.combined, ["source_id", "id", "uuid"])
        self.log("project-source-add.parse", True, f"source_id={s.source_id or 'unknown'}")

    def ask_first(self, s: State) -> None:
        prompt = "Reply with compact JSON including keys status and topic, with topic='smoke-test-first'."
        variants: list[list[str]] = []
        for pref in self.refs_for_project("ask", s):
            for pref2 in self.refs_for_prompt("ask", prompt):
                variants.append(["ask", *pref, *pref2])
        r = self.try_variants("ask#1", variants)
        combined = r.combined
        s.conversation_id = self.extract(combined, ["conversation_id", "chat_id", "thread_id", "session_id"]) or s.conversation_id
        s.message_id = self.extract(combined, ["message_id", "assistant_message_id", "user_message_id", "id"]) or s.message_id
        self.log("ask#1.parse", True, f"conversation_id={s.conversation_id or 'unknown'}, message_id={s.message_id or 'unknown'}")

    def ask_reply(self, s: State) -> None:
        if not s.conversation_id and not s.message_id:
            raise SmokeError("Cannot guarantee same-chat reply: first ask did not expose conversation_id or message_id")
        prompt = "Reply briefly and confirm this is the second message in the same conversation."
        variants: list[list[str]] = []
        for pref in self.refs_for_project("ask", s):
            for cref in self.refs_for_conversation("ask", s):
                for rref in self.refs_for_reply("ask", s):
                    for pref2 in self.refs_for_prompt("ask", prompt):
                        variants.append(["ask", *pref, *cref, *rref, *pref2])
        r = self.try_variants("ask#2-reply", variants)
        combined = r.combined
        second_cid = self.extract(combined, ["conversation_id", "chat_id", "thread_id", "session_id"])
        second_mid = self.extract(combined, ["message_id", "assistant_message_id", "user_message_id", "id"])
        if s.conversation_id and second_cid and s.conversation_id != second_cid:
            raise SmokeError(f"Second ask returned different conversation_id: first={s.conversation_id} second={second_cid}")
        s.conversation_id = second_cid or s.conversation_id
        s.message_id = second_mid or s.message_id
        self.log("ask#2.parse", True, f"conversation_id={s.conversation_id or 'unknown'}, message_id={s.message_id or 'unknown'}")

    def shell(self, s: State) -> None:
        variants = [["shell", *ref] for ref in self.refs_for_project("shell", s)] + [["shell"]]
        attempts: list[CommandResult] = []
        for variant in variants:
            r = self.run(variant, input_text="exit\n")
            attempts.append(r)
            if r.returncode == 0:
                self.log("shell", True, f"accepted variant: {' '.join(variant)}")
                return
        self.log("shell", False, "all variants failed")
        raise SmokeError("\n\n".join(self.fmt_result(f"Attempt {i+1}", r) for i, r in enumerate(attempts)))

    def project_source_remove(self, s: State) -> None:
        variants: list[list[str]] = []
        for pref in self.refs_for_project("project-source-remove", s):
            for sref in self.refs_for_source_remove("project-source-remove", s):
                variants.append(["project-source-remove", *pref, *sref])
        self.try_variants("project-source-remove", variants)

    def project_remove(self, s: State) -> None:
        variants = [["project-remove", *ref] for ref in self.refs_for_project("project-remove", s)]
        self.try_variants("project-remove", variants)

    def run_all(self, s: State) -> int:
        try:
            self.preflight()
            self.login_check()
            self.project_create(s)
            self.project_resolve(s)
            self.project_ensure(s)
            self.project_source_add(s)
            self.ask_first(s)
            self.ask_reply(s)
            self.shell(s)
            self.project_source_remove(s)
            self.project_remove(s)
            self.log("suite", True, "completed")
            return 0
        except Exception as exc:
            self.log("suite", False, str(exc))
            if not self.keep_project:
                try:
                    self.project_remove(s)
                except Exception as cleanup_exc:
                    self.log("cleanup.project-remove", False, str(cleanup_exc))
            return 1


def random_suffix(n: int = 8) -> str:
    alphabet = string.ascii_lowercase + string.digits
    return "".join(random.choice(alphabet) for _ in range(n))


def make_temp_source_file() -> str:
    fd, path = tempfile.mkstemp(prefix="chatgpt-cli-source-", suffix=".txt")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(textwrap.dedent(f"""\
        # smoke test source
        created_at_epoch: {int(time.time())}
        purpose: validate project-source-add and project-source-remove
        """))
    return path


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Adaptive smoke test for chatgpt_cli.py using config defaults")
    p.add_argument("--cli", default="chatgpt_cli.py")
    p.add_argument("--python", dest="python_exe", default=sys.executable)
    p.add_argument("--timeout", type=int, default=120)
    p.add_argument("--project-name", default=f"chatgpt-cli-smoke-{time.strftime('%Y%m%d-%H%M%S')}-{random_suffix()}")
    p.add_argument("--keep-project", action="store_true")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    cli_path = str(Path(args.cli).expanduser())
    if not Path(cli_path).exists():
        print(f"ERROR: CLI script not found: {cli_path}", file=sys.stderr)
        return 2

    state = State(project_name=args.project_name, source_path=make_temp_source_file())
    print(f"CLI: {cli_path}")
    print(f"Python: {args.python_exe}")
    print(f"Project: {state.project_name}")
    print(f"Source file: {state.source_path}")
    print("Using config defaults from ~/.config/chatgpt-cli/config.json")
    print()

    return Runner(cli_path, args.python_exe, args.timeout, args.keep_project).run_all(state)


if __name__ == "__main__":
    raise SystemExit(main())
