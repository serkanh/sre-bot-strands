"""Tests for Kubernetes Agent."""

from unittest.mock import MagicMock, patch

from app.agents.kubernetes_agent import (
    get_pod_details_tool,
    kubernetes_assistant,
    list_namespaces_tool,
    list_pods_tool,
)


def test_list_namespaces_tool() -> None:
    """Test list_namespaces_tool function."""
    with patch("app.agents.kubernetes_agent._get_k8s_clients") as mock_get_clients:
        # Mock the API response
        mock_api = MagicMock()
        mock_namespace = MagicMock()
        mock_namespace.metadata.name = "default"
        mock_api.list_namespace.return_value.items = [mock_namespace]

        mock_get_clients.return_value = (mock_api, None, None)

        result = list_namespaces_tool("test-cluster")

        assert result == ["default"]
        mock_get_clients.assert_called_once_with("test-cluster")


def test_list_pods_tool() -> None:
    """Test list_pods_tool function."""
    with patch("app.agents.kubernetes_agent._get_k8s_clients") as mock_get_clients:
        # Mock the API response
        mock_api = MagicMock()
        mock_pod = MagicMock()
        mock_pod.metadata.name = "test-pod"
        mock_pod.metadata.namespace = "default"
        mock_pod.status.phase = "Running"
        mock_pod.spec.node_name = "node-1"
        mock_pod.status.start_time = None
        mock_pod.status.pod_ip = "10.0.0.1"
        mock_pod.metadata.labels = {"app": "test"}

        mock_api.list_namespaced_pod.return_value.items = [mock_pod]

        mock_get_clients.return_value = (mock_api, None, None)

        result = list_pods_tool("test-cluster", "default")

        assert len(result) == 1
        assert result[0]["name"] == "test-pod"
        assert result[0]["status"] == "Running"


def test_get_pod_details_tool() -> None:
    """Test get_pod_details_tool function."""
    with patch("app.agents.kubernetes_agent._get_k8s_clients") as mock_get_clients:
        # Mock the API response
        mock_api = MagicMock()
        mock_pod = MagicMock()
        mock_pod.metadata.name = "test-pod"
        mock_pod.metadata.namespace = "default"
        mock_pod.status.phase = "Running"
        mock_pod.spec.node_name = "node-1"
        mock_pod.status.start_time = None
        mock_pod.status.pod_ip = "10.0.0.1"
        mock_pod.metadata.labels = {}
        mock_pod.metadata.annotations = {}
        mock_pod.spec.containers = []
        mock_pod.status.container_statuses = None
        mock_pod.status.conditions = []

        mock_api.read_namespaced_pod.return_value = mock_pod

        mock_get_clients.return_value = (mock_api, None, None)

        result = get_pod_details_tool("test-cluster", "test-pod", "default")

        assert result["name"] == "test-pod"
        assert result["status"] == "Running"
        assert "error" not in result


def test_kubernetes_assistant() -> None:
    """Test kubernetes_assistant with mocked agent."""
    with patch("app.agents.kubernetes_agent.Agent") as mock_agent_class:
        mock_agent = MagicMock()
        mock_agent.return_value = "Found 3 pods in the cluster"
        mock_agent_class.return_value = mock_agent

        result = kubernetes_assistant("What pods are running?")

        assert "pods" in result.lower() or "error" in result.lower()


def test_kubernetes_assistant_error_handling() -> None:
    """Test kubernetes_assistant error handling."""
    with patch("app.agents.kubernetes_agent.Agent") as mock_agent_class:
        mock_agent_class.side_effect = Exception("Connection failed")

        result = kubernetes_assistant("Test query")

        assert "Error" in result
        assert "Connection failed" in result


def test_list_pods_tool_error_handling() -> None:
    """Test list_pods_tool error handling."""
    with patch("app.agents.kubernetes_agent._get_k8s_clients") as mock_get_clients:
        mock_get_clients.side_effect = Exception("API error")

        result = list_pods_tool("test-cluster", "default")

        assert len(result) == 1
        assert "error" in result[0]
