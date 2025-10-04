"""Tests for Coordinator Agent."""

from unittest.mock import MagicMock, patch

import pytest

from app.agents.coordinator_agent import CoordinatorAgent
from app.config import Settings


@pytest.fixture
def mock_settings():
    """Mock settings for coordinator testing."""
    return Settings(
        SERVICE_MODE="api",
        AWS_REGION="us-east-1",
        BEDROCK_MODEL_ID="test-model-id",
        SESSION_STORAGE_PATH="./test_sessions",
        AWS_ACCESS_KEY_ID="test-key",
        AWS_SECRET_ACCESS_KEY="test-secret",
    )


@patch("app.agents.coordinator_agent.BedrockModel")
@patch("app.agents.coordinator_agent.Agent")
def test_coordinator_initialization(mock_agent_class, mock_bedrock_model, mock_settings):
    """Test Coordinator agent initialization."""
    _ = CoordinatorAgent(mock_settings)

    # Verify Bedrock model created
    mock_bedrock_model.assert_called_once_with(
        model_id="test-model-id",
        region_name="us-east-1",
    )

    # Verify Agent created with tools
    mock_agent_class.assert_called_once()
    call_kwargs = mock_agent_class.call_args.kwargs
    assert "tools" in call_kwargs
    assert len(call_kwargs["tools"]) > 0  # Has finops_assistant tool


@pytest.mark.asyncio
@patch("app.agents.coordinator_agent.BedrockModel")
@patch("app.agents.coordinator_agent.Agent")
async def test_coordinator_routes_cost_query(mock_agent_class, mock_bedrock_model, mock_settings):
    """Test coordinator routes cost queries to FinOps agent."""
    # Setup mock agent
    mock_agent_instance = MagicMock()

    # Mock streaming response
    async def mock_stream(*args, **kwargs):
        yield {"start": True}
        yield {"current_tool_use": {"name": "finops_assistant"}}
        yield {"data": "Your AWS costs are $100"}
        yield {"complete": True}

    mock_agent_instance.stream_async = mock_stream
    mock_agent_class.return_value = mock_agent_instance

    # Create coordinator
    coordinator = CoordinatorAgent(mock_settings)

    # Test cost query
    events = []
    async for event in coordinator.chat("What are my AWS costs?", "test_user"):
        events.append(event)

    # Verify routing to finops_assistant
    tool_events = [e for e in events if e.get("type") == "tool_use"]
    assert len(tool_events) > 0
    assert any("finops" in e.get("tool_name", "").lower() for e in tool_events)


@pytest.mark.asyncio
@patch("app.agents.coordinator_agent.BedrockModel")
@patch("app.agents.coordinator_agent.Agent")
async def test_coordinator_handles_general_query(
    mock_agent_class, mock_bedrock_model, mock_settings
):
    """Test coordinator handles general queries directly."""
    # Setup mock agent
    mock_agent_instance = MagicMock()

    # Mock streaming response without tool use
    async def mock_stream(*args, **kwargs):
        yield {"start": True}
        yield {"data": "Here's how to troubleshoot..."}
        yield {"complete": True}

    mock_agent_instance.stream_async = mock_stream
    mock_agent_class.return_value = mock_agent_instance

    # Create coordinator
    coordinator = CoordinatorAgent(mock_settings)

    # Test general query
    events = []
    async for event in coordinator.chat("How do I troubleshoot EC2?", "test_user"):
        events.append(event)

    # Verify direct response (no tool use)
    message_events = [e for e in events if e.get("type") == "agent_message"]
    assert len(message_events) > 0
