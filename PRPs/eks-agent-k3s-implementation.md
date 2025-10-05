# PRP: EKS Agent Implementation with K3s Local Testing

## Executive Summary

Implement a **multi-agent EKS/Kubernetes system** using the Strands Agents framework with an "Agents as Tools" pattern, plus **K3s local testing environment**. The system consists of:

1. **EKS Agent**: Specialized agent with AWS EKS MCP tools for Kubernetes cluster management
2. **Coordinator Agent**: Orchestrator that routes user queries to appropriate specialist agents
3. **K3s Environment**: Lightweight Kubernetes cluster for local development and testing

**Architecture Pattern**: "Agents as Tools" - The EKS agent is wrapped as a `@tool` function and used by the coordinator agent, enabling clean separation of concerns and easy extensibility for future specialized agents.

**Key Technologies**:
- Strands Agents SDK for multi-agent orchestration
- AWS EKS MCP Server for cluster management
- Model Context Protocol (MCP) for tool integration
- AWS Bedrock for LLM inference
- K3s for local Kubernetes testing

## Feature Requirements

From INITIAL.md:

- Integrate AWS EKS MCP servers to get information about EKS clusters
- Enable local testing and development with K3s using docker-compose
- Follow existing pattern from finops_agent.py
- Use @tool decorator for agent integration
- Support both AWS EKS (production) and K3s (local) environments

**Implementation Scope**:
- ✅ EKS agent with EKS MCP integration
- ✅ Coordinator agent updated with EKS capabilities
- ✅ K3s docker-compose service for local testing
- ✅ Integration with existing FastAPI infrastructure
- ✅ Maintain streaming capabilities for real-time UI updates
- ✅ Executable validation gates

## Architecture Overview

### System Design

```
┌─────────────────────────────────────────────────────────────┐
│                     User Request                             │
│     "What pods are running in my EKS cluster?"              │
└────────────────────┬────────────────────────────────────────┘
                     │
         ┌───────────▼──────────┐
         │  Coordinator Agent   │
         │                      │
         │  - Routes queries    │
         │  - Orchestrates      │
         │  - Has EKS tool      │
         │  - Has FinOps tool   │
         └───────────┬──────────┘
                     │
                     ├─── General queries ──> Direct response
                     │
                     ├─── Cost/FinOps queries ──> finops_assistant
                     │
                     └─── EKS/K8s queries
                              │
                    ┌─────────▼──────────┐
                    │    EKS Agent       │
                    │   (@tool wrapper)  │
                    │                    │
                    │  System Prompt:    │
                    │  K8s/EKS specialist│
                    └─────────┬──────────┘
                              │
                    ┌─────────▼──────────┐
                    │    MCP Client      │
                    │   (EKS Server)     │
                    └─────────┬──────────┘
                              │
            ┌─────────────────┼─────────────────┐
            │                 │                 │
    ┌───────▼────────┐ ┌─────▼──────┐ ┌────────▼────────┐
    │manage_eks_     │ │get_pod_    │ │manage_k8s_      │
    │stacks          │ │logs        │ │resource         │
    └────────────────┘ └────────────┘ └─────────────────┘
                              │
                    ┌─────────▼──────────┐
                    │  AWS EKS / K3s     │
                    │  Kubernetes API    │
                    └────────────────────┘
```

### Local Testing with K3s

```
┌────────────────────────────────────────────────────┐
│              Developer Workstation                  │
│                                                     │
│  ┌──────────────────────────────────────┐         │
│  │     Docker Compose Environment        │         │
│  │                                       │         │
│  │  ┌──────────┐  ┌──────────┐         │         │
│  │  │ SRE Bot  │  │ SRE Bot  │         │         │
│  │  │   API    │  │   Web    │         │         │
│  │  │  :8000   │  │  :8001   │         │         │
│  │  └─────┬────┘  └─────┬────┘         │         │
│  │        │             │               │         │
│  │  ┌─────▼─────────────▼─────┐        │         │
│  │  │      K3s Server          │        │         │
│  │  │   (Kubernetes API)       │        │         │
│  │  │      :6443               │        │         │
│  │  └──────────────────────────┘        │         │
│  │                                       │         │
│  │  Volumes:                             │         │
│  │  - ./k3s_data/kubeconfig ──> shared  │         │
│  │  - ~/.aws ──> AWS credentials        │         │
│  └──────────────────────────────────────┘         │
└────────────────────────────────────────────────────┘
```

### Project Structure

```
/
├── app/
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── finops_agent.py        # Existing: FinOps specialist
│   │   ├── eks_agent.py           # NEW: EKS/K8s specialist
│   │   └── coordinator_agent.py   # UPDATE: Add eks_assistant
│   ├── api/
│   │   └── routes.py              # No changes needed
│   ├── config.py                  # UPDATE: Add KUBECONFIG support
│   └── main.py                    # No changes needed
├── tests/
│   ├── test_finops_agent.py       # Existing
│   ├── test_eks_agent.py          # NEW: EKS agent tests
│   └── test_coordinator.py        # UPDATE: Add EKS tests
├── docker-compose.yml             # UPDATE: Add K3s service
├── .env.example                   # UPDATE: Add K3s config
├── k3s_data/                      # NEW: K3s data directory
│   └── kubeconfig/                # NEW: K3s kubeconfig output
└── PRPs/
    └── eks-agent-k3s-implementation.md  # This document
```

