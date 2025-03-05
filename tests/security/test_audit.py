import json
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch, AsyncMock

import pytest

from agentorchestrator.security.audit import (
    AuditEventType,
    AuditLogger,
    initialize_audit_logger,
    log_api_request,
    log_auth_failure,
    log_auth_success,
    AuditEvent,
)


@pytest.fixture
def mock_redis():
    """Fixture to provide a mock Redis client."""
    mock = AsyncMock()
    mock.pipeline.return_value = AsyncMock()
    return mock


@pytest.fixture
def audit_logger(mock_redis):
    """Fixture to provide an initialized AuditLogger with a mock Redis client."""
    logger = AuditLogger(redis_client=mock_redis)
    return logger


class TestAuditEventType:
    """Tests for the AuditEventType enum."""

    def test_event_type_values(self):
        """Test that AuditEventType enum has expected values."""
        assert AuditEventType.AUTHENTICATION.value == "authentication"
        assert AuditEventType.AUTHORIZATION.value == "authorization"
        assert AuditEventType.AGENT.value == "agent"
        assert AuditEventType.FINANCIAL.value == "financial"
        assert AuditEventType.ADMIN.value == "admin"
        assert AuditEventType.DATA.value == "data"


class TestAuditEvent:
    """Tests for the AuditEvent class."""

    def test_audit_event_creation(self):
        """Test creating an AuditEvent instance."""
        event = AuditEvent(
            event_id="test-event",
            timestamp=datetime.now().isoformat(),
            event_type=AuditEventType.AUTHENTICATION,
            user_id="user123",
            api_key_id="api-key-123",
            ip_address="192.168.1.1",
            resource_type="user",
            resource_id="user123",
            action="login",
            status="success",
            message="User logged in successfully",
            metadata={"browser": "Chrome", "os": "Windows"},
        )

        assert event.event_id == "test-event"
        assert event.event_type == AuditEventType.AUTHENTICATION
        assert event.user_id == "user123"
        assert event.api_key_id == "api-key-123"
        assert event.ip_address == "192.168.1.1"
        assert event.resource_type == "user"
        assert event.resource_id == "user123"
        assert event.action == "login"
        assert event.status == "success"
        assert event.message == "User logged in successfully"
        assert event.metadata["browser"] == "Chrome"
        assert event.metadata["os"] == "Windows"

    def test_audit_event_to_dict(self):
        """Test converting an AuditEvent to a dictionary."""
        timestamp = datetime.now().isoformat()
        event = AuditEvent(
            event_id="test-event",
            timestamp=timestamp,
            event_type=AuditEventType.AUTHENTICATION,
            user_id="user123",
            action="login",
            status="success",
            message="User logged in successfully",
        )

        event_dict = event.dict()
        assert event_dict["event_id"] == "test-event"
        assert event_dict["timestamp"] == timestamp
        assert event_dict["event_type"] == AuditEventType.AUTHENTICATION
        assert event_dict["user_id"] == "user123"
        assert event_dict["action"] == "login"
        assert event_dict["status"] == "success"
        assert event_dict["message"] == "User logged in successfully"

    def test_audit_event_from_dict_with_bytes(self):
        """Test creating an AuditEvent from a dictionary with bytes event type."""
        data = {
            "event_id": "test-event",
            "timestamp": datetime.now().isoformat(),
            "event_type": b"authentication",  # Bytes event type
            "user_id": "user123",
            "action": "login",
            "status": "success",
            "message": "User logged in successfully",
        }

        event = AuditEvent.from_dict(data)
        assert event.event_id == "test-event"
        assert event.event_type == AuditEventType.AUTHENTICATION
        assert event.user_id == "user123"
        assert event.action == "login"
        assert event.status == "success"
        assert event.message == "User logged in successfully"


