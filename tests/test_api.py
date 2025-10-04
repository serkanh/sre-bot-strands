"""Tests for API endpoints."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.agents.coordinator_agent import CoordinatorAgent
from app.main import create_app


@pytest.fixture
def mock_settings():
    """Mock settings for testing."""
    with patch("app.config.get_settings") as mock:
        mock.return_value.SERVICE_MODE = "api"
        mock.return_value.PORT = 8000
        mock.return_value.AWS_REGION = "us-east-1"
        mock.return_value.BEDROCK_MODEL_ID = "test-model"
        mock.return_value.SESSION_STORAGE_PATH = "./test_sessions"
        mock.return_value.LOG_LEVEL = "INFO"
        yield mock.return_value


@pytest.fixture
def client(mock_settings):
    """Create test client."""
    from app.agents.coordinator_agent import CoordinatorAgent
    from app.api import routes
    from app.services.session_manager import SessionManager

    # Initialize the global instances for testing
    routes.agent = CoordinatorAgent(mock_settings)
    routes.session_manager = SessionManager(mock_settings.SESSION_STORAGE_PATH)

    app = create_app()
    return TestClient(app)


def test_health_endpoint(client):
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "service_mode" in data
    assert "bedrock_connected" in data
    assert data["service_mode"] == "api"


def test_get_config(client):
    """Test get configuration endpoint."""
    response = client.get("/api/config")
    assert response.status_code == 200
    data = response.json()
    assert "model_id" in data


@pytest.mark.asyncio
async def test_chat_endpoint(client):
    """Test chat endpoint with mocked agent."""

    # Mock the agent's chat method
    async def mock_events(*args, **kwargs):
        yield {"type": "thinking", "status": "thinking"}
        yield {"type": "agent_message", "content": "Test response", "is_chunk": True}

    with patch.object(CoordinatorAgent, "chat", side_effect=lambda *args, **kwargs: mock_events()):
        response = client.post(
            "/api/chat",
            json={"user_id": "test_user", "message": "Hello"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "user_id" in data
        assert "response" in data
        assert "events" in data


def test_get_session(client):
    """Test get session endpoint."""
    response = client.get("/api/session/test_user")
    assert response.status_code == 200
    data = response.json()
    assert "user_id" in data
    assert "messages" in data
    assert "message_count" in data


def test_clear_session(client):
    """Test clear session endpoint."""
    response = client.delete("/api/session/test_user")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] == "success"
