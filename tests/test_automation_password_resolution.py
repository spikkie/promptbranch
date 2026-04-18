from pathlib import Path

from chatgpt_automation.automation import _resolve_password_file_path


def test_resolve_password_file_path_prefers_existing_secret_fallback(monkeypatch, tmp_path):
    missing = tmp_path / "missing-password.txt"
    secret_dir = tmp_path / "run" / "secrets"
    secret_dir.mkdir(parents=True)
    secret_file = secret_dir / "chatgpt_password"
    secret_file.write_text("secret\n", encoding="utf-8")

    monkeypatch.setenv("CHATGPT_PASSWORD_FILE", str(missing))

    original_resolve = Path.resolve

    def patched_resolve(self, strict=False):
        if str(self) == "/run/secrets/chatgpt_password":
            return secret_file
        return original_resolve(self, strict=strict)

    monkeypatch.setattr(Path, "resolve", patched_resolve)

    assert _resolve_password_file_path() == str(secret_file)


def test_resolve_password_file_path_returns_first_candidate_when_nothing_exists(monkeypatch, tmp_path):
    missing = tmp_path / "missing-password.txt"
    monkeypatch.setenv("CHATGPT_PASSWORD_FILE", str(missing))

    assert _resolve_password_file_path() == str(missing.resolve())
