"""
Role-Based Access Control (RBAC) for AORBIT.

This module provides a comprehensive RBAC system suitable for financial applications,
with fine-grained permissions, hierarchical roles, and resource-specific access controls.
"""

import json
import logging
from typing import Dict, List, Optional, Set, Union, Any
from fastapi import Depends, HTTPException, Request, Security, status
from redis import Redis

logger = logging.getLogger(__name__)


class Role:
    """Role definition for RBAC."""
    
    def __init__(
        self,
        name: str,
        description: str = "",
        permissions: List[str] = None,
        resources: List[str] = None,
        parent_roles: List[str] = None
    ):
        """Initialize a role.
        
        Args:
            name: Role name
            description: Role description
            permissions: List of permissions
            resources: List of resources this role can access
            parent_roles: List of parent role names
        """
        self.name = name
        self.description = description
        self.permissions = permissions or []
        self.resources = resources or []
        self.parent_roles = parent_roles or []


class EnhancedApiKey:
    """Enhanced API key with advanced access controls."""

    def __init__(
        self,
        key: str,
        name: str,
        description: str = "",
        roles: List[str] = None,
        rate_limit: int = 60,  # requests per minute
        expiration: Optional[int] = None,  # Unix timestamp when the key expires
        ip_whitelist: List[str] = None,  # List of allowed IP addresses
        user_id: Optional[str] = None,  # Associated user ID if applicable
        organization_id: Optional[str] = None,  # Associated organization
        metadata: Dict[str, Any] = None,
        is_active: bool = True
    ):
        """Initialize an EnhancedApiKey.
        
        Args:
            key: API key value
            name: API key name
            description: API key description
            roles: List of roles associated with the key
            rate_limit: Rate limit for API requests
            expiration: Expiration timestamp for the key
            ip_whitelist: List of allowed IP addresses
            user_id: Associated user ID
            organization_id: Associated organization ID
            metadata: Additional metadata for the key
            is_active: Whether the key is active
        """
        self.key = key
        self.name = name
        self.description = description
        self.roles = roles or []
        self.rate_limit = rate_limit
        self.expiration = expiration
        self.ip_whitelist = ip_whitelist or []
        self.user_id = user_id
        self.organization_id = organization_id
        self.metadata = metadata or {}
        self.is_active = is_active


