"""Tests for Strands Agent wrapper."""

from unittest.mock import MagicMock, patch

import pytest

from app.agents.strands_agent import StrandsAgent
from app.config import Settings


@pytest.fixture
def mock_settings():
    """Mock settings for agent testing."""
    return Settings(
        SERVICE_MODE="api",
        PORT=8000,
        AWS_REGION="us-east-1",
        BEDROCK_MODEL_ID="test-model-id",
        SESSION_STORAGE_PATH="./test_sessions",
        LOG_LEVEL="INFO",
        AWS_ACCESS_KEY_ID="test-key",
        AWS_SECRET_ACCESS_KEY="test-secret",
    )


@pytest.fixture
def mock_bedrock_model():
    """Mock BedrockModel."""
    with patch("app.agents.strands_agent.BedrockModel") as mock:
        yield mock


@pytest.fixture
def mock_agent_class():
    """Mock Agent class."""
    with patch("app.agents.strands_agent.Agent") as mock:
        yield mock


def test_strands_agent_initialization(mock_settings, mock_bedrock_model, mock_agent_class):
    """Test StrandsAgent initialization."""
    agent = StrandsAgent(mock_settings)

    # Verify BedrockModel was called with correct parameters
    mock_bedrock_model.assert_called_once_with(
        model_id="test-model-id",
        region_name="us-east-1",
    )

    # Verify Agent was initialized with model
    mock_agent_class.assert_called_once()
    assert agent.settings == mock_settings


@pytest.mark.asyncio
async def test_strands_agent_chat(mock_settings, mock_bedrock_model, mock_agent_class):
    """Test StrandsAgent chat method."""
    # Create mock agent instance
    mock_agent_instance = MagicMock()

    # Mock the stream_async method with proper async iterator
    class MockEvent:
        def __init__(self, event_type, event_data=None):
            self.type = event_type
            self.data = event_data or {}

    async def mock_stream(*args, **kwargs):
        yield MockEvent("thinking")
        yield MockEvent("tool_use", {"tool_name": "test_tool"})
        yield MockEvent("agent_message", {"content": "Test response"})

    mock_agent_instance.stream_async = mock_stream
    mock_agent_class.return_value = mock_agent_instance

    # Create agent and test chat
    agent = StrandsAgent(mock_settings)

    events = []
    async for event in agent.chat("Test prompt", "test_user"):
        events.append(event)

    # Verify events
    assert len(events) == 3
    assert events[0]["type"] == "thinking"
    assert events[1]["type"] == "tool_use"
    assert events[1]["tool_name"] == "test_tool"
    assert events[2]["type"] == "agent_message"
    assert events[2]["content"] == "Test response"


@pytest.mark.asyncio
async def test_strands_agent_chat_error(mock_settings, mock_bedrock_model, mock_agent_class):
    """Test StrandsAgent chat method with error."""
    # Create mock agent instance that raises an error
    mock_agent_instance = MagicMock()

    async def mock_stream_error(*args, **kwargs):
        test_error_msg = "Test error"
        raise Exception(test_error_msg)
        yield  # This line won't be reached but makes it a generator

    mock_agent_instance.stream_async = mock_stream_error
    mock_agent_class.return_value = mock_agent_instance

    # Create agent and test chat
    agent = StrandsAgent(mock_settings)

    events = []
    async for event in agent.chat("Test prompt", "test_user"):
        events.append(event)

    # Verify error event
    assert len(events) == 1
    assert events[0]["type"] == "error"
    assert "Test error" in events[0]["message"]


def test_strands_agent_configure(mock_settings, mock_bedrock_model, mock_agent_class):
    """Test StrandsAgent configure method."""
    agent = StrandsAgent(mock_settings)

    # Configure with new settings
    agent.configure(temperature=0.7, max_tokens=1000)

    # Method should execute without errors
    # Note: Current implementation is a placeholder
    assert True