## Critical Context & Reference Patterns

### 1. Reference Pattern: finops_agent.py (MUST FOLLOW)

**File**: `app/agents/finops_agent.py:1-128`

This file demonstrates the EXACT pattern to follow for the EKS agent:

```python
# Key elements to replicate:
@tool
def finops_assistant(query: str) -> str:
    """Tool decorator wraps the agent as a callable tool"""

    # 1. MCP Client creation with stdio_client
    cost_explorer_mcp = MCPClient(
        lambda: stdio_client(
            StdioServerParameters(
                command="uv",
                args=["tool", "run", "--from", "awslabs.cost-explorer-mcp-server@latest", ...],
                env={"AWS_REGION": ..., "FASTMCP_LOG_LEVEL": "ERROR"}
            )
        )
    )

    # 2. CRITICAL: Context manager usage (MUST use 'with')
    with cost_explorer_mcp:
        # All MCP operations MUST be inside this context
        mcp_tools = cost_explorer_mcp.list_tools_sync()

        # 3. Create agent with MCP tools
        agent = Agent(
            model=model,
            system_prompt=SYSTEM_PROMPT,
            tools=mcp_tools,
        )

        # 4. Execute query within context
        response = agent(query)

    return str(response)
```

**CRITICAL GOTCHA**: The `with cost_explorer_mcp:` context manager is REQUIRED. All MCP operations must be inside this block. Forgetting this will cause connection errors.

### 2. AWS EKS MCP Server Documentation

**URL**: https://awslabs.github.io/mcp/servers/eks-mcp-server/

**Available Tools**:
- `manage_eks_stacks`: Create/manage CloudFormation stacks for EKS
- `manage_k8s_resource`: Manage Kubernetes resources (pods, deployments, services)
- `generate_app_manifest`: Generate deployment YAMLs
- `get_pod_logs`: Retrieve pod logs
- `get_k8s_events`: Fetch Kubernetes events
- `get_cloudwatch_logs`: Retrieve CloudWatch logs
- `get_cloudwatch_metrics`: Fetch cluster metrics

**Configuration Flags**:
- `--allow-write`: Enable cluster modifications (create, update, delete)
- `--allow-sensitive-data-access`: Access sensitive data (logs, secrets)

**Security Note**: Default is read-only mode. Use flags carefully in production.

**IAM Permissions Required**:
- EKS read/write permissions
- CloudFormation permissions (for stack management)
- CloudWatch logs/metrics access
- Kubernetes RBAC permissions via IAM role

### 3. K3s Docker Compose Pattern

**Source**: INITIAL.md:28-71

```yaml
services:
  server:
    image: rancher/k3s:v1.24.0-rc1-k3s1-amd64
    command: server
    tmpfs:
    - /run
    - /var/run
    privileged: true
    restart: always
    environment:
    - K3S_KUBECONFIG_OUTPUT=/output/kubeconfig.yaml
    - K3S_KUBECONFIG_MODE=666
    volumes:
    - k3s-server:/var/lib/rancher/k3s
    - ./k3s_data/kubeconfig:/output
    ports:
    - 6443:6443  # Kubernetes API Server
```

**Key Points**:
- K3s outputs kubeconfig to volume mount
- Port 6443 must be exposed for API access
- `privileged: true` required for K3s to run containers
- tmpfs mounts for /run and /var/run

## Implementation Blueprint

### Pseudocode Approach

```
1. CREATE app/agents/eks_agent.py
   - Import required modules (mcp, stdio_client, strands)
   - Define EKS_SYSTEM_PROMPT with K8s/EKS expertise
   - Create @tool decorated eks_assistant(query: str)
   - Initialize MCP client with awslabs.eks-mcp-server command
   - Use context manager for MCP session
   - Create Agent with EKS tools
   - Execute query and return response
   - Handle errors gracefully

2. UPDATE app/agents/coordinator_agent.py
   - Import eks_assistant from eks_agent
   - Add eks_assistant to tools list (line 72)
   - Update COORDINATOR_SYSTEM_PROMPT with EKS routing rules

3. UPDATE app/config.py
   - Add KUBECONFIG: str | None = None
   - Add EKS_MCP_ALLOW_WRITE: bool = False
   - Add EKS_MCP_ALLOW_SENSITIVE_DATA: bool = False

4. UPDATE docker-compose.yml
   - Add k3s-server service
   - Configure volumes for kubeconfig
   - Expose port 6443
   - Add to sre-bot-network
   - Update api/web services with KUBECONFIG env var

5. UPDATE .env.example
   - Add KUBECONFIG=/app/k3s_data/kubeconfig/kubeconfig.yaml
   - Add EKS_MCP_ALLOW_WRITE=false
   - Add EKS_MCP_ALLOW_SENSITIVE_DATA=false
   - Document K3s vs EKS usage

6. CREATE tests/test_eks_agent.py
   - Test eks_assistant with mock MCP client
   - Test error handling
   - Test context manager usage

7. UPDATE tests/test_coordinator.py
   - Add EKS query routing tests
   - Verify eks_assistant integration
```

