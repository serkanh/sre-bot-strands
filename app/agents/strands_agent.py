"""Strands Agent wrapper for AWS Bedrock."""

import logging
from collections.abc import AsyncIterator
from typing import Any

from strands import Agent
from strands.models import BedrockModel

from app.config import Settings

logger = logging.getLogger(__name__)


class StrandsAgent:
    """Wrapper around Strands Agent with AWS Bedrock configuration."""

    def __init__(self, settings: Settings):
        """Initialize the Strands agent with Bedrock model.

        Args:
            settings: Application settings containing AWS and model configuration
        """
        self.settings = settings

        # Initialize Bedrock model
        self.model = BedrockModel(
            model_id=settings.BEDROCK_MODEL_ID,
            region_name=settings.AWS_REGION,
        )

        # Initialize agent with model and tools
        # Note: We can add tools from strands-agents-tools here
        self.agent = Agent(
            model=self.model,
            tools=[],  # Add tools as needed
        )

        logger.info(
            "Initialized Strands agent with model %s in region %s",
            settings.BEDROCK_MODEL_ID,
            settings.AWS_REGION,
        )

    async def chat(self, prompt: str, user_id: str) -> AsyncIterator[dict[str, Any]]:
        """Chat with the agent using async streaming.

        Args:
            prompt: User's input message
            user_id: User identifier for session management

        Yields:
            Events from the agent (thinking, tool_use, agent_message)
        """
        logger.info("Processing chat request for user %s", user_id)

        try:
            async for event in self.agent.stream_async(prompt):
                # Debug: log the raw event structure
                logger.debug("Raw event type: %s, event: %s", type(event).__name__, str(event)[:200])

                # Handle text data chunks from Strands
                if "data" in event:
                    text_chunk = event["data"]
                    logger.debug("Text chunk for user %s: %s", user_id, text_chunk)
                    yield {
                        "type": "agent_message",
                        "content": text_chunk,
                        "is_chunk": True,
                    }

                # Handle tool usage
                elif "current_tool_use" in event:
                    tool_info = event["current_tool_use"]
                    tool_name = tool_info.get("name", "unknown") if isinstance(tool_info, dict) else "unknown"
                    logger.debug("Tool use for user %s: %s", user_id, tool_name)
                    yield {
                        "type": "tool_use",
                        "tool_name": tool_name,
                        "status": f"Using tool: {tool_name}",
                    }

                # Handle completion
                elif event.get("complete"):
                    logger.debug("Agent completed for user %s", user_id)
                    yield {
                        "type": "complete",
                        "status": "Agent completed processing",
                    }

                # Handle agent thinking/processing indicators
                elif "start" in event or "init_event_loop" in event:
                    logger.debug("Agent starting for user %s", user_id)
                    yield {
                        "type": "thinking",
                        "status": "Agent is thinking...",
                    }

        except Exception as e:
            logger.error("Error in agent chat for user %s: %s", user_id, e)
            yield {
                "type": "error",
                "message": str(e),
            }

    def configure(self, **kwargs: Any) -> None:
        """Update agent configuration dynamically.

        Args:
            **kwargs: Configuration parameters to update
        """
        # This can be extended to update model settings, tools, etc.
        logger.info("Updating agent configuration: %s", kwargs)
        # Placeholder for dynamic configuration
