import pytest
import uuid
from unittest.mock import MagicMock, patch
from fastapi import HTTPException

from agentorchestrator.security.rbac import (
    Permission, Resource, Role, EnhancedApiKey, RBACManager,
    initialize_rbac, check_permission
)


@pytest.fixture
def mock_redis():
    """Fixture to provide a mock Redis client."""
    mock = MagicMock()
    # Mock the hget method to return None by default (key not found)
    mock.hget.return_value = None
    return mock


@pytest.fixture
def rbac_manager(mock_redis):
    """Fixture to provide an initialized RBACManager with a mock Redis client."""
    manager = RBACManager(redis_client=mock_redis)
    return manager


class TestPermission:
    """Tests for the Permission enum."""
    
    def test_permission_values(self):
        """Test that Permission enum has expected values."""
        assert Permission.READ.value == "read"
        assert Permission.WRITE.value == "write"
        assert Permission.EXECUTE.value == "execute"
        assert Permission.ADMIN.value == "admin"
        assert Permission.FINANCE_READ.value == "finance_read"
        assert Permission.FINANCE_WRITE.value == "finance_write"
        assert Permission.AGENT_CREATE.value == "agent_create"
        assert Permission.AGENT_EXECUTE.value == "agent_execute"


class TestResource:
    """Tests for the Resource class."""
    
    def test_resource_creation(self):
        """Test creating a Resource instance."""
        resource = Resource(resource_type="account", resource_id="12345")
        assert resource.resource_type == "account"
        assert resource.resource_id == "12345"
        assert resource.actions == set()
        
    def test_resource_with_actions(self):
        """Test creating a Resource with actions."""
        resource = Resource(
            resource_type="account",
            resource_id="12345",
            actions={Permission.READ, Permission.WRITE}
        )
        assert Permission.READ in resource.actions
        assert Permission.WRITE in resource.actions
        assert Permission.EXECUTE not in resource.actions
        
    def test_resource_equality(self):
        """Test Resource equality comparison."""
        resource1 = Resource(resource_type="account", resource_id="12345")
        resource2 = Resource(resource_type="account", resource_id="12345")
        resource3 = Resource(resource_type="user", resource_id="12345")
        
        assert resource1 == resource2
        assert resource1 != resource3


class TestRole:
    """Tests for the Role class."""
    
    def test_role_creation(self):
        """Test creating a Role instance."""
        role = Role(name="test_role", permissions={Permission.READ})
        assert role.name == "test_role"
        assert Permission.READ in role.permissions
        assert not role.resources
        assert not role.parent_roles
        
    def test_role_with_resources(self):
        """Test creating a Role with resources."""
        resource = Resource(resource_type="account", resource_id="12345")
        role = Role(
            name="test_role",
            permissions={Permission.READ},
            resources=[resource]
        )
        assert resource in role.resources
        
    def test_role_with_parent(self):
        """Test creating a Role with a parent role."""
        parent_role = Role(
            name="parent_role",
            permissions={Permission.READ}
        )
        child_role = Role(
            name="child_role",
            permissions={Permission.WRITE},
            parent_roles=[parent_role]
        )
        assert parent_role in child_role.parent_roles
        
    def test_has_permission_direct(self):
        """Test has_permission method with direct permissions."""
        role = Role(name="test_role", permissions={Permission.READ, Permission.WRITE})
        assert role.has_permission(Permission.READ)
        assert role.has_permission(Permission.WRITE)
        assert not role.has_permission(Permission.EXECUTE)
        
    def test_has_permission_inherited(self):
        """Test has_permission method with inherited permissions."""
        parent_role = Role(
            name="parent_role",
            permissions={Permission.READ}
        )
        child_role = Role(
            name="child_role",
            permissions={Permission.WRITE},
            parent_roles=[parent_role]
        )
        assert child_role.has_permission(Permission.READ)  # Inherited
        assert child_role.has_permission(Permission.WRITE)  # Direct
        assert not child_role.has_permission(Permission.EXECUTE)  # Not present
        
    def test_has_permission_nested_inheritance(self):
        """Test has_permission with multi-level inheritance."""
        grandparent = Role(name="grandparent", permissions={Permission.READ})
        parent = Role(name="parent", permissions={Permission.WRITE}, parent_roles=[grandparent])
        child = Role(name="child", permissions={Permission.EXECUTE}, parent_roles=[parent])
        
        assert child.has_permission(Permission.READ)  # From grandparent
        assert child.has_permission(Permission.WRITE)  # From parent
        assert child.has_permission(Permission.EXECUTE)  # Direct
        assert not child.has_permission(Permission.ADMIN)  # Not present


class TestEnhancedApiKey:
    """Tests for the EnhancedApiKey class."""
    
    def test_api_key_creation(self):
        """Test creating an EnhancedApiKey instance."""
        api_key = EnhancedApiKey(
            api_key_id="test-key",
            roles=["admin"],
            user_id="user123"
        )
        assert api_key.api_key_id == "test-key"
        assert "admin" in api_key.roles
        assert api_key.user_id == "user123"
        assert api_key.rate_limit is None
        assert api_key.expiration is None
        assert not api_key.ip_whitelist
        
    def test_api_key_with_all_fields(self):
        """Test creating an EnhancedApiKey with all fields."""
        api_key = EnhancedApiKey(
            api_key_id="test-key",
            roles=["admin"],
            user_id="user123",
            rate_limit=100,
            expiration="2023-12-31",
            ip_whitelist=["192.168.1.1", "10.0.0.1"]
        )
        assert api_key.rate_limit == 100
        assert api_key.expiration == "2023-12-31"
        assert "192.168.1.1" in api_key.ip_whitelist
        assert "10.0.0.1" in api_key.ip_whitelist


