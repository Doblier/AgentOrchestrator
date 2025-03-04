import pytest
import json
from unittest.mock import MagicMock, patch
from datetime import datetime

from agentorchestrator.security.audit import (
    AuditLogger, AuditEventType,
    initialize_audit_logger,
    log_auth_success,
    log_auth_failure,
    log_api_request
)


@pytest.fixture
def mock_redis():
    """Fixture to provide a mock Redis client."""
    mock = MagicMock()
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
            metadata={"browser": "Chrome", "os": "Windows"}
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
            message="User logged in successfully"
        )
        
        event_dict = event.dict()
        assert event_dict["event_id"] == "test-event"
        assert event_dict["timestamp"] == timestamp
        assert event_dict["event_type"] == AuditEventType.AUTHENTICATION
        assert event_dict["user_id"] == "user123"
        assert event_dict["action"] == "login"
        assert event_dict["status"] == "success"
        assert event_dict["message"] == "User logged in successfully"


class TestAuditLogger:
    """Tests for the AuditLogger class."""
    
    def test_log_event(self, audit_logger, mock_redis):
        """Test logging an event."""
        event = AuditEvent(
            event_id="test-event",
            timestamp=datetime.now().isoformat(),
            event_type=AuditEventType.AUTHENTICATION,
            user_id="user123",
            action="login",
            status="success",
            message="User logged in successfully"
        )
        
        audit_logger.log_event(event)
        
        # Verify Redis was called with expected arguments
        mock_redis.zadd.assert_called_once()
        mock_redis.hset.assert_called_once()
        
    def test_get_event_by_id(self, audit_logger, mock_redis):
        """Test retrieving an event by ID."""
        # Configure mock to return a serialized event
        mock_redis.hget.return_value = json.dumps({
            "event_id": "test-event",
            "timestamp": datetime.now().isoformat(),
            "event_type": AuditEventType.AUTHENTICATION.value,
            "user_id": "user123",
            "action": "login",
            "status": "success",
            "message": "User logged in successfully"
        })
        
        event = audit_logger.get_event_by_id("test-event")
        
        assert event is not None
        assert event.event_id == "test-event"
        assert event.event_type == AuditEventType.AUTHENTICATION
        assert event.user_id == "user123"
        assert event.action == "login"
        assert event.status == "success"
        assert event.message == "User logged in successfully"
        
    def test_get_nonexistent_event(self, audit_logger, mock_redis):
        """Test retrieving a nonexistent event."""
        # Configure mock to return None (event doesn't exist)
        mock_redis.hget.return_value = None
        
        event = audit_logger.get_event_by_id("nonexistent-event")
        
        assert event is None
        
    def test_query_events(self, audit_logger, mock_redis):
        """Test querying events with filters."""
        # Configure mock to return a list of event IDs
        mock_redis.zrevrange.return_value = [b"event1", b"event2"]
        
        # Configure mock to return serialized events
        def mock_hget(key, field):
            if field == b"event1":
                return json.dumps({
                    "event_id": "event1",
                    "timestamp": datetime.now().isoformat(),
                    "event_type": AuditEventType.AUTHENTICATION.value,
                    "user_id": "user123",
                    "action": "login",
                    "status": "success",
                    "message": "User logged in successfully"
                })
            elif field == b"event2":
                return json.dumps({
                    "event_id": "event2",
                    "timestamp": datetime.now().isoformat(),
                    "event_type": AuditEventType.AUTHENTICATION.value,
                    "user_id": "user456",
                    "action": "login",
                    "status": "failure",
                    "message": "Invalid credentials"
                })
            return None
        
        mock_redis.hget.side_effect = mock_hget
        
        # Query events
        events = audit_logger.query_events(
            event_type=AuditEventType.AUTHENTICATION,
            start_time=datetime.now() - datetime.timedelta(days=1),
            end_time=datetime.now(),
            limit=10
        )
        
        assert len(events) == 2
        assert events[0].event_id == "event1"
        assert events[1].event_id == "event2"
        
    def test_query_events_with_user_filter(self, audit_logger, mock_redis):
        """Test querying events with user filter."""
        # Configure mock to return a list of event IDs
        mock_redis.zrevrange.return_value = [b"event1", b"event2"]
        
        # Configure mock to return serialized events
        def mock_hget(key, field):
            if field == b"event1":
                return json.dumps({
                    "event_id": "event1",
                    "timestamp": datetime.now().isoformat(),
                    "event_type": AuditEventType.AUTHENTICATION.value,
                    "user_id": "user123",
                    "action": "login",
                    "status": "success",
                    "message": "User logged in successfully"
                })
            elif field == b"event2":
                return json.dumps({
                    "event_id": "event2",
                    "timestamp": datetime.now().isoformat(),
                    "event_type": AuditEventType.AUTHENTICATION.value,
                    "user_id": "user456",
                    "action": "login",
                    "status": "failure",
                    "message": "Invalid credentials"
                })
            return None
        
        mock_redis.hget.side_effect = mock_hget
        
        # Query events with user filter
        events = audit_logger.query_events(
            user_id="user123",
            start_time=datetime.now() - datetime.timedelta(days=1),
            end_time=datetime.now(),
            limit=10
        )
        
        # Only one event should match the user filter
        assert len(events) == 1
        assert events[0].event_id == "event1"
        assert events[0].user_id == "user123"
        
    def test_export_events(self, audit_logger, mock_redis):
        """Test exporting events to JSON."""
        # Configure mock to return a list of event IDs
        mock_redis.zrevrange.return_value = [b"event1", b"event2"]
        
        # Configure mock to return serialized events
        def mock_hget(key, field):
            if field == b"event1":
                return json.dumps({
                    "event_id": "event1",
                    "timestamp": datetime.now().isoformat(),
                    "event_type": AuditEventType.AUTHENTICATION.value,
                    "user_id": "user123",
                    "action": "login",
                    "status": "success",
                    "message": "User logged in successfully"
                })
            elif field == b"event2":
                return json.dumps({
                    "event_id": "event2",
                    "timestamp": datetime.now().isoformat(),
                    "event_type": AuditEventType.AUTHENTICATION.value,
                    "user_id": "user456",
                    "action": "login",
                    "status": "failure",
                    "message": "Invalid credentials"
                })
            return None
        
        mock_redis.hget.side_effect = mock_hget
        
        # Export events
        export_json = audit_logger.export_events(
            start_time=datetime.now() - datetime.timedelta(days=1),
            end_time=datetime.now()
        )
        
        # Verify export format
        export_data = json.loads(export_json)
        assert "events" in export_data
        assert "metadata" in export_data
        assert len(export_data["events"]) == 2
        assert export_data["events"][0]["event_id"] == "event1"
        assert export_data["events"][1]["event_id"] == "event2"