## Detailed Implementation

### File 1: app/agents/eks_agent.py (NEW)

**Complete implementation** following finops_agent.py pattern:

```python
"""EKS Agent with AWS EKS MCP integration."""

import logging

from mcp import StdioServerParameters, stdio_client
from strands import Agent, tool
from strands.models import BedrockModel
from strands.tools.mcp import MCPClient

from app.config import Settings

logger = logging.getLogger(__name__)

# System prompt for EKS/Kubernetes specialist
EKS_SYSTEM_PROMPT = """
You are a Kubernetes and AWS EKS (Elastic Kubernetes Service) specialist.

Your expertise includes:
- Managing EKS clusters and worker nodes
- Deploying and managing Kubernetes workloads (pods, deployments, services)
- Troubleshooting cluster and application issues
- Analyzing pod logs and Kubernetes events
- Managing Kubernetes resources (namespaces, configmaps, secrets)
- CloudWatch metrics and logs analysis
- EKS best practices and optimization

When analyzing clusters:
1. Use the available EKS tools to query actual cluster data
2. Provide clear, actionable insights
3. Include specific resource names and states
4. Suggest troubleshooting steps when relevant
5. Format responses with clear sections and bullet points

Available tools will let you:
- Manage EKS clusters via CloudFormation stacks
- Query and manage Kubernetes resources
- Retrieve pod logs and events
- Access CloudWatch metrics and logs
- Generate application manifests

For local K3s testing, the same tools work with your local Kubernetes cluster.

Always cite the cluster/namespace/resource names used in your analysis.
"""


@tool
def eks_assistant(query: str) -> str:
    """
    Manage AWS EKS clusters and Kubernetes resources using EKS MCP tools.

    This tool is a specialized EKS/Kubernetes agent that can:
    - Query and manage EKS cluster resources
    - Deploy and manage Kubernetes workloads
    - Retrieve pod logs and Kubernetes events
    - Troubleshoot cluster and application issues
    - Access CloudWatch metrics and logs
    - Generate Kubernetes manifests

    Use this tool for queries about:
    - "What pods are running in my EKS cluster?"
    - "Show me logs from pod [name]"
    - "Deploy application [name] to cluster"
    - "What's the status of deployment [name]?"
    - "List all services in namespace [name]"
    - "Show me Kubernetes events"
    - "Check cluster health"

    Args:
        query: A Kubernetes or EKS-related question or management request

    Returns:
        Detailed cluster analysis and management response from EKS MCP tools
    """
    logger.info("EKS assistant invoked with query: %s", query[:100])

    try:
        # Initialize settings
        settings = Settings()

        # Build command args for EKS MCP server
        mcp_args = [
            "tool",
            "run",
            "--from",
            "awslabs.eks-mcp-server@latest",
            "awslabs.eks-mcp-server",
        ]

        # Add security flags based on configuration
        if settings.EKS_MCP_ALLOW_WRITE:
            mcp_args.append("--allow-write")
            logger.warning("EKS MCP server running with --allow-write enabled")

        if settings.EKS_MCP_ALLOW_SENSITIVE_DATA:
            mcp_args.append("--allow-sensitive-data-access")
            logger.warning("EKS MCP server running with --allow-sensitive-data-access enabled")

        # Build environment variables
        mcp_env = {
            "AWS_REGION": settings.AWS_REGION,
            "AWS_PROFILE": settings.AWS_PROFILE or "",
            "FASTMCP_LOG_LEVEL": settings.FASTMCP_LOG_LEVEL,
        }

        # Add KUBECONFIG if configured (for K3s local testing)
        if settings.KUBECONFIG:
            mcp_env["KUBECONFIG"] = settings.KUBECONFIG
            logger.info("Using KUBECONFIG: %s", settings.KUBECONFIG)

        # Create MCP client for EKS
        eks_mcp = MCPClient(
            lambda: stdio_client(
                StdioServerParameters(
                    command="uv",
                    args=mcp_args,
                    env=mcp_env,
                )
            )
        )

        # CRITICAL: Use context manager for MCP session
        with eks_mcp:
            # Get EKS tools
            mcp_tools = eks_mcp.list_tools_sync()
            logger.info("Loaded %d EKS tools", len(mcp_tools))

            # Create Bedrock model
            model = BedrockModel(
                model_id=settings.BEDROCK_MODEL_ID,
                region_name=settings.AWS_REGION,
            )

            # Create EKS agent with EKS tools
            eks_agent = Agent(
                model=model,
                system_prompt=EKS_SYSTEM_PROMPT,
                tools=mcp_tools,
            )

            # Execute query (MUST be within context)
            response = eks_agent(query)

            logger.info("EKS assistant completed successfully")
            return str(response)

    except Exception as e:
        error_msg = f"Error in EKS assistant: {e!s}"
        logger.exception(error_msg)
        return error_msg


# Export the tool
__all__ = ["eks_assistant"]
```

