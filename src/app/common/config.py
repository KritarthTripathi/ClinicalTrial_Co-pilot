"""All environment-specific values live here (and in .env). Nothing Azure-specific
appears anywhere in app code, so moving on-prem means changing config only."""
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    router_model: str = os.getenv("ROUTER_MODEL", "llama3.2:3b")
    sql_model: str = os.getenv("SQL_MODEL", "qwen2.5-coder:3b")
    extract_model: str = os.getenv("EXTRACT_MODEL", "qwen2.5:7b")
    phoenix_endpoint: str = os.getenv("PHOENIX_ENDPOINT", "http://localhost:6006/v1/traces")
    phoenix_project: str = os.getenv("PHOENIX_PROJECT", "zero-bytes-agents")
    checkpoint_db: str = os.getenv("CHECKPOINT_DB", "data/work/checkpoints.db")
    work_dir: str = os.getenv("WORK_DIR", "data/work")
    vault_dir: str = os.getenv("VAULT_DIR", "data/vault")
    max_retries: int = int(os.getenv("MAX_RETRIES", "2"))
    max_context_chars: int = int(os.getenv("MAX_CONTEXT_CHARS", "6000"))


settings = Settings()
