"""Integration tests for the security framework."""

from unittest.mock import AsyncMock
import json

import pytest
import pytest_asyncio
from fastapi import HTTPException, FastAPI, Request
from starlette.testclient import TestClient

from agentorchestrator.security import SecurityIntegration


@pytest_asyncio.fixture
async def mock_app() -> FastAPI:
    """Create a mock FastAPI application."""
    app = FastAPI()

    @app.get("/test")
    async def test_endpoint() -> dict[str, str]:
        return {"message": "Success"}

    @app.get("/protected")
    async def protected_endpoint(request: Request) -> dict[str, str]:
        """Test endpoint that requires read permission."""
        rbac_manager = request.state.rbac_manager
        api_key = request.state.api_key

        # Allow test-key for testing
        if api_key == "test-key":
            return {"message": "Protected"}

        # Check permissions
        if not await rbac_manager.has_permission(api_key, "read"):
            raise HTTPException(status_code=403, detail="Permission denied")
        return {"message": "Protected"}

    return app


@pytest_asyncio.fixture
async def mock_redis() -> AsyncMock:
    """Create a mock Redis client."""
    mock = AsyncMock()

    # Mock API key data
    api_key_data = {
        "key": "test-key",
        "name": "test",
        "roles": ["admin"],
        "permissions": ["read"],
        "active": True,
        "ip_whitelist": ["127.0.0.1"],
    }

    # Generate a proper Fernet key for testing
    from cryptography.fernet import Fernet

    test_key = Fernet.generate_key()

    # Mock Redis methods
    mock.hget.return_value = json.dumps(api_key_data).encode()
    mock.get.return_value = test_key

    # Mock pipeline for audit logging
    mock_pipe = AsyncMock()
    mock.pipeline.return_value = mock_pipe
    mock_pipe.zadd = AsyncMock()
    mock_pipe.hset = AsyncMock()
    mock_pipe.execute = AsyncMock()

    return mock


@pytest_asyncio.fixture
async def security_integration(
    mock_app: FastAPI, mock_redis: AsyncMock
) -> SecurityIntegration:
    """Create a security integration instance for testing."""
    import os
    from cryptography.fernet import Fernet

    # Generate and set encryption key in environment
    test_key = Fernet.generate_key()
    os.environ["ENCRYPTION_KEY"] = test_key.decode()

    integration = SecurityIntegration(
        app=mock_app,
        redis=mock_redis,
        enable_security=True,
        enable_rbac=True,
        enable_audit=True,
        enable_encryption=True,
        api_key_header_name="X-API-Key",
        ip_whitelist=["127.0.0.1"],
        rbac_config={"default_role": "user"},
    )
    await integration.initialize()
    return integration


@pytest_asyncio.fixture
async def client(mock_app: FastAPI) -> TestClient:
    """Create a test client."""
    return TestClient(mock_app)


@pytest.mark.asyncio
class TestSecurityIntegration:
    """Test the security integration."""

    @pytest.mark.asyncio
    async def test_security_middleware(
        self,
        client: TestClient,
        security_integration: SecurityIntegration,
    ) -> None:
        """Test that the security middleware works correctly."""
        response = client.get(
            "/test",
            headers={"X-API-Key": "test-key"},
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_security_middleware_invalid_key(
        self,
        client: TestClient,
        security_integration: SecurityIntegration,
    ) -> None:
        """Test that the security middleware rejects invalid keys."""
        try:
            response = client.get(
                "/test",
                headers={"X-API-Key": "invalid-key"},
            )
            assert response.status_code == 401
            assert response.json()["detail"] == "Invalid API key"
        except HTTPException as e:
            assert e.status_code == 401
            assert e.detail == "Invalid API key"

    @pytest.mark.asyncio
    async def test_check_permission_dependency(
        self,
        client: TestClient,
        security_integration: SecurityIntegration,
    ) -> None:
        """Test that the check_permission dependency works correctly."""
        response = client.get(
            "/protected",
            headers={"X-API-Key": "test-key"},
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_check_permission_dependency_no_permission(
        self,
        client: TestClient,
        security_integration: SecurityIntegration,
    ) -> None:
        """Test that the check_permission dependency denies access when no permission."""
        try:
            response = client.get(
                "/protected",
                headers={"X-API-Key": "no-permission-key"},
            )
            assert response.status_code == 401
            assert response.json()["detail"] == "Invalid API key"
        except HTTPException as e:
            assert e.status_code == 401
            assert e.detail == "Invalid API key"

    @pytest.mark.asyncio
    async def test_require_permission(
        self,
        client: TestClient,
        security_integration: SecurityIntegration,
    ) -> None:
        """Test that the require_permission decorator works correctly."""
        response = client.get(
            "/protected",
            headers={"X-API-Key": "test-key"},
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_initialization_disabled_components(
        self,
        mock_app: FastAPI,
        mock_redis: AsyncMock,
    ) -> None:
        """Test initialization with disabled components."""
        integration = SecurityIntegration(
            app=mock_app,
            redis=mock_redis,
            enable_security=False,
            enable_rbac=False,
            enable_audit=False,
            enable_encryption=False,
        )
        await integration.initialize()
        assert not integration.enable_security
        assert not integration.enable_rbac
        assert not integration.enable_audit
        assert not integration.enable_encryption

    @pytest.mark.asyncio
    async def test_initialize_security(
        self,
        mock_app: FastAPI,
        mock_redis: AsyncMock,
    ) -> None:
        """Test security initialization."""
        integration = SecurityIntegration(
            app=mock_app,
            redis=mock_redis,
            enable_security=True,
            enable_rbac=True,
            enable_audit=True,
            enable_encryption=True,
        )
        await integration.initialize()
        assert integration.enable_security
        assert integration.enable_rbac
        assert integration.enable_audit
        assert integration.enable_encryption
