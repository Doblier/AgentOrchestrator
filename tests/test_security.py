"""Test cases for the security framework."""

from unittest.mock import MagicMock, AsyncMock, patch
import json

import pytest
import pytest_asyncio
from fastapi import FastAPI, Request, HTTPException
from fastapi.testclient import TestClient

from agentorchestrator.api.middleware import APISecurityMiddleware
from agentorchestrator.security.integration import SecurityIntegration


@pytest_asyncio.fixture
async def mock_redis_client() -> AsyncMock:
    """Create a mock Redis client."""
    mock = AsyncMock()
    mock.hget.return_value = json.dumps(
        {
            "key": "test-key",
            "name": "test",
            "roles": ["admin"],
            "permissions": ["read"],
            "active": True,
        }
    )
    return mock


@pytest_asyncio.fixture
async def mock_rbac_manager() -> AsyncMock:
    """Create a mock RBAC manager."""
    mock = AsyncMock()
    mock.has_permission.return_value = True
    return mock


@pytest_asyncio.fixture
async def mock_audit_logger() -> AsyncMock:
    """Create a mock audit logger."""
    mock = AsyncMock()
    mock.log_event = AsyncMock()
    return mock


@pytest_asyncio.fixture
async def mock_encryptor():
    """Create a mock encryptor."""
    mock = AsyncMock()
    mock.encrypt = AsyncMock(return_value=b"encrypted-data")
    mock.decrypt = AsyncMock(return_value=b"decrypted-data")
    return mock


@pytest.fixture
def test_app(mock_redis_client: MagicMock) -> FastAPI:
    """Create a test FastAPI application with security enabled."""
    app = FastAPI(title="AORBIT Test")

    # Add the security middleware
    app.add_middleware(
        APISecurityMiddleware,
        api_key_header="X-API-Key",
        enable_security=True,
        redis=mock_redis_client,
    )

    @app.get("/test")
    async def test_endpoint() -> dict[str, str]:
        """Test endpoint that requires no permissions."""
        return {"message": "Success"}

    @app.get("/protected")
    async def protected_endpoint(request: Request) -> dict[str, str]:
        """Test endpoint that requires read permission."""
        rbac_manager = request.state.rbac_manager
        api_key = request.state.api_key

        # Check permissions
        if not await rbac_manager.has_permission(api_key, "read"):
            raise HTTPException(status_code=403, detail="Permission denied")
        return {"message": "Protected"}

    return app


@pytest.fixture
def client(test_app: FastAPI) -> TestClient:
    """Create a test client."""
    return TestClient(test_app)


