"""Tests for FinOps Agent."""

from unittest.mock import MagicMock, patch

from app.agents.finops_agent import finops_assistant


@patch("app.agents.finops_agent.MCPClient")
@patch("app.agents.finops_agent.Agent")
@patch("app.agents.finops_agent.BedrockModel")
def test_finops_assistant_basic_query(mock_bedrock_model, mock_agent_class, mock_mcp_client):
    """Test FinOps assistant handles basic cost query."""
    # Setup mocks
    mock_mcp_instance = MagicMock()
    mock_mcp_client.return_value = mock_mcp_instance
    mock_mcp_instance.list_tools_sync.return_value = [
        {"name": "get_cost_and_usage", "description": "Get cost data"}
    ]

    mock_agent_instance = MagicMock()
    mock_agent_instance.return_value = "Your AWS costs for last month were $1,234.56"
    mock_agent_class.return_value = mock_agent_instance

    # Test query
    result = finops_assistant("What are my AWS costs for last month?")

    # Verify
    assert "costs" in result.lower()
    mock_mcp_instance.list_tools_sync.assert_called_once()
    mock_agent_class.assert_called_once()


@patch("app.agents.finops_agent.MCPClient")
def test_finops_assistant_mcp_error_handling(mock_mcp_client):
    """Test FinOps assistant handles MCP connection errors."""
    # Simulate MCP connection error
    mock_mcp_client.side_effect = Exception("MCP connection failed")

    # Test query
    result = finops_assistant("What are my costs?")

    # Verify error is handled gracefully
    assert "Error" in result
    assert "FinOps assistant" in result


@patch("app.agents.finops_agent.MCPClient")
@patch("app.agents.finops_agent.Agent")
@patch("app.agents.finops_agent.BedrockModel")
def test_finops_assistant_forecast_query(mock_bedrock_model, mock_agent_class, mock_mcp_client):
    """Test FinOps assistant handles forecast queries."""
    # Setup mocks
    mock_mcp_instance = MagicMock()
    mock_mcp_client.return_value = mock_mcp_instance
    mock_mcp_instance.list_tools_sync.return_value = [
        {"name": "get_cost_forecast", "description": "Forecast costs"}
    ]

    mock_agent_instance = MagicMock()
    mock_agent_instance.return_value = "Forecasted costs: $1,500 for next month"
    mock_agent_class.return_value = mock_agent_instance

    # Test forecast query
    result = finops_assistant("Forecast my AWS costs for next month")

    # Verify forecast response
    assert "forecast" in result.lower() or "$" in result
    mock_mcp_instance.list_tools_sync.assert_called_once()