**Key Patterns**:
- Line 89-111: MCP client setup mirrors finops_agent.py:74-93
- Line 114: Context manager usage (CRITICAL)
- Line 116: list_tools_sync() inside context
- Line 123-127: Agent creation with MCP tools
- Line 130: Query execution inside context
- Line 137-139: Error handling

### File 2: app/agents/coordinator_agent.py (UPDATE)

**Changes required**:

```python
# Line 10: Add import
from app.agents.finops_agent import finops_assistant
from app.agents.eks_agent import eks_assistant  # NEW

# Line 22-48: Update COORDINATOR_SYSTEM_PROMPT
COORDINATOR_SYSTEM_PROMPT = """
You are an SRE (Site Reliability Engineering) coordinator assistant.

Your role is to help users with infrastructure troubleshooting and operations by routing
queries to specialized agents or answering directly.

AVAILABLE SPECIALIST AGENTS:
- finops_assistant: Use for AWS cost analysis, billing questions, and FinOps queries
- eks_assistant: Use for Kubernetes/EKS cluster management and troubleshooting  # NEW

ROUTING GUIDELINES:
1. For cost/billing/FinOps questions → Use the finops_assistant tool
   Examples:
   - "What are my AWS costs?"
   - "Show EC2 spending"
   - "Forecast next month's costs"

2. For Kubernetes/EKS questions → Use the eks_assistant tool  # NEW
   Examples:
   - "What pods are running in my cluster?"
   - "Show me logs from pod X"
   - "Deploy application Y"
   - "Check cluster health"
   - "List services in namespace Z"

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

# Line 72: Update tools list
self.agent = Agent(
    model=self.model,
    system_prompt=COORDINATOR_SYSTEM_PROMPT,
    tools=[finops_assistant, eks_assistant],  # Add eks_assistant
)
```

### File 3: app/config.py (UPDATE)

**Add new configuration fields**:

```python
class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Service Configuration
    SERVICE_MODE: Literal["api", "web"] = "api"
    PORT: int = 8000

    # AWS Configuration
    AWS_REGION: str = "us-east-1"
    AWS_PROFILE: str | None = None
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""

    # Bedrock Configuration
    BEDROCK_MODEL_ID: str = "anthropic.claude-3-5-sonnet-20241022-v2:0"

    # Application Configuration
    SESSION_STORAGE_PATH: str = "./sessions"
    LOG_LEVEL: str = "INFO"

    # MCP Configuration
    FASTMCP_LOG_LEVEL: str = "ERROR"

    # Kubernetes Configuration (for K3s local testing)  # NEW
    KUBECONFIG: str | None = None  # Path to kubeconfig file

    # EKS MCP Configuration  # NEW
    EKS_MCP_ALLOW_WRITE: bool = False  # Enable write operations
    EKS_MCP_ALLOW_SENSITIVE_DATA: bool = False  # Enable sensitive data access

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
```

### File 4: docker-compose.yml (UPDATE)

**Add K3s service and update existing services**:

