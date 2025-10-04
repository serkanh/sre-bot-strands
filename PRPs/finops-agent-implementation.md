# PRP: FinOps Agent Implementation with Multi-Agent Architecture

## Executive Summary

Implement a **multi-agent FinOps system** using the Strands Agents framework with an "Agents as Tools" pattern. The system consists of:

1. **FinOps Agent**: Specialized agent with AWS Cost Explorer MCP tools for cost analysis
2. **Coordinator Agent**: Orchestrator that routes user queries to the appropriate specialist agent

**Architecture Pattern**: "Agents as Tools" - The FinOps agent is wrapped as a `@tool` function and used by the coordinator agent, enabling clean separation of concerns and easy extensibility for future specialized agents.

**Key Technologies**:
- Strands Agents SDK for multi-agent orchestration
- AWS Cost Explorer MCP Server for cost data access
- Model Context Protocol (MCP) for tool integration
- AWS Bedrock for LLM inference

## Feature Requirements

From INITIAL.md:

- Build an SRE agent for troubleshooting and infrastructure management
- Include FinOps agent with AWS Cost Explorer access
- Coordinator agent to route queries to specialized agents
- Multi-agent structure using Strands framework
- Query Cost Explorer MCP tools for resource costs

**Current Iteration Scope**:
- ✅ FinOps agent with Cost Explorer MCP integration
- ✅ Coordinator agent with "Agents as Tools" pattern
- ✅ Integration with existing FastAPI infrastructure
- ✅ Maintain streaming capabilities for real-time UI updates
- ⏸️ Additional specialized agents (future iterations)

## Architecture Overview

### System Design

```
┌─────────────────────────────────────────────────────────────┐
│                     User Request                             │
└────────────────────┬────────────────────────────────────────┘
                     │
         ┌───────────▼──────────┐
         │  Coordinator Agent   │
         │                      │
         │  - Routes queries    │
         │  - Orchestrates      │
         │  - Has FinOps tool   │
         └───────────┬──────────┘
                     │
                     ├─── General queries ──> Direct response
                     │
                     └─── Cost/FinOps queries
                              │
                    ┌─────────▼──────────┐
                    │   FinOps Agent     │
                    │   (@tool wrapper)  │
                    │                    │
                    │  System Prompt:    │
                    │  Cost analysis     │
                    │  specialist        │
                    └─────────┬──────────┘
                              │
                    ┌─────────▼──────────┐
                    │    MCP Client      │
                    │  (Cost Explorer)   │
                    └─────────┬──────────┘
                              │
            ┌─────────────────┼─────────────────┐
            │                 │                 │
    ┌───────▼────────┐ ┌─────▼──────┐ ┌────────▼────────┐
    │get_cost_and_   │ │get_cost_   │ │get_dimension_   │
    │usage           │ │forecast    │ │values           │
    └────────────────┘ └────────────┘ └─────────────────┘
                              │
                    ┌─────────▼──────────┐
                    │ AWS Cost Explorer  │
                    │       API          │
                    └────────────────────┘
```

### Project Structure

```
/
├── app/
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── strands_agent.py       # Existing base wrapper
│   │   ├── finops_agent.py        # NEW: FinOps specialist with MCP
│   │   └── coordinator_agent.py   # NEW: Orchestrator with routing
│   ├── api/
│   │   └── routes.py              # UPDATE: Use coordinator agent
│   ├── config.py                  # UPDATE: Add MCP config
│   └── main.py
├── tests/
│   ├── test_finops_agent.py       # NEW: FinOps agent tests
│   └── test_coordinator.py        # NEW: Coordinator tests
├── .mcp.json                      # UPDATE: Add Cost Explorer MCP
└── pyproject.toml                 # UPDATE: Add MCP dependency
```

## Technical Context

### 1. AWS Cost Explorer MCP Server

**Documentation**: https://awslabs.github.io/mcp/servers/cost-explorer-mcp-server/

**Installation**:
```bash
# Install uvx (if not already installed)
pip install uv

# MCP server runs via uvx (no manual installation needed)
# Command: uvx awslabs.cost-explorer-mcp-server@latest
```

**Available Tools**:
1. `get_today_date` - Get current date for date range queries
2. `get_dimension_values` - Get available dimension values (services, regions, etc.)
3. `get_tag_values` - Get tag values for filtering
4. `get_cost_and_usage` - Main cost query tool with grouping and filtering
5. `get_cost_and_usage_comparisons` - Compare costs between time periods
6. `get_cost_comparison_drivers` - Identify cost change drivers
7. `get_cost_forecast` - Forecast future costs

