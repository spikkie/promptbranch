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
    source_name: str
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

    def run(self, argv: Sequence[str], *, project_url: str | None = None, input_text: str | None = None) -> CommandResult:
        full_argv = [self.python_exe, self.cli_path]
        if project_url:
            full_argv += ["--project-url", project_url]
        full_argv += list(argv)
        proc = subprocess.run(
            full_argv,
            input=input_text,
            text=True,
            capture_output=True,
            timeout=self.timeout,
        )
        return CommandResult(full_argv[2:] if project_url else full_argv[2:], proc.returncode, proc.stdout, proc.stderr)

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

    def try_variants(
        self,
        step: str,
        variants: Iterable[Sequence[str]],
        *,
        project_url: str | None = None,
        input_text: str | None = None,
    ) -> CommandResult:
        attempts: list[CommandResult] = []
        for variant in variants:
            r = self.run(list(variant), project_url=project_url, input_text=input_text)
            attempts.append(r)
            if r.returncode == 0:
                self.log(step, True, f"accepted variant: {' '.join(r.argv)}")
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
        if not s.project_url:
            raise SmokeError("project-create did not expose project_url; later project-scoped commands need it")

    def project_resolve(self, s: State) -> None:
        variants = [["project-resolve", s.project_name], ["project-resolve", s.project_url]]
        r = self.try_variants("project-resolve", variants)
        combined = r.combined
        s.project_id = self.extract(combined, ["project_id", "id", "uuid"]) or s.project_id
        s.project_url = self.extract(combined, ["project_url", "url"]) or s.project_url
        self.log("project-resolve.parse", True, f"project_id={s.project_id or 'unknown'}, project_url={s.project_url or 'unknown'}")

    def project_ensure(self, s: State) -> None:
        variants = [["project-ensure", s.project_name], ["project-ensure", s.project_url]]
        r = self.try_variants("project-ensure", variants)
        combined = r.combined
        s.project_id = self.extract(combined, ["project_id", "id", "uuid"]) or s.project_id
        s.project_url = self.extract(combined, ["project_url", "url"]) or s.project_url
        self.log("project-ensure.parse", True, f"project_id={s.project_id or 'unknown'}, project_url={s.project_url or 'unknown'}")

    def project_source_add(self, s: State) -> None:
        variants = [
            ["project-source-add", "--type", "file", "--file", s.source_path, "--name", s.source_name],
            ["project-source-add", "--type", "file", "--file", s.source_path],
            ["project-source-add", "--type", "text", "--value", f"source_name={s.source_name}\npath={s.source_path}", "--name", s.source_name],
        ]
        r = self.try_variants("project-source-add", variants, project_url=s.project_url)
        s.source_id = self.extract(r.combined, ["source_id", "id", "uuid"])
        self.log("project-source-add.parse", True, f"source_id={s.source_id or 'unknown'}")

    def ask_first(self, s: State) -> None:
        prompt = "Reply with compact JSON including keys status and topic, with topic='smoke-test-first'."
        variants = [
            ["ask", prompt],
            ["ask", "--json", prompt],
        ]
        r = self.try_variants("ask#1", variants, project_url=s.project_url)
        combined = r.combined
        s.conversation_id = self.extract(combined, ["conversation_id", "chat_id", "thread_id", "session_id"]) or s.conversation_id
        s.message_id = self.extract(combined, ["message_id", "assistant_message_id", "user_message_id", "id"]) or s.message_id
        self.log("ask#1.parse", True, f"conversation_id={s.conversation_id or 'unknown'}, message_id={s.message_id or 'unknown'}")

    def ask_reply(self, s: State) -> None:
        prompt = "Reply briefly and confirm this is the second message in the same conversation."
        variants = [
            ["ask", prompt],
            ["ask", "--json", prompt],
        ]
        r = self.try_variants("ask#2", variants, project_url=s.project_url)
        combined = r.combined
        second_cid = self.extract(combined, ["conversation_id", "chat_id", "thread_id", "session_id"])
        second_mid = self.extract(combined, ["message_id", "assistant_message_id", "user_message_id", "id"])
        if s.conversation_id and second_cid:
            if s.conversation_id != second_cid:
                raise SmokeError(f"Second ask used a different conversation_id: first={s.conversation_id} second={second_cid}")
            self.log("ask#2.same-chat", True, f"conversation_id preserved: {second_cid}")
        else:
            self.log("ask#2.same-chat", False, "CLI did not expose conversation threading flags or returned IDs; same-chat reply remains unproven")
        s.conversation_id = second_cid or s.conversation_id
        s.message_id = second_mid or s.message_id
        self.log("ask#2.parse", True, f"conversation_id={s.conversation_id or 'unknown'}, message_id={s.message_id or 'unknown'}")

    def shell(self, s: State) -> None:
        variants = [["shell"], ["shell", "--json"]]
        attempts: list[CommandResult] = []
        for variant in variants:
            r = self.run(variant, project_url=s.project_url, input_text="exit\n")
            attempts.append(r)
            if r.returncode == 0:
                self.log("shell", True, f"accepted variant: {' '.join(r.argv)}")
                return
        self.log("shell", False, "all variants failed")
        raise SmokeError("\n\n".join(self.fmt_result(f"Attempt {i+1}", r) for i, r in enumerate(attempts)))

    def project_source_remove(self, s: State) -> None:
        targets = [s.source_name, os.path.basename(s.source_path), s.source_path]
        variants: list[list[str]] = []
        for target in targets:
            variants.append(["project-source-remove", "--exact", target])
            variants.append(["project-source-remove", target])
        self.try_variants("project-source-remove", variants, project_url=s.project_url)

    def project_remove(self, s: State) -> None:
        self.try_variants("project-remove", [["project-remove"]], project_url=s.project_url)

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
            if not self.keep_project and s.project_url:
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
    p = argparse.ArgumentParser(description="Project-scoped smoke test for chatgpt_cli.py using config defaults")
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

    source_path = make_temp_source_file()
    state = State(
        project_name=args.project_name,
        source_path=source_path,
        source_name=f"smoke-source-{random_suffix(6)}",
    )
    print(f"CLI: {cli_path}")
    print(f"Python: {args.python_exe}")
    print(f"Project: {state.project_name}")
    print(f"Source file: {state.source_path}")
    print(f"Source name: {state.source_name}")
    print("Using config defaults from ~/.config/chatgpt-cli/config.json")
    print()

    return Runner(cli_path, args.python_exe, args.timeout, args.keep_project).run_all(state)


if __name__ == "__main__":
    raise SystemExit(main())