@pytest.mark.asyncio
class TestSecurityFramework:
    """Test the security framework."""

    async def test_rbac_permission_denied(
        self,
        client: TestClient,
        mock_redis_client: AsyncMock,
        mock_rbac_manager: AsyncMock,
    ) -> None:
        """Test that RBAC denies access when permission is not granted."""
        # Mock Redis to return key data
        mock_redis_client.hget.return_value = json.dumps(
            {
                "key": "no-permission-key",
                "name": "test",
                "roles": ["user"],
                "permissions": [],
                "active": True,
            }
        )

        # Mock RBAC manager to deny permission
        mock_rbac_manager.has_permission.return_value = False

        # Patch RBAC manager in middleware
        with patch(
            "agentorchestrator.api.middleware.RBACManager",
            return_value=mock_rbac_manager,
        ):
            response = client.get(
                "/protected",
                headers={"X-API-Key": "no-permission-key"},
            )
            assert response.status_code == 403
            assert response.json()["detail"] == "Permission denied"

    async def test_rbac_permission_granted(
        self,
        client: TestClient,
        mock_redis_client: AsyncMock,
        mock_rbac_manager: AsyncMock,
    ) -> None:
        """Test that RBAC grants access when permission is granted."""
        # Mock Redis to return key data
        mock_redis_client.hget.return_value = json.dumps(
            {
                "key": "test-key",
                "name": "test",
                "roles": ["admin"],
                "permissions": ["read"],
                "active": True,
            }
        )

        # Mock RBAC manager to grant permission
        mock_rbac_manager.has_permission.return_value = True

        # Patch RBAC manager in middleware
        with patch(
            "agentorchestrator.api.middleware.RBACManager",
            return_value=mock_rbac_manager,
        ):
            response = client.get(
                "/protected",
                headers={"X-API-Key": "test-key"},
            )
            assert response.status_code == 200

    async def test_encryption_lifecycle(
        self,
        client: TestClient,
        mock_redis_client: AsyncMock,
        mock_encryptor: AsyncMock,
    ) -> None:
        """Test encryption key lifecycle."""
        # Mock Redis to return encryption key
        mock_redis_client.get.return_value = b"test-encryption-key"

        # Mock Redis to return key data
        mock_redis_client.hget.return_value = json.dumps(
            {
                "key": "test-key",
                "name": "test",
                "roles": ["admin"],
                "permissions": ["read"],
                "active": True,
            }
        )

        # Patch encryptor in middleware
        with (
            patch(
                "agentorchestrator.security.encryption.Encryptor",
                return_value=mock_encryptor,
            ),
            patch(
                "agentorchestrator.api.middleware.RBACManager", return_value=AsyncMock()
            ),
            patch(
                "agentorchestrator.api.middleware.AuditLogger", return_value=AsyncMock()
            ),
        ):
            response = client.get(
                "/test",
                headers={"X-API-Key": "test-key"},
            )
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_audit_logging(
        self,
        client: TestClient,
        mock_redis_client: AsyncMock,
        mock_audit_logger: AsyncMock,
        mock_rbac_manager: AsyncMock,
    ) -> None:
        """Test that audit logging captures events."""
        # Mock Redis to return key data
        mock_redis_client.hget.return_value = json.dumps(
            {
                "key": "test-key",
                "name": "test",
                "roles": ["admin"],
                "permissions": ["read"],
                "active": True,
            }
        )

        # Mock RBAC manager to grant permission
        mock_rbac_manager.has_permission.return_value = True

        # Mock Redis pipeline for audit logging
        mock_pipe = AsyncMock()
        mock_redis_client.pipeline.return_value = mock_pipe
        mock_pipe.zadd = AsyncMock()
        mock_pipe.hset = AsyncMock()
        mock_pipe.execute = AsyncMock()

        # Patch RBAC manager and audit logger in middleware
        with (
            patch(
                "agentorchestrator.api.middleware.RBACManager",
                return_value=mock_rbac_manager,
            ),
            patch(
                "agentorchestrator.api.middleware.AuditLogger",
                return_value=mock_audit_logger,
            ),
        ):
            response = client.get(
                "/protected",
                headers={"X-API-Key": "test-key"},
            )
            assert response.status_code == 200
            mock_audit_logger.log_event.assert_called_once_with(
                event_type="api_request",
                user_id="test-key",
                details={
                    "method": "GET",
                    "path": "/protected",
                    "headers": {
                        "host": "testserver",
                        "accept": "*/*",
                        "accept-encoding": "gzip, deflate",
                        "connection": "keep-alive",
                        "user-agent": "testclient",
                        "x-api-key": "test-key",
                    },
                },
            )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("api_key", "expected_status"),
    [
        (None, 401),  # No API key
        ("invalid-key", 401),  # Invalid API key
        ("test-key", 200),  # Valid API key
    ],
)
async def test_api_security_middleware(
    api_key: str | None,
    expected_status: int,
    mock_redis_client: AsyncMock,
    mock_rbac_manager: AsyncMock,
) -> None:
    """Test the API security middleware."""
    app = FastAPI()

    # Add the security middleware
    app.add_middleware(
        APISecurityMiddleware,
        api_key_header="X-API-Key",
        enable_security=True,
        redis=mock_redis_client,
    )

    @app.get("/test")
    async def test_endpoint() -> dict[str, str]:
        """Test endpoint that requires no permissions."""
        return {"message": "Success"}

    # Create test client
    client = TestClient(app)

    # Mock Redis to return key data for test-key
    if api_key == "test-key":
        mock_redis_client.hget.return_value = json.dumps(
            {
                "key": "test-key",
                "name": "test",
                "roles": ["admin"],
                "permissions": ["read"],
                "active": True,
            }
        )
    elif api_key == "invalid-key":
        mock_redis_client.hget.return_value = None

    # Mock RBAC manager
    with patch(
        "agentorchestrator.api.middleware.RBACManager", return_value=mock_rbac_manager
    ):
        # Make request with or without API key
        headers = {"X-API-Key": api_key} if api_key else {}
        try:
            response = client.get("/test", headers=headers)
            assert response.status_code == expected_status
            if expected_status == 401:
                if api_key is None:
                    assert response.json()["detail"] == "API key not found"
                else:
                    assert response.json()["detail"] == "Invalid API key"
            elif expected_status == 200:
                assert response.json() == {"message": "Success"}
        except HTTPException as e:
            assert e.status_code == expected_status
            if expected_status == 401:
                if api_key is None:
                    assert e.detail == "API key not found"
                else:
                    assert e.detail == "Invalid API key"


@pytest.mark.asyncio
def test_initialize_security_disabled() -> None:
    """Test initializing security when it's disabled."""
    app = FastAPI()
    security = SecurityIntegration(
        app=app,
        redis=MagicMock(),
        enable_security=False,
        enable_rbac=False,
        enable_audit=False,
        enable_encryption=False,
    )

    # Verify security is disabled
    assert security.enable_security is False
    assert security.enable_rbac is False
    assert security.enable_audit is False
    assert security.enable_encryption is False