**Authentication**:
- Uses AWS credentials via `AWS_PROFILE` environment variable
- Requires IAM permissions: `ce:GetCostAndUsage`, `ce:GetCostForecast`, `ce:GetDimensionValues`

**Cost Considerations**:
- Each Cost Explorer API request costs **$0.01**
- Important to cache results and avoid redundant queries

**Configuration** (.mcp.json):
```json
{
  "mcpServers": {
    "awslabs.cost-explorer-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.cost-explorer-mcp-server@latest"],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR",
        "AWS_PROFILE": "your-aws-profile",
        "AWS_REGION": "us-east-1"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

### 2. Strands MCP Integration

**Documentation**: https://strandsagents.com/latest/documentation/docs/user-guide/concepts/tools/mcp-tools/

**Key Pattern** (CRITICAL):
```python
from mcp import stdio_client, StdioServerParameters
from strands import Agent
from strands.tools.mcp import MCPClient

# Create MCP client with stdio transport
mcp_client = MCPClient(lambda: stdio_client(
    StdioServerParameters(
        command="uvx",
        args=["awslabs.cost-explorer-mcp-server@latest"]
    )
))

# MUST use context manager - MCP session must remain active
with mcp_client:
    # Get tools from MCP server
    tools = mcp_client.list_tools_sync()

    # Create agent with MCP tools
    agent = Agent(tools=tools)

    # Use agent (MUST be within context)
    response = agent("What are my AWS costs?")
```

**Critical Requirements**:
- ALL agent operations MUST be within `with mcp_client:` context
- Agent creation AND usage must happen inside context
- Context manager ensures MCP session stays connected
- Common error: creating agent inside context, using outside → MCPClientInitializationError

### 3. "Agents as Tools" Pattern

**Documentation**: https://strandsagents.com/latest/documentation/docs/user-guide/concepts/multi-agent/agents-as-tools/

**Pattern Structure**:
```python
from strands import Agent, tool

# Step 1: Create specialized agent as tool function
@tool
def finops_assistant(query: str) -> str:
    """
    Analyze AWS costs and provide FinOps insights.

    Use this tool for:
    - Cost analysis and breakdowns
    - Cost forecasting
    - Resource cost optimization
    - Budget tracking

    Args:
        query: A cost-related question or analysis request

    Returns:
        Detailed cost analysis with recommendations
    """
    # MCP integration happens here
    specialist_agent = Agent(
        system_prompt="You are a FinOps specialist...",
        tools=[mcp_tools]  # Cost Explorer tools
    )
    response = specialist_agent(query)
    return str(response)

# Step 2: Create coordinator with specialist as tool
coordinator = Agent(
    system_prompt="""
    You route queries to specialized agents:
    - For cost/billing/FinOps → Use finops_assistant tool
    - For other queries → Answer directly
    """,
    tools=[finops_assistant]  # Specialist wrapped as tool
)

# Usage
coordinator("What were my EC2 costs last month?")
# → Coordinator calls finops_assistant tool
# → FinOps agent queries Cost Explorer MCP
# → Returns cost analysis
```

**Benefits**:
- Clear separation: coordinator routes, specialist executes
- Extensible: easy to add more specialist agents
- Testable: can mock specialist tools
- Matches example from INITIAL.md

### 4. Existing Codebase Patterns

**Current Agent Structure** (app/agents/strands_agent.py):
```python
class StrandsAgent:
    def __init__(self, settings: Settings):
        self.model = BedrockModel(
            model_id=settings.BEDROCK_MODEL_ID,
            region_name=settings.AWS_REGION,
        )
        self.agent = Agent(model=self.model, tools=[])

    async def chat(self, prompt: str, user_id: str) -> AsyncIterator[dict]:
        async for event in self.agent.stream_async(prompt):
            # Stream events: thinking, tool_use, agent_message
            yield event
```

**Current API Integration** (app/api/routes.py):
```python
@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, agent: StrandsAgent = Depends(get_agent)):
    events = []
    final_response = ""

    async for event in agent.chat(request.message, request.user_id):
        events.append(event)
        if event.get("type") == "agent_message":
            final_response += event.get("content", "")

    return ChatResponse(response=final_response, events=events)
```

**Test Pattern** (tests/test_agent.py):
```python
@pytest.fixture
def mock_settings():
    return Settings(
        AWS_REGION="us-east-1",
        BEDROCK_MODEL_ID="test-model-id",
        AWS_ACCESS_KEY_ID="test-key",
        AWS_SECRET_ACCESS_KEY="test-secret",
    )

