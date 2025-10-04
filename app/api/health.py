"""Health check endpoint for both API and Web services."""

import logging

from fastapi import APIRouter, Depends

from app.config import Settings, get_settings
from app.models.schemas import HealthResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check(settings: Settings = Depends(get_settings)) -> HealthResponse:
    """Health check endpoint that verifies service status and AWS Bedrock connectivity.

    Args:
        settings: Application settings

    Returns:
        HealthResponse with status, service_mode, and bedrock_connected fields
    """
    # Test AWS Bedrock connectivity
    bedrock_connected = await _check_bedrock_connectivity(settings)

    return HealthResponse(
        status="healthy" if bedrock_connected else "degraded",
        service_mode=settings.SERVICE_MODE,
        bedrock_connected=bedrock_connected,
        details={
            "region": settings.AWS_REGION,
            "model_id": settings.BEDROCK_MODEL_ID,
        },
    )


async def _check_bedrock_connectivity(settings: Settings) -> bool:
    """Check if AWS Bedrock is accessible.

    Args:
        settings: Application settings

    Returns:
        True if Bedrock is accessible, False otherwise
    """
    try:
        import boto3

        # Create Bedrock client
        # Note: boto3 automatically uses AWS_PROFILE from environment if set
        bedrock = boto3.client(
            "bedrock",  # Use bedrock (not bedrock-runtime) for list operations
            region_name=settings.AWS_REGION,
        )

        # Try to list available models (lightweight check)
        # Note: This requires bedrock:ListFoundationModels permission
        bedrock.list_foundation_models(byProvider="anthropic")

        logger.debug("Bedrock connectivity check: Success")
        return True
    except Exception as e:
        logger.error("Bedrock connectivity check failed: %s", str(e))
        return False