class RBACManager:
    """Role-Based Access Control (RBAC) manager."""
    
    def __init__(self, redis_client: Redis):
        """Initialize the RBAC manager.
        
        Args:
            redis_client: Redis client for storing roles
        """
        self.redis = redis_client
        self._role_cache: Dict[str, Role] = {}
    
    def create_role(
        self, 
        name: str, 
        description: str = "", 
        permissions: List[str] = None, 
        resources: List[str] = None,
        parent_roles: List[str] = None
    ) -> Role:
        """Create a new role.
        
        Args:
            name: Role name
            description: Role description
            permissions: List of permissions
            resources: List of resources
            parent_roles: List of parent role names
            
        Returns:
            Created role
        """
        # Check if role already exists
        existing_role = self.get_role(name)
        if existing_role:
            return existing_role
            
        # Create new role
        role = Role(
            name=name,
            description=description,
            permissions=permissions or [],
            resources=resources or [],
            parent_roles=parent_roles or []
        )
        
        # Save to Redis
        role_key = f"role:{name}"
        role_data = {
            "name": name,
            "description": description,
            "permissions": permissions or [],
            "resources": resources or [],
            "parent_roles": parent_roles or []
        }
        
        try:
            self.redis.set(role_key, json.dumps(role_data))
            
            # Update roles set
            self.redis.sadd("roles", name)
            
            # Cache role
            self._role_cache[name] = role
            logger.info(f"Created role: {name}")
            return role
        except Exception as e:
            logger.error(f"Error creating role {name}: {e}")
            raise
    
    def get_role(self, role_name: str) -> Optional[Role]:
        """Get a role by name.
        
        Args:
            role_name: Name of the role to retrieve
            
        Returns:
            Role if found, None otherwise
        """
        # Try cache first
        if role_name in self._role_cache:
            return self._role_cache[role_name]
        
        try:
            # Get from Redis
            role_key = f"role:{role_name}"
            exists = self.redis.exists(role_key)
            
            if not exists:
                return None
                
            # Get role data
            role_json = self.redis.get(role_key)
            if not role_json:
                return None
            
            # Parse JSON
            role_data = json.loads(role_json)
            role = Role(
                name=role_name,
                description=role_data.get("description", ""),
                permissions=role_data.get("permissions", []),
                resources=role_data.get("resources", []),
                parent_roles=role_data.get("parent_roles", [])
            )
            
            # Cache role
            self._role_cache[role_name] = role
            return role
        except Exception as e:
            logger.error(f"Error retrieving role {role_name}: {e}")
            return None

    async def get_all_roles(self) -> List[Role]:
        """Get all roles.
        
        Returns:
            List of all roles
        """
        roles = []
        role_data = await self.redis.hgetall(self._roles_key)
        
        for role_json in role_data.values():
            try:
                role = Role.model_validate_json(role_json)
                roles.append(role)
                self._role_cache[role.name] = role
            except Exception:
                continue
                
        return roles

    async def delete_role(self, role_name: str) -> bool:
        """Delete a role.
        
        Args:
            role_name: Name of the role to delete
            
        Returns:
            True if the role was deleted, False otherwise
        """
        result = await self.redis.hdel(self._roles_key, role_name)
        if role_name in self._role_cache:
            del self._role_cache[role_name]
        return result > 0

    def get_effective_permissions(self, role_names: List[str]) -> Set[str]:
        """Get all effective permissions for a list of roles, including inherited permissions.
        
        Args:
            role_names: List of role names
            
        Returns:
            Set of all effective permissions
        """
        effective_permissions: Set[str] = set()
        processed_roles: Set[str] = set()
        
        def process_role(role_name: str):
            if role_name in processed_roles:
                return
            
            processed_roles.add(role_name)
            role = self.get_role(role_name)
            
            if not role:
                return
                
            # Add this role's permissions
            for perm in role.permissions:
                effective_permissions.add(perm)
            
            # Process parent roles recursively
            for parent in role.parent_roles:
                process_role(parent)
        
        # Process each role in the list
        for role_name in role_names:
            process_role(role_name)
            
        return effective_permissions

    def create_api_key(self, api_key: EnhancedApiKey) -> bool:
        """Create or update an API key.
        
        Args:
            api_key: API key definition
            
        Returns:
            True if successful
        """
        try:
            api_key_json = json.dumps(api_key.__dict__)
            self.redis.hset(self._api_keys_key, api_key.key, api_key_json)
            return True
        except Exception as e:
            logger.error(f"Error creating API key: {e}")
            return False

    def get_api_key(self, key: str) -> Optional[EnhancedApiKey]:
        """Get an API key by its value.
        
        Args:
            key: API key to get
            
        Returns:
            EnhancedApiKey if found, None otherwise
        """
        try:
            api_key_json = self.redis.hget(self._api_keys_key, key)
            if not api_key_json:
                return None
                
            api_key_data = json.loads(api_key_json)
            return EnhancedApiKey(**api_key_data)
        except Exception:
            return None

    async def delete_api_key(self, key: str) -> bool:
        """Delete an API key.
        
        Args:
            key: API key to delete
            
        Returns:
            True if deleted, False otherwise
        """
        result = await self.redis.hdel(self._api_keys_key, key)
        return result > 0

    async def has_permission(self, api_key: str, required_permission: str, 
                             resource_type: Optional[str] = None, 
                             resource_id: Optional[str] = None) -> bool:
        """Check if an API key has a specific permission.
        
        Args:
            api_key: API key value
            required_permission: Permission to check
            resource_type: Optional resource type
            resource_id: Optional resource ID
            
        Returns:
            True if the API key has the permission, False otherwise
        """
        key_data = await self.get_api_key(api_key)
        if not key_data or not key_data.is_active:
            return False
            
        # Get all permissions from all roles
        permissions = await self.get_effective_permissions(key_data.roles)
        
        # Admin permission grants everything
        if "admin:system" in permissions:
            return True
            
        # Check if the required permission is in the set
        if required_permission in permissions:
            return True
            
        return False


# Default roles definition
DEFAULT_ROLES = [
    {
        "name": "admin",
        "description": "Administrator with full access",
        "permissions": ["*"],
        "resources": ["*"],
        "parent_roles": []
    },
    {
        "name": "user",
        "description": "Standard user with limited access",
        "permissions": ["read", "execute"],
        "resources": ["workflow", "agent"],
        "parent_roles": []
    },
    {
        "name": "api",
        "description": "API access for integrations",
        "permissions": ["read", "write", "execute"],
        "resources": ["workflow", "agent"],
        "parent_roles": []
    },
    {
        "name": "guest",
        "description": "Guest with minimal access",
        "permissions": ["read"],
        "resources": ["workflow"],
        "parent_roles": []
    }
]


def initialize_rbac(redis_client) -> RBACManager:
    """Initialize RBAC with default roles.
    
    Args:
        redis_client: Redis client
        
    Returns:
        Initialized RBACManager
    """
    logger.info("Initializing RBAC system")
    rbac_manager = RBACManager(redis_client)
    
    # Create default roles if they don't exist
    for role_def in DEFAULT_ROLES:
        role_name = role_def["name"]
        if not rbac_manager.get_role(role_name):
            logger.info(f"Creating default role: {role_name}")
            rbac_manager.create_role(
                name=role_name,
                description=role_def["description"],
                permissions=role_def["permissions"],
                resources=role_def["resources"],
                parent_roles=role_def["parent_roles"]
            )
    
    return rbac_manager


# FastAPI security dependency
async def check_permission(
    request: Request,
    permission: str,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
) -> bool:
    """Check if the current request has the required permission.
    
    Args:
        request: FastAPI request
        permission: Required permission
        resource_type: Optional resource type
        resource_id: Optional resource ID
        
    Returns:
        True if authorized, raises HTTPException otherwise
    """
    if not hasattr(request.state, "api_key_data"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
        
    api_key_data = request.state.api_key_data
    rbac_manager = request.app.state.rbac_manager
    
    if not await rbac_manager.has_permission(
        api_key_data.key, permission, resource_type, resource_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permission denied: {permission} required",
        )
        
    return True 