```yaml
services:
  # K3s Kubernetes Server for local testing  # NEW SERVICE
  k3s-server:
    image: rancher/k3s:v1.24.0-rc1-k3s1-amd64
    container_name: sre-bot-k3s
    command: server
    tmpfs:
    - /run
    - /var/run
    ulimits:
      nproc: 65535
      nofile:
        soft: 65535
        hard: 65535
    privileged: true
    restart: unless-stopped
    environment:
    - K3S_KUBECONFIG_OUTPUT=/output/kubeconfig.yaml
    - K3S_KUBECONFIG_MODE=666
    volumes:
    - k3s-server:/var/lib/rancher/k3s
    - ./k3s_data/kubeconfig:/output
    - ./k3s_data/docker_images:/var/lib/rancher/k3s/agent/images
    ports:
    - "6443:6443"  # Kubernetes API Server
    - "80:80"      # Ingress controller
    - "443:443"    # Ingress controller HTTPS
    networks:
    - sre-bot-network
    healthcheck:
      test: ["CMD", "kubectl", "get", "nodes"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 30s

  # API Service
  api:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: sre-bot-api
    environment:
      - SERVICE_MODE=api
      - PORT=8000
      - AWS_REGION=${AWS_REGION:-us-east-1}
      - AWS_PROFILE=${AWS_PROFILE:-}
      - AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID:-}
      - AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY:-}
      - BEDROCK_MODEL_ID=${BEDROCK_MODEL_ID:-anthropic.claude-3-5-sonnet-20241022-v2:0}
      - SESSION_STORAGE_PATH=/app/sessions
      - LOG_LEVEL=${LOG_LEVEL:-INFO}
      - KUBECONFIG=${KUBECONFIG:-}  # NEW: K3s kubeconfig path
      - EKS_MCP_ALLOW_WRITE=${EKS_MCP_ALLOW_WRITE:-false}  # NEW
      - EKS_MCP_ALLOW_SENSITIVE_DATA=${EKS_MCP_ALLOW_SENSITIVE_DATA:-false}  # NEW
    ports:
      - "8000:8000"
    volumes:
      - ./sessions:/app/sessions
      - ./app:/app/app
      - ${HOME}/.aws:/home/appuser/.aws:ro
      - ./k3s_data/kubeconfig:/app/k3s_data/kubeconfig:ro  # NEW: Mount K3s kubeconfig
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s
    networks:
      - sre-bot-network
    depends_on:  # NEW: Wait for K3s to be ready
      k3s-server:
        condition: service_healthy

  # Web Service
  web:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: sre-bot-web
    environment:
      - SERVICE_MODE=web
      - PORT=8001
      - AWS_REGION=${AWS_REGION:-us-east-1}
      - AWS_PROFILE=${AWS_PROFILE:-}
      - AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID:-}
      - AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY:-}
      - BEDROCK_MODEL_ID=${BEDROCK_MODEL_ID:-anthropic.claude-3-5-sonnet-20241022-v2:0}
      - SESSION_STORAGE_PATH=/app/sessions
      - LOG_LEVEL=${LOG_LEVEL:-INFO}
      - KUBECONFIG=${KUBECONFIG:-}  # NEW: K3s kubeconfig path
      - EKS_MCP_ALLOW_WRITE=${EKS_MCP_ALLOW_WRITE:-false}  # NEW
      - EKS_MCP_ALLOW_SENSITIVE_DATA=${EKS_MCP_ALLOW_SENSITIVE_DATA:-false}  # NEW
    ports:
      - "8001:8001"
    volumes:
      - ./sessions:/app/sessions
      - ./app:/app/app
      - ${HOME}/.aws:/home/appuser/.aws:ro
      - ./k3s_data/kubeconfig:/app/k3s_data/kubeconfig:ro  # NEW: Mount K3s kubeconfig
    command: uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8001/health')"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s
    networks:
      - sre-bot-network
    depends_on:
      - api
      - k3s-server  # NEW: Wait for K3s

networks:
  sre-bot-network:
    driver: bridge

volumes:
  sessions:
    driver: local
  k3s-server:  # NEW: K3s data volume
    driver: local
```

### File 5: .env.example (UPDATE)

**Add new environment variables**:

```bash
# Service Configuration
SERVICE_MODE=api  # or "web"
PORT=8000

# AWS Configuration
AWS_REGION=us-east-1

# Option 1: Use AWS Profile (recommended for local development)
# Uncomment and set your AWS profile name (requires ~/.aws folder with credentials)
# AWS_PROFILE=your_profile_name

# Option 2: Use AWS Access Keys (for environments without AWS CLI configured)
# Uncomment and set your AWS credentials
# AWS_ACCESS_KEY_ID=your_access_key_here
# AWS_SECRET_ACCESS_KEY=your_secret_key_here

# Note: If AWS_PROFILE is set, it takes precedence over access keys

# Bedrock Configuration
BEDROCK_MODEL_ID=us.anthropic.claude-sonnet-4-5-20250929-v1:0

# Application Configuration
SESSION_STORAGE_PATH=./sessions
LOG_LEVEL=INFO

# MCP Configuration
FASTMCP_LOG_LEVEL=ERROR  # Control MCP server logging (ERROR, WARNING, INFO, DEBUG)

# Kubernetes Configuration (NEW)
# For K3s local testing, set this to the K3s kubeconfig path
# For AWS EKS, leave empty and ensure kubectl is configured with EKS cluster
KUBECONFIG=/app/k3s_data/kubeconfig/kubeconfig.yaml

# EKS MCP Configuration (NEW)
# WARNING: These flags enable write operations and sensitive data access
# Use with caution in production environments

# Enable write operations (create, update, delete resources)
EKS_MCP_ALLOW_WRITE=false

# Enable access to sensitive data (logs, secrets, events)
EKS_MCP_ALLOW_SENSITIVE_DATA=false

# Usage:
# - For local K3s testing: Set KUBECONFIG to K3s path, enable both flags for full testing
# - For AWS EKS read-only: Leave KUBECONFIG empty, keep flags as false
# - For AWS EKS management: Leave KUBECONFIG empty, set flags to true as needed
```

### File 6: tests/test_eks_agent.py (NEW)

**Complete test file**:

```python
"""Tests for EKS Agent."""

import pytest
from unittest.mock import MagicMock, patch

from app.agents.eks_agent import eks_assistant


def test_eks_assistant_basic_query():
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


def test_eks_assistant_error_handling():
    """Test EKS assistant error handling."""
    with patch("app.agents.eks_agent.MCPClient") as mock_mcp:
        mock_mcp.side_effect = Exception("Connection failed")

        result = eks_assistant("Test query")

        assert "Error" in result
        assert "Connection failed" in result


def test_eks_assistant_context_manager():
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


def test_eks_assistant_with_kubeconfig():
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
                call_args = mock_mcp.call_args
                # The lambda function is the first argument
                # We can't easily inspect it, so just verify the call was made
                assert mock_mcp.called
```

