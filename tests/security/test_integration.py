import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi import FastAPI, Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
import logging

from agentorchestrator.security.integration import (
    SecurityIntegration, initialize_security
)


@pytest.fixture
def mock_redis():
    """Fixture to provide a mock Redis client."""
    mock = MagicMock()
    return mock


@pytest.fixture
def mock_app():
    """Fixture to provide a mock FastAPI application."""
    app = MagicMock()
    app.middleware = MagicMock()
    app.state = MagicMock()
    return app


@pytest.fixture
def security_integration(mock_app, mock_redis):
    """Fixture to provide an initialized SecurityIntegration instance."""
    integration = SecurityIntegration(
        app=mock_app,
        redis_client=mock_redis,
        enable_audit=True,
        enable_rbac=True,
        enable_encryption=True
    )
    return integration


class TestSecurityIntegration:
    """Tests for the SecurityIntegration class."""
    
    def test_initialization(self, mock_app, mock_redis):
        """Test the initialization of the SecurityIntegration class."""
        with patch('agentorchestrator.security.integration.initialize_rbac') as mock_init_rbac:
            with patch('agentorchestrator.security.integration.initialize_audit_logger') as mock_init_audit:
                with patch('agentorchestrator.security.integration.initialize_encryption') as mock_init_encryption:
                    # Set up mocks
                    mock_rbac = MagicMock()
                    mock_audit = MagicMock()
                    mock_encryption = MagicMock()
                    
                    mock_init_rbac.return_value = mock_rbac
                    mock_init_audit.return_value = mock_audit
                    mock_init_encryption.return_value = mock_encryption
                    
                    # Initialize the integration
                    integration = SecurityIntegration(
                        app=mock_app,
                        redis_client=mock_redis,
                        enable_audit=True,
                        enable_rbac=True,
                        enable_encryption=True
                    )
                    
                    # Verify the components were initialized
                    mock_init_rbac.assert_called_once_with(mock_redis)
                    mock_init_audit.assert_called_once_with(mock_redis)
                    mock_init_encryption.assert_called_once()
                    
                    # Verify the attributes were set
                    assert integration.rbac_manager == mock_rbac
                    assert integration.audit_logger == mock_audit
                    assert integration.encryption_manager == mock_encryption
                    
                    # Verify middleware was set up
                    mock_app.middleware.assert_called_once()
    
    def test_initialization_disabled_components(self, mock_app, mock_redis):
        """Test initialization with disabled components."""
        with patch('agentorchestrator.security.integration.initialize_rbac') as mock_init_rbac:
            with patch('agentorchestrator.security.integration.initialize_audit_logger') as mock_init_audit:
                with patch('agentorchestrator.security.integration.initialize_encryption') as mock_init_encryption:
                    # Initialize with disabled components
                    integration = SecurityIntegration(
                        app=mock_app,
                        redis_client=mock_redis,
                        enable_audit=False,
                        enable_rbac=False,
                        enable_encryption=False
                    )
                    
                    # Verify no components were initialized
                    mock_init_rbac.assert_not_called()
                    mock_init_audit.assert_not_called()
                    mock_init_encryption.assert_not_called()
                    
                    # Verify the attributes are None
                    assert integration.rbac_manager is None
                    assert integration.audit_logger is None
                    assert integration.encryption_manager is None
    
    @pytest.mark.asyncio
    async def test_security_middleware(self, security_integration):
        """Test the security middleware."""
        # Mock request and handler
        request = MagicMock()
        request.headers = {"X-API-Key": "test-key"}
        request.client = MagicMock()
        request.client.host = "192.168.1.1"
        
        handler = AsyncMock()
        handler.return_value = "response"
        
        # Mock the API key validation
        with patch.object(security_integration, 'rbac_manager') as mock_rbac:
            with patch.object(security_integration, 'audit_logger') as mock_audit:
                # Configure mock to return valid API key data
                mock_rbac.get_api_key_data.return_value = MagicMock(
                    api_key_id="test-key",
                    user_id="user123",
                    ip_whitelist=[]
                )
                
                # Call the middleware
                response = await security_integration._security_middleware(request, handler)
                
                # Verify the handler was called
                handler.assert_called_once_with(request)
                
                # Verify the response
                assert response == "response"
                
                # Verify the audit log was called
                mock_audit.log_event.assert_called()
    
    @pytest.mark.asyncio
    async def test_security_middleware_invalid_key(self, security_integration):
        """Test the security middleware with an invalid API key."""
        # Mock request and handler
        request = MagicMock()
        request.headers = {"X-API-Key": "invalid-key"}
        request.client = MagicMock()
        request.client.host = "192.168.1.1"
        
        handler = AsyncMock()
        
        # Mock the API key validation
        with patch.object(security_integration, 'rbac_manager') as mock_rbac:
            with patch.object(security_integration, 'audit_logger') as mock_audit:
                # Configure mock to return None (invalid API key)
                mock_rbac.get_api_key_data.return_value = None
                
                # Call the middleware should raise an exception
                with pytest.raises(HTTPException) as excinfo:
                    await security_integration._security_middleware(request, handler)
                
                # Verify the error code is 401 (Unauthorized)
                assert excinfo.value.status_code == 401
                
                # Verify the handler was not called
                handler.assert_not_called()
                
                # Verify the audit log was called for the failure
                mock_audit.log_event.assert_called()
    
    @pytest.mark.asyncio
    async def test_security_middleware_ip_whitelist(self, security_integration):
        """Test the security middleware with IP whitelist."""
        # Mock request and handler
        request = MagicMock()
        request.headers = {"X-API-Key": "test-key"}
        request.client = MagicMock()
        request.client.host = "192.168.1.1"
        
        handler = AsyncMock()
        
        # Mock the API key validation
        with patch.object(security_integration, 'rbac_manager') as mock_rbac:
            with patch.object(security_integration, 'audit_logger') as mock_audit:
                # Configure mock to return API key with IP whitelist
                mock_rbac.get_api_key_data.return_value = MagicMock(
                    api_key_id="test-key",
                    user_id="user123",
                    ip_whitelist=["10.0.0.1"]  # Different from request IP
                )
                
                # Call the middleware should raise an exception
                with pytest.raises(HTTPException) as excinfo:
                    await security_integration._security_middleware(request, handler)
                
                # Verify the error code is 403 (Forbidden)
                assert excinfo.value.status_code == 403
                
                # Verify the handler was not called
                handler.assert_not_called()
                
                # Verify the audit log was called for the failure
                mock_audit.log_event.assert_called()
    
    def test_check_permission_dependency(self, security_integration):
        """Test the check_permission_dependency method."""
        with patch.object(security_integration, 'rbac_manager') as mock_rbac:
            # Configure mock to return True (has permission)
            mock_rbac.check_permission.return_value = True
            
            # Create the dependency
            dependency = security_integration.check_permission_dependency("READ")
            
            # Mock request
            request = MagicMock()
            request.state.api_key = "test-key"
            
            # Call the dependency
            result = dependency(request)
            
            # Verify the result
            assert result is True
            
            # Verify rbac_manager was called
            mock_rbac.check_permission.assert_called_once()
    
    def test_check_permission_dependency_no_permission(self, security_integration):
        """Test the check_permission_dependency method when permission is denied."""
        with patch.object(security_integration, 'rbac_manager') as mock_rbac:
            # Configure mock to return False (no permission)
            mock_rbac.check_permission.return_value = False
            
            # Create the dependency
            dependency = security_integration.check_permission_dependency("ADMIN")
            
            # Mock request
            request = MagicMock()
            request.state.api_key = "test-key"
            
            # Call the dependency should raise an exception
            with pytest.raises(HTTPException) as excinfo:
                dependency(request)
            
            # Verify the error code is 403 (Forbidden)
            assert excinfo.value.status_code == 403
            
            # Verify rbac_manager was called
            mock_rbac.check_permission.assert_called_once()
    
    def test_require_permission(self, security_integration):
        """Test the require_permission method."""
        # Mock the dependency
        with patch.object(security_integration, 'check_permission_dependency') as mock_dependency:
            mock_dependency.return_value = "dependency_result"
            
            # Call the method
            result = security_integration.require_permission("READ")
            
            # Verify mock_dependency was called
            mock_dependency.assert_called_once_with("READ")
            
            # Verify the result
            assert result == "dependency_result"


