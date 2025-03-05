"""Security integration module for the AORBIT framework."""

import json
from typing import Optional, Callable
import os

from fastapi import FastAPI, HTTPException, Request, status, Depends
from loguru import logger
from redis import Redis
from starlette.responses import JSONResponse, Response
from starlette.middleware.base import BaseHTTPMiddleware

from agentorchestrator.security.audit import (
    initialize_audit_logger,
    log_auth_failure,
    log_auth_success,
    log_api_request,
)
from agentorchestrator.security.encryption import initialize_encryption
from agentorchestrator.security.rbac import initialize_rbac
from agentorchestrator.api.middleware import APISecurityMiddleware


class SecurityMiddleware(BaseHTTPMiddleware):
    """Security middleware for request processing."""

    def __init__(
        self,
        app,
        security_integration,
    ):
        """Initialize the security middleware.

        Args:
            app: The FastAPI application
            security_integration: The security integration instance
        """
        super().__init__(app)
        self.security_integration = security_integration

    async def dispatch(
        self,
        request: Request,
        call_next: Callable,
    ) -> Response:
        """Process the request and apply security checks.

        Args:
            request: Incoming request
            call_next: Next middleware in the chain

        Returns:
            Response from next middleware
        """
        # Skip security for OPTIONS requests and docs
        if request.method == "OPTIONS" or request.url.path in [
            "/docs",
            "/redoc",
            "/openapi.json",
            "/",
            "/api/v1/health",
        ]:
            return await call_next(request)

        # Get API key from request header
        api_key = request.headers.get(self.security_integration.api_key_header_name)

        # Record client IP address
        client_ip = request.client.host if request.client else None

        # Enterprise security integration
        if self.security_integration.enable_rbac or self.security_integration.enable_audit:
            # Process API key for role and permissions
            role = None
            user_id = None

            if api_key and self.security_integration.rbac_manager:
                # Get role from API key
                redis_role = await self.security_integration.redis.get(f"apikey:{api_key}")

                if redis_role:
                    role = redis_role.decode("utf-8")
                    request.state.role = role

                    # Check IP whitelist if applicable
                    ip_whitelist = await self.security_integration.redis.get(
                        f"apikey:{api_key}:ip_whitelist"
                    )
                    if ip_whitelist:
                        ip_whitelist = json.loads(ip_whitelist.decode())
                        if ip_whitelist and client_ip not in ip_whitelist:
                            if self.security_integration.audit_logger:
                                await log_auth_failure(
                                    ip_address=client_ip,
                                    reason="IP address not in whitelist",
                                    redis_client=self.security_integration.redis,
                                    api_key_id=api_key,
                                )
                            return JSONResponse(
                                status_code=403,
                                content={
                                    "detail": "Forbidden: IP address not authorized"
                                },
                            )

                    # Log successful authentication
                    if self.security_integration.audit_logger:
                        await log_auth_success(
                            user_id=user_id,
                            api_key_id=api_key,
                            ip_address=client_ip,
                            redis_client=self.security_integration.redis,
                        )

            # Store API key and role in request state for use in route handlers
            request.state.api_key = api_key

            # Log request
            if self.security_integration.audit_logger:
                await log_api_request(
                    request=request,
                    user_id=user_id,
                    api_key_id=api_key,
                    status_code=200,
                    redis_client=self.security_integration.redis,
                )

        # Legacy API key validation
        elif api_key:
            # Simple API key validation
            if not api_key.startswith(("aorbit", "ao-")):
                logger.warning(f"Invalid API key format from {client_ip}")
                if self.security_integration.audit_logger:
                    await log_auth_failure(
                        ip_address=client_ip,
                        reason="Invalid API key format",
                        redis_client=self.security_integration.redis,
                        api_key_id=api_key,
                    )
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={"detail": "Unauthorized: Invalid API key"},
                )

        # Continue request processing
        try:
            response = await call_next(request)
            return response
        except Exception as e:
            logger.error(f"Error processing request: {str(e)}")

            # Log error
            if hasattr(request.state, "api_key") and self.security_integration.audit_logger:
                await log_api_request(
                    request=request,
                    user_id=user_id,
                    api_key_id=request.state.api_key,
                    status_code=500,
                    redis_client=self.security_integration.redis,
                )

            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": "Internal Server Error"},
            )