class TestAuditLogger:
    """Tests for the AuditLogger class."""

    @pytest.mark.asyncio
    async def test_log_event(self, audit_logger, mock_redis):
        """Test logging an event."""
        event = AuditEvent(
            event_id="test-event",
            timestamp=datetime.now().isoformat(),
            event_type=AuditEventType.AUTHENTICATION,
            user_id="user123",
            action="login",
            status="success",
            message="User logged in successfully",
        )

        # Configure mock pipeline
        mock_pipe = AsyncMock()
        mock_redis.pipeline.return_value = mock_pipe

        await audit_logger.log_event(event)

        # Verify Redis pipeline was called with expected arguments
        assert mock_pipe.zadd.call_count == 3  # timestamp, type, and user indices
        timestamp = datetime.fromisoformat(event.timestamp).timestamp()
        mock_pipe.zadd.assert_any_call(
            "audit:index:timestamp", {event.event_id: timestamp}
        )
        mock_pipe.zadd.assert_any_call(
            f"audit:index:type:{event.event_type}", {event.event_id: timestamp}
        )
        mock_pipe.zadd.assert_any_call(
            f"audit:index:user:{event.user_id}", {event.event_id: timestamp}
        )
        mock_pipe.hset.assert_called_once_with(
            "audit:events", event.event_id, event.model_dump_json()
        )
        mock_pipe.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_event_by_id(self, audit_logger, mock_redis):
        """Test retrieving an event by ID."""
        # Configure mock to return a serialized event
        mock_redis.hget.return_value = json.dumps(
            {
                "event_id": "test-event",
                "timestamp": datetime.now().isoformat(),
                "event_type": "authentication",  # Changed to match enum value
                "user_id": "user123",
                "action": "login",
                "status": "success",
                "message": "User logged in successfully",
            }
        )

        event = await audit_logger.get_event_by_id("test-event")
        assert event.event_id == "test-event"
        assert event.user_id == "user123"
        assert event.event_type == AuditEventType.AUTHENTICATION

    @pytest.mark.asyncio
    async def test_get_nonexistent_event(self, audit_logger, mock_redis):
        """Test retrieving a nonexistent event."""
        # Configure mock to return None (event doesn't exist)
        mock_redis.hget.return_value = None

        event = await audit_logger.get_event_by_id("nonexistent-event")
        assert event is None

    @pytest.mark.asyncio
    async def test_query_events(self, audit_logger, mock_redis):
        """Test querying events with filters."""
        # Configure mock to return a list of event IDs
        mock_redis.zrevrangebyscore.return_value = [b"event1", b"event2"]

        # Configure mock to return serialized events
        def mock_hget(key, field):
            if field == "event1":
                return json.dumps(
                    {
                        "event_id": "event1",
                        "timestamp": datetime.now().isoformat(),
                        "event_type": "authentication",  # Using lowercase enum value
                        "user_id": "user123",
                        "action": "login",
                        "status": "success",
                        "message": "User logged in successfully",
                    }
                )
            if field == "event2":
                return json.dumps(
                    {
                        "event_id": "event2",
                        "timestamp": datetime.now().isoformat(),
                        "event_type": "authentication",  # Using lowercase enum value
                        "user_id": "user456",
                        "action": "login",
                        "status": "failure",
                        "message": "Invalid credentials",
                    }
                )
            return None

        mock_redis.hget.side_effect = mock_hget

        # Query events
        events = await audit_logger.query_events(
            event_type=AuditEventType.AUTHENTICATION,
            start_time=datetime.now() - timedelta(days=1),
            end_time=datetime.now(),
            limit=10,
        )

        assert len(events) == 2

    @pytest.mark.asyncio
    async def test_query_events_with_user_filter(self, audit_logger, mock_redis):
        """Test querying events with user filter."""
        # Configure mock to return a list of event IDs
        mock_redis.zrevrangebyscore.return_value = [b"event1", b"event2"]

        # Configure mock to return serialized events
        def mock_hget(key, field):
            if field == "event1":
                return json.dumps(
                    {
                        "event_id": "event1",
                        "timestamp": datetime.now().isoformat(),
                        "event_type": "authentication",  # Using lowercase enum value
                        "user_id": "user123",
                        "action": "login",
                        "status": "success",
                        "message": "User logged in successfully",
                    }
                )
            if field == "event2":
                return json.dumps(
                    {
                        "event_id": "event2",
                        "timestamp": datetime.now().isoformat(),
                        "event_type": "authentication",  # Using lowercase enum value
                        "user_id": "user456",
                        "action": "login",
                        "status": "failure",
                        "message": "Invalid credentials",
                    }
                )
            return None

        mock_redis.hget.side_effect = mock_hget

        # Query events with user filter
        events = await audit_logger.query_events(
            user_id="user123",
            start_time=datetime.now() - timedelta(days=1),
            end_time=datetime.now(),
            limit=10,
        )

        assert len(events) == 1
        assert events[0].user_id == "user123"

    @pytest.mark.asyncio
    async def test_export_events(self, audit_logger, mock_redis):
        """Test exporting events to JSON."""
        # Configure mock to return a list of event IDs
        mock_redis.zrevrangebyscore.return_value = [b"event1"]

        # Configure mock to return a serialized event
        mock_redis.hget.return_value = json.dumps(
            {
                "event_id": "event1",
                "timestamp": datetime.now().isoformat(),
                "event_type": "authentication",  # Using lowercase enum value
                "user_id": "user123",
                "action": "login",
                "status": "success",
                "message": "User logged in successfully",
            }
        )

        # Export events
        export_json = await audit_logger.export_events(
            start_time=datetime.now() - timedelta(days=1),
            end_time=datetime.now(),
        )

        # Parse and verify export
        export_data = json.loads(export_json)
        assert "events" in export_data
        assert "metadata" in export_data
        assert len(export_data["events"]) == 1
        assert export_data["events"][0]["user_id"] == "user123"


