"""Configuración del MCP Server cargada desde .env vía pydantic-settings."""

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    socrata_domain: str = "www.datos.gov.co"
    socrata_app_token: str | None = None
    discovery_api_url: str = "https://api.us.socrata.com/api/catalog/v1"

    mcp_transport: str = "sse"
    mcp_host: str = "0.0.0.0"
    mcp_port: int = 3000

    log_level: str = "INFO"

    @field_validator("socrata_app_token", mode="before")
    @classmethod
    def _empty_or_comment_to_none(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped or stripped.startswith("#"):
            return None
        return stripped


settings = Settings()
