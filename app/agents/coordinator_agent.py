"""Coordinator Agent for routing queries to specialized agents."""

import logging
from collections.abc import AsyncIterator
from typing import Any

from strands import Agent
from strands.models import BedrockModel

from app.agents.finops_agent import finops_assistant
from app.agents.kubernetes_agent import kubernetes_assistant
from app.config import Settings

logger = logging.getLogger(__name__)

# Coordinator system prompt with routing logic
COORDINATOR_SYSTEM_PROMPT = """
You are an SRE (Site Reliability Engineering) coordinator assistant.

Your role is to help users with infrastructure troubleshooting and operations by routing
queries to specialized agents or answering directly.

AVAILABLE SPECIALIST AGENTS:
- finops_assistant: Use for AWS cost analysis, billing questions, and FinOps queries
- kubernetes_assistant: Use for Kubernetes cluster management and troubleshooting

ROUTING GUIDELINES:
1. For cost/billing/FinOps questions → Use the finops_assistant tool
   Examples:
   - "What are my AWS costs?"
   - "Show EC2 spending"
   - "Forecast next month's costs"
   - "Compare costs between months"
   - "Which service costs the most?"

2. For Kubernetes questions → Use the kubernetes_assistant tool
   Examples:
   - "What pods are running in my cluster?"
   - "Show me logs from pod X"
   - "List deployments in namespace Y"
   - "What events occurred?"
   - "Check pod status"
   - "List all namespaces"

3. For general SRE questions → Answer directly
   Examples:
   - "How do I troubleshoot X?"
   - "What's the best practice for Y?"
   - "Explain how Z works"

4. If unsure whether to use a specialist → Ask clarifying questions

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
            tools=[finops_assistant, kubernetes_assistant],  # Add specialist agents as tools
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
                logger.debug("Event type: %s for user %s", type(event).__name__, user_id)

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
                    logger.info("Coordinator using tool: %s for user %s", tool_name, user_id)
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
            logger.exception("Error in coordinator for user %s: %s", user_id, str(e))
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
