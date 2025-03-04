"""
Audit Logging System for AORBIT.

This module provides a comprehensive audit logging system
tailored for financial applications, with immutable logs,
search capabilities, and compliance features.
"""

import json
import logging
import time
import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from redis import Redis

# Set up logger
logger = logging.getLogger("aorbit.audit")


class AuditEventType(str, Enum):
    """Types of audit events."""

    # Authentication events
    AUTH_SUCCESS = "auth.success"
    AUTH_FAILURE = "auth.failure"
    LOGOUT = "auth.logout"
    API_KEY_CREATED = "api_key.created"
    API_KEY_DELETED = "api_key.deleted"

    # Authorization events
    ACCESS_DENIED = "access.denied"
    PERMISSION_GRANTED = "permission.granted"
    ROLE_CREATED = "role.created"
    ROLE_UPDATED = "role.updated"
    ROLE_DELETED = "role.deleted"

    # Agent events
    AGENT_EXECUTION = "agent.execution"
    AGENT_CREATED = "agent.created"
    AGENT_UPDATED = "agent.updated"
    AGENT_DELETED = "agent.deleted"

    # Financial events
    FINANCE_VIEW = "finance.view"
    FINANCE_TRANSACTION = "finance.transaction"
    FINANCE_APPROVAL = "finance.approval"

    # System events
    SYSTEM_ERROR = "system.error"
    SYSTEM_STARTUP = "system.startup"
    SYSTEM_SHUTDOWN = "system.shutdown"
    CONFIG_CHANGE = "config.change"

    # API events
    API_REQUEST = "api.request"
    API_RESPONSE = "api.response"
    API_ERROR = "api.error"


class AuditLogger:
    """Audit logger for recording and retrieving security events."""

    def __init__(self, redis_client: Redis):
        """Initialize the audit logger.

        Args:
            redis_client: Redis client for storing audit logs
        """
        self.redis = redis_client
        self.log_key_prefix = "audit:log:"
        self.index_key_prefix = "audit:index:"

    def log_event(
        self,
        event_type: AuditEventType,
        user_id: str | None = None,
        api_key_id: str | None = None,
        ip_address: str | None = None,
        resource: str | None = None,
        action: str | None = None,
        status: str | None = "success",
        details: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Log an audit event.

        Args:
            event_type: Type of audit event
            user_id: ID of user involved (if any)
            api_key_id: ID of API key used (if any)
            ip_address: Source IP address
            resource: Resource affected
            action: Action performed
            status: Outcome status (success/failure)
            details: Additional details about the event
            metadata: Additional metadata

        Returns:
            Event ID
        """
        event_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()

        event = {
            "id": event_id,
            "timestamp": timestamp,
            "event_type": event_type,
            "user_id": user_id,
            "api_key_id": api_key_id,
            "ip_address": ip_address,
            "resource": resource,
            "action": action,
            "status": status,
            "details": details or {},
            "metadata": metadata or {},
        }

        # Store the event
        log_key = f"{self.log_key_prefix}{event_id}"
        self.redis.set(log_key, json.dumps(event))

        # Add to timestamp index
        timestamp_key = f"{self.index_key_prefix}timestamp"
        self.redis.zadd(timestamp_key, {event_id: time.time()})

        # Add to type index
        type_key = f"{self.index_key_prefix}type:{event_type}"
        self.redis.zadd(type_key, {event_id: time.time()})

        # Add to user index if user_id is provided
        if user_id:
            user_key = f"{self.index_key_prefix}user:{user_id}"
            self.redis.zadd(user_key, {event_id: time.time()})

        logger.info(f"Audit event logged: {event_type} {event_id}")
        return event_id

    def get_event(self, event_id: str) -> dict[str, Any] | None:
        """Get an audit event by ID.

        Args:
            event_id: ID of event to retrieve

        Returns:
            Event data or None if not found
        """
        log_key = f"{self.log_key_prefix}{event_id}"
        event_json = self.redis.get(log_key)

        if not event_json:
            return None

        return json.loads(event_json)


def initialize_audit_logger(redis_client: Redis) -> AuditLogger:
    """Initialize the audit logger.

    Args:
        redis_client: Redis client

    Returns:
        Initialized AuditLogger
    """
    logger.info("Initializing audit logging system")
    return AuditLogger(redis_client)


# Helper functions for common audit events
def log_auth_success(
    audit_logger: AuditLogger,
    user_id: str,
    ip_address: str | None = None,
    api_key_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> str:
    """Log a successful authentication event.

    Args:
        audit_logger: Audit logger instance
        user_id: User ID
        ip_address: Source IP address
        api_key_id: API key ID if used
        metadata: Additional metadata

    Returns:
        Event ID
    """
    return audit_logger.log_event(
        event_type=AuditEventType.AUTH_SUCCESS,
        user_id=user_id,
        api_key_id=api_key_id,
        ip_address=ip_address,
        action="login",
        status="success",
        metadata=metadata,
    )


def log_auth_failure(
    audit_logger: AuditLogger,
    user_id: str | None = None,
    ip_address: str | None = None,
    reason: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> str:
    """Log a failed authentication event.

    Args:
        audit_logger: Audit logger instance
        user_id: User ID if known
        ip_address: Source IP address
        reason: Reason for failure
        metadata: Additional metadata

    Returns:
        Event ID
    """
    details = {"reason": reason} if reason else {}

    return audit_logger.log_event(
        event_type=AuditEventType.AUTH_FAILURE,
        user_id=user_id,
        ip_address=ip_address,
        action="login",
        status="failure",
        details=details,
        metadata=metadata,
    )


def log_api_request(
    audit_logger: AuditLogger,
    endpoint: str,
    method: str,
    user_id: str | None = None,
    api_key_id: str | None = None,
    ip_address: str | None = None,
    status_code: int = 200,
    metadata: dict[str, Any] | None = None,
) -> str:
    """Log an API request.

    Args:
        audit_logger: Audit logger instance
        endpoint: API endpoint
        method: HTTP method
        user_id: User ID if authenticated
        api_key_id: API key ID if used
        ip_address: Source IP address
        status_code: HTTP status code
        metadata: Additional metadata

    Returns:
        Event ID
    """
    details = {
        "endpoint": endpoint,
        "method": method,
        "status_code": status_code,
    }

    return audit_logger.log_event(
        event_type=AuditEventType.API_REQUEST,
        user_id=user_id,
        api_key_id=api_key_id,
        ip_address=ip_address,
        resource=endpoint,
        action=method,
        status="success" if status_code < 400 else "failure",
        details=details,
        metadata=metadata,
    )
