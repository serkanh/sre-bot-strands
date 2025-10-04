"""FinOps Agent with AWS Cost Explorer MCP integration."""

import logging

from mcp import StdioServerParameters, stdio_client
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
        cost_explorer_mcp = MCPClient(
            lambda: stdio_client(
                StdioServerParameters(
                    command="uvx",
                    args=["awslabs.cost-explorer-mcp-server@latest"],
                    env={
                        "AWS_REGION": settings.AWS_REGION,
                        "AWS_PROFILE": settings.AWS_PROFILE or "",
                        "FASTMCP_LOG_LEVEL": "ERROR",
                    },
                )
            )
        )

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
        error_msg = f"Error in FinOps assistant: {e!s}"
        logger.exception(error_msg)
        return error_msg


# Export the tool
__all__ = ["finops_assistant"]