def test_log_auth_success():
    """Test the log_auth_success helper function."""
    with patch('agentorchestrator.security.audit.AuditLogger') as mock_logger_class:
        # Set up mock
        mock_logger = MagicMock()
        mock_logger_class.return_value = mock_logger
        
        # Call the helper function
        log_auth_success(
            user_id="user123",
            api_key_id="api-key-123",
            ip_address="192.168.1.1",
            redis_client=MagicMock()
        )
        
        # Verify logger was called with correct event data
        mock_logger.log_event.assert_called_once()
        event = mock_logger.log_event.call_args[0][0]
        assert event.event_type == AuditEventType.AUTHENTICATION
        assert event.user_id == "user123"
        assert event.api_key_id == "api-key-123"
        assert event.ip_address == "192.168.1.1"
        assert event.action == "authentication"
        assert event.status == "success"


def test_log_auth_failure():
    """Test the log_auth_failure helper function."""
    with patch('agentorchestrator.security.audit.AuditLogger') as mock_logger_class:
        # Set up mock
        mock_logger = MagicMock()
        mock_logger_class.return_value = mock_logger
        
        # Call the helper function
        log_auth_failure(
            ip_address="192.168.1.1",
            reason="Invalid API key",
            api_key_id="invalid-key",
            redis_client=MagicMock()
        )
        
        # Verify logger was called with correct event data
        mock_logger.log_event.assert_called_once()
        event = mock_logger.log_event.call_args[0][0]
        assert event.event_type == AuditEventType.AUTHENTICATION
        assert event.ip_address == "192.168.1.1"
        assert event.api_key_id == "invalid-key"
        assert event.action == "authentication"
        assert event.status == "failure"
        assert "Invalid API key" in event.message


def test_log_api_request():
    """Test the log_api_request helper function."""
    with patch('agentorchestrator.security.audit.AuditLogger') as mock_logger_class:
        # Set up mock
        mock_logger = MagicMock()
        mock_logger_class.return_value = mock_logger
        
        # Create a mock request
        mock_request = MagicMock()
        mock_request.url.path = "/api/v1/resources"
        mock_request.method = "GET"
        mock_request.client.host = "192.168.1.1"
        
        # Call the helper function
        log_api_request(
            request=mock_request,
            user_id="user123",
            api_key_id="api-key-123",
            status_code=200,
            redis_client=MagicMock()
        )
        
        # Verify logger was called with correct event data
        mock_logger.log_event.assert_called_once()
        event = mock_logger.log_event.call_args[0][0]
        assert event.event_type == AuditEventType.API
        assert event.user_id == "user123"
        assert event.api_key_id == "api-key-123"
        assert event.ip_address == "192.168.1.1"
        assert event.resource_type == "endpoint"
        assert event.resource_id == "/api/v1/resources"
        assert event.action == "GET"
        assert event.status == "200"


def test_initialize_audit_logger():
    """Test the initialize_audit_logger function."""
    with patch('agentorchestrator.security.audit.AuditLogger') as mock_logger_class:
        # Set up mock
        mock_logger = MagicMock()
        mock_logger_class.return_value = mock_logger
        
        # Call the initialize function
        logger = initialize_audit_logger(redis_client=MagicMock())
        
        # Verify logger was created and initialization event was logged
        assert logger == mock_logger
        mock_logger.log_event.assert_called_once()
        event = mock_logger.log_event.call_args[0][0]
        assert event.event_type == AuditEventType.ADMIN
        assert event.action == "initialization"
        assert event.status == "success"
        assert "Audit logging system initialized" in event.message 