@patch("app.agents.strands_agent.BedrockModel")
@patch("app.agents.strands_agent.Agent")
def test_agent_initialization(mock_agent_class, mock_bedrock_model, mock_settings):
    agent = StrandsAgent(mock_settings)
    mock_bedrock_model.assert_called_once()
    assert agent.settings == mock_settings
```

## Implementation Blueprint

### Phase 1: MCP Integration Setup

**1.1 Update pyproject.toml**:
```toml
[project]
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.34.0",
    "strands-agents==1.10.0",
    "strands-agents-tools==0.2.9",
    "mcp>=1.0.0",  # NEW: Model Context Protocol
    "pydantic>=2.11.0",
    "pydantic-settings>=2.0.0",
    "boto3>=1.35.0",
    "python-dotenv>=1.0.0",
]
```

**1.2 Update .env.example**:
```bash
# Existing AWS Config
AWS_REGION=us-east-1
AWS_PROFILE=your-aws-profile  # Used by MCP servers

# NEW: MCP Configuration
FASTMCP_LOG_LEVEL=ERROR  # Optional: Control MCP logging
```

**1.3 Update .mcp.json** (Optional - for Claude Desktop integration):
```json
{
  "mcpServers": {
    "awslabs.cost-explorer-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.cost-explorer-mcp-server@latest"],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR",
        "AWS_PROFILE": "your-aws-profile",
        "AWS_REGION": "us-east-1"
      },
      "disabled": false
    },
    "awslabs.aws-documentation-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.aws-documentation-mcp-server@latest"],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR",
        "AWS_DOCUMENTATION_PARTITION": "aws"
      },
      "disabled": false
    }
  }
}
```

### Phase 2: FinOps Agent Implementation

**app/agents/finops_agent.py**:
```python
"""FinOps Agent with AWS Cost Explorer MCP integration."""

import logging
from typing import Any

from mcp import stdio_client, StdioServerParameters
from strands import Agent, tool
from strands.models import BedrockModel
from strands.tools.mcp import MCPClient

from app.config import Settings

logger = logging.getLogger(__name__)

# System prompt for FinOps specialist
FINOPS_SYSTEM_PROMPT = """
You are a FinOps (Financial Operations) specialist focused on AWS cost optimization.

Your expertise includes:
- Analyzing AWS cost and usage data
- Identifying cost trends and anomalies
- Providing cost optimization recommendations
- Forecasting future AWS spend
- Breaking down costs by service, region, and tags

When analyzing costs:
1. Use the available Cost Explorer tools to query actual data
2. Provide clear, actionable insights
3. Include specific cost figures and percentages
4. Suggest optimization opportunities when relevant
5. Format responses with clear sections and bullet points

Available tools will let you:
- Query costs by time period, service, region, or tags
- Compare costs between different time periods
- Forecast future costs based on historical data
- Get dimension values for filtering

Always cite the time period and filters used in your analysis.
"""


@tool
def finops_assistant(query: str) -> str:
    """
    Analyze AWS costs and provide FinOps insights using Cost Explorer data.

    This tool is a specialized FinOps agent that can:
    - Analyze historical AWS costs and usage
    - Compare costs between time periods
    - Forecast future AWS spend
    - Break down costs by service, region, account, or tags
    - Identify cost optimization opportunities

    Use this tool for queries about:
    - "What are my AWS costs for [time period]?"
    - "Show me cost breakdown by [service/region/etc]"
    - "Compare my costs between [period1] and [period2]"
    - "Forecast my AWS costs for [future period]"
    - "Which services cost the most?"
    - "How can I optimize my AWS costs?"

    Args:
        query: A cost-related question or analysis request

    Returns:
        Detailed cost analysis with data from AWS Cost Explorer
    """
    logger.info("FinOps assistant invoked with query: %s", query[:100])

    try:
        # Initialize settings
        settings = Settings()

        # Create MCP client for Cost Explorer
        cost_explorer_mcp = MCPClient(lambda: stdio_client(
            StdioServerParameters(
                command="uvx",
                args=["awslabs.cost-explorer-mcp-server@latest"],
                env={
                    "AWS_REGION": settings.AWS_REGION,
                    "AWS_PROFILE": settings.AWS_PROFILE or "",
                    "FASTMCP_LOG_LEVEL": "ERROR",
                }
            )
        ))

        # CRITICAL: Use context manager for MCP session
        with cost_explorer_mcp:
            # Get Cost Explorer tools
            mcp_tools = cost_explorer_mcp.list_tools_sync()
            logger.info("Loaded %d Cost Explorer tools", len(mcp_tools))

            # Create Bedrock model
            model = BedrockModel(
                model_id=settings.BEDROCK_MODEL_ID,
                region_name=settings.AWS_REGION,
            )

            # Create FinOps agent with Cost Explorer tools
            finops_agent = Agent(
                model=model,
                system_prompt=FINOPS_SYSTEM_PROMPT,
                tools=mcp_tools,
            )

            # Execute query (MUST be within context)
            response = finops_agent(query)

            logger.info("FinOps assistant completed successfully")
            return str(response)

    except Exception as e:
        error_msg = f"Error in FinOps assistant: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return error_msg


