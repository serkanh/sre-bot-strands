"""Application configuration using Pydantic Settings."""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Service Configuration
    SERVICE_MODE: Literal["api", "web"] = "api"
    PORT: int = 8000

    # AWS Configuration
    AWS_REGION: str = "us-east-1"
    AWS_PROFILE: str | None = None  # Optional: use AWS profile instead of access keys
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""

    # Bedrock Configuration
    BEDROCK_MODEL_ID: str = "anthropic.claude-3-5-sonnet-20241022-v2:0"

    # Application Configuration
    SESSION_STORAGE_PATH: str = "./sessions"
    LOG_LEVEL: str = "INFO"

    # MCP Configuration
    FASTMCP_LOG_LEVEL: str = "ERROR"  # Control MCP server logging

    # Kubernetes Configuration (for K3s local testing)
    KUBECONFIG: str | None = None  # Path to kubeconfig file

    # EKS MCP Configuration
    EKS_MCP_ALLOW_WRITE: bool = False  # Enable write operations
    EKS_MCP_ALLOW_SENSITIVE_DATA: bool = False  # Enable sensitive data access

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance.

    Returns:
        Settings instance
    """
    return Settings()
