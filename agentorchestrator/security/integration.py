"""
Integration module for security components.

This module provides a unified interface for integrating all security
components into the main application.
"""

import os
import logging
from typing import Optional, Dict, Any, List
import json
from fastapi import FastAPI, Request, Response, HTTPException, Depends, Security, status
from fastapi.security import APIKeyHeader
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from redis import Redis

from agentorchestrator.security.rbac import (
    RBACManager, 
    initialize_rbac,
    check_permission
)
from agentorchestrator.security.audit import (
    AuditLogger, 
    AuditEventType,
    initialize_audit_logger,
    log_auth_success,
    log_auth_failure,
    log_api_request
)
from agentorchestrator.security.encryption import (
    Encryptor,
    initialize_encryption
)

logger = logging.getLogger(__name__)


class SecurityIntegration:
    """Integrates all security components into the application."""

    def __init__(
        self,
        app: FastAPI,
        redis_client: Redis,
        api_key_header_name: str = "X-API-Key",
        audit_enabled: bool = True,
        rbac_enabled: bool = True,
        encryption_enabled: bool = True,
    ):
        """Initialize the security integration.
        
        Args:
            app: FastAPI application
            redis_client: Redis client
            api_key_header_name: Name of the API key header
            audit_enabled: Whether to enable audit logging
            rbac_enabled: Whether to enable RBAC
            encryption_enabled: Whether to enable encryption
        """
        self.app = app
        self.redis_client = redis_client
        self.api_key_header_name = api_key_header_name
        self.audit_enabled = audit_enabled
        self.rbac_enabled = rbac_enabled
        self.encryption_enabled = encryption_enabled
        
        # Initialize placeholders for components
        self.rbac_manager = None
        self.audit_logger = None
        self.encryption_manager = None
        self.data_protection = None
        
        # Note: We don't call _initialize_components or _setup_middleware here
        # They will be called separately by initialize_security
    
    async def _initialize_components(self):
        """Initialize security components."""
        if self.rbac_enabled:
            self.rbac_manager = await initialize_rbac(self.redis_client)
            self.app.state.rbac_manager = self.rbac_manager
            logger.info("RBAC system initialized")
        
        if self.audit_enabled:
            self.audit_logger = await initialize_audit_logger(self.redis_client)
            self.app.state.audit_logger = self.audit_logger
            logger.info("Audit logging system initialized")
        
        if self.encryption_enabled:
            self.encryption_manager = initialize_encryption()
            self.data_protection = DataProtectionService(self.encryption_manager)
            self.app.state.encryption_manager = self.encryption_manager
            self.app.state.data_protection = self.data_protection
            logger.info("Encryption system initialized")
        
        # Add security instance to app state for access in other parts of the application
        self.app.state.security = self
    
    def _setup_middleware(self):
        """Set up security middleware."""
        # Add API key security scheme to OpenAPI docs
        api_key_scheme = APIKeyHeader(name=self.api_key_header_name, auto_error=False)
        
        # Using add_middleware instead of the decorator to avoid the timing issue
        self.app.add_middleware(
            BaseHTTPMiddleware,
            dispatch=self._security_middleware_dispatch
        )
    
    async def _security_middleware_dispatch(self, request: Request, call_next):
        """Security middleware for request processing.
            
        Args:
            request: Incoming request
            call_next: Next middleware in the chain
            
        Returns:
            Response from next middleware
        """
        # Skip security for OPTIONS requests and docs
        if request.method == "OPTIONS" or request.url.path in [
            "/docs", "/redoc", "/openapi.json", "/", "/api/v1/health"
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
                redis_role = await self.redis_client.get(f"apikey:{api_key}")
                
                if redis_role:
                    role = redis_role.decode("utf-8")
                    request.state.role = role
                    
                    # Check IP whitelist if applicable
                    ip_whitelist = await self.redis_client.get(f"apikey:{api_key}:ip_whitelist")
                    if ip_whitelist:
                        ip_whitelist = json.loads(ip_whitelist)
                        if ip_whitelist and client_ip not in ip_whitelist:
                            if self.audit_logger:
                                await log_auth_failure(
                                    self.audit_logger,
                                    api_key_id=api_key,
                                    ip_address=client_ip,
                                    reason="IP address not in whitelist"
                                )
                            return JSONResponse(
                                status_code=403,
                                content={"detail": "Forbidden: IP address not authorized"}
                            )
                    
                    # Log successful authentication
                    if self.audit_logger:
                        await log_auth_success(
                            self.audit_logger,
                            api_key_id=api_key,
                            ip_address=client_ip
                        )
            
            # Store API key and role in request state for use in route handlers
            request.state.api_key = api_key
            
            # Log request
            if self.audit_logger:
                await log_api_request(
                    self.audit_logger,
                    event_type=AuditEventType.AGENT_EXECUTION,
                    action=f"{request.method} {request.url.path}",
                    status="REQUESTED",
                    message=f"API request initiated: {request.method} {request.url.path}",
                    user_id=user_id,
                    api_key_id=api_key,
                    ip_address=client_ip,
                    metadata={
                        "query_params": dict(request.query_params),
                        "path_params": getattr(request, "path_params", {}),
                        "method": request.method,
                    }
                )
                
        # Legacy API key validation
        elif api_key:
            # Simple API key validation
            if not api_key.startswith(("aorbit", "ao-")):
                logger.warning(f"Invalid API key format from {client_ip}")
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED, 
                    content={"detail": "Unauthorized: Invalid API key"}
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
                content={"detail": "Internal Server Error"}
            )
            
    async def check_permission_dependency(
        self,
        permission: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
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
                api_key, permission, resource_type, resource_id
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
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
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


def initialize_security(redis_client) -> Dict[str, Any]:
    """Initialize all security components.
    
    Args:
        redis_client: Redis client
        
    Returns:
        Dictionary of security components
    """
    logger.info("Initializing enterprise security framework")
    
    # Initialize components
    try:
        rbac_manager = initialize_rbac(redis_client)
        logger.info("RBAC system initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing RBAC system: {e}")
        rbac_manager = None
    
    try:
        audit_logger = initialize_audit_logger(redis_client)
        logger.info("Audit logging system initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing audit logging system: {e}")
        audit_logger = None
    
    try:
        encryption_key = os.environ.get('AORBIT_ENCRYPTION_KEY')
        encryptor = initialize_encryption(encryption_key)
        logger.info("Encryption service initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing encryption service: {e}")
        encryptor = None
    
    # Create security integration container
    security = {
        "rbac_manager": rbac_manager,
        "audit_logger": audit_logger,
        "encryptor": encryptor,
    }
    
    # Log startup
    if audit_logger:
        audit_logger.log_event(
            event_type=AuditEventType.SYSTEM_STARTUP,
            action="initialize",
            status="success",
            details={"components": [k for k, v in security.items() if v is not None]}
        )
    
    logger.info("Enterprise security framework initialized successfully")
    return security 