class TestRBACManager:
    """Tests for the RBACManager class."""
    
    def test_create_role(self, rbac_manager, mock_redis):
        """Test creating a role."""
        # Configure mock to return None (role doesn't exist)
        mock_redis.hget.return_value = None
        
        role = Role(name="test_role", permissions={Permission.READ})
        result = rbac_manager.create_role(role)
        
        assert result is True
        # Verify Redis was called with expected arguments
        mock_redis.hset.assert_called_once()
        
    def test_create_existing_role(self, rbac_manager, mock_redis):
        """Test creating a role that already exists."""
        # Configure mock to return a value (role exists)
        mock_redis.hget.return_value = b'{"name":"test_role","permissions":["read"]}'
        
        role = Role(name="test_role", permissions={Permission.READ})
        result = rbac_manager.create_role(role)
        
        assert result is False
        # Verify hset was not called
        mock_redis.hset.assert_not_called()
        
    @patch('json.loads')
    def test_get_role(self, mock_loads, rbac_manager, mock_redis):
        """Test getting a role."""
        # Configure mock to return a serialized role
        mock_redis.hget.return_value = b'{"name":"test_role","permissions":["read"]}'
        mock_loads.return_value = {"name": "test_role", "permissions": ["read"]}
        
        role = rbac_manager.get_role("test_role")
        
        assert role is not None
        assert role.name == "test_role"
        assert Permission.READ in role.permissions
        
    def test_get_nonexistent_role(self, rbac_manager, mock_redis):
        """Test getting a role that doesn't exist."""
        # Configure mock to return None (role doesn't exist)
        mock_redis.hget.return_value = None
        
        role = rbac_manager.get_role("nonexistent_role")
        
        assert role is None
        
    def test_create_api_key(self, rbac_manager, mock_redis):
        """Test creating an API key."""
        # Mock UUID to return a predictable value
        with patch('uuid.uuid4', return_value=uuid.UUID("00000000-0000-0000-0000-000000000000")):
            api_key = rbac_manager.create_api_key(
                user_id="user123",
                roles=["admin"],
                rate_limit=100
            )
            
            assert api_key.startswith("aorbit-")
            assert len(api_key) > 10  # Should be a reasonably long key
            mock_redis.hset.assert_called_once()
            
    @patch('json.loads')
    def test_get_api_key_data(self, mock_loads, rbac_manager, mock_redis):
        """Test getting API key data."""
        # Configure mock to return a serialized API key
        mock_redis.hget.return_value = b'{"api_key_id":"test-key","roles":["admin"],"user_id":"user123"}'
        mock_loads.return_value = {"api_key_id": "test-key", "roles": ["admin"], "user_id": "user123"}
        
        api_key_data = rbac_manager.get_api_key_data("test-key")
        
        assert api_key_data is not None
        assert api_key_data.api_key_id == "test-key"
        assert "admin" in api_key_data.roles
        assert api_key_data.user_id == "user123"
        
    def test_check_permission_with_role(self, rbac_manager, mock_redis):
        """Test check_permission with a valid role and permission."""
        # Set up mocks for the role and API key
        with patch.object(rbac_manager, 'get_api_key_data') as mock_get_key:
            with patch.object(rbac_manager, 'get_role') as mock_get_role:
                # Configure API key mock
                mock_api_key = EnhancedApiKey(
                    api_key_id="test-key",
                    roles=["admin"],
                    user_id="user123"
                )
                mock_get_key.return_value = mock_api_key
                
                # Configure role mock
                mock_role = Role(name="admin", permissions={Permission.READ, Permission.WRITE, Permission.ADMIN})
                mock_get_role.return_value = mock_role
                
                # Test permission check
                result = rbac_manager.check_permission("test-key", Permission.READ)
                assert result is True
                
                result = rbac_manager.check_permission("test-key", Permission.ADMIN)
                assert result is True
                
                result = rbac_manager.check_permission("test-key", Permission.FINANCE_READ)
                assert result is False


def test_initialize_rbac(mock_redis):
    """Test the initialize_rbac function."""
    with patch.object(RBACManager, 'create_role') as mock_create_role:
        # Configure mock to always return True (successful role creation)
        mock_create_role.return_value = True
        
        # Initialize RBAC
        rbac_manager = initialize_rbac(mock_redis)
        
        # Verify all default roles were created
        assert mock_create_role.call_count >= 5  # At least 5 default roles


@patch('agentorchestrator.security.rbac.RBACManager')
def test_check_permission_function(mock_rbac_manager_class):
    """Test the check_permission function."""
    # Set up mocks
    mock_manager = MagicMock()
    mock_rbac_manager_class.return_value = mock_manager
    
    # Configure mock to return True for valid permission check
    mock_manager.check_permission.return_value = True
    
    # Test successful permission check
    result = check_permission(
        api_key="test-key",
        permission=Permission.READ,
        redis_client=MagicMock()
    )
    assert result is True
    
    # Configure mock to return False for invalid permission check
    mock_manager.check_permission.return_value = False
    
    # Test failed permission check
    with pytest.raises(HTTPException) as excinfo:
        check_permission(
            api_key="test-key",
            permission=Permission.ADMIN,
            redis_client=MagicMock()
        )
    assert excinfo.value.status_code == 403  # Forbidden 