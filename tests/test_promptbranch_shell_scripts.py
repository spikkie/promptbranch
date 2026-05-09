import json
import os
import subprocess
from pathlib import Path


def test_promptbranch_statusline_uses_nearest_pb_profile(tmp_path: Path):
    root = tmp_path / "repo"
    nested = root / "a" / "b"
    profile = root / ".pb_profile"
    nested.mkdir(parents=True)
    profile.mkdir()
    (profile / ".promptbranch_state.json").write_text(
        json.dumps(
            {
                "project_name": "Demo Project",
                "conversation_id": "conv-123",
                "project_url": "https://chatgpt.com/",
                "conversation_url": "https://chatgpt.com/c/abc",
            }
        ),
        encoding="utf-8",
    )
    script = Path(__file__).resolve().parents[1] / "scripts" / "promptbranch-statusline.sh"
    result = subprocess.run(
        [str(script), "--json", "--path", str(nested)],
        text=True,
        capture_output=True,
        check=True,
    )
    payload = json.loads(result.stdout)
    assert payload["has_profile"] is True
    assert payload["project"] == "Demo Project"
    assert payload["task"] == "conv-123"


def test_promptbranch_aliases_contains_expected_shortcuts():
    alias_file = Path(__file__).resolve().parents[1] / "scripts" / "promptbranch-aliases.sh"
    text = alias_file.read_text(encoding="utf-8")
    assert "alias pbs='promptbranch state'" in text
    assert "alias pbtl='promptbranch task list'" in text
    assert "alias pbsl='promptbranch src list'" in text
    assert "alias pbsf='promptbranch src add --type file --file'" in text
    assert "alias pbsr='promptbranch src rm'" in text
    assert "alias pbss='promptbranch src sync'" in text
    assert "alias pbac='promptbranch artifact current'" in text



def test_release_control_tests_only_skips_release_mutation_steps(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "VERSION").write_text("v9.9.9\n", encoding="utf-8")
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    calls = tmp_path / "calls.log"

    (fake_bin / "promptbranch").write_text("#!/usr/bin/env bash\necho promptbranch \"$@\" >> \"$PB_FAKE_CALL_LOG\"\n", encoding="utf-8")
    (fake_bin / "promptbranch").chmod(0o755)
    (fake_bin / "timeout").write_text(
        "#!/usr/bin/env bash\n"
        "if [[ \"$1\" == \"--foreground\" ]]; then shift; fi\n"
        "shift\n"
        "exec \"$@\"\n",
        encoding="utf-8",
    )
    (fake_bin / "timeout").chmod(0o755)
    (fake_bin / "pb").write_text(
        "#!/usr/bin/env bash\n"
        "echo pb \"$@\" >> \"$PB_FAKE_CALL_LOG\"\n"
        "if [[ \"$1 $2\" == \"test full\" ]]; then echo '{\"ok\": true, \"action\": \"test_suite\", \"version\": \"v9.9.9\"}'; exit 0; fi\n"
        "if [[ \"$1 $2\" == \"test report\" ]]; then echo '{\"ok\": true, \"action\": \"test_report\", \"status\": \"verified\"}'; exit 0; fi\n"
        "echo unexpected pb args >&2\n"
        "exit 2\n",
        encoding="utf-8",
    )
    (fake_bin / "pb").chmod(0o755)

    script = Path(__file__).resolve().parents[1] / "chatgpt_claudecode_workflow_release_control.sh"
    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}:{env['PATH']}"
    env["PB_FAKE_CALL_LOG"] = str(calls)
    env["PROMPTBRANCH_TEST_SESSION_LOG"] = "release-control-tests-only.log"

    result = subprocess.run(
        [str(script), "--tests-only", "--version", "v9.9.9"],
        cwd=repo,
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )

    assert "tests_only:     1" in result.stdout
    assert "Download ZIP not found" not in result.stdout + result.stderr
    assert not (repo / "chatgpt_claudecode_workflow_v9.9.9.zip").exists()
    assert (repo / "pb_test.full.v9.9.9.log").is_file()
    assert (repo / "pb_test.full.v9.9.9.report.json").is_file()
    assert (repo / "release-control-tests-only.log").is_file()
    call_text = calls.read_text(encoding="utf-8")
    assert "pb test full --json" in call_text
    assert "pb test report pb_test.full.v9.9.9.log --json" in call_text
    assert "promptbranch src add" not in call_text
