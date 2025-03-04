"""Test cases for the security framework."""

from typing import Any
from unittest.mock import MagicMock

import pytest
from fastapi import Depends, FastAPI, Request
from fastapi.testclient import TestClient

from agentorchestrator.api.middleware import APISecurityMiddleware
from agentorchestrator.security import SecurityIntegration


@pytest.fixture
def mock_redis_client() -> MagicMock:
    """Create a mock Redis client for testing."""
    return MagicMock()

@pytest.fixture
def test_app(mock_redis_client: MagicMock) -> FastAPI:
    """Create a test FastAPI application with security enabled."""
    app = FastAPI(title="AORBIT Test")

    # Initialize security
    security = SecurityIntegration(
        app=app,
        redis=mock_redis_client,
        enable_rbac=True,
        enable_audit=True,
        enable_encryption=True,
    )
    app.state.security = security

    # Add a test endpoint with permission requirement
    @app.get(
        "/protected",
        dependencies=[Depends(security.require_permission("read:data"))],
    )
    async def protected_endpoint() -> dict[str, str]:
        return {"message": "Access granted"}

    # Add a test endpoint for encryption
    @app.post("/encrypt")
    async def encrypt_data(request: Request) -> dict[str, str]:
        data = await request.json()
        encrypted = app.state.security.encryption_manager.encrypt(data)
        return {"encrypted": encrypted}

    # Add a test endpoint for decryption
    @app.post("/decrypt")
    async def decrypt_data(request: Request) -> dict[str, Any]:
        data = await request.json()
        decrypted = app.state.security.encryption_manager.decrypt(data["encrypted"])
        return {"decrypted": decrypted}

    return app

@pytest.fixture
def client(test_app: FastAPI) -> TestClient:
    """Create a test client."""
    return TestClient(test_app)

class TestSecurityFramework:
    """Test cases for the AORBIT Enterprise Security Framework."""

    def test_rbac_permission_denied(
        self, client: TestClient, mock_redis_client: MagicMock,
    ) -> None:
        """Test that unauthorized access is denied."""
        # Mock Redis to deny permission
        mock_redis_client.exists.return_value = False

        # Make request without API key
        response = client.get("/protected")

        # Verify unauthorized response
        assert response.status_code == 401
        assert "Unauthorized" in response.json()["detail"]

    def test_rbac_permission_granted(
        self, client: TestClient, mock_redis_client: MagicMock,
    ) -> None:
        """Test that authorized access is granted."""
        # Mock Redis to grant permission
        mock_redis_client.exists.return_value = True
        mock_redis_client.get.return_value = {
            "roles": ["admin"],
            "permissions": ["read:data"],
        }

        # Make request with valid API key
        response = client.get(
            "/protected",
            headers={"X-API-Key": "test-key"},
        )

        # Verify successful response
        assert response.status_code == 200
        assert response.json() == {"message": "Access granted"}

    def test_encryption_lifecycle(
        self, client: TestClient,
    ) -> None:
        """Test encryption and decryption of data."""
        # Data to encrypt
        test_data = {"secret": "sensitive information"}

        # Encrypt data
        response = client.post("/encrypt", json=test_data)
        assert response.status_code == 200
        encrypted_data = response.json()["encrypted"]

        # Decrypt data
        response = client.post("/decrypt", json={"encrypted": encrypted_data})
        assert response.status_code == 200
        decrypted_data = response.json()["decrypted"]

        # Verify decrypted data matches original
        assert decrypted_data == test_data

    def test_audit_logging(
        self, client: TestClient, mock_redis_client: MagicMock,
    ) -> None:
        """Test that audit logging captures events."""
        # Mock Redis lpush method for audit logging
        mock_redis_client.lpush.return_value = True

        # Make request that should be audited
        client.get(
            "/protected",
            headers={"X-API-Key": "test-key"},
        )

        # Verify audit log was created
        mock_redis_client.lpush.assert_called_once()
        assert "audit:logs" in mock_redis_client.lpush.call_args[0]

@pytest.mark.parametrize(
    ("api_key", "expected_status"),
    [
        (None, 401),  # No API key
        ("invalid-key", 401),  # Invalid API key
        ("test-key", 200),  # Valid API key
    ],
)
def test_api_security_middleware(
    api_key: str | None, expected_status: int,
) -> None:
    """Test the API security middleware."""
    app = FastAPI()

    # Add the security middleware
    app.add_middleware(
        APISecurityMiddleware,
        api_key_header="X-API-Key",
        enable_security=True,
    )

    @app.get("/test")
    async def test_endpoint() -> dict[str, str]:
        return {"message": "Success"}

    # Create test client
    client = TestClient(app)

    # Make request with or without API key
    headers = {"X-API-Key": api_key} if api_key else {}
    response = client.get("/test", headers=headers)

    # Verify response status
    assert response.status_code == expected_status

def test_initialize_security_disabled() -> None:
    """Test initializing security when it's disabled."""
    app = FastAPI()
    security = SecurityIntegration(
        app=app,
        redis=MagicMock(),
        enable_security=False,
    )

    # Verify security is disabled
    assert security.enable_security is False
    assert security.enable_rbac is False
    assert security.enable_audit is False
    assert security.enable_encryption is False
