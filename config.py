import os

from dotenv import dotenv_values, load_dotenv


class Settings:
    def __init__(self, source: str = "env"):
        self.source = source
        self._secrets = self._load()

    def _load(self):
        if self.source == "env":
            load_dotenv()
            file_values = dict(dotenv_values())
            merged = file_values.copy()
            merged.update({k: v for k, v in os.environ.items() if v is not None})
            return merged
        elif self.source == "vault":
            # Placeholder for vault-based loading
            raise NotImplementedError("Vault integration not yet implemented.")
        else:
            raise ValueError(f"Unsupported secret source: {self.source}")

    def get(self, key: str, default=None):
        return self._secrets.get(key, default)

    def all(self):
        return self._secrets.copy()