# Export the tool
__all__ = ["finops_assistant"]
```

### Phase 3: Coordinator Agent Implementation

**app/agents/coordinator_agent.py**:
```python
"""Coordinator Agent for routing queries to specialized agents."""

import logging
from collections.abc import AsyncIterator
from typing import Any

from strands import Agent
from strands.models import BedrockModel

from app.agents.finops_agent import finops_assistant
from app.config import Settings

logger = logging.getLogger(__name__)

# Coordinator system prompt with routing logic
COORDINATOR_SYSTEM_PROMPT = """
You are an SRE (Site Reliability Engineering) coordinator assistant.

Your role is to help users with infrastructure troubleshooting and operations by routing
queries to specialized agents or answering directly.

AVAILABLE SPECIALIST AGENTS:
- finops_assistant: Use for AWS cost analysis, billing questions, and FinOps queries

ROUTING GUIDELINES:
1. For cost/billing/FinOps questions → Use the finops_assistant tool
   Examples:
   - "What are my AWS costs?"
   - "Show EC2 spending"
   - "Forecast next month's costs"
   - "Compare costs between months"
   - "Which service costs the most?"

2. For general SRE questions → Answer directly
   Examples:
   - "How do I troubleshoot X?"
   - "What's the best practice for Y?"
   - "Explain how Z works"

3. If unsure whether to use a specialist → Ask clarifying questions

When using specialist tools:
- Pass the complete user query to the tool
- Let the specialist handle the analysis
- Present the specialist's response to the user

Always be helpful, clear, and concise in your responses.
"""


class CoordinatorAgent:
    """Coordinator agent that routes queries to specialized agents."""

    def __init__(self, settings: Settings):
        """Initialize the coordinator agent.

        Args:
            settings: Application settings
        """
        self.settings = settings

        # Create Bedrock model
        self.model = BedrockModel(
            model_id=settings.BEDROCK_MODEL_ID,
            region_name=settings.AWS_REGION,
        )

        # Create coordinator agent with specialist tools
        self.agent = Agent(
            model=self.model,
            system_prompt=COORDINATOR_SYSTEM_PROMPT,
            tools=[finops_assistant],  # Add FinOps specialist as tool
        )

        logger.info(
            "Initialized Coordinator agent with model %s",
            settings.BEDROCK_MODEL_ID,
        )

    async def chat(self, prompt: str, user_id: str) -> AsyncIterator[dict[str, Any]]:
        """Chat with the coordinator agent using async streaming.

        Args:
            prompt: User's input message
            user_id: User identifier for session management

        Yields:
            Events from the agent (thinking, tool_use, agent_message)
        """
        logger.info("Coordinator processing request for user %s", user_id)

        try:
            async for event in self.agent.stream_async(prompt):
                # Log event type for debugging
                logger.debug(
                    "Event type: %s for user %s",
                    type(event).__name__,
                    user_id
                )

                # Handle text data chunks
                if "data" in event:
                    text_chunk = event["data"]
                    yield {
                        "type": "agent_message",
                        "content": text_chunk,
                        "is_chunk": True,
                    }

                # Handle tool usage (including finops_assistant calls)
                elif "current_tool_use" in event:
                    tool_info = event["current_tool_use"]
                    tool_name = (
                        tool_info.get("name", "unknown")
                        if isinstance(tool_info, dict)
                        else "unknown"
                    )
                    logger.info(
                        "Coordinator using tool: %s for user %s",
                        tool_name,
                        user_id
                    )
                    yield {
                        "type": "tool_use",
                        "tool_name": tool_name,
                        "status": f"Using {tool_name}...",
                    }

                # Handle completion
                elif event.get("complete"):
                    logger.info("Coordinator completed for user %s", user_id)
                    yield {
                        "type": "complete",
                        "status": "Processing completed",
                    }

                # Handle thinking/processing
                elif "start" in event or "init_event_loop" in event:
                    yield {
                        "type": "thinking",
                        "status": "Analyzing your request...",
                    }

        except Exception as e:
            logger.error(
                "Error in coordinator for user %s: %s",
                user_id,
                str(e),
                exc_info=True
            )
            yield {
                "type": "error",
                "message": str(e),
            }

    def configure(self, **kwargs: Any) -> None:
        """Update agent configuration dynamically.

        Args:
            **kwargs: Configuration parameters to update
        """
        logger.info("Updating coordinator configuration: %s", kwargs)
        # Placeholder for dynamic configuration
