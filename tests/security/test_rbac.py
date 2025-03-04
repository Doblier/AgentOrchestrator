import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi import HTTPException

from agentorchestrator.security.rbac import (
    RBACManager, Role, EnhancedApiKey,
    initialize_rbac,
    check_permission
)


@pytest.fixture
def mock_redis():
    """Fixture to provide a mock Redis client."""
    mock = AsyncMock()
    return mock


@pytest.fixture
def rbac_manager(mock_redis):
    """Fixture to provide an initialized RBACManager."""
    return RBACManager(mock_redis)


@pytest.mark.security
class TestRBACManager:
    """Test cases for the RBACManager class."""
    
    @pytest.mark.asyncio
    async def test_create_role(self, rbac_manager, mock_redis):
        """Test creating a new role."""
        # Set up mock
        mock_redis.exists.return_value = False
        mock_redis.set.return_value = True
        mock_redis.sadd.return_value = 1
        
        # Create role
        role = await rbac_manager.create_role(
            name="admin",
            description="Administrator role",
            permissions=["read", "write"],
            resources=["*"],
            parent_roles=[]
        )
        
        # Verify role was created
        assert role.name == "admin"
        assert role.description == "Administrator role"
        assert role.permissions == ["read", "write"]
        assert role.resources == ["*"]
        assert role.parent_roles == []
        
        # Verify Redis calls
        mock_redis.exists.assert_called_once_with("role:admin")
        mock_redis.set.assert_called_once()
        mock_redis.sadd.assert_called_once_with("roles", "admin")
    
    @pytest.mark.asyncio
    async def test_get_role(self, rbac_manager, mock_redis):
        """Test retrieving a role."""
        # Set up mock
        mock_redis.exists.return_value = True
        mock_redis.get.return_value = '{"name": "admin", "description": "Admin role", "permissions": ["read"], "resources": ["*"], "parent_roles": []}'
        
        # Get role
        role = await rbac_manager.get_role("admin")
        
        # Verify role was retrieved
        assert role.name == "admin"
        assert role.description == "Admin role"
        assert role.permissions == ["read"]
        assert role.resources == ["*"]
        assert role.parent_roles == []
        
        # Verify Redis calls
        mock_redis.exists.assert_called_once_with("role:admin")
        mock_redis.get.assert_called_once_with("role:admin")
    
    @pytest.mark.asyncio
    async def test_get_role_not_found(self, rbac_manager, mock_redis):
        """Test retrieving a non-existent role."""
        # Set up mock
        mock_redis.exists.return_value = False
        
        # Get role
        role = await rbac_manager.get_role("nonexistent")
        
        # Verify role was not found
        assert role is None
        
        # Verify Redis calls
        mock_redis.exists.assert_called_once_with("role:nonexistent")
        mock_redis.get.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_get_effective_permissions(self, rbac_manager, mock_redis):
        """Test getting effective permissions for roles."""
        # Set up mock
        mock_redis.exists.return_value = True
        mock_redis.get.side_effect = [
            '{"name": "admin", "permissions": ["read", "write"], "parent_roles": []}',
            '{"name": "user", "permissions": ["read"], "parent_roles": []}'
        ]
        
        # Get effective permissions
        permissions = await rbac_manager.get_effective_permissions(["admin", "user"])
        
        # Verify permissions
        assert permissions == {"read", "write"}
        
        # Verify Redis calls
        assert mock_redis.exists.call_count == 2
        assert mock_redis.get.call_count == 2
    
    @pytest.mark.asyncio
    async def test_create_api_key(self, rbac_manager, mock_redis):
        """Test creating an API key."""
        # Set up mock
        mock_redis.exists.return_value = False
        mock_redis.hset.return_value = True
        
        # Create API key
        api_key = await rbac_manager.create_api_key(
            name="test_key",
            roles=["admin"],
            user_id="user123",
            rate_limit=100
        )
        
        # Verify API key was created
        assert api_key.key.startswith("aorbit_")
        assert api_key.name == "test_key"
        assert api_key.roles == ["admin"]
        assert api_key.user_id == "user123"
        assert api_key.rate_limit == 100
        
        # Verify Redis calls
        mock_redis.hset.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_api_key(self, rbac_manager, mock_redis):
        """Test getting API key data."""
        # Set up mock
        mock_redis.hget.return_value = '{"key": "test_key", "name": "Test Key", "roles": ["admin"], "user_id": "user123", "rate_limit": 100}'
        
        # Get API key data
        api_key = await rbac_manager.get_api_key("test_key")
        
        # Verify API key data was retrieved
        assert api_key.key == "test_key"
        assert api_key.name == "Test Key"
        assert api_key.roles == ["admin"]
        assert api_key.user_id == "user123"
        assert api_key.rate_limit == 100
        
        # Verify Redis calls
        mock_redis.hget.assert_called_once_with("rbac:api_keys", "test_key")
    
    @pytest.mark.asyncio
    async def test_has_permission(self, rbac_manager, mock_redis):
        """Test checking permissions."""
        # Set up mock
        mock_redis.hget.return_value = '{"key": "test_key", "name": "Test Key", "roles": ["admin"], "user_id": "user123", "rate_limit": 100}'
        mock_redis.exists.return_value = True
        mock_redis.get.return_value = '{"name": "admin", "permissions": ["read", "write"], "parent_roles": []}'
        
        # Check permission
        result = await rbac_manager.has_permission("test_key", "read")
        
        # Verify permission was checked
        assert result is True
        
        # Verify Redis calls
        mock_redis.hget.assert_called_once_with("rbac:api_keys", "test_key")
        mock_redis.exists.assert_called_once()
        mock_redis.get.assert_called_once()


@pytest.mark.security
@pytest.mark.asyncio
async def test_initialize_rbac(mock_redis):
    """Test initializing the RBAC system."""
    with patch('agentorchestrator.security.rbac.RBACManager') as mock_rbac_class:
        # Set up mock
        mock_rbac = AsyncMock()
        mock_rbac_class.return_value = mock_rbac
        mock_rbac.get_role.return_value = None
        
        # Initialize RBAC
        rbac = await initialize_rbac(mock_redis)
        
        # Verify RBAC was initialized
        mock_rbac_class.assert_called_once_with(mock_redis)
        assert rbac == mock_rbac


@pytest.mark.security
@pytest.mark.asyncio
async def test_check_permission():
    """Test the check_permission dependency."""
    with patch('agentorchestrator.security.rbac.RBACManager') as mock_rbac_class:
        # Set up mock
        mock_rbac = AsyncMock()
        mock_rbac_class.return_value = mock_rbac
        mock_rbac.has_permission.return_value = True
        
        # Create request
        request = MagicMock()
        request.state.api_key = "test-key"
        request.state.api_key_data = MagicMock(key="test-key")
        request.app.state.rbac_manager = mock_rbac
        
        # Check permission
        result = await check_permission(request, "read")
        
        # Verify permission was checked
        assert result is True
        mock_rbac.has_permission.assert_called_once_with("test-key", "read", None, None) 