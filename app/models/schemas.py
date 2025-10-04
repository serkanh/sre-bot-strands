"""Pydantic models for API request/response validation."""

from typing import Any

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Request model for chat endpoint."""

    user_id: str = Field(..., description="Unique identifier for the user")
    message: str = Field(..., description="User's message to the agent")


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""

    user_id: str
    response: str
    events: list[dict[str, Any]] = Field(
        default_factory=list, description="Stream events from the agent"
    )
    metrics: dict[str, Any] | None = Field(
        None, description="Optional metrics (latency, tokens, etc.)"
    )


class ConfigUpdate(BaseModel):
    """Request model for configuration updates."""

    model_id: str | None = Field(None, description="Bedrock model ID")
    system_prompt: str | None = Field(None, description="System prompt for the agent")
    temperature: float | None = Field(None, ge=0.0, le=1.0, description="Model temperature")
    max_tokens: int | None = Field(None, gt=0, description="Maximum tokens to generate")


class ConfigResponse(BaseModel):
    """Response model for configuration endpoint."""

    model_id: str
    system_prompt: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None


class SessionResponse(BaseModel):
    """Response model for session endpoint."""

    user_id: str
    messages: list[dict[str, str]]
    message_count: int


class HealthResponse(BaseModel):
    """Response model for health check endpoint."""

    status: str = Field(..., description="Service health status")
    service_mode: str = Field(..., description="Current service mode (api or web)")
    bedrock_connected: bool = Field(..., description="AWS Bedrock connectivity status")
    details: dict[str, Any] | None = Field(None, description="Additional health details")