```

### Phase 4: API Integration

**Update app/api/routes.py**:
```python
"""Shared API routes for both API and Web services."""

import logging

from fastapi import APIRouter, Depends, HTTPException

from app.agents.coordinator_agent import CoordinatorAgent  # NEW: Use coordinator
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

# Global instances
agent: CoordinatorAgent | None = None  # CHANGED: CoordinatorAgent instead of StrandsAgent
session_manager: SessionManager | None = None


def get_agent() -> CoordinatorAgent:  # CHANGED: Return type
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
    agent: CoordinatorAgent = Depends(get_agent),  # CHANGED: Type annotation
    session_mgr: SessionManager = Depends(get_session_manager),
) -> ChatResponse:
    """Chat endpoint with streaming event support.

    The coordinator agent will route queries to appropriate specialists.
    """
    logger.info("Chat request from user: %s", request.user_id)

    # Add user message to session
    session_mgr.add_message(request.user_id, "user", request.message)

    events = []
    final_response = ""

    try:
        # Stream events from coordinator agent
        async for event in agent.chat(request.message, request.user_id):
            events.append(event)

            # Accumulate text chunks
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

# ... rest of the endpoints remain the same ...
```

**Update app/main.py** (lifespan function):
```python
"""Main application factory with SERVICE_MODE routing."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.agents.coordinator_agent import CoordinatorAgent  # NEW: Import coordinator
from app.api import health, routes
from app.config import get_settings
from app.services.session_manager import SessionManager

# ... logging configuration ...


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan handler for startup and shutdown."""
    settings = get_settings()
    logger.info("Starting application in %s mode on port %s", settings.SERVICE_MODE, settings.PORT)

    # Initialize shared components
    routes.agent = CoordinatorAgent(settings)  # CHANGED: Use CoordinatorAgent
    routes.session_manager = SessionManager(settings.SESSION_STORAGE_PATH)

    logger.info("Application initialized successfully with Coordinator agent")

    yield

    logger.info("Shutting down application")


# ... rest of main.py remains the same ...
```

**Update app/config.py**:
```python
"""Application configuration using Pydantic Settings."""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Service Configuration
    SERVICE_MODE: Literal["api", "web"] = "api"
    PORT: int = 8000

    # AWS Configuration
    AWS_REGION: str = "us-east-1"
    AWS_PROFILE: str | None = None  # For AWS CLI and MCP servers
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""

    # Bedrock Configuration
    BEDROCK_MODEL_ID: str = "anthropic.claude-3-5-sonnet-20241022-v2:0"

    # Application Configuration
    SESSION_STORAGE_PATH: str = "./sessions"
    LOG_LEVEL: str = "INFO"

    # NEW: MCP Configuration
    FASTMCP_LOG_LEVEL: str = "ERROR"  # Control MCP server logging

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
```

### Phase 5: Testing Implementation

**tests/test_finops_agent.py**:
```python
"""Tests for FinOps Agent."""

from unittest.mock import MagicMock, patch

import pytest

from app.agents.finops_agent import finops_assistant


@patch("app.agents.finops_agent.MCPClient")
@patch("app.agents.finops_agent.Agent")
@patch("app.agents.finops_agent.BedrockModel")
def test_finops_assistant_basic_query(
    mock_bedrock_model, mock_agent_class, mock_mcp_client
):
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
def test_finops_assistant_forecast_query(
    mock_bedrock_model, mock_agent_class, mock_mcp_client
):
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
```

**tests/test_coordinator.py**:
```python
"""Tests for Coordinator Agent."""