@patch('agentorchestrator.security.integration.logging.getLogger')
@patch.dict('os.environ', {
    'SECURITY_ENABLED': 'true',
    'RBAC_ENABLED': 'true',
    'AUDIT_ENABLED': 'true',
    'ENCRYPTION_ENABLED': 'true'
})
def test_initialize_security(mock_getlogger, mock_app, mock_redis):
    """Test the initialize_security function."""
    mock_logger = MagicMock()
    mock_getlogger.return_value = mock_logger
    
    with patch('agentorchestrator.security.integration.SecurityIntegration') as mock_integration_class:
        # Set up mock
        mock_integration = MagicMock()
        mock_integration_class.return_value = mock_integration
        
        # Call the initialize function
        result = initialize_security(mock_app, mock_redis)
        
        # Verify the result
        assert result == mock_integration
        
        # Verify SecurityIntegration was created with the right parameters
        mock_integration_class.assert_called_once_with(
            app=mock_app,
            redis_client=mock_redis,
            enable_rbac=True,
            enable_audit=True,
            enable_encryption=True
        )
        
        # Verify the security instance was added to app.state
        assert mock_app.state.security == mock_integration
        
        # Verify logging was called
        assert mock_logger.info.called


@patch('agentorchestrator.security.integration.logging.getLogger')
@patch.dict('os.environ', {
    'SECURITY_ENABLED': 'false'
})
def test_initialize_security_disabled(mock_getlogger, mock_app, mock_redis):
    """Test the initialize_security function when security is disabled."""
    mock_logger = MagicMock()
    mock_getlogger.return_value = mock_logger
    
    with patch('agentorchestrator.security.integration.SecurityIntegration') as mock_integration_class:
        # Call the initialize function
        result = initialize_security(mock_app, mock_redis)
        
        # Verify the result is None (security disabled)
        assert result is None
        
        # Verify SecurityIntegration was not created
        mock_integration_class.assert_not_called()
        
        # Verify logging was called
        assert mock_logger.info.called 