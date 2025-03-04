"""Security integration module for the AORBIT framework."""

import json
import os
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Request, status, Depends
from fastapi.security import APIKeyHeader
from loguru import logger
from redis import Redis
from starlette.responses import JSONResponse

from agentorchestrator.security.audit import (
    AuditEvent,
    AuditEventType,
    initialize_audit_logger,
    log_auth_failure,
    log_auth_success,
    log_api_request,
)
from agentorchestrator.security.encryption import initialize_encryption
from agentorchestrator.security.rbac import initialize_rbac


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
        """Initialize the security integration.

        Args:
            app: FastAPI application instance
            redis: Redis client instance
            enable_security: Whether to enable security features
            enable_rbac: Whether to enable RBAC
            enable_audit: Whether to enable audit logging
            enable_encryption: Whether to enable encryption
            api_key_header_name: Name of the header containing the API key
            ip_whitelist: List of whitelisted IP addresses
            encryption_key: Encryption key for sensitive data
            rbac_config: RBAC configuration
        """
        self.app = app
        self.redis = redis
        self.enable_security = enable_security
        self.rbac_enabled = enable_rbac
        self.audit_enabled = enable_audit
        self.encryption_enabled = enable_encryption
        self.api_key_header_name = api_key_header_name
        self.ip_whitelist = ip_whitelist or []
        self.encryption_manager = None
        self.rbac_manager = None
        self.audit_logger = None

        # Initialize components
        self._setup_middleware(encryption_key, rbac_config)

    def _setup_middleware(self, encryption_key: Optional[str] = None, rbac_config: Optional[dict] = None):
        """Set up security middleware components.

        Args:
            encryption_key (Optional[str]): Encryption key for sensitive data
            rbac_config (Optional[dict]): RBAC configuration
        """
        # Initialize encryption
        if encryption_key:
            self.encryption_manager = initialize_encryption(encryption_key)
            logger.info("Encryption initialized")

        # Initialize RBAC
        if rbac_config:
            self.rbac_manager = initialize_rbac(self.redis, rbac_config)
            logger.info("RBAC initialized")

        # Initialize audit logging
        self.audit_logger = initialize_audit_logger(self.redis)
        if self.audit_logger:
            logger.info("Audit logging initialized")

        # Using add_middleware instead of the decorator to avoid the timing issue
        self.app.middleware("http")(self._security_middleware)

        # Add API key security scheme to OpenAPI docs if security is enabled
        if self.enable_security:
            self.app.add_middleware(
                "http",
                dependencies=[Depends(self.check_permission_dependency("*"))]
            )

    async def _security_middleware(self, request: Request, call_next):
        """Security middleware for request processing.

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
        api_key = request.headers.get(self.api_key_header_name)

        # Record client IP address
        client_ip = request.client.host if request.client else None

        # Enterprise security integration
        if self.rbac_enabled or self.audit_enabled:
            # Process API key for role and permissions
            role = None
            user_id = None

            if api_key and self.rbac_manager:
                # Get role from API key
                redis_role = await self.redis.get(f"apikey:{api_key}")

                if redis_role:
                    role = redis_role.decode("utf-8")
                    request.state.role = role

                    # Check IP whitelist if applicable
                    ip_whitelist = await self.redis.get(
                        f"apikey:{api_key}:ip_whitelist"
                    )
                    if ip_whitelist:
                        ip_whitelist = json.loads(ip_whitelist)
                        if ip_whitelist and client_ip not in ip_whitelist:
                            if self.audit_logger:
                                await log_auth_failure(
                                    self.audit_logger,
                                    api_key_id=api_key,
                                    ip_address=client_ip,
                                    reason="IP address not in whitelist",
                                )
                            return JSONResponse(
                                status_code=403,
                                content={
                                    "detail": "Forbidden: IP address not authorized"
                                },
                            )

                    # Log successful authentication
                    if self.audit_logger:
                        log_auth_success(
                            user_id=user_id,
                            api_key_id=api_key,
                            ip_address=client_ip,
                            redis_client=self.redis,
                        )

            # Store API key and role in request state for use in route handlers
            request.state.api_key = api_key

            # Log request
            if self.audit_logger:
                log_api_request(
                    request=request,
                    user_id=user_id,
                    api_key_id=api_key,
                    status_code=200,
                    redis_client=self.redis,
                )

        # Legacy API key validation
        elif api_key:
            # Simple API key validation
            if not api_key.startswith(("aorbit", "ao-")):
                logger.warning(f"Invalid API key format from {client_ip}")
                if self.audit_logger:
                    log_auth_failure(
                        ip_address=client_ip,
                        reason="Invalid API key format",
                        redis_client=self.redis,
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
            if hasattr(request.state, "api_key") and self.audit_logger:
                await log_api_request(
                    self.audit_logger,
                    event_type=AuditEventType.AGENT_EXECUTION,
                    action=f"{request.method} {request.url.path}",
                    status="ERROR",
                    message=f"API request failed: {str(e)}",
                    api_key_id=request.state.api_key,
                    ip_address=client_ip,
                )

            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": "Internal Server Error"},
            )

    async def check_permission_dependency(
        self,
        permission: str,
        resource_type: str | None = None,
        resource_id: str | None = None,
    ):
        """Check if the current request has the required permission.

        Args:
            permission: Required permission
            resource_type: Optional resource type
            resource_id: Optional resource ID

        Returns:
            True if authorized, raises HTTPException otherwise
        """

        # This is a wrapper for the check_permission function from RBAC module
        async def dependency(request: Request):
            if not self.rbac_enabled:
                return True

            if not hasattr(request.state, "api_key"):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required",
                )

            api_key = request.state.api_key

            if not await self.rbac_manager.has_permission(
                api_key,
                permission,
                resource_type,
                resource_id,
            ):
                # Log permission denied if audit is enabled
                if self.audit_logger:
                    await log_api_request(
                        self.audit_logger,
                        event_type=AuditEventType.ACCESS_DENIED,
                        action=f"access {resource_type}/{resource_id}",
                        status="denied",
                        message=f"Permission denied: {permission} required",
                        api_key_id=api_key,
                        ip_address=request.client.host if request.client else None,
                        resource_type=resource_type,
                        resource_id=resource_id,
                    )

                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission denied: {permission} required",
                )

            return True

        return Depends(dependency)

    def require_permission(
        self,
        permission: str,
        resource_type: str | None = None,
        resource_id: str | None = None,
    ):
        """Create a dependency that requires a specific permission.

        Args:
            permission: Required permission
            resource_type: Optional resource type
            resource_id: Optional resource ID

        Returns:
            FastAPI dependency
        """
        return self.check_permission_dependency(permission, resource_type, resource_id)


async def initialize_security(redis_client: Redis) -> SecurityIntegration:
    """Initialize the security framework.

    Args:
        redis_client: Redis client instance

    Returns:
        SecurityIntegration instance
    """
    logger.info("\nInitializing enterprise security framework")

    # Initialize RBAC
    rbac = await initialize_rbac(redis_client)
    logger.info("\nRBAC system initialized successfully")

    # Initialize audit logging
    audit_logger = initialize_audit_logger(redis_client)
    logger.info("\nAudit logging system initialized successfully")

    # Initialize encryption
    try:
        encryption = initialize_encryption()
        logger.info("\nEncryption service initialized successfully")
    except Exception as e:
        logger.error(f"\nError initializing encryption service: {str(e)}")
        encryption = None

    # Create security integration instance
    security = SecurityIntegration(
        app=FastAPI(),
        redis=redis_client,
        enable_security=True,
        enable_rbac=True,
        enable_audit=True,
        enable_encryption=True,
    )

    # Log initialization event
    if audit_logger:
        event = AuditEvent(
            event_type=AuditEventType.ADMIN,
            action="initialization",
            status="success",
            message="Security framework initialized",
        )
        audit_logger.log_event(event)

    return security
