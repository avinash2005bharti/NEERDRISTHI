from fastapi import Header, HTTPException, status
from ..config import settings
from ..observability.logger import logger


async def verify_internal_service_secret(
    x_internal_service_secret: str = Header(default="", alias="x-internal-service-secret")
) -> bool:
    """
    Ensure caller possesses the internal service secret shared between Gateway and Agent Core.
    """
    configured_secret = settings.INTERNAL_SERVICE_SECRET.strip()

    if not configured_secret:
        # In local dev when secret is left blank in .env.example, allow request but log warning
        logger.debug("INTERNAL_SERVICE_SECRET is unconfigured. Allowing request in local dev mode.")
        return True

    if x_internal_service_secret != configured_secret:
        logger.warning("Unauthorized attempt to access internal agent-core endpoint.")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Invalid internal service secret.",
        )

    return True