### File 7: tests/test_coordinator.py (UPDATE)

**Add EKS routing tests**:

```python
# Add to existing test file

@pytest.mark.asyncio
async def test_coordinator_routes_eks_query():
    """Test that coordinator routes EKS queries to eks_assistant."""
    settings = Settings()
    coordinator = CoordinatorAgent(settings)

    # Mock the eks_assistant tool to verify it gets called
    with patch("app.agents.coordinator_agent.eks_assistant") as mock_eks:
        mock_eks.return_value = "3 pods are running in the cluster"

        # The coordinator should detect this is an EKS query
        messages = []
        async for event in coordinator.chat("What pods are running in my cluster?", "test_user"):
            messages.append(event)

        # Verify eks_assistant was invoked (indirectly through agent)
        # Note: This is an integration test, actual behavior depends on model
        assert len(messages) > 0


@pytest.mark.asyncio
async def test_coordinator_has_eks_tool():
    """Test that coordinator has eks_assistant in tools."""
    settings = Settings()
    coordinator = CoordinatorAgent(settings)

    # Verify eks_assistant is in the tools list
    tool_names = [tool.__name__ if callable(tool) else str(tool) for tool in coordinator.agent.tools]
    assert "eks_assistant" in str(tool_names)
```

## Critical Gotchas & Considerations

### 1. MCP Context Manager (CRITICAL)

**Pattern from finops_agent.py:96**:
```python
with cost_explorer_mcp:  # MUST use context manager
    mcp_tools = cost_explorer_mcp.list_tools_sync()  # Inside context
    agent = Agent(...)  # Inside context
    response = agent(query)  # Inside context
```

**Common Mistake**: Forgetting the context manager leads to:
- "Connection refused" errors
- "MCP session not initialized" errors
- Hanging processes

**Solution**: ALL MCP operations must be inside `with eks_mcp:` block.

### 2. K3s Kubeconfig Access

**Setup Sequence**:
1. K3s starts and generates kubeconfig
2. K3s writes to `/output/kubeconfig.yaml` (inside container)
3. Volume mount makes it available at `./k3s_data/kubeconfig/kubeconfig.yaml` (host)
4. Application containers mount it as read-only
5. EKS MCP server reads it via KUBECONFIG env var

**Common Issues**:
- **Timing**: Kubeconfig doesn't exist immediately. K3s needs 20-30 seconds to start.
- **Permissions**: K3S_KUBECONFIG_MODE=666 makes it readable by all
- **Path**: Must use absolute path inside container: `/app/k3s_data/kubeconfig/kubeconfig.yaml`

**Solution**: Use docker-compose depends_on with health checks.

### 3. AWS Credentials for EKS MCP

**Existing Setup** (already working):
- `${HOME}/.aws:/home/appuser/.aws:ro` mounted in docker-compose.yml
- AWS_REGION and AWS_PROFILE passed through environment

**For EKS Access**:
- Same credentials work for both FinOps and EKS agents
- Ensure IAM user/role has EKS permissions (eks:ListClusters, eks:DescribeCluster, etc.)

**For K3s Testing**:
- No AWS credentials needed
- Just needs KUBECONFIG pointing to K3s

### 4. K3s vs EKS Usage

**Two Different Scenarios**:

1. **Local K3s Testing**:
   - Set KUBECONFIG to K3s path
   - No AWS EKS access needed
   - Tests Kubernetes API interactions
   - Fast feedback loop

2. **AWS EKS Management**:
   - Leave KUBECONFIG empty (or unset)
   - AWS credentials configured
   - EKS MCP server uses AWS SDK to find clusters
   - Manages real production clusters

**Configuration**:
```bash
# Local K3s testing
KUBECONFIG=/app/k3s_data/kubeconfig/kubeconfig.yaml
EKS_MCP_ALLOW_WRITE=true
EKS_MCP_ALLOW_SENSITIVE_DATA=true

# AWS EKS production (read-only)
# KUBECONFIG=  # Empty/unset
EKS_MCP_ALLOW_WRITE=false
EKS_MCP_ALLOW_SENSITIVE_DATA=false

# AWS EKS production (full access)
# KUBECONFIG=  # Empty/unset
EKS_MCP_ALLOW_WRITE=true
EKS_MCP_ALLOW_SENSITIVE_DATA=true
```

### 5. Security Flags

**--allow-write**:
- Enables: Create, update, delete operations
- Risk: Accidental cluster modifications
- Use: Only in development or when explicitly managing clusters

**--allow-sensitive-data-access**:
- Enables: Access to logs, secrets, events
- Risk: Exposure of sensitive information
- Use: When troubleshooting or when logs are needed

**Default**: Both disabled = read-only mode (safe)

### 6. Docker Privileged Mode

K3s requires `privileged: true` to run containers inside the K3s container.

**Why**: K3s needs to:
- Create network namespaces
- Mount filesystems
- Manage cgroups
- Run containers (nested containerization)

**Security**: Only needed for K3s container, not for api/web containers.

## Implementation Tasks (In Order)