from unittest.mock import AsyncMock, MagicMock, patch

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
    coordinator = CoordinatorAgent(mock_settings)

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
async def test_coordinator_routes_cost_query(
    mock_agent_class, mock_bedrock_model, mock_settings
):
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
```

## Critical Gotchas & Considerations

### MCP Integration Gotchas

1. **Context Manager Requirement** (CRITICAL):
   ```python
   # ❌ WRONG - Agent used outside context
   with mcp_client:
       agent = Agent(tools=mcp_client.list_tools_sync())
   response = agent("query")  # ERROR: MCP session closed

   # ✅ CORRECT - Everything within context
   with mcp_client:
       agent = Agent(tools=mcp_client.list_tools_sync())
       response = agent("query")  # Works!
   ```

2. **AWS Credentials for MCP**:
   - Cost Explorer MCP needs separate AWS credentials
   - Must have IAM permissions: `ce:GetCostAndUsage`, `ce:GetCostForecast`, `ce:GetDimensionValues`
   - Use `AWS_PROFILE` environment variable for MCP server
   - Different from Bedrock credentials (which can use access keys)

3. **Cost Explorer API Pricing**:
   - Each API call costs **$0.01**
   - Can get expensive with frequent queries
   - Consider implementing caching for repeated queries
   - Warn users about costs in documentation

4. **Tool Description Quality**:
   - FinOps agent tool description must be detailed
   - Coordinator uses descriptions to decide when to route
   - Poor descriptions = coordinator won't route correctly
   - Include example queries in description

5. **Async Streaming Compatibility**:
   - Coordinator must maintain streaming through tool calls
   - Events should bubble up from FinOps agent to coordinator
   - Web UI relies on events for real-time status
   - Test that "thinking" and "tool_use" events work

### Multi-Agent Gotchas

6. **Tool Invocation Overhead**:
   - Each tool call adds latency
   - FinOps queries will be slower (coordinator → FinOps → MCP → Cost Explorer)
   - Set user expectations about response time
   - Consider timeout handling

7. **Error Propagation**:
   - Errors in FinOps agent must be handled gracefully
   - Don't crash coordinator if specialist fails
   - Return helpful error messages to user
   - Log errors for debugging

8. **Session Context**:
   - Coordinator maintains conversation history
   - FinOps agent gets query as single string
   - Context from previous messages may be lost
   - Consider passing relevant context in query

### Testing Gotchas

9. **Mocking MCP Client**:
   - MCP client uses context manager
   - Must mock `__enter__` and `__exit__` methods
   - Mock `list_tools_sync()` to return tool list
   - Test both success and error paths

10. **Async Testing**:
    - Use `@pytest.mark.asyncio` for async tests
    - Mock async generators for streaming
    - Test event ordering in streams
    - Verify all event types are emitted

### Deployment Gotchas

11. **uvx Availability**:
    - MCP server requires `uvx` command
    - Must be installed in Docker container
    - Add to Dockerfile: `RUN pip install uv`
    - Document local installation for development

12. **AWS Profile in Docker**:
    - Container needs access to `~/.aws/credentials`
    - Mount AWS credentials directory (read-only)
    - Or use environment variables for credentials
    - Security consideration: don't commit credentials

## Dependencies

**Update pyproject.toml**:
```toml
[project]
name = "sre-bot-strands"
version = "0.1.0"
description = "SRE Bot with FinOps Multi-Agent System"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.34.0",
    "strands-agents==1.10.0",
    "strands-agents-tools==0.2.9",
    "mcp>=1.0.0",  # NEW: Model Context Protocol
    "pydantic>=2.11.0",
    "pydantic-settings>=2.0.0",
    "boto3>=1.35.0",
    "python-dotenv>=1.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "ruff>=0.8.0",
    "mypy>=1.13.0",
    "httpx>=0.27.0",
]
```

## Implementation Tasks (Ordered)

### Phase 1: Environment Setup (15 min)
1. [ ] Update `pyproject.toml` with `mcp>=1.0.0` dependency
2. [ ] Run `uv sync` to install new dependencies
3. [ ] Update `.env.example` with `AWS_PROFILE` and `FASTMCP_LOG_LEVEL`
4. [ ] Verify `uvx` is installed: `uvx --version`
5. [ ] Test Cost Explorer MCP server: `uvx awslabs.cost-explorer-mcp-server@latest --help`

### Phase 2: FinOps Agent (45 min)
6. [ ] Create `app/agents/finops_agent.py` file
7. [ ] Implement `FINOPS_SYSTEM_PROMPT` with detailed instructions
8. [ ] Implement `finops_assistant` function with `@tool` decorator
9. [ ] Add MCP client initialization with `stdio_client`
10. [ ] Implement context manager pattern for MCP
11. [ ] Add comprehensive error handling
12. [ ] Add logging for debugging
13. [ ] Test FinOps agent standalone (manual test with Cost Explorer query)

### Phase 3: Coordinator Agent (30 min)
14. [ ] Create `app/agents/coordinator_agent.py` file
15. [ ] Implement `COORDINATOR_SYSTEM_PROMPT` with routing logic
16. [ ] Create `CoordinatorAgent` class matching `StrandsAgent` pattern
17. [ ] Add `finops_assistant` to coordinator's tools list
18. [ ] Implement `async chat()` method with streaming
19. [ ] Add event handling (thinking, tool_use, agent_message)
20. [ ] Add error handling and logging

### Phase 4: API Integration (20 min)
21. [ ] Update `app/api/routes.py` imports to use `CoordinatorAgent`
22. [ ] Change agent type annotations from `StrandsAgent` to `CoordinatorAgent`
23. [ ] Update `app/main.py` lifespan function to initialize `CoordinatorAgent`
24. [ ] Update `app/config.py` with MCP configuration fields
25. [ ] Test API endpoint with cost query: `POST /api/chat`

### Phase 5: Testing (45 min)
26. [ ] Create `tests/test_finops_agent.py`
27. [ ] Write test for basic cost query
28. [ ] Write test for MCP error handling
29. [ ] Write test for forecast query
30. [ ] Create `tests/test_coordinator.py`
31. [ ] Write test for coordinator initialization
32. [ ] Write test for cost query routing
33. [ ] Write test for general query handling
34. [ ] Run all tests: `uv run pytest tests/ -v`

### Phase 6: Code Quality (15 min)
35. [ ] Run `uv run ruff format .`
36. [ ] Run `uv run ruff check --fix .`
37. [ ] Run `uv run mypy app/` and fix type errors
38. [ ] Review and fix any remaining warnings

### Phase 7: Documentation (30 min)
39. [ ] Update `README.md` with multi-agent architecture
40. [ ] Document FinOps agent capabilities
41. [ ] Add prerequisites (uvx, AWS permissions)
42. [ ] Add example cost queries
43. [ ] Document Cost Explorer API costs ($0.01 per request)
44. [ ] Add troubleshooting section for MCP issues
45. [ ] Update `.env.example` with new variables

### Phase 8: Integration Testing (30 min)
46. [ ] Start services: `docker-compose up --build`
47. [ ] Test health endpoint: `curl http://localhost:8000/health`
48. [ ] Test cost query via API:
    ```bash
    curl -X POST http://localhost:8000/api/chat \
      -H "Content-Type: application/json" \
      -d '{"user_id": "test", "message": "What are my AWS costs for last month?"}'
    ```
