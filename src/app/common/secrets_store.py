"""Secrets behind an interface. Docker secrets/env today; swap in HashiCorp Vault,
an HSM, or Azure Key Vault (as an adapter) without touching callers."""
import os
from pathlib import Path
from typing import Protocol


class SecretStore(Protocol):
    def get(self, name: str) -> str: ...


class LocalSecretStore:
    """Reads /run/secrets/<name> (Docker secret), falling back to env NAME upper-cased."""

    def __init__(self, secrets_dir: str = "/run/secrets"):
        self.dir = Path(secrets_dir)

    def get(self, name: str) -> str:
        f = self.dir / name
        if f.exists():
            return f.read_text().strip()
        val = os.getenv(name.upper())
        if val:
            return val
        raise KeyError(f"secret '{name}' not found in {self.dir} or env {name.upper()}")


def default_store() -> SecretStore:
    return LocalSecretStore()