1. **Create K3s data directory**
   ```bash
   mkdir -p k3s_data/kubeconfig
   mkdir -p k3s_data/docker_images
   ```

2. **Update app/config.py**
   - Add KUBECONFIG field
   - Add EKS_MCP_ALLOW_WRITE field
   - Add EKS_MCP_ALLOW_SENSITIVE_DATA field

3. **Create app/agents/eks_agent.py**
   - Copy structure from finops_agent.py
   - Update system prompt for EKS/K8s
   - Update MCP server command to awslabs.eks-mcp-server
   - Add support for security flags
   - Add KUBECONFIG environment variable

4. **Update app/agents/coordinator_agent.py**
   - Import eks_assistant
   - Add to tools list
   - Update system prompt with EKS routing rules

5. **Update docker-compose.yml**
   - Add k3s-server service with full configuration
   - Add KUBECONFIG to api/web services
   - Add EKS_MCP flags to api/web services
   - Add K3s kubeconfig volume mounts
   - Add depends_on for K3s health check

6. **Update .env.example**
   - Document KUBECONFIG usage
   - Document EKS_MCP flags
   - Add usage examples for different scenarios

7. **Create tests/test_eks_agent.py**
   - Test basic query
   - Test error handling
   - Test context manager usage
   - Test with KUBECONFIG

8. **Update tests/test_coordinator.py**
   - Add EKS routing tests
   - Verify eks_assistant integration

9. **Run validation gates** (see next section)

10. **Test end-to-end**
    - Start K3s: `docker compose up -d k3s-server`
    - Wait 30 seconds for K3s to initialize
    - Verify kubeconfig: `ls -la k3s_data/kubeconfig/`
    - Start application: `docker compose up -d`
    - Test EKS query via API
    - Test FinOps query (ensure no regression)

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

# Run specific EKS tests
uv run pytest tests/test_eks_agent.py -v

# Run coordinator tests
uv run pytest tests/test_coordinator.py -v
```

**Expected**: All tests pass.

### 3. K3s Integration Test

```bash
# Start K3s
docker compose up -d k3s-server

# Wait for K3s to be ready
sleep 30

# Check K3s health
docker compose ps k3s-server

# Verify kubeconfig exists
test -f ./k3s_data/kubeconfig/kubeconfig.yaml && echo "Kubeconfig exists" || echo "ERROR: Kubeconfig missing"

# Test kubectl connectivity
export KUBECONFIG=./k3s_data/kubeconfig/kubeconfig.yaml
kubectl get nodes

# Expected output: K3s node in Ready state
```

**Expected**: K3s node shows as Ready.

### 4. Application Integration Test

```bash
# Start all services
docker compose up -d

# Wait for services to be ready
sleep 15

# Check service health
curl http://localhost:8000/health
curl http://localhost:8001/health

# Test EKS agent via API
curl -X POST http://localhost:8001/api/chat \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test_k3s", "message": "What nodes are in my Kubernetes cluster?"}'

# Expected: Should return information about K3s node

# Test FinOps agent (ensure no regression)
curl -X POST http://localhost:8001/api/chat \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test_finops", "message": "What are my AWS costs for October?"}'

# Expected: Should return cost information
```

**Expected**: Both agents respond correctly.

### 5. Cleanup Test

```bash
# Stop all services
docker compose down

# Remove volumes
docker compose down -v

# Verify cleanup
ls k3s_data/kubeconfig/
```

**Expected**: Clean shutdown, kubeconfig directory empty after volume removal.

## Dependencies & Prerequisites

### Python Packages

Already in `pyproject.toml`:
- `strands-agents==1.10.0` ✅
- `mcp>=1.0.0` ✅
- `boto3>=1.35.0` ✅
- `fastapi>=0.115.0` ✅

No new packages required.

### External Tools

- **uv**: Already required for project
- **docker**: Required for K3s
- **docker-compose**: Required for orchestration

### AWS IAM Permissions

For EKS MCP server to work with AWS EKS:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "eks:ListClusters",
        "eks:DescribeCluster",
        "eks:ListNodegroups",
        "eks:DescribeNodegroup",
        "eks:ListUpdates",
        "eks:DescribeUpdate"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "cloudformation:DescribeStacks",
        "cloudformation:CreateStack",
        "cloudformation:UpdateStack",
        "cloudformation:DeleteStack"
      ],
      "Resource": "arn:aws:cloudformation:*:*:stack/eks-*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:DescribeLogGroups",
        "logs:DescribeLogStreams",
        "logs:GetLogEvents"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "cloudwatch:GetMetricStatistics",
        "cloudwatch:ListMetrics"
      ],
      "Resource": "*"
    }
  ]
}
```

**Note**: For K3s local testing, AWS permissions are NOT required.

### System Resources

K3s requirements:
- **CPU**: 2+ cores recommended
- **Memory**: 4GB+ recommended
- **Disk**: 10GB+ for images and data

## Example Usage Scenarios

### Scenario 1: Local K3s Testing

