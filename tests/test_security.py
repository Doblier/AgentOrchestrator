"""
Tests for the AORBIT Enterprise Security Framework components.
"""

import os
import json
import pytest
from fastapi import Depends, FastAPI, Request, Response
from fastapi.testclient import TestClient
import redis.asyncio as redis
from unittest.mock import patch, MagicMock

from agentorchestrator.security.rbac import RBACManager
from agentorchestrator.security.audit import AuditLogger
from agentorchestrator.security.encryption import Encryptor
from agentorchestrator.security.integration import SecurityIntegration, initialize_security
from agentorchestrator.api.middleware import APISecurityMiddleware


@pytest.fixture
def mock_redis_client():
    """Create a mock Redis client for testing."""
    mock_client = MagicMock()
    mock_client.get.return_value = None
    mock_client.set.return_value = True
    mock_client.exists.return_value = False
    mock_client.sadd.return_value = 1
    mock_client.sismember.return_value = False
    return mock_client


@pytest.fixture
def test_app(mock_redis_client):
    """Create a test FastAPI application with security enabled."""
    app = FastAPI(title="AORBIT Test")
    
    # Set environment variables for testing
    os.environ["SECURITY_ENABLED"] = "true"
    os.environ["RBAC_ENABLED"] = "true"
    os.environ["AUDIT_LOGGING_ENABLED"] = "true"
    os.environ["ENCRYPTION_ENABLED"] = "true"
    os.environ["ENCRYPTION_KEY"] = "T3st1ngK3yF0rEncrypti0n1234567890=="
    
    # Initialize security
    security = initialize_security(app, mock_redis_client)
    
    # Add a test endpoint with permission requirement
    @app.get("/protected", dependencies=[Depends(security.require_permission("read:data"))])
    async def protected_endpoint():
        return {"message": "Access granted"}
    
    # Add a test endpoint for encryption
    @app.post("/encrypt")
    async def encrypt_data(request: Request):
        data = await request.json()
        encrypted = app.state.security.encryption_manager.encrypt(json.dumps(data))
        return {"encrypted": encrypted}
    
    @app.post("/decrypt")
    async def decrypt_data(request: Request):
        data = await request.json()
        decrypted = app.state.security.encryption_manager.decrypt(data["encrypted"])
        return {"decrypted": json.loads(decrypted)}
    
    return app


@pytest.fixture
def client(test_app):
    """Create a test client."""
    return TestClient(test_app)


class TestSecurityFramework:
    """Test cases for the AORBIT Enterprise Security Framework."""
    
    def test_rbac_permission_denied(self, client, mock_redis_client):
        """Test that unauthorized access is denied."""
        # Mock Redis to deny permission
        mock_redis_client.sismember.return_value = False
        
        # Make request without API key
        response = client.get("/protected")
        assert response.status_code == 401
        assert "Unauthorized" in response.json()["detail"]
        
        # Make request with invalid API key
        response = client.get("/protected", headers={"X-API-Key": "invalid_key"})
        assert response.status_code == 401
        assert "Unauthorized" in response.json()["detail"]
    
    def test_rbac_permission_granted(self, client, mock_redis_client):
        """Test that authorized access is granted."""
        # Mock Redis to grant permission
        mock_redis_client.get.return_value = "user:admin"  # Return role for API key
        mock_redis_client.sismember.return_value = True  # Return true for permission check
        
        # Make request with valid API key
        response = client.get("/protected", headers={"X-API-Key": "valid_key"})
        assert response.status_code == 200
        assert response.json() == {"message": "Access granted"}
    
    def test_encryption_lifecycle(self, client):
        """Test encryption and decryption of data."""
        # Data to encrypt
        test_data = {"sensitive": "data", "account": "12345"}
        
        # Encrypt the data
        response = client.post("/encrypt", json=test_data)
        assert response.status_code == 200
        encrypted_data = response.json()["encrypted"]
        assert encrypted_data != test_data
        
        # Decrypt the data
        response = client.post("/decrypt", json={"encrypted": encrypted_data})
        assert response.status_code == 200
        decrypted_data = response.json()["decrypted"]
        assert decrypted_data == test_data
    
    def test_audit_logging(self, client, mock_redis_client):
        """Test that audit logging captures events."""
        # Mock Redis lpush method for audit logging
        mock_redis_client.lpush = MagicMock(return_value=True)
        
        # Make a request that should be logged
        client.get("/protected", headers={"X-API-Key": "audit_test_key"})
        
        # Verify that an audit log entry was created
        mock_redis_client.lpush.assert_called()
        # The first arg is the key, the second is the log entry
        log_entry_arg = mock_redis_client.lpush.call_args[0][1]
        assert isinstance(log_entry_arg, str)
        log_entry = json.loads(log_entry_arg)
        assert "event_type" in log_entry
        assert "timestamp" in log_entry
        assert "details" in log_entry


@pytest.mark.parametrize(
    "api_key,expected_status", 
    [
        (None, 401),  # No API key
        ("invalid", 401),  # Invalid API key
        ("aorbit_test", 200),  # Valid API key format
    ]
)
def test_api_security_middleware(api_key, expected_status):
    """Test the API security middleware."""
    app = FastAPI()
    
    # Add the security middleware
    app.add_middleware(APISecurityMiddleware, api_key_header="X-API-Key", enable_security=True)
    
    @app.get("/test")
    async def test_endpoint():
        return {"message": "Success"}
    
    client = TestClient(app)
    
    # Prepare headers
    headers = {}
    if api_key:
        headers["X-API-Key"] = api_key
    
    # Make request
    response = client.get("/test", headers=headers)
    assert response.status_code == expected_status
    
    # If success, check response body
    if expected_status == 200:
        assert response.json() == {"message": "Success"}


def test_initialize_security_disabled():
    """Test initializing security when it's disabled."""
    app = FastAPI()
    
    # Set environment variables to disable security
    os.environ["SECURITY_ENABLED"] = "false"
    
    mock_redis = MagicMock()
    security = initialize_security(app, mock_redis)
    
    # Security should be initialized but components should be None
    assert security is not None
    assert security.rbac_manager is None
    assert security.audit_logger is None
    assert security.encryption_manager is None 