class SecurityIntegration:
    """Security integration for the AORBIT framework."""

    def __init__(
        self,
        app: FastAPI,
        redis: Redis,
        enable_security: bool = True,
        enable_rbac: bool = True,
        enable_audit: bool = True,
        enable_encryption: bool = True,
        api_key_header_name: str = "X-API-Key",
        ip_whitelist: Optional[list[str]] = None,
        encryption_key: Optional[str] = None,
        rbac_config: Optional[dict] = None,
    ) -> None:
        """Initialize the security integration."""
        self.app = app
        self.redis = redis
        self.enable_security = enable_security
        self.enable_rbac = enable_rbac
        self.enable_audit = enable_audit
        self.enable_encryption = enable_encryption
        self.api_key_header_name = api_key_header_name
        self.ip_whitelist = ip_whitelist or []
        self.encryption_key = encryption_key
        self.encryption_manager = None
        self.rbac_manager = None
        self.audit_logger = None

    async def initialize(self) -> None:
        """Initialize the security components."""
        # Initialize encryption
        if self.enable_encryption:
            # Set encryption key in environment if not already set
            if not os.getenv("ENCRYPTION_KEY"):
                os.environ["ENCRYPTION_KEY"] = self.encryption_key or "test-key"
            self.encryption_manager = initialize_encryption()
            logger.info("Encryption initialized")

        # Initialize RBAC
        if self.enable_rbac:
            self.rbac_manager = initialize_rbac(self.redis)
            logger.info("RBAC initialized")

        # Initialize audit logging
        if self.enable_audit:
            self.audit_logger = initialize_audit_logger(self.redis)
            logger.info("Audit logging initialized")

        # Add security middleware
        self.app.add_middleware(
            APISecurityMiddleware,
            api_key_header=self.api_key_header_name,
            enable_security=self.enable_security,
            enable_ip_whitelist=bool(self.ip_whitelist),
            audit_logger=self.audit_logger,
            redis=self.redis,
        )

    def check_permission_dependency(self, permission: str) -> Callable:
        """Create a FastAPI dependency for checking permissions.

        Args:
            permission: The required permission

        Returns:
            A callable function that checks for the required permission
        """
        async def check_permission(request: Request) -> None:
            """Check if the request has the required permission.

            Args:
                request: The FastAPI request

            Raises:
                HTTPException: If the permission check fails
            """
            if not self.enable_rbac:
                return

            api_key = getattr(request.state, "api_key", None)
            if not api_key:
                raise HTTPException(
                    status_code=401,
                    detail="API key not found",
                )

            if not await self.rbac_manager.check_permission(api_key, permission):
                raise HTTPException(
                    status_code=403,
                    detail=f"Permission '{permission}' required",
                )

        return check_permission

    def require_permission(self, permission: str) -> Depends:
        """Create a FastAPI dependency for requiring a permission.

        Args:
            permission: The permission to require

        Returns:
            Depends: A FastAPI dependency that checks if the request has the required permission
        """
        async def check_permission(request: Request) -> None:
            """Check if the request has the required permission.

            Args:
                request: The FastAPI request object

            Raises:
                HTTPException: If the permission check fails
            """
            if not self.enable_rbac:
                return

            api_key = request.state.api_key
            if not api_key:
                raise HTTPException(
                    status_code=401,
                    detail="API key not found",
                )

            has_permission = await self.rbac_manager.has_permission(api_key, permission)
            if not has_permission:
                raise HTTPException(
                    status_code=403,
                    detail=f"Permission '{permission}' required",
                )

        return Depends(check_permission)


async def initialize_security(
    app: FastAPI,
    redis_client: Redis,
    enable_security: bool = True,
    enable_rbac: bool = True,
    enable_audit: bool = True,
    enable_encryption: bool = True,
) -> "SecurityIntegration":
    """Initialize enterprise security framework.

    Args:
        app: FastAPI application instance
        redis_client: Redis client instance
        enable_security: Whether to enable security features
        enable_rbac: Whether to enable RBAC
        enable_audit: Whether to enable audit logging
        enable_encryption: Whether to enable encryption

    Returns:
        SecurityIntegration: Initialized security integration
    """
    logger.info("\nInitializing enterprise security framework")

    # Create security integration instance
    security = SecurityIntegration(
        app=app,
        redis=redis_client,
        enable_security=enable_security,
        enable_rbac=enable_rbac,
        enable_audit=enable_audit,
        enable_encryption=enable_encryption,
    )
    await security.initialize()
    return security
