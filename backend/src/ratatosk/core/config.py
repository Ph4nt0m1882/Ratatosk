from enum import Enum
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class RunMode(str, Enum):
    SOLO = "solo"        # Api launch by the flutter app
    DAEMON = "daemon"    # Api launch by the system
    SERVER = "server"    # Api on a distant server

class FeaturesConfig(BaseModel):
    """Ratatosk subsystem switches."""
    rag: bool = Field(default=True, description="Document Memory and Vector Search")
    sandbox: bool = Field(default=True, description="Isolated code execution, App manipulation, browser manipulation, ...")
    mcp: bool = Field(default=True, description="Model Context Protocol support")

class Settings(BaseSettings):
    app_name: str = "Ratatosk"
    app_description: str = "Universal AI Orchestrator & Gateway"
    app_version: str = "0.1.0"
    
    # Execution mode and network configuration
    mode: RunMode = RunMode.SOLO
    host: str | None = None
    port: int = 8000
    debug: bool = False
    
    # features configuration
    features: FeaturesConfig = Field(default_factory=FeaturesConfig)
    
    # API keys for external services
    anthropic_api_key: str | None = None
    gemini_api_key: str | None = None
    openai_api_key: str | None = None

    model_config = SettingsConfigDict(
        env_prefix="RATATOSK_",
        env_file=".env",
        extra="ignore",
    )

    @property
    def bind_host(self) -> str:
        """automatically determine the host to bind to based on the mode and configuration."""
        if self.host:
            return self.host
        return "0.0.0.0" if self.mode == RunMode.SERVER else "127.0.0.1"

settings = Settings()