49. [ ] Test general query via API:
    ```bash
    curl -X POST http://localhost:8000/api/chat \
      -H "Content-Type: application/json" \
      -d '{"user_id": "test", "message": "How do I troubleshoot EC2 instances?"}'
    ```
50. [ ] Test via Web UI (http://localhost:8001)
51. [ ] Verify event streaming shows tool usage
52. [ ] Check logs for coordinator → FinOps routing

### Phase 9: Final Validation (15 min)
53. [ ] Run all validation gates (see below)
54. [ ] Verify Cost Explorer MCP tools are loaded (check logs)
55. [ ] Test error handling (invalid AWS credentials)
56. [ ] Verify session persistence works
57. [ ] Review all new code for best practices

## Validation Gates (Executable)

```bash
# 1. Code Formatting & Linting
uv run ruff format .
uv run ruff check --fix .

# 2. Type Checking
uv run mypy app/

# 3. Unit Tests
uv run pytest tests/ -v

# 4. Docker Build
docker-compose build

# 5. Start Services
docker-compose up -d

# 6. Wait for startup
sleep 15

# 7. Health Check
curl -f http://localhost:8000/health || echo "Health check failed"

# 8. Test FinOps Query
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"user_id":"test","message":"What are my AWS costs for the last 30 days?"}' \
  | jq '.response' || echo "FinOps query failed"

# 9. Test General Query (should NOT use FinOps tool)
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"user_id":"test","message":"What is Docker?"}' \
  | jq '.response' || echo "General query failed"

# 10. Test Forecast Query
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"user_id":"test","message":"Forecast my AWS costs for next month"}' \
  | jq '.response' || echo "Forecast query failed"

# 11. Check Logs for Tool Usage
docker-compose logs api | grep -i "finops" || echo "FinOps tool not used"

# 12. Check Logs for MCP Tools Loaded
docker-compose logs api | grep -i "cost explorer tools" || echo "MCP tools not loaded"

# 13. Web UI Test
curl -f http://localhost:8001/static/index.html || echo "Web UI not accessible"

# 14. Stop Services
docker-compose down
```

## Success Criteria

- [ ] All validation gates pass without errors
- [ ] FinOps agent successfully connects to Cost Explorer MCP
- [ ] Coordinator correctly routes cost queries to FinOps agent
- [ ] Coordinator answers general queries directly (without FinOps tool)
- [ ] Streaming events work through multi-agent chain
- [ ] Web UI displays tool usage ("Using finops_assistant...")
- [ ] Cost queries return actual AWS cost data
- [ ] Forecast queries return future cost predictions
- [ ] Error handling works (graceful failures, informative messages)
- [ ] Tests achieve >80% code coverage for new modules
- [ ] Documentation is complete and accurate
- [ ] No type errors from mypy
- [ ] No lint errors from ruff

## Documentation Resources

### Strands Framework
- Strands Quickstart: https://strandsagents.com/latest/documentation/docs/user-guide/quickstart/
- Agents as Tools: https://strandsagents.com/latest/documentation/docs/user-guide/concepts/multi-agent/agents-as-tools/
- MCP Tools: https://strandsagents.com/latest/documentation/docs/user-guide/concepts/tools/mcp-tools/
- Workflow Pattern: https://strandsagents.com/latest/documentation/docs/user-guide/concepts/multi-agent/workflow/

### AWS Cost Explorer MCP
- Cost Explorer MCP Server: https://awslabs.github.io/mcp/servers/cost-explorer-mcp-server/
- AWS MCP Servers: https://github.com/awslabs/mcp
- AWS Billing MCP Blog: https://aws.amazon.com/blogs/aws-cloud-financial-management/aws-announces-billing-and-cost-management-mcp-server/

### Model Context Protocol
- MCP Specification: https://modelcontextprotocol.io
- MCP Python SDK: https://github.com/modelcontextprotocol/python-sdk

### Examples
- Multi-Agent Example: https://strandsagents.com/latest/documentation/docs/examples/python/multi_agent_example/multi_agent_example/
- Agent Workflows: https://strandsagents.com/latest/documentation/docs/examples/python/agents_workflows/

## PRP Self-Assessment

### Quality Checklist
- [x] All necessary context included (Strands, MCP, Cost Explorer, multi-agent patterns)
- [x] Validation gates are executable by AI
- [x] References existing patterns from codebase
- [x] Clear implementation path with ordered tasks
- [x] Error handling and gotchas documented comprehensively
- [x] Complete dependency list with versions
- [x] Architecture diagram showing agent relationships
- [x] Code examples for all major components
- [x] Specific URLs to documentation
- [x] Success criteria clearly defined
- [x] Test patterns provided

### Confidence Score: **8/10**

**Rationale**: This PRP provides comprehensive context with proven patterns:

**Strengths** (+8 points):
- Clear "Agents as Tools" architecture matching INITIAL.md example
- Detailed MCP integration with context manager pattern
- Complete code examples for FinOps and Coordinator agents
- Existing codebase patterns followed (StrandsAgent structure)
- Comprehensive testing strategy with mocks
- Critical gotchas identified (context manager, AWS costs)
- Executable validation gates
- 50+ granular implementation tasks

**Potential Challenges** (-2 points):
1. **MCP Integration Complexity**: First-time MCP integration in this codebase
   - Mitigation: Detailed examples and references provided
   - Context manager pattern clearly documented

2. **AWS Cost Explorer Permissions**: May need IAM policy updates
   - Mitigation: Required permissions documented
   - Error handling for permission issues included

3. **Tool Routing Accuracy**: Coordinator may not always route correctly
   - Mitigation: Detailed system prompt with examples
   - Testing includes routing verification

**Why Not 9-10**:
- No existing MCP code in codebase to reference (new integration)
- AWS Cost Explorer API costs may surprise users (documented but worth noting)
- Multi-agent streaming complexity not tested in existing code

**Why Not Lower**:
- Architecture pattern is well-documented in Strands docs
- Similar patterns exist in codebase (StrandsAgent wrapper)
- Comprehensive examples and validation gates reduce risk
- Clear rollback strategy (revert to StrandsAgent if needed)

The AI agent has a high probability of one-pass implementation success given:
- Detailed code examples for every component
- Clear task ordering with time estimates
- Comprehensive testing strategy
- Validation gates to verify each step
- Extensive documentation references
