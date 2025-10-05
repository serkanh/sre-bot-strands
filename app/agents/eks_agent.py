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
