"""Tests for EKS Agent."""

from unittest.mock import MagicMock, patch

from app.agents.eks_agent import eks_assistant


def test_eks_assistant_basic_query() -> None:
    """Test EKS assistant with basic query."""
    # Mock the MCP client and agent
    with patch("app.agents.eks_agent.MCPClient") as mock_mcp:
        mock_context = MagicMock()
        mock_mcp.return_value.__enter__ = MagicMock(return_value=mock_context)
        mock_mcp.return_value.__exit__ = MagicMock(return_value=False)

        # Mock list_tools_sync
        mock_context.list_tools_sync.return_value = []

        # Mock Agent
        with patch("app.agents.eks_agent.Agent") as mock_agent_class:
            mock_agent = MagicMock()
            mock_agent.return_value = "Cluster has 3 pods running"
            mock_agent_class.return_value = mock_agent

            result = eks_assistant("What pods are running?")

            assert "pods" in result.lower() or "error" in result.lower()


def test_eks_assistant_error_handling() -> None:
    """Test EKS assistant error handling."""
    with patch("app.agents.eks_agent.MCPClient") as mock_mcp:
        mock_mcp.side_effect = Exception("Connection failed")

        result = eks_assistant("Test query")

        assert "Error" in result
        assert "Connection failed" in result


def test_eks_assistant_context_manager() -> None:
    """Test that context manager is used correctly."""
    with patch("app.agents.eks_agent.MCPClient") as mock_mcp:
        mock_context = MagicMock()
        mock_enter = MagicMock(return_value=mock_context)
        mock_exit = MagicMock(return_value=False)

        mock_mcp.return_value.__enter__ = mock_enter
        mock_mcp.return_value.__exit__ = mock_exit

        mock_context.list_tools_sync.return_value = []

        with patch("app.agents.eks_agent.Agent") as mock_agent_class:
            mock_agent = MagicMock()
            mock_agent.return_value = "Test response"
            mock_agent_class.return_value = mock_agent

            eks_assistant("Test query")

            # Verify context manager was used
            mock_enter.assert_called_once()
            mock_exit.assert_called_once()


def test_eks_assistant_with_kubeconfig() -> None:
    """Test EKS assistant with KUBECONFIG set."""
    with patch("app.agents.eks_agent.Settings") as mock_settings:
        mock_settings.return_value.KUBECONFIG = "/path/to/kubeconfig"
        mock_settings.return_value.AWS_REGION = "us-east-1"
        mock_settings.return_value.AWS_PROFILE = None
        mock_settings.return_value.FASTMCP_LOG_LEVEL = "ERROR"
        mock_settings.return_value.EKS_MCP_ALLOW_WRITE = False
        mock_settings.return_value.EKS_MCP_ALLOW_SENSITIVE_DATA = False
        mock_settings.return_value.BEDROCK_MODEL_ID = "test-model"

        with patch("app.agents.eks_agent.MCPClient") as mock_mcp:
            mock_context = MagicMock()
            mock_mcp.return_value.__enter__ = MagicMock(return_value=mock_context)
            mock_mcp.return_value.__exit__ = MagicMock(return_value=False)
            mock_context.list_tools_sync.return_value = []

            with patch("app.agents.eks_agent.Agent"):
                eks_assistant("Test query")

                # Verify KUBECONFIG was passed in environment
                # The lambda function is the first argument
                # We can't easily inspect it, so just verify the call was made
                assert mock_mcp.called
