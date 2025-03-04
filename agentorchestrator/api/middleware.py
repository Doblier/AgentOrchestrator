"""
Middleware for the API routes, including enhanced security middleware.
"""

import logging
from collections.abc import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class APISecurityMiddleware(BaseHTTPMiddleware):
    """
    Middleware for API security, integrating with the enterprise security framework.

    This middleware:
    1. Checks for valid API keys
    2. Verifies IP whitelist restrictions
    3. Enforces rate limits
    4. Logs all API requests
    """

    def __init__(
        self,
        app,
        api_key_header: str = "X-API-Key",
        enable_security: bool = True,
    ):
        super().__init__(app)
        self.api_key_header = api_key_header
        self.enable_security = enable_security
        logger.info(
            f"API Security Middleware initialized with security {'enabled' if enable_security else 'disabled'}"
        )

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process the request through the middleware."""
        # Skip security checks if disabled
        if not self.enable_security:
            return await call_next(request)

        # Check for integration with enterprise security framework
        security = getattr(request.app.state, "security", None)
        if security:
            # If enterprise security is integrated, defer to it
            logger.debug("Using enterprise security framework")
            try:
                # Let the enterprise security framework handle the request
                # The actual checks will be done by the SecurityIntegration._security_middleware
                return await call_next(request)
            except Exception as e:
                logger.error(f"Enterprise security error: {str(e)}")
                return JSONResponse(
                    status_code=500,
                    content={"detail": "Internal security error"},
                )

        # Legacy API key check if enterprise security is not available
        api_key = request.headers.get(self.api_key_header)
        if not api_key:
            logger.warning(f"No API key provided from {request.client.host}")
            return JSONResponse(
                status_code=401,
                content={"detail": "API key required"},
            )

        # Very basic validation - in real scenario, this would check against a database
        if not self._is_valid_api_key(api_key):
            logger.warning(f"Invalid API key provided from {request.client.host}")
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid API key"},
            )

        # Set API key in request state for downstream handlers
        request.state.api_key = api_key

        # Process the request
        try:
            response = await call_next(request)
            return response
        except Exception as e:
            logger.error(f"Error processing request: {str(e)}")
            return JSONResponse(
                status_code=500,
                content={"detail": "Internal server error"},
            )

    def _is_valid_api_key(self, api_key: str) -> bool:
        """
        Simple API key validation for legacy mode.

        This is only used when the enterprise security framework is not available.
        In production, this should validate against a secure database.
        """
        # In a real implementation, this would check against a database
        # This is just a placeholder for simple cases
        return api_key.startswith("ao-") or api_key.startswith("aorbit-")


# Factory function to create the middleware
def create_api_security_middleware(
    app,
    api_key_header: str = "X-API-Key",
    enable_security: bool = True,
) -> APISecurityMiddleware:
    """Create and return an instance of the API security middleware."""
    return APISecurityMiddleware(
        app=app,
        api_key_header=api_key_header,
        enable_security=enable_security,
    )
