from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    app_name: str = "Ratatosk"
    app_description: str = "A simple AI orchestrator self-hosted on your own server."
    app_version: str = "0.1.0"

    host: str = "127.0.0.1"
    port: int = 8000
    debug: bool = False

    # list of different AI API key
    google_api_key: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_prefix="RATATOSK_",
    )


settings = Settings()
