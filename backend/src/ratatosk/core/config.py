import os
import sys
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def get_app_dir(app_name: str = "ratatosk") -> Path:
    home = Path.home()
    if sys.platform == "win32":
        base = Path(os.getenv("APPDATA", home / "AppData" / "Roaming"))
    elif sys.platform == "darwin":
        base = home / "Library" / "Application Support"
    else:
        base = Path(os.getenv("XDG_DATA_HOME", home / ".local" / "share"))

    app_dir = base / app_name
    app_dir.mkdir(parents=True, exist_ok=True)
    return app_dir


class Settings(BaseSettings):
    """Application settings."""

    app_name: str = "Ratatosk"
    app_description: str = "A simple AI orchestrator self-hosted on your own server."
    app_version: str = "0.1.0"
    app_dir: Path = get_app_dir(app_name)

    host: str = "127.0.0.1"
    port: int = 8000
    debug: bool = False

    # list of different AI API key
    google_api_key: str = ""

    @property
    def cache_dir(self) -> Path:
        path = self.app_dir / "cache"
        path.mkdir(parents=True, exist_ok=True)
        return path

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_prefix="RATATOSK_",
    )


settings = Settings()