@pytest.mark.asyncio
async def test_initialize_audit_logger(mock_redis):
    """Test initializing the audit logger."""
    # Configure mock pipeline
    mock_pipe = AsyncMock()
    mock_redis.pipeline.return_value = mock_pipe

    logger = await initialize_audit_logger(mock_redis)

    # Verify logger was created
    assert isinstance(logger, AuditLogger)
    assert logger.redis == mock_redis

    # Verify initialization event was logged
    assert mock_pipe.zadd.call_count == 2  # timestamp and type indices
    mock_pipe.hset.assert_called_once()
    mock_pipe.execute.assert_called_once()


@pytest.mark.asyncio
async def test_log_auth_success(mock_redis):
    """Test logging a successful authentication event."""
    # Configure mock pipeline
    mock_pipe = AsyncMock()
    mock_redis.pipeline.return_value = mock_pipe

    await log_auth_success(
        user_id="user123",
        api_key_id="api-key-123",
        ip_address="192.168.1.1",
        redis_client=mock_redis,
    )

    # Verify event was logged
    assert mock_pipe.zadd.call_count == 3  # timestamp, type, and user indices
    mock_pipe.hset.assert_called_once()
    mock_pipe.execute.assert_called_once()


@pytest.mark.asyncio
async def test_log_auth_failure(mock_redis):
    """Test logging a failed authentication event."""
    # Configure mock pipeline
    mock_pipe = AsyncMock()
    mock_redis.pipeline.return_value = mock_pipe

    await log_auth_failure(
        ip_address="192.168.1.1",
        reason="Invalid credentials",
        redis_client=mock_redis,
        api_key_id="api-key-123",
    )

    # Verify event was logged
    assert mock_pipe.zadd.call_count == 2  # timestamp and type indices
    mock_pipe.hset.assert_called_once()
    mock_pipe.execute.assert_called_once()


@pytest.mark.asyncio
async def test_log_api_request(mock_redis):
    """Test logging an API request event."""
    # Configure mock pipeline
    mock_pipe = AsyncMock()
    mock_redis.pipeline.return_value = mock_pipe

    # Create a mock request
    mock_request = MagicMock()
    mock_request.method = "GET"
    mock_request.url.path = "/api/v1/test"
    mock_request.client.host = "192.168.1.1"

    await log_api_request(
        request=mock_request,
        user_id="user123",
        api_key_id="api-key-123",
        status_code=200,
        redis_client=mock_redis,
    )

    # Verify event was logged
    assert mock_pipe.zadd.call_count == 3  # timestamp, type, and user indices
    mock_pipe.hset.assert_called_once()
    mock_pipe.execute.assert_called_once()
