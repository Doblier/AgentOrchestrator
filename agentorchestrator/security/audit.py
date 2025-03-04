"""
Audit Logging System for AORBIT.

This module provides a comprehensive audit logging system
tailored for financial applications, with immutable logs,
search capabilities, and compliance features.
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional, List

from pydantic import BaseModel
from redis import Redis

# Set up logger
logger = logging.getLogger("aorbit.audit")


class AuditEventType(str, Enum):
    """Types of audit events."""

    # Core event types
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    AGENT = "agent"
    FINANCIAL = "financial"
    ADMIN = "admin"
    DATA = "data"

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


class AuditEvent(BaseModel):
    """Represents an audit event in the system."""

    event_type: AuditEventType
    event_id: str | None = None
    timestamp: str | None = None
    user_id: str | None = None
    api_key_id: str | None = None
    ip_address: str | None = None
    resource_type: str | None = None
    resource_id: str | None = None
    action: str | None = None
    status: str = "success"
    message: str | None = None
    metadata: dict | None = None

    def __init__(self, **data):
        """Initialize an audit event."""
        if "event_id" not in data:
            data["event_id"] = str(uuid.uuid4())
        if "timestamp" not in data:
            data["timestamp"] = datetime.now(timezone.utc).isoformat()
        if "event_type" in data and isinstance(data["event_type"], str):
            data["event_type"] = AuditEventType(data["event_type"])
        super().__init__(**data)

    def dict(self) -> dict:
        """Convert the event to a dictionary.

        Returns:
            Dictionary representation of the event
        """
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: dict) -> "AuditEvent":
        """Create an AuditEvent from a dictionary.

        Args:
            data: Dictionary containing event data

        Returns:
            New AuditEvent instance
        """
        if "event_type" in data:
            if isinstance(data["event_type"], str):
                data["event_type"] = AuditEventType(data["event_type"])
            elif isinstance(data["event_type"], bytes):
                data["event_type"] = AuditEventType(data["event_type"].decode())
        return cls(**data)


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

    async def log_event(self, event: AuditEvent) -> str:
        """Log an audit event."""
        # Convert timestamp to Unix timestamp for Redis
        timestamp = datetime.fromisoformat(event.timestamp).timestamp()

        # Add event to Redis with multiple indexes
        await self.redis.zadd("audit:index:timestamp", {event.event_id: timestamp})
        await self.redis.zadd(
            f"audit:index:type:{event.event_type}", {event.event_id: timestamp}
        )
        if event.user_id:
            await self.redis.zadd(
                f"audit:index:user:{event.user_id}", {event.event_id: timestamp}
            )

        # Store event data
        await self.redis.hset("audit:events", event.event_id, event.model_dump_json())

        logger.info(f"Audit event logged: {event.event_type} {event.event_id}")
        return event.event_id

    async def get_event_by_id(self, event_id: str) -> Optional[AuditEvent]:
        """Retrieve an audit event by ID."""
        event_data = await self.redis.hget("audit:events", event_id)
        if event_data:
            event_dict = json.loads(event_data)
            return AuditEvent.from_dict(event_dict)
        return None

    def query_events(
        self,
        event_type: Optional[AuditEventType] = None,
        user_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[AuditEvent]:
        """Query audit events with filters."""
        # Get the appropriate index based on filters
        if event_type:
            index_key = f"audit:index:type:{event_type}"
        elif user_id:
            index_key = f"audit:index:user:{user_id}"
        else:
            index_key = "audit:index:timestamp"

        # Convert timestamps to Unix timestamps for Redis
        start_ts = start_time.timestamp() if start_time else 0
        end_ts = end_time.timestamp() if end_time else float("inf")

        # Get event IDs from the index
        event_ids = self.redis.zrevrangebyscore(
            index_key, end_ts, start_ts, start=0, num=limit
        )

        # Retrieve events
        events = []
        for event_id in event_ids:
            event_data = self.redis.hget("audit:events", event_id.decode())
            if event_data:
                event_dict = json.loads(event_data)
                event = AuditEvent.from_dict(event_dict)
                # Apply additional filters
                if user_id and event.user_id != user_id:
                    continue
                events.append(event)

        return events

    def export_events(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> str:
        """Export audit events to JSON."""
        events = self.query_events(start_time=start_time, end_time=end_time)
        metadata = {
            "export_time": datetime.now(timezone.utc).isoformat(),
            "total_events": len(events),
            "time_range": {
                "start": start_time.isoformat() if start_time else None,
                "end": end_time.isoformat() if end_time else None,
            },
        }
        return json.dumps(
            {"events": [event.model_dump() for event in events], "metadata": metadata}
        )


def initialize_audit_logger(redis_client: Redis) -> AuditLogger:
    """Initialize the audit logger.

    Args:
        redis_client: Redis client

    Returns:
        Initialized AuditLogger
    """
    logger = AuditLogger(redis_client)
    event = AuditEvent(
        event_type=AuditEventType.ADMIN,
        action="initialization",
        status="success",
        message="Audit logging system initialized",
    )
    logger.log_event(event)
    return logger


# Helper functions for common audit events
def log_auth_success(
    user_id: str,
    api_key_id: str,
    ip_address: str,
    redis_client: Redis,
) -> str:
    """Log a successful authentication event.

    Args:
        user_id: ID of authenticated user
        api_key_id: ID of API key used
        ip_address: Source IP address
        redis_client: Redis client

    Returns:
        Event ID
    """
    logger = AuditLogger(redis_client)
    event = AuditEvent(
        event_type=AuditEventType.AUTHENTICATION,
        user_id=user_id,
        api_key_id=api_key_id,
        ip_address=ip_address,
        action="authentication",
        status="success",
        message="User logged in successfully",
    )
    return logger.log_event(event)


def log_auth_failure(
    ip_address: str,
    reason: str,
    redis_client: Redis,
    api_key_id: str | None = None,
) -> str:
    """Log a failed authentication event.

    Args:
        ip_address: Source IP address
        reason: Failure reason
        redis_client: Redis client
        api_key_id: ID of API key used (if any)

    Returns:
        Event ID
    """
    logger = AuditLogger(redis_client)
    event = AuditEvent(
        event_type=AuditEventType.AUTHENTICATION,
        ip_address=ip_address,
        api_key_id=api_key_id,
        action="authentication",
        status="failure",
        message=f"Authentication failed: {reason}",
    )
    return logger.log_event(event)


def log_api_request(
    request: Any,
    user_id: str,
    api_key_id: str,
    status_code: int,
    redis_client: Redis,
) -> str:
    """Log an API request."""
    event = AuditEvent(
        event_type=AuditEventType.API_REQUEST,
        user_id=user_id,
        api_key_id=api_key_id,
        ip_address=request.client.host,
        resource_type="endpoint",
        resource_id=request.url.path,
        action=f"{request.method} {request.url.path}",
        status="success" if status_code < 400 else "error",
        message=f"API request completed with status {status_code}",
    )

    logger = AuditLogger(redis_client)
    return logger.log_event(event)
