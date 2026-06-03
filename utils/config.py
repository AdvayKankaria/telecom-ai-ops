"""Application configuration and environment validation."""

from __future__ import annotations

import os
from pathlib import Path

# Fix Hugging Face cache permission issues globally BEFORE any HF imports
os.environ["HF_HOME"] = str(Path(__file__).resolve().parent.parent / ".hf_cache")
os.environ["HF_HUB_DISABLE_IMPLICIT_TOKEN"] = "1"

from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent
DATA_PATH: Path = PROJECT_ROOT / "data"
DB_PATH: Path = DATA_PATH / "telecom_ops.db"
DOCS_PATH: Path = DATA_PATH / "documents"
INDEX_PATH: Path = DATA_PATH / "vector_index"

BILLING_AUTO_APPROVE_LIMIT: float = 50.0


def _required_env(key: str) -> str:
    """Return required environment value or raise an explicit error."""
    value = os.getenv(key, "").strip()
    if not value:
        raise EnvironmentError(
            f"Missing required environment variable '{key}'. "
            "Add it to .env based on .env.example."
        )
    return value


OPENAI_API_KEY: str = _required_env("OPENAI_API_KEY")
GOOGLE_API_KEY: str = _required_env("GOOGLE_API_KEY")
NETWORK_DIAGNOSTICS_URL: str = os.getenv(
    "NETWORK_DIAGNOSTICS_URL", "http://127.0.0.1:8001"
).strip()
BILLING_RESOLUTION_URL: str = os.getenv(
    "BILLING_RESOLUTION_URL", "http://127.0.0.1:8002"
).strip()
