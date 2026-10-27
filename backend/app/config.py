import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    storage_backend: str = "firestore"
    sqlite_path: str = str(ROOT / ".local" / "coins.sqlite3")
    openai_api_key: str = field(default="", repr=False)
    openai_model: str = "gpt-5.4-mini"
    openai_base_url: str = "https://api.openai.com/v1"
    firebase_json: str = field(default="", repr=False)
    firebase_path: str = field(default="", repr=False)
    allowed_origins: tuple = ("http://localhost:5500", "http://127.0.0.1:5500")

    @classmethod
    def from_env(cls):
        load_dotenv(ROOT / ".env", override=False)
        mode = os.getenv("STORAGE_BACKEND", "firestore").strip()
        if mode not in {"firestore", "sqlite"}:
            raise ValueError("STORAGE_BACKEND must be firestore or sqlite")
        origins = tuple(origin.strip().rstrip("/") for origin in os.getenv(
            "ALLOWED_ORIGINS", "http://localhost:5500,http://127.0.0.1:5500").split(",") if origin.strip())
        if "*" in origins:
            raise ValueError("ALLOWED_ORIGINS must contain explicit origins")
        return cls(storage_backend=mode, sqlite_path=os.getenv("SQLITE_PATH", cls.sqlite_path),
                   openai_api_key=os.getenv("OPENAI_API_KEY", ""),
                   openai_model=os.getenv("OPENAI_MODEL", cls.openai_model),
                   openai_base_url=os.getenv("OPENAI_BASE_URL", cls.openai_base_url).strip().rstrip("/"),
                   firebase_json=os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON", ""),
                   firebase_path=os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH", ""), allowed_origins=origins)
