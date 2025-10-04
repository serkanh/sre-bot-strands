"""Shared API routes for both API and Web services."""

import logging

from fastapi import APIRouter, Depends, HTTPException

from app.agents.strands_agent import StrandsAgent
from app.config import Settings, get_settings
from app.models.schemas import (
    ChatRequest,
    ChatResponse,
    ConfigResponse,
    ConfigUpdate,
    SessionResponse,
)
from app.services.session_manager import SessionManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")

# Global instances (will be initialized in main.py)
agent: StrandsAgent | None = None
session_manager: SessionManager | None = None


def get_agent() -> StrandsAgent:
    """Dependency to get the agent instance."""
    if agent is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    return agent


def get_session_manager() -> SessionManager:
    """Dependency to get the session manager instance."""
    if session_manager is None:
        raise HTTPException(status_code=503, detail="Session manager not initialized")
    return session_manager


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    agent: StrandsAgent = Depends(get_agent),
    session_mgr: SessionManager = Depends(get_session_manager),
) -> ChatResponse:
    """Chat endpoint with streaming event support.

    Args:
        request: Chat request with user_id and message
        agent: Strands agent instance
        session_mgr: Session manager instance

    Returns:
        ChatResponse with response text and event stream data
    """
    logger.info("Chat request from user: %s", request.user_id)

    # Add user message to session
    session_mgr.add_message(request.user_id, "user", request.message)

    events = []
    final_response = ""

    try:
        # Stream events from agent
        async for event in agent.chat(request.message, request.user_id):
            events.append(event)

            # Accumulate text chunks from agent messages
            if event.get("type") == "agent_message" and event.get("is_chunk"):
                final_response += event.get("content", "")

        # Add assistant message to session
        if final_response:
            session_mgr.add_message(request.user_id, "assistant", final_response)

        return ChatResponse(
            user_id=request.user_id,
            response=final_response,
            events=events,
            metrics={
                "event_count": len(events),
            },
        )

    except Exception as e:
        logger.error("Error in chat endpoint for user %s: %s", request.user_id, str(e))
        error_msg = f"Chat processing error: {e!s}"
        raise HTTPException(status_code=500, detail=error_msg) from e


@router.get("/config", response_model=ConfigResponse)
async def get_config(settings: Settings = Depends(get_settings)) -> ConfigResponse:
    """Get current agent configuration.

    Args:
        settings: Application settings

    Returns:
        ConfigResponse with current configuration
    """
    return ConfigResponse(
        model_id=settings.BEDROCK_MODEL_ID,
        system_prompt=None,  # Can be extended to include system prompt
        temperature=None,
        max_tokens=None,
    )


@router.post("/config", response_model=ConfigResponse)
async def update_config(
    config_update: ConfigUpdate,
    agent: StrandsAgent = Depends(get_agent),
    settings: Settings = Depends(get_settings),
) -> ConfigResponse:
    """Update agent configuration dynamically.

    Args:
        config_update: Configuration update request
        agent: Strands agent instance
        settings: Application settings

    Returns:
        ConfigResponse with updated configuration
    """
    logger.info("Updating agent configuration: %s", config_update.model_dump(exclude_none=True))

    # Update agent configuration
    agent.configure(**config_update.model_dump(exclude_none=True))

    # Return current configuration (merged with updates)
    return ConfigResponse(
        model_id=config_update.model_id or settings.BEDROCK_MODEL_ID,
        system_prompt=config_update.system_prompt,
        temperature=config_update.temperature,
        max_tokens=config_update.max_tokens,
    )


@router.get("/session/{user_id}", response_model=SessionResponse)
async def get_session(
    user_id: str,
    session_mgr: SessionManager = Depends(get_session_manager),
) -> SessionResponse:
    """Get session history for a user.

    Args:
        user_id: User identifier
        session_mgr: Session manager instance

    Returns:
        SessionResponse with user messages
    """
    messages = session_mgr.get_messages(user_id)

    return SessionResponse(
        user_id=user_id,
        messages=messages,
        message_count=len(messages),
    )


@router.delete("/session/{user_id}")
async def clear_session(
    user_id: str,
    session_mgr: SessionManager = Depends(get_session_manager),
) -> dict[str, str]:
    """Clear session history for a user.

    Args:
        user_id: User identifier
        session_mgr: Session manager instance

    Returns:
        Success message
    """
    success = session_mgr.clear_session(user_id)

    if success:
        return {"status": "success", "message": f"Session cleared for user {user_id}"}

    raise HTTPException(status_code=500, detail="Failed to clear session")
