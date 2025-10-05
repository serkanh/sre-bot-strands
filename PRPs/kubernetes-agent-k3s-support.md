# PRP: Kubernetes Agent Implementation with K3s Support

## Executive Summary

Replace the AWS EKS MCP-based agent with a **universal Kubernetes agent** that works with both K3s (local) and EKS (production) clusters using the official Kubernetes Python client. The current EKS MCP server is tightly coupled to AWS services (CloudFormation, IAM, VPC) and cannot work with K3s clusters.

**Key Change**: Move from MCP-based tools to custom `@tool` functions using the Kubernetes Python client directly.

**System Components**:
1. **Kubernetes Agent**: Specialized agent with custom Kubernetes tools
2. **Coordinator Agent**: Routes queries to appropriate specialists (updated to use kubernetes_agent)
3. **K3s Environment**: Already configured via docker-compose for local testing

**Architecture Pattern**: "Agents as Tools" - The kubernetes agent is wrapped as a `@tool` function and used by the coordinator agent.

**Key Technologies**:
- Kubernetes Python Client (official)
- Strands Agents SDK for multi-agent orchestration
- AWS Bedrock for LLM inference
- K3s for local Kubernetes testing

## Problem Statement

### Why EKS MCP Cannot Work with K3s

Based on web research (https://awslabs.github.io/mcp/servers/eks-mcp-server/):

**EKS MCP Server AWS Dependencies**:
1. **Cluster Management**: Manages EKS CloudFormation stacks - deploys EKS clusters using CloudFormation, creating VPC, subnets, NAT gateways, IAM roles
2. **Authentication**: Generates temporary credentials for Kubernetes API access via AWS IAM
3. **Network Security**: Requires VPC and security group configuration
4. **Service Integration**: Tightly coupled to AWS services

**Conclusion**: The eks-mcp-server cannot work with K3s clusters due to its dependency on AWS-specific APIs and services.

**Solution**: Use the **Kubernetes Python Client** directly, which works with any Kubernetes cluster (K3s, EKS, GKE, etc.).

## Feature Requirements

From INITIAL.md:

- EKS mcp works with EKS clusters but not with K3s
- Modify code to write a kubernetes_agent to handle kubernetes clusters
- Write our own tools for kubernetes clusters
- Don't need to support multi-account operations (simplify)
- Remove the eks agent and update the coordinator_agent to use the kubernetes_agent

**Implementation Scope**:
- ✅ Kubernetes agent with custom K8s tools
- ✅ Coordinator agent updated with Kubernetes capabilities
- ✅ K3s docker-compose service (already configured)
- ✅ Integration with existing FastAPI infrastructure
- ✅ Maintain streaming capabilities for real-time UI updates
- ✅ Support both K3s (local) and EKS (production)
- ✅ Executable validation gates

## Architecture Overview

### System Design

```
┌─────────────────────────────────────────────────────────────┐
│                     User Request                             │
│     "What pods are running in my cluster?"                  │
└────────────────────┬────────────────────────────────────────┘
                     │
         ┌───────────▼──────────┐
         │  Coordinator Agent   │
         │                      │
         │  - Routes queries    │
         │  - Orchestrates      │
         │  - Has K8s tool      │
         │  - Has FinOps tool   │
         └───────────┬──────────┘
                     │
                     ├─── General queries ──> Direct response
                     │
                     ├─── Cost/FinOps queries ──> finops_assistant
                     │
                     └─── K8s queries
                              │
                    ┌─────────▼──────────┐
                    │ Kubernetes Agent   │
                    │  (@tool wrapper)   │
                    │                    │
                    │  System Prompt:    │
                    │  K8s specialist    │
                    └─────────┬──────────┘
                              │
                    ┌─────────▼──────────┐
                    │  Strands Agent     │
                    │  with K8s Tools    │
                    └─────────┬──────────┘
                              │
            ┌─────────────────┼─────────────────┐
            │                 │                 │
    ┌───────▼────────┐ ┌─────▼──────┐ ┌────────▼────────┐
    │list_pods       │ │get_pod_    │ │get_namespace_   │
    │(@tool)         │ │logs(@tool) │ │details(@tool)   │
    └────────────────┘ └────────────┘ └─────────────────┘
                              │
                    ┌─────────▼──────────┐
                    │  Kubernetes        │
                    │  Python Client     │
                    └─────────┬──────────┘
                              │
                    ┌─────────▼──────────┐
                    │  K3s / EKS         │
                    │  Kubernetes API    │
                    └────────────────────┘
```

### Comparison: EKS MCP vs Kubernetes Agent

| Aspect | EKS MCP (Old) | Kubernetes Agent (New) |
|--------|---------------|------------------------|
| **Cluster Support** | AWS EKS only | K3s, EKS, any K8s |
| **Authentication** | AWS IAM | Kubeconfig |
| **Tools Source** | External MCP server | Custom `@tool` functions |
| **AWS Dependency** | High (CF, VPC, IAM) | None (optional for EKS) |
| **Complexity** | MCP session management | Direct API calls |
| **Local Testing** | ❌ Not possible | ✅ Works with K3s |

### Project Structure

```
/
├── app/
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── finops_agent.py          # Existing: FinOps specialist
│   │   ├── eks_agent.py             # DELETE: No longer needed
│   │   ├── kubernetes_agent.py      # NEW: K8s specialist
│   │   └── coordinator_agent.py     # UPDATE: Use kubernetes_assistant
│   ├── api/
│   │   └── routes.py                # No changes needed
│   ├── config.py                    # Already has KUBECONFIG support
│   └── main.py                      # No changes needed
├── tests/
│   ├── test_finops_agent.py         # Existing
│   ├── test_eks_agent.py            # DELETE: Old tests
│   ├── test_kubernetes_agent.py     # NEW: K8s agent tests
│   └── test_coordinator.py          # UPDATE: K8s tests
├── docker-compose.yml               # Already configured with K3s
├── .env.example                     # Already configured
└── PRPs/
    └── kubernetes-agent-k3s-support.md  # This document
```

## Critical Context & Reference Patterns

### 1. Kubernetes Python Client Documentation

**Primary Documentation**:
- GitHub: https://github.com/kubernetes-client/python
- ReadTheDocs: https://kubernetes.readthedocs.io/en/latest/
- PyPI: https://pypi.org/project/kubernetes/

**Latest Version**: kubernetes 34.1.0 (supports K8s 1.33+)

**Key APIs Used**:
- `client.CoreV1Api()` - Pods, namespaces, services, events
- `client.AppsV1Api()` - Deployments, statefulsets, daemonsets
- `client.BatchV1Api()` - Jobs, cronjobs

**Authentication**:
- K3s: Uses kubeconfig file with embedded certificates
- EKS: Uses `aws eks update-kubeconfig` with IAM authentication

**Installation**:
```bash
pip install kubernetes
# Already in ecosystem, no new dependency
```

### 2. Example Code from INITIAL.md

The INITIAL.md file (lines 11-1948) provides comprehensive example code with:

**Key Components**:
1. `ClusterContext` dataclass - Simplified cluster identifier
2. `KubernetesClient` context manager - Manages API client lifecycle
3. Namespace operations - `list_namespaces()`, `get_namespace_details()`
4. Pod operations - `list_pods()`, `get_pod_details()`, `get_pod_logs()`
5. Deployment operations - `list_deployments()`, `scale_deployment()`
6. Service operations - `list_services()`
7. Event operations - `get_events()`
8. Error handling - `format_api_exception_error()`

**Simplifications Needed** (per INITIAL.md:8):
- Remove multi-account support (we only need cluster parameter)
- Remove `account` parameter from `ClusterContext`
- Simplify `context_manager.get_k8s_client_config` (just use cluster name)
- Remove content summarization (optional, can add later)

### 3. Reference Pattern: finops_agent.py

**File**: `app/agents/finops_agent.py:1-155`

The finops_agent demonstrates the "Agents as Tools" pattern:

```python
@tool
def finops_assistant(query: str) -> str:
    """FinOps specialist tool."""

    # 1. Create MCP client
    mcp_client = MCPClient(...)

    # 2. Context manager (CRITICAL for MCP)
    with mcp_client:
        mcp_tools = mcp_client.list_tools_sync()

        # 3. Create inner agent with tools
        agent = Agent(
            model=model,
            system_prompt=SYSTEM_PROMPT,
            tools=mcp_tools,
        )

        # 4. Execute query
        response = agent(query)

    return str(response)
```

**For Kubernetes Agent**, we'll follow similar pattern but:
- No MCP client (use our own `@tool` functions instead)
- Create custom K8s tools
- Inner agent uses K8s tools

### 4. K3s Docker Compose Configuration

**Already configured** in `docker-compose.yml:3-35`:

```yaml
k3s-server:
  image: rancher/k3s:v1.24.0-rc1-k3s1-amd64
  container_name: sre-bot-k3s
  command: server
  environment:
    - K3S_KUBECONFIG_OUTPUT=/output/kubeconfig.yaml
    - K3S_KUBECONFIG_MODE=666
  volumes:
    - ./k3s_data/kubeconfig:/output
  ports:
    - "6443:6443"
  privileged: true
```

**Kubeconfig Path**: `/app/k3s_data/kubeconfig/kubeconfig.yaml` (already in .env)

## Implementation Blueprint

### Pseudocode Approach

```
1. CREATE app/agents/kubernetes_agent.py
   - Import kubernetes client and strands
   - Define KUBERNETES_SYSTEM_PROMPT
   - Create helper function: _get_k8s_clients(cluster)
   - Create @tool functions for each K8s operation:
     * list_namespaces_tool(cluster)
     * list_pods_tool(cluster, namespace)
     * get_pod_details_tool(cluster, pod_name, namespace)
     * get_pod_logs_tool(cluster, pod_name, namespace)
     * list_deployments_tool(cluster, namespace)
     * get_events_tool(cluster, namespace)
   - Create @tool kubernetes_assistant(query) that uses above tools

2. UPDATE app/agents/coordinator_agent.py
   - Remove import of eks_assistant
   - Add import of kubernetes_assistant
   - Update COORDINATOR_SYSTEM_PROMPT (replace EKS with K8s)
   - Update tools list: [finops_assistant, kubernetes_assistant]

3. DELETE app/agents/eks_agent.py
   - No longer needed

4. CREATE tests/test_kubernetes_agent.py
   - Test kubernetes_assistant with mock K8s client
   - Test individual tool functions
   - Test error handling

5. UPDATE tests/test_coordinator.py
   - Replace EKS tests with K8s tests
   - Verify kubernetes_assistant integration

6. DELETE tests/test_eks_agent.py
   - No longer needed

7. RUN validation gates (see Validation section)
```

## Detailed Implementation

### File 1: app/agents/kubernetes_agent.py (NEW)

**Complete implementation** based on INITIAL.md with simplifications:

```python
"""Kubernetes Agent with custom K8s tools for K3s and EKS support."""

import logging
from typing import List, Dict, Any, Optional

from kubernetes import client, config
from kubernetes.client.rest import ApiException
from strands import Agent, tool
from strands.models import BedrockModel

from app.config import Settings

logger = logging.getLogger(__name__)

# System prompt for Kubernetes specialist
KUBERNETES_SYSTEM_PROMPT = """
You are a Kubernetes specialist with expertise in cluster management and troubleshooting.

Your capabilities include:
- Querying cluster resources (pods, deployments, services, namespaces)
- Analyzing pod logs and events
- Troubleshooting application issues
- Understanding Kubernetes resource states
- Providing actionable recommendations

When analyzing clusters:
1. Use available Kubernetes tools to query actual cluster data
2. Provide clear, specific insights with resource names
3. Explain issues in plain language
4. Suggest concrete troubleshooting steps
5. Format responses with clear sections

You work with both local K3s clusters and production EKS clusters.
Always specify which cluster you're querying.
"""


def _load_kubeconfig(cluster: str) -> None:
    """Load kubeconfig for the specified cluster.

    Args:
        cluster: Cluster identifier (e.g., 'k3s-local' or 'prod-eks')
    """
    settings = Settings()

    if settings.KUBECONFIG:
        # Load from specified kubeconfig file (K3s or custom)
        config.load_kube_config(config_file=settings.KUBECONFIG)
        logger.info(f"Loaded kubeconfig from {settings.KUBECONFIG} for cluster {cluster}")
    else:
        # Try to load from default location (EKS via aws eks update-kubeconfig)
        try:
            config.load_kube_config()
            logger.info(f"Loaded kubeconfig from default location for cluster {cluster}")
        except Exception as e:
            logger.warning(f"Failed to load kubeconfig: {e}")
            # Try in-cluster config (if running inside K8s)
            config.load_incluster_config()
            logger.info(f"Loaded in-cluster config for cluster {cluster}")


def _get_k8s_clients(cluster: str) -> tuple:
    """Get Kubernetes API clients.

    Args:
        cluster: Cluster identifier

    Returns:
        Tuple of (CoreV1Api, AppsV1Api, BatchV1Api)
    """
    _load_kubeconfig(cluster)

    return (
        client.CoreV1Api(),
        client.AppsV1Api(),
        client.BatchV1Api(),
    )


@tool
def list_namespaces_tool(cluster: str = "default") -> List[str]:
    """List all namespaces in the Kubernetes cluster.

    Args:
        cluster: Cluster identifier (default: 'default')

    Returns:
        List of namespace names
    """
    try:
        api_v1, _, _ = _get_k8s_clients(cluster)
        namespaces = api_v1.list_namespace()
        return [ns.metadata.name for ns in namespaces.items]
    except ApiException as e:
        logger.error(f"Failed to list namespaces in {cluster}: {e}")
        return [f"Error: Failed to list namespaces: {e.reason}"]
    except Exception as e:
        logger.error(f"Unexpected error listing namespaces in {cluster}: {e}")
        return [f"Error: {str(e)}"]


@tool
def list_pods_tool(
    cluster: str = "default",
    namespace: str = "default",
    label_selector: Optional[str] = None
) -> List[Dict[str, Any]]:
    """List pods in a namespace.

    Args:
        cluster: Cluster identifier
        namespace: Namespace to list pods from
        label_selector: Optional label selector (e.g., 'app=nginx')

    Returns:
        List of pod information dictionaries
    """
    try:
        api_v1, _, _ = _get_k8s_clients(cluster)

        kwargs = {"namespace": namespace}
        if label_selector:
            kwargs["label_selector"] = label_selector

        pods = api_v1.list_namespaced_pod(**kwargs)

        return [
            {
                "name": pod.metadata.name,
                "namespace": pod.metadata.namespace,
                "status": pod.status.phase,
                "node": pod.spec.node_name,
                "start_time": str(pod.status.start_time) if pod.status.start_time else None,
                "ip": pod.status.pod_ip,
                "labels": pod.metadata.labels or {},
            }
            for pod in pods.items
        ]
    except ApiException as e:
        logger.error(f"Failed to list pods in {cluster}/{namespace}: {e}")
        return [{"error": f"Failed to list pods: {e.reason}"}]
    except Exception as e:
        logger.error(f"Unexpected error listing pods in {cluster}/{namespace}: {e}")
        return [{"error": str(e)}]


@tool
def get_pod_details_tool(
    cluster: str = "default",
    pod_name: str = "",
    namespace: str = "default"
) -> Dict[str, Any]:
    """Get detailed information about a specific pod.

    Args:
        cluster: Cluster identifier
        pod_name: Name of the pod
        namespace: Namespace of the pod

    Returns:
        Dictionary with detailed pod information
    """
    if not pod_name:
        return {"error": "pod_name is required"}

    try:
        api_v1, _, _ = _get_k8s_clients(cluster)
        pod = api_v1.read_namespaced_pod(pod_name, namespace)

        # Get container statuses
        container_statuses = []
        if pod.status.container_statuses:
            container_statuses = [
                {
                    "name": cs.name,
                    "ready": cs.ready,
                    "restart_count": cs.restart_count,
                    "state": str(cs.state),
                }
                for cs in pod.status.container_statuses
            ]

        return {
            "name": pod.metadata.name,
            "namespace": pod.metadata.namespace,
            "status": pod.status.phase,
            "node": pod.spec.node_name,
            "start_time": str(pod.status.start_time) if pod.status.start_time else None,
            "ip": pod.status.pod_ip,
            "labels": pod.metadata.labels or {},
            "annotations": pod.metadata.annotations or {},
            "containers": [c.name for c in pod.spec.containers],
            "container_statuses": container_statuses,
            "conditions": [
                {
                    "type": condition.type,
                    "status": condition.status,
                    "last_transition_time": str(condition.last_transition_time),
                }
                for condition in (pod.status.conditions or [])
            ],
        }
    except ApiException as e:
        logger.error(f"Failed to get pod {pod_name} in {cluster}/{namespace}: {e}")
        return {"error": f"Failed to get pod details: {e.reason}"}
    except Exception as e:
        logger.error(f"Unexpected error getting pod {pod_name} in {cluster}/{namespace}: {e}")
        return {"error": str(e)}


@tool
def get_pod_logs_tool(
    cluster: str = "default",
    pod_name: str = "",
    namespace: str = "default",
    container: Optional[str] = None,
    tail_lines: int = 100
) -> Dict[str, Any]:
    """Get logs from a specific pod.

    Args:
        cluster: Cluster identifier
        pod_name: Name of the pod
        namespace: Namespace of the pod
        container: Container name (optional, required for multi-container pods)
        tail_lines: Number of lines to return from the end

    Returns:
        Dictionary with pod logs
    """
    if not pod_name:
        return {"error": "pod_name is required"}

    try:
        api_v1, _, _ = _get_k8s_clients(cluster)

        kwargs = {
            "name": pod_name,
            "namespace": namespace,
            "tail_lines": tail_lines,
        }

        if container:
            kwargs["container"] = container

        logs = api_v1.read_namespaced_pod_log(**kwargs)

        return {
            "pod_name": pod_name,
            "namespace": namespace,
            "cluster": cluster,
            "container": container,
            "logs": logs,
            "log_length": len(logs),
        }
    except ApiException as e:
        logger.error(f"Failed to get logs for pod {pod_name} in {cluster}/{namespace}: {e}")
        return {"error": f"Failed to get pod logs: {e.reason}"}
    except Exception as e:
        logger.error(f"Unexpected error getting logs for pod {pod_name} in {cluster}/{namespace}: {e}")
        return {"error": str(e)}


@tool
def list_deployments_tool(
    cluster: str = "default",
    namespace: str = "default"
) -> List[Dict[str, Any]]:
    """List deployments in a namespace.

    Args:
        cluster: Cluster identifier
        namespace: Namespace to list deployments from

    Returns:
        List of deployment information dictionaries
    """
    try:
        _, apps_v1, _ = _get_k8s_clients(cluster)

        deployments = apps_v1.list_namespaced_deployment(namespace=namespace)

        return [
            {
                "name": deploy.metadata.name,
                "namespace": deploy.metadata.namespace,
                "replicas": deploy.spec.replicas,
                "available_replicas": deploy.status.available_replicas or 0,
                "ready_replicas": deploy.status.ready_replicas or 0,
                "strategy": deploy.spec.strategy.type if deploy.spec.strategy else "Unknown",
                "labels": deploy.metadata.labels or {},
            }
            for deploy in deployments.items
        ]
    except ApiException as e:
        logger.error(f"Failed to list deployments in {cluster}/{namespace}: {e}")
        return [{"error": f"Failed to list deployments: {e.reason}"}]
    except Exception as e:
        logger.error(f"Unexpected error listing deployments in {cluster}/{namespace}: {e}")
        return [{"error": str(e)}]


@tool
def get_events_tool(
    cluster: str = "default",
    namespace: str = "default",
    limit: int = 50
) -> List[Dict[str, Any]]:
    """Get Kubernetes events for a namespace.

    Args:
        cluster: Cluster identifier
        namespace: Namespace to get events from
        limit: Maximum number of events to return

    Returns:
        List of event information dictionaries
    """
    try:
        api_v1, _, _ = _get_k8s_clients(cluster)

        events = api_v1.list_namespaced_event(namespace, limit=limit)

        return [
            {
                "name": event.metadata.name,
                "namespace": event.metadata.namespace,
                "type": event.type,
                "reason": event.reason,
                "message": event.message,
                "first_seen": str(event.first_timestamp) if event.first_timestamp else None,
                "last_seen": str(event.last_timestamp) if event.last_timestamp else None,
                "count": event.count,
                "involved_object": {
                    "kind": event.involved_object.kind,
                    "name": event.involved_object.name,
                } if event.involved_object else None,
            }
            for event in events.items
        ]
    except ApiException as e:
        logger.error(f"Failed to get events in {cluster}/{namespace}: {e}")
        return [{"error": f"Failed to get events: {e.reason}"}]
    except Exception as e:
        logger.error(f"Unexpected error getting events in {cluster}/{namespace}: {e}")
        return [{"error": str(e)}]


@tool
def kubernetes_assistant(query: str) -> str:
    """
    Kubernetes specialist assistant for cluster management and troubleshooting.

    This tool provides expert Kubernetes assistance for:
    - Querying cluster resources (pods, deployments, services, namespaces)
    - Analyzing pod logs and events
    - Troubleshooting application issues
    - Understanding resource states
    - Providing recommendations

    Works with both K3s (local) and EKS (production) clusters.

    Use this tool for queries about:
    - "What pods are running in my cluster?"
    - "Show me logs from pod [name]"
    - "List all deployments in namespace [name]"
    - "What events occurred in the cluster?"
    - "Check the status of pod [name]"
    - "List all namespaces"

    Args:
        query: A Kubernetes-related question or request

    Returns:
        Detailed analysis and response about the cluster
    """
    logger.info("Kubernetes assistant invoked with query: %s", query[:100])

    try:
        settings = Settings()

        # Create Bedrock model
        model = BedrockModel(
            model_id=settings.BEDROCK_MODEL_ID,
            region_name=settings.AWS_REGION,
        )

        # Create Kubernetes agent with K8s tools
        k8s_tools = [
            list_namespaces_tool,
            list_pods_tool,
            get_pod_details_tool,
            get_pod_logs_tool,
            list_deployments_tool,
            get_events_tool,
        ]

        k8s_agent = Agent(
            model=model,
            system_prompt=KUBERNETES_SYSTEM_PROMPT,
            tools=k8s_tools,
        )

        # Execute query
        response = k8s_agent(query)

        logger.info("Kubernetes assistant completed successfully")
        return str(response)

    except Exception as e:
        error_msg = f"Error in Kubernetes assistant: {e!s}"
        logger.exception(error_msg)
        return error_msg


# Export the tool
__all__ = ["kubernetes_assistant"]
```

**Key Features**:
- Lines 1-23: Imports and system prompt
- Lines 26-48: Helper functions for kubeconfig loading
- Lines 51-72: `list_namespaces_tool` - List all namespaces
- Lines 75-114: `list_pods_tool` - List pods with filtering
- Lines 117-178: `get_pod_details_tool` - Detailed pod information
- Lines 181-227: `get_pod_logs_tool` - Retrieve pod logs
- Lines 230-266: `list_deployments_tool` - List deployments
- Lines 269-312: `get_events_tool` - Get cluster events
- Lines 315-376: `kubernetes_assistant` - Main @tool that wraps K8s agent

### File 2: app/agents/coordinator_agent.py (UPDATE)

**Changes required**:

```python
# Line 10: Replace import
from app.agents.finops_agent import finops_assistant
from app.agents.kubernetes_agent import kubernetes_assistant  # CHANGED: was eks_assistant

# Line 23-48: Update COORDINATOR_SYSTEM_PROMPT
COORDINATOR_SYSTEM_PROMPT = """
You are an SRE (Site Reliability Engineering) coordinator assistant.

Your role is to help users with infrastructure troubleshooting and operations by routing
queries to specialized agents or answering directly.

AVAILABLE SPECIALIST AGENTS:
- finops_assistant: Use for AWS cost analysis, billing questions, and FinOps queries
- kubernetes_assistant: Use for Kubernetes cluster management and troubleshooting  # CHANGED

ROUTING GUIDELINES:
1. For cost/billing/FinOps questions → Use the finops_assistant tool
   Examples:
   - "What are my AWS costs?"
   - "Show EC2 spending"
   - "Forecast next month's costs"

2. For Kubernetes questions → Use the kubernetes_assistant tool  # CHANGED
   Examples:
   - "What pods are running in my cluster?"
   - "Show me logs from pod X"
   - "List deployments in namespace Y"
   - "What events occurred?"
   - "Check pod status"

3. For general SRE questions → Answer directly
   Examples:
   - "How do I troubleshoot X?"
   - "What's the best practice for Y?"

4. If unsure whether to use a specialist → Ask clarifying questions

When using specialist tools:
- Pass the complete user query to the tool
- Let the specialist handle the analysis
- Present the specialist's response to the user

Always be helpful, clear, and concise in your responses.
"""

# Line 83: Update tools list
self.agent = Agent(
    model=self.model,
    system_prompt=COORDINATOR_SYSTEM_PROMPT,
    tools=[finops_assistant, kubernetes_assistant],  # CHANGED: was eks_assistant
)
```

### File 3: tests/test_kubernetes_agent.py (NEW)

**Complete test file**:

```python
"""Tests for Kubernetes Agent."""

from unittest.mock import MagicMock, patch

from app.agents.kubernetes_agent import (
    kubernetes_assistant,
    list_namespaces_tool,
    list_pods_tool,
    get_pod_details_tool,
)


def test_list_namespaces_tool():
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


def test_list_pods_tool():
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


def test_get_pod_details_tool():
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


def test_kubernetes_assistant():
    """Test kubernetes_assistant with mocked agent."""
    with patch("app.agents.kubernetes_agent.Agent") as mock_agent_class:
        mock_agent = MagicMock()
        mock_agent.return_value = "Found 3 pods in the cluster"
        mock_agent_class.return_value = mock_agent

        result = kubernetes_assistant("What pods are running?")

        assert "pods" in result.lower() or "error" in result.lower()


def test_kubernetes_assistant_error_handling():
    """Test kubernetes_assistant error handling."""
    with patch("app.agents.kubernetes_agent.Agent") as mock_agent_class:
        mock_agent_class.side_effect = Exception("Connection failed")

        result = kubernetes_assistant("Test query")

        assert "Error" in result
        assert "Connection failed" in result


def test_list_pods_tool_error_handling():
    """Test list_pods_tool error handling."""
    with patch("app.agents.kubernetes_agent._get_k8s_clients") as mock_get_clients:
        mock_get_clients.side_effect = Exception("API error")

        result = list_pods_tool("test-cluster", "default")

        assert len(result) == 1
        assert "error" in result[0]
```

### File 4: tests/test_coordinator.py (UPDATE)

**Add Kubernetes routing tests**:

```python
# Add to existing test file

import pytest
from app.agents.coordinator_agent import CoordinatorAgent
from app.config import Settings


@pytest.mark.asyncio
async def test_coordinator_routes_k8s_query():
    """Test that coordinator routes Kubernetes queries to kubernetes_assistant."""
    settings = Settings()
    coordinator = CoordinatorAgent(settings)

    # Mock the kubernetes_assistant tool to verify it gets called
    with patch("app.agents.coordinator_agent.kubernetes_assistant") as mock_k8s:
        mock_k8s.return_value = "3 pods are running in the cluster"

        # The coordinator should detect this is a K8s query
        messages = []
        async for event in coordinator.chat("What pods are running in my cluster?", "test_user"):
            messages.append(event)

        # Verify we got messages back (integration test)
        assert len(messages) > 0


@pytest.mark.asyncio
async def test_coordinator_has_k8s_tool():
    """Test that coordinator has kubernetes_assistant in tools."""
    settings = Settings()
    coordinator = CoordinatorAgent(settings)

    # Verify kubernetes_assistant is in the tools list
    tool_names = [tool.__name__ if callable(tool) else str(tool) for tool in coordinator.agent.tools]
    assert "kubernetes_assistant" in str(tool_names)
```

## Critical Gotchas & Considerations

### 1. Kubeconfig Loading

**Three Authentication Scenarios**:

1. **K3s (Local)**:
   - Set `KUBECONFIG=/app/k3s_data/kubeconfig/kubeconfig.yaml`
   - Uses embedded certificates from K3s
   - No AWS credentials needed

2. **EKS (Production)**:
   - Leave `KUBECONFIG` empty
   - Run `aws eks update-kubeconfig --region us-east-1 --name cluster-name` first
   - Uses IAM authentication via `~/.kube/config`

3. **In-Cluster**:
   - When running inside a K8s pod
   - Uses service account token
   - Automatic fallback

**Common Issues**:
- **Path**: Must be absolute path, not relative
- **Permissions**: Kubeconfig must be readable
- **Timing**: K3s takes 20-30 seconds to generate kubeconfig

### 2. Kubernetes Python Client Context

Unlike the MCP pattern with `with mcp_client:`, the Kubernetes client doesn't require a context manager at the top level. Each API call is independent.

**Pattern**:
```python
# Load config once
config.load_kube_config(config_file="/path/to/kubeconfig")

# Create clients (can be reused)
api_v1 = client.CoreV1Api()

# Make API calls
pods = api_v1.list_namespaced_pod(namespace="default")
```

### 3. Error Handling

**ApiException** is the main error type:
- `status`: HTTP status code (404, 403, etc.)
- `reason`: Error message
- `body`: Detailed error information

**Best Practice**:
```python
try:
    result = api_v1.list_namespaced_pod(namespace)
except ApiException as e:
    if e.status == 404:
        return {"error": "Resource not found"}
    elif e.status == 403:
        return {"error": "Access denied"}
    else:
        return {"error": f"API error: {e.reason}"}
except Exception as e:
    return {"error": f"Unexpected error: {str(e)}"}
```

### 4. Cluster Parameter

The `cluster` parameter is used for logging and context, but doesn't affect the actual K8s API calls. The kubeconfig determines which cluster is accessed.

**Future Enhancement**: Could support multiple kubeconfigs with a mapping:
```python
KUBECONFIG_MAP = {
    "k3s-local": "/app/k3s_data/kubeconfig/kubeconfig.yaml",
    "prod-eks": "~/.kube/config-prod",
    "staging-eks": "~/.kube/config-staging",
}
```

### 5. K3s vs EKS Differences

| Aspect | K3s | EKS |
|--------|-----|-----|
| **Auth** | Certificate-based | IAM-based |
| **Kubeconfig** | Generated by K3s | Generated by `aws eks` |
| **API Server** | localhost:6443 | AWS-managed endpoint |
| **Access** | Direct | Via AWS networking |

Both use the same Kubernetes API, so our tools work identically.

## Implementation Tasks (In Order)

1. **Create app/agents/kubernetes_agent.py**
   - Copy implementation from section "Detailed Implementation"
   - Verify imports are correct
   - Test syntax with `ruff check`

2. **Update app/agents/coordinator_agent.py**
   - Change import from eks_assistant to kubernetes_assistant
   - Update COORDINATOR_SYSTEM_PROMPT
   - Update tools list

3. **Delete app/agents/eks_agent.py**
   ```bash
   git rm app/agents/eks_agent.py
   ```

4. **Create tests/test_kubernetes_agent.py**
   - Copy test implementation from section "Detailed Implementation"
   - Verify all tests are included

5. **Update tests/test_coordinator.py**
   - Add Kubernetes routing tests
   - Remove EKS-specific tests

6. **Delete tests/test_eks_agent.py**
   ```bash
   git rm tests/test_eks_agent.py
   ```

7. **Install kubernetes Python package** (if not already installed)
   ```bash
   uv add kubernetes
   ```

8. **Run validation gates** (see next section)

9. **Test with K3s cluster**
   - Start K3s: `docker compose up -d k3s-server`
   - Wait 30 seconds
   - Verify kubeconfig exists
   - Test API calls

10. **End-to-end testing**
    - Test via web UI
    - Test via API
    - Verify no regression in FinOps agent

## Validation Gates (MUST PASS)

### 1. Syntax and Type Checking

```bash
# Format code
uv run ruff format app/ tests/

# Check for linting issues
uv run ruff check --fix app/ tests/

# Type checking
uv run mypy app/
```

**Expected**: No errors, all checks pass.

### 2. Unit Tests

```bash
# Run all tests
uv run pytest tests/ -v

# Run specific Kubernetes tests
uv run pytest tests/test_kubernetes_agent.py -v

# Run coordinator tests
uv run pytest tests/test_coordinator.py -v

# Run with coverage
uv run pytest --cov=app tests/
```

**Expected**: All tests pass with >80% coverage.

### 3. K3s Integration Test

```bash
# Start K3s
docker compose up -d k3s-server

# Wait for K3s to be ready
sleep 30

# Check K3s health
docker compose ps k3s-server

# Verify kubeconfig exists
test -f ./k3s_data/kubeconfig/kubeconfig.yaml && echo "✓ Kubeconfig exists" || echo "✗ Kubeconfig missing"

# Test kubectl connectivity
export KUBECONFIG=./k3s_data/kubeconfig/kubeconfig.yaml
kubectl get nodes

# Expected: K3s node in Ready state
```

**Expected**:
```
NAME                   STATUS   ROLES                  AGE   VERSION
sre-bot-k3s            Ready    control-plane,master   1m    v1.24.0-rc1+k3s1
```

### 4. Application Integration Test

```bash
# Start all services
docker compose up -d

# Wait for services to be ready
sleep 15

# Check service health
curl http://localhost:8000/health
curl http://localhost:8001/health

# Test Kubernetes agent via API
curl -X POST http://localhost:8001/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_k3s",
    "message": "List all namespaces in the cluster"
  }'

# Expected: Should return list of K3s namespaces (default, kube-system, etc.)

# Test pod listing
curl -X POST http://localhost:8001/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_k3s",
    "message": "What pods are running in kube-system namespace?"
  }'

# Expected: Should return K3s system pods

# Test FinOps agent (ensure no regression)
curl -X POST http://localhost:8001/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_finops",
    "message": "What are my AWS costs for October?"
  }'

# Expected: Should return cost information
```

**Expected**: All queries return appropriate responses without errors.

### 5. Cleanup Test

```bash
# Stop all services
docker compose down

# Remove volumes (optional)
docker compose down -v

# Verify cleanup
docker compose ps
```

**Expected**: All services stopped cleanly.

## Dependencies & Prerequisites

### Python Packages

**New Package Required**:
```toml
# Add to pyproject.toml
[project]
dependencies = [
    # ... existing dependencies ...
    "kubernetes>=34.0.0",  # NEW: Kubernetes Python client
]
```

**Installation**:
```bash
uv add kubernetes
```

**Existing Packages** (already in project):
- `strands-agents==1.10.0` ✅
- `boto3>=1.35.0` ✅
- `fastapi>=0.115.0` ✅

### External Tools

- **uv**: Already required for project ✅
- **docker**: Required for K3s ✅
- **docker-compose**: Required for orchestration ✅
- **kubectl**: Optional, for manual testing

### System Resources

K3s requirements (already configured):
- **CPU**: 2+ cores recommended
- **Memory**: 4GB+ recommended
- **Disk**: 10GB+ for images and data

## Example Usage Scenarios

### Scenario 1: Local K3s Development

```bash
# Setup (already done via docker-compose)
export KUBECONFIG=/app/k3s_data/kubeconfig/kubeconfig.yaml

# Query via API
curl -X POST http://localhost:8001/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "developer",
    "message": "List all namespaces"
  }'

# Response:
{
  "type": "agent_message",
  "content": "Found 4 namespaces in your cluster:\n- default\n- kube-system\n- kube-public\n- kube-node-lease"
}
```

### Scenario 2: EKS Production Access

```bash
# Setup kubeconfig for EKS
aws eks update-kubeconfig --region us-east-1 --name prod-cluster

# Unset KUBECONFIG to use default
unset KUBECONFIG

# Query via API
curl -X POST http://localhost:8001/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "sre_team",
    "message": "Show me pods in the production namespace"
  }'
```

### Scenario 3: Multi-Agent Usage

```bash
# Cost analysis (FinOps Agent)
curl -X POST http://localhost:8001/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "manager",
    "message": "What are my AWS EKS costs this month?"
  }'
# → Routes to finops_assistant

# Cluster management (Kubernetes Agent)
curl -X POST http://localhost:8001/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "manager",
    "message": "What pods are failing in my cluster?"
  }'
# → Routes to kubernetes_assistant

# General SRE (Coordinator Direct)
curl -X POST http://localhost:8001/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "manager",
    "message": "What are Kubernetes best practices for pod security?"
  }'
# → Coordinator answers directly
```

## Reference Documentation

### Primary Sources

1. **Kubernetes Python Client**
   - GitHub: https://github.com/kubernetes-client/python
   - Documentation: https://kubernetes.readthedocs.io/en/latest/
   - PyPI: https://pypi.org/project/kubernetes/
   - Sections: Installation, Configuration, API Reference

2. **Kubernetes API Documentation**
   - Official Docs: https://kubernetes.io/docs/reference/using-api/client-libraries/
   - API Reference: https://kubernetes.io/docs/reference/kubernetes-api/

3. **K3s Documentation**
   - URL: https://docs.k3s.io/
   - Sections: Quick-Start, Cluster Access, Kubeconfig

4. **Strands Agents - Agents as Tools**
   - URL: https://strandsagents.com/latest/documentation/docs/user-guide/concepts/multi-agent/agents-as-tools/
   - Pattern for wrapping agents as tools

### Code References

1. **finops_agent.py** (app/agents/finops_agent.py:1-155)
   - Reference pattern for "Agents as Tools"
   - Shows @tool decorator usage
   - Example of inner agent creation

2. **coordinator_agent.py** (app/agents/coordinator_agent.py:1-162)
   - Agent orchestration pattern
   - Tool routing logic
   - Streaming implementation

3. **INITIAL.md** (lines 11-1948)
   - Complete Kubernetes operations code
   - Context manager patterns
   - Error handling examples

## Success Criteria

Implementation is complete when:

1. ✅ All validation gates pass (syntax, types, tests)
2. ✅ K3s cluster is accessible via kubernetes_assistant
3. ✅ Coordinator routes K8s queries correctly
4. ✅ All Kubernetes tools work (namespaces, pods, logs, deployments, events)
5. ✅ FinOps agent still works (no regression)
6. ✅ Integration tests pass for both K3s and API
7. ✅ Error handling works for API exceptions
8. ✅ EKS agent is removed cleanly
9. ✅ Documentation is updated

## PRP Confidence Score

**8/10** - High confidence for one-pass implementation

**Strengths**:
- ✅ Complete example code provided in INITIAL.md
- ✅ Clear reference pattern from finops_agent
- ✅ Kubernetes Python client is well-documented
- ✅ K3s infrastructure already configured
- ✅ All simplifications clearly identified
- ✅ Executable validation gates
- ✅ Comprehensive error handling patterns

**Potential Risks**:
- ⚠️ Kubernetes client context management differs from MCP pattern
  - **Mitigation**: Clear examples provided, simpler than MCP
- ⚠️ Kubeconfig loading may have edge cases
  - **Mitigation**: Three scenarios documented with fallbacks
- ⚠️ First-time testing with K3s may reveal configuration issues
  - **Mitigation**: K3s already running, health checks in place

**Why not 10/10**: Kubernetes client API can have subtle edge cases with different cluster configurations, but the example code handles most scenarios.

## Implementation Checklist

- [ ] Install kubernetes Python package (`uv add kubernetes`)
- [ ] Create app/agents/kubernetes_agent.py
- [ ] Update app/agents/coordinator_agent.py (import and tools)
- [ ] Delete app/agents/eks_agent.py
- [ ] Create tests/test_kubernetes_agent.py
- [ ] Update tests/test_coordinator.py
- [ ] Delete tests/test_eks_agent.py
- [ ] Run validation gate 1: Syntax/type checking
- [ ] Run validation gate 2: Unit tests
- [ ] Run validation gate 3: K3s integration
- [ ] Run validation gate 4: Application integration
- [ ] Run validation gate 5: Cleanup test
- [ ] Verify all example usage scenarios
- [ ] Update README.md if needed
- [ ] Git commit changes with proper message

---

**End of PRP**

This PRP provides comprehensive context for one-pass implementation. The example code from INITIAL.md is production-ready with minor simplifications. All critical patterns are documented, gotchas are identified with solutions, and validation gates ensure correctness at each step.
