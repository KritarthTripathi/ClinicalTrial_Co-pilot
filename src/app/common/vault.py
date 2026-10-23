"""Encrypted store for the placeholder -> original PII map. Kept out of graph state,
traces and checkpoints. Re-identification reads from here, locally, after the run."""
import json
from pathlib import Path

from cryptography.fernet import Fernet

from .config import settings
from .secrets_store import SecretStore, default_store


class PIIVault:
    def __init__(self, store: SecretStore | None = None):
        key = (store or default_store()).get("pii_vault_key")
        self.fernet = Fernet(key.encode())
        self.dir = Path(settings.vault_dir)
        self.dir.mkdir(parents=True, exist_ok=True)

    def save(self, session_id: str, mapping: dict) -> None:
        blob = self.fernet.encrypt(json.dumps(mapping).encode())
        (self.dir / f"{session_id}.bin").write_bytes(blob)

    def load(self, session_id: str) -> dict:
        blob = (self.dir / f"{session_id}.bin").read_bytes()
        return json.loads(self.fernet.decrypt(blob))

    def reidentify(self, session_id: str, text: str) -> str:
        for placeholder, original in self.load(session_id).items():
            text = text.replace(placeholder, original)
        return text
