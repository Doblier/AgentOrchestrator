"""Integration tests for the security framework."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from agentorchestrator.security import SecurityIntegration
from agentorchestrator.security.integration import initialize_security


@pytest.fixture
async def mock_app() -> MagicMock:
    """Create a mock FastAPI application."""
    return MagicMock()


@pytest.fixture
async def mock_redis() -> AsyncMock:
    """Create a mock Redis client."""
    return AsyncMock()


class TestSecurityIntegration:
    """Test cases for the SecurityIntegration class."""

    @pytest.mark.asyncio
    async def test_initialization_disabled_components(
        self, mock_app: MagicMock, mock_redis: AsyncMock,
    ) -> None:
        """Test initialization with disabled components."""
        with (
            patch(
                "agentorchestrator.security.integration.initialize_rbac",
            ) as mock_init_rbac,
            patch(
                "agentorchestrator.security.integration.initialize_audit_logger",
            ) as mock_init_audit,
            patch(
                "agentorchestrator.security.integration.initialize_encryption",
            ) as mock_init_encryption,
        ):
            # Initialize with all components disabled
            security_integration = SecurityIntegration(
                app=mock_app,
                redis=mock_redis,
                enable_rbac=False,
                enable_audit=False,
                enable_encryption=False,
            )

            # Verify initialization
            assert security_integration.app == mock_app
            assert security_integration.redis == mock_redis
            assert not security_integration.rbac_enabled
            assert not security_integration.audit_enabled
            assert not security_integration.encryption_enabled

            # Verify no component initialization
            mock_init_rbac.assert_not_called()
            mock_init_audit.assert_not_called()
            mock_init_encryption.assert_not_called()

    @pytest.mark.asyncio
    async def test_security_middleware(
        self, security_integration: SecurityIntegration,
    ) -> None:
        """Test the security middleware."""
        # Mock request and handler
        request = MagicMock()
        handler = AsyncMock()
        handler.return_value = "handler_result"

        # Mock RBAC check
        security_integration.rbac_manager = MagicMock()
        security_integration.rbac_manager.check_permission = AsyncMock(
            return_value=True,
        )

        # Mock audit logger
        security_integration.audit_logger = MagicMock()
        security_integration.audit_logger.log_request = AsyncMock()

        # Call the middleware
        result = await security_integration._security_middleware(request, handler)

        # Verify result
        assert result == "handler_result"

        # Verify RBAC check
        security_integration.rbac_manager.check_permission.assert_called_once()

        # Verify audit logging
        security_integration.audit_logger.log_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_security_middleware_invalid_key(
        self, security_integration: SecurityIntegration,
    ) -> None:
        """Test the security middleware with an invalid API key."""
        # Mock request and handler
        request = MagicMock()
        handler = AsyncMock()

        # Mock RBAC check to fail
        security_integration.rbac_manager = MagicMock()
        security_integration.rbac_manager.check_permission = AsyncMock(
            return_value=False,
        )

        # Call the middleware and expect an exception
        with pytest.raises(HTTPException) as exc_info:
            await security_integration._security_middleware(request, handler)

        # Verify exception
        assert exc_info.value.status_code == 403
        assert "Permission denied" in str(exc_info.value.detail)

        # Verify RBAC check
        security_integration.rbac_manager.check_permission.assert_called_once()

    @pytest.mark.asyncio
    async def test_security_middleware_ip_whitelist(
        self, security_integration: SecurityIntegration,
    ) -> None:
        """Test the security middleware with IP whitelist."""
        # Mock request and handler
        request = MagicMock()
        request.client.host = "127.0.0.1"
        handler = AsyncMock()
        handler.return_value = "handler_result"

        # Set IP whitelist
        security_integration.ip_whitelist = ["127.0.0.1"]

        # Call the middleware
        result = await security_integration._security_middleware(request, handler)

        # Verify result
        assert result == "handler_result"

        # Verify handler was called
        handler.assert_called_once_with(request)

    def test_check_permission_dependency(
        self, security_integration: SecurityIntegration,
    ) -> None:
        """Test the check_permission_dependency method."""
        # Mock request
        request = MagicMock()
        request.state.security = MagicMock()
        request.state.security.rbac_manager = MagicMock()
        request.state.security.rbac_manager.check_permission = MagicMock(
            return_value=True,
        )

        # Check permission
        result = security_integration.check_permission_dependency(
            request, "read:data", "resource1",
        )

        # Verify result
        assert result is True

        # Verify RBAC check
        request.state.security.rbac_manager.check_permission.assert_called_once()

    def test_check_permission_dependency_no_permission(
        self, security_integration: SecurityIntegration,
    ) -> None:
        """Test the check_permission_dependency method when permission is denied."""
        # Mock request
        request = MagicMock()
        request.state.security = MagicMock()
        request.state.security.rbac_manager = MagicMock()
        request.state.security.rbac_manager.check_permission = MagicMock(
            return_value=False,
        )

        # Check permission and expect an exception
        with pytest.raises(HTTPException) as exc_info:
            security_integration.check_permission_dependency(
                request, "read:data", "resource1",
            )

        # Verify exception
        assert exc_info.value.status_code == 403
        assert "Permission denied" in str(exc_info.value.detail)

        # Verify RBAC check
        request.state.security.rbac_manager.check_permission.assert_called_once()

    def test_require_permission(
        self, security_integration: SecurityIntegration,
    ) -> None:
        """Test the require_permission method."""
        # Mock the dependency
        with patch.object(
            security_integration, "check_permission_dependency",
        ) as mock_dependency:
            mock_dependency.return_value = "dependency_result"

            # Create dependency
            dependency = security_integration.require_permission(
                "read:data", "resource1",
            )

            # Call the dependency
            result = dependency("request")

            # Verify result
            assert result == "dependency_result"

            # Verify dependency call
            mock_dependency.assert_called_once_with(
                "request", "read:data", "resource1",
            )


@pytest.mark.parametrize(
    "env_vars",
    [
        {
            "SECURITY_ENABLED": "true",
            "RBAC_ENABLED": "true",
            "AUDIT_LOGGING_ENABLED": "true",
            "ENCRYPTION_ENABLED": "true",
        },
    ],
)
def test_initialize_security(
    mock_getlogger: MagicMock, mock_app: MagicMock, mock_redis: AsyncMock,
) -> None:
    """Test the initialize_security function."""
    # Mock logger
    mock_getlogger.return_value = MagicMock()

    # Mock security integration
    with patch(
        "agentorchestrator.security.integration.SecurityIntegration",
    ) as mock_integration_class:
        # Set up mock
        mock_integration = MagicMock()
        mock_integration_class.return_value = mock_integration

        # Call initialize function
        result = initialize_security(mock_app, mock_redis)

        # Verify result
        assert result == mock_integration

        # Verify integration initialization
        mock_integration_class.assert_called_once()


@pytest.mark.parametrize(
    "env_vars",
    [
        {
            "SECURITY_ENABLED": "false",
        },
    ],
)
def test_initialize_security_disabled(
    mock_getlogger: MagicMock, mock_app: MagicMock, mock_redis: AsyncMock,
) -> None:
    """Test the initialize_security function when security is disabled."""
    # Mock logger
    mock_getlogger.return_value = MagicMock()

    # Mock security integration
    with patch(
        "agentorchestrator.security.integration.SecurityIntegration",
    ) as mock_integration_class:
        # Call initialize function
        result = initialize_security(mock_app, mock_redis)

        # Verify result is None
        assert result is None

        # Verify no integration initialization
        mock_integration_class.assert_not_called()