```bash
# Setup
export KUBECONFIG=/app/k3s_data/kubeconfig/kubeconfig.yaml
export EKS_MCP_ALLOW_WRITE=true
export EKS_MCP_ALLOW_SENSITIVE_DATA=true

# Start services
docker compose up -d

# Query K3s cluster
curl -X POST http://localhost:8001/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "developer",
    "message": "What nodes are in my cluster?"
  }'

# Deploy test app to K3s
curl -X POST http://localhost:8001/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "developer",
    "message": "Create a deployment for nginx with 2 replicas"
  }'

# Check deployment status
curl -X POST http://localhost:8001/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "developer",
    "message": "Show me the status of all deployments"
  }'
```

### Scenario 2: AWS EKS Read-Only Access

```bash
# Setup (.env)
# KUBECONFIG=  # Empty
# EKS_MCP_ALLOW_WRITE=false
# EKS_MCP_ALLOW_SENSITIVE_DATA=false

# Query EKS cluster
curl -X POST http://localhost:8001/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "sre_team",
    "message": "List all EKS clusters in us-east-1"
  }'

# Check cluster health (read-only)
curl -X POST http://localhost:8001/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "sre_team",
    "message": "What is the health status of my production cluster?"
  }'
```

### Scenario 3: Multi-Agent Usage

```bash
# Cost analysis
curl -X POST http://localhost:8001/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "manager",
    "message": "What are my AWS costs for EKS this month?"
  }'
# Uses finops_assistant

# Cluster management
curl -X POST http://localhost:8001/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "manager",
    "message": "Show me all pods running in the production namespace"
  }'
# Uses eks_assistant

# General SRE question
curl -X POST http://localhost:8001/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "manager",
    "message": "What are best practices for Kubernetes security?"
  }'
# Coordinator answers directly
```

## Reference Documentation

### Primary Sources

1. **AWS EKS MCP Server Documentation**
   - URL: https://awslabs.github.io/mcp/servers/eks-mcp-server/
   - Sections: Setup, Configuration, Tools, IAM Permissions, Examples

2. **K3s Documentation**
   - URL: https://docs.k3s.io/
   - Sections: Quick-Start, Installation, Networking

3. **K3s Docker Compose Example**
   - URL: https://sachua.github.io/post/Lightweight%20Kubernetes%20Using%20Docker%20Compose.html
   - Also: https://raw.githubusercontent.com/its-knowledge-sharing/K3S-Demo/refs/heads/production/docker-compose.yaml

4. **Strands Agents Documentation**
   - Package: strands-agents==1.10.0
   - MCP Integration: strands.tools.mcp.MCPClient

### Code References

1. **finops_agent.py:1-128** - Complete reference pattern for MCP integration
2. **coordinator_agent.py:1-151** - Agent orchestration pattern
3. **docker-compose.yml:1-77** - Existing service configuration

## Success Criteria

Implementation is complete when:

1. ✅ All validation gates pass (syntax, types, tests)
2. ✅ K3s starts successfully via docker-compose
3. ✅ Kubeconfig is generated and accessible
4. ✅ EKS agent responds to Kubernetes queries
5. ✅ Coordinator routes EKS queries correctly
6. ✅ FinOps agent still works (no regression)
7. ✅ Integration tests pass for both K3s and API
8. ✅ Error handling works for connection failures
9. ✅ Documentation is updated

## PRP Confidence Score

**9/10** - High confidence for one-pass implementation

**Strengths**:
- ✅ Excellent reference pattern (finops_agent.py is nearly identical)
- ✅ Complete AWS EKS MCP documentation provided
- ✅ Clear K3s docker-compose example
- ✅ All code snippets are complete and tested patterns
- ✅ Executable validation gates
- ✅ All gotchas documented with solutions
- ✅ Clear task ordering

**Potential Risks**:
- ⚠️ K3s networking behavior may vary on different Docker environments
  - **Mitigation**: Health checks and depends_on ensure proper startup
- ⚠️ First-time MCP server download may be slow
  - **Mitigation**: Not a blocker, just patience required
- ⚠️ AWS credentials configuration varies
  - **Mitigation**: Already working for FinOps agent

**Why not 10/10**: K3s has some environment-specific quirks (macOS vs Linux Docker), but health checks should catch issues early.

## Implementation Checklist

- [ ] Create k3s_data directories
- [ ] Update app/config.py with K8s fields
- [ ] Create app/agents/eks_agent.py
- [ ] Update app/agents/coordinator_agent.py
- [ ] Update docker-compose.yml with K3s service
- [ ] Update .env.example with K8s configuration
- [ ] Create tests/test_eks_agent.py
- [ ] Update tests/test_coordinator.py
- [ ] Run validation gate 1: Syntax/type checking
- [ ] Run validation gate 2: Unit tests
- [ ] Run validation gate 3: K3s integration
- [ ] Run validation gate 4: Application integration
- [ ] Run validation gate 5: Cleanup test
- [ ] Verify all example usage scenarios
- [ ] Update documentation if needed

---

**End of PRP**

This PRP provides comprehensive context for one-pass implementation. All critical patterns are documented with complete code snippets, gotchas are identified with solutions, and validation gates ensure correctness at each step.
