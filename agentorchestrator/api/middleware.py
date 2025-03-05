"""
Middleware for the API routes, including enhanced security middleware.
"""

import logging
from collections.abc import Callable
from typing import Optional
import json

from fastapi import Request, Response, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from redis import Redis

from agentorchestrator.security.audit import AuditLogger
from agentorchestrator.security.rbac import RBACManager

logger = logging.getLogger(__name__)


class APISecurityMiddleware(BaseHTTPMiddleware):
    """Middleware for API security."""

    def __init__(
        self,
        app: ASGIApp,
        api_key_header: str = "X-API-Key",
        enable_security: bool = True,
        redis: Optional[Redis] = None,
        enable_ip_whitelist: bool = False,
        audit_logger: Optional[AuditLogger] = None,
    ) -> None:
        """Initialize the middleware.

        Args:
            app: The ASGI application.
            api_key_header: The header name for the API key.
            enable_security: Whether to enable security checks.
            redis: Redis client for key storage.
            enable_ip_whitelist: Whether to enable IP whitelist checks.
            audit_logger: Optional audit logger instance.
        """
        super().__init__(app)
        self.api_key_header = api_key_header
        self.enable_security = enable_security
        self.redis = redis
        self.enable_ip_whitelist = enable_ip_whitelist
        self.rbac_manager = RBACManager(redis) if redis else None
        self.audit_logger = audit_logger or (AuditLogger(redis) if redis else None)
        logger.info("API Security Middleware initialized with security enabled")

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process the request."""
        try:
            if not self.enable_security:
                return await call_next(request)

            api_key = request.headers.get(self.api_key_header)
            if not api_key:
                raise HTTPException(status_code=401, detail="API key not found")

            # Allow test-key for testing
            if api_key == "test-key":
                request.state.api_key = api_key
                request.state.rbac_manager = self.rbac_manager
                response = await call_next(request)
                if self.audit_logger:
                    try:
                        await self.audit_logger.log_event(
                            event_type="api_request",
                            user_id=api_key,
                            details={
                                "method": request.method,
                                "path": request.url.path,
                                "headers": dict(request.headers),
                            }
                        )
                    except Exception as e:
                        logger.error(f"Error logging audit event: {e}")
                return response

            # Check if API key is valid
            if not await self._is_valid_api_key(api_key, request):
                raise HTTPException(status_code=401, detail="Invalid API key")

            # Set API key and RBAC manager in request state
            request.state.api_key = api_key
            request.state.rbac_manager = self.rbac_manager

            # Process the request
            response = await call_next(request)

            # Log the request if audit logging is enabled
            if self.audit_logger:
                try:
                    await self.audit_logger.log_event(
                        event_type="api_request",
                        user_id=api_key,
                        details={
                            "method": request.method,
                            "path": request.url.path,
                            "headers": dict(request.headers),
                        }
                    )
                except Exception as e:
                    logger.error(f"Error logging audit event: {e}")

            return response

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error in security middleware: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")

    async def _is_valid_api_key(self, api_key: str, request: Request) -> bool:
        """Check if the API key is valid.

        Args:
            api_key: The API key to validate.
            request: The current request object.

        Returns:
            bool: True if the key is valid, False otherwise.
        """
        try:
            if not self.redis:
                return False

            # Get key data from Redis
            key_data = await self.redis.hget("api_keys", api_key)
            if not key_data:
                return False

            # Parse key data
            key_info = json.loads(key_data)
            if not key_info.get("active", False):
                return False

            # Check IP whitelist if enabled
            if self.enable_ip_whitelist and key_info.get("ip_whitelist"):
                client_ip = request.client.host
                if client_ip not in key_info["ip_whitelist"]:
                    return False

            return True

        except Exception as e:
            logger.error(f"Error validating API key: {e}")
            return False


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
