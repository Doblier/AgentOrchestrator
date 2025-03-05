"""
Role-Based Access Control (RBAC) for AORBIT.

This module provides a comprehensive RBAC system suitable for financial applications,
with fine-grained permissions, hierarchical roles, and resource-specific access controls.
"""

import json
import logging
from typing import Any
import time
from datetime import datetime, timezone, timedelta
import secrets

from fastapi import Request
from redis import Redis

logger = logging.getLogger(__name__)


class Role:
    """Role definition for RBAC."""

    def __init__(
        self,
        name: str,
        description: str = "",
        permissions: list[str] = None,
        resources: list[str] = None,
        parent_roles: list[str] = None,
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
        roles: list[str] = None,
        rate_limit: int = 60,  # requests per minute
        expiration: int | None = None,  # Unix timestamp when the key expires
        ip_whitelist: list[str] = None,  # List of allowed IP addresses
        user_id: str | None = None,  # Associated user ID if applicable
        organization_id: str | None = None,  # Associated organization
        metadata: dict[str, Any] = None,
        is_active: bool = True,
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
        self._role_cache: dict[str, Role] = {}
        self._roles_key = "rbac:roles"
        self._api_keys_key = "rbac:api_keys"
        self._api_key_names_key = "rbac:api_key_names"

    async def create_role(
        self,
        name: str,
        description: str = "",
        permissions: list[str] = None,
        resources: list[str] = None,
        parent_roles: list[str] = None,
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
        existing_role = await self.get_role(name)
        if existing_role:
            return existing_role

        # Create new role
        role = Role(
            name=name,
            description=description,
            permissions=permissions or [],
            resources=resources or [],
            parent_roles=parent_roles or [],
        )

        # Save to Redis
        role_key = f"role:{name}"
        role_data = {
            "name": name,
            "description": description,
            "permissions": permissions or [],
            "resources": resources or [],
            "parent_roles": parent_roles or [],
        }

        try:
            # Use Redis pipeline for atomic operations
            pipe = await self.redis.pipeline()
            await pipe.set(role_key, json.dumps(role_data))
            await pipe.sadd("roles", name)
            await pipe.execute()

            # Cache role
            self._role_cache[name] = role
            logger.info(f"Created role: {name}")
            return role
        except Exception as e:
            logger.error(f"Error creating role {name}: {e}")
            raise

    async def get_role(self, role_name: str) -> Role | None:
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
            exists = await self.redis.exists(role_key)

            if not exists:
                return None

            # Get role data
            role_json = await self.redis.get(role_key)
            if not role_json:
                return None

            # Parse JSON
            role_data = json.loads(role_json)
            role = Role(
                name=role_name,
                description=role_data.get("description", ""),
                permissions=role_data.get("permissions", []),
                resources=role_data.get("resources", []),
                parent_roles=role_data.get("parent_roles", []),
            )

            # Cache role
            self._role_cache[role_name] = role
            return role
        except Exception as e:
            logger.error(f"Error retrieving role {role_name}: {e}")
            return None

    async def get_effective_permissions(self, role_names: list[str]) -> set[str]:
        """Get all effective permissions for a list of roles, including inherited permissions.

        Args:
            role_names: List of role names

        Returns:
            Set of all effective permissions
        """
        effective_permissions: set[str] = set()
        processed_roles: set[str] = set()

        async def process_role(role_name: str):
            if role_name in processed_roles:
                return

            processed_roles.add(role_name)
            role = await self.get_role(role_name)
            if not role:
                return

            # Add direct permissions
            effective_permissions.update(role.permissions)

            # Process parent roles
            for parent_role in role.parent_roles:
                await process_role(parent_role)

        # Process all roles
        for role_name in role_names:
            await process_role(role_name)

        return effective_permissions

    async def create_api_key(
        self,
        name: str,
        roles: list[str] | None = None,
        description: str | None = None,
        rate_limit: int = 100,
        expires_in: int | None = None,
    ) -> EnhancedApiKey:
        """Create a new API key.

        Args:
            name: Name of the API key
            roles: List of role names to assign
            description: Optional description
            rate_limit: Rate limit per minute
            expires_in: Optional expiration time in seconds

        Returns:
            The created API key

        Raises:
            ValueError: If the API key name already exists
        """
        roles = roles or []
        description = description or ""

        # Check if API key name already exists
        exists = await self.redis.sismember(self._api_key_names_key, name)
        if exists:
            raise ValueError(f"API key name '{name}' already exists")

        # Create API key object
        expiration = None
        if expires_in:
            expiration = int((datetime.now(timezone.utc) + timedelta(seconds=expires_in)).timestamp())

        api_key = EnhancedApiKey(
            key=f"ao-{secrets.token_urlsafe(32)}",
            name=name,
            roles=roles,
            description=description,
            rate_limit=rate_limit,
            expiration=expiration,
        )

        # Convert to JSON for storage
        api_key_dict = {
            "key": api_key.key,
            "name": api_key.name,
            "description": api_key.description,
            "roles": api_key.roles,
            "rate_limit": api_key.rate_limit,
            "expiration": api_key.expiration,
            "ip_whitelist": api_key.ip_whitelist,
            "user_id": api_key.user_id,
            "organization_id": api_key.organization_id,
            "metadata": api_key.metadata,
            "is_active": api_key.is_active,
        }
        api_key_json = json.dumps(api_key_dict)

        # Use pipeline for atomic operations
        pipe = await self.redis.pipeline()
        await pipe.hset(self._api_keys_key, api_key.key, api_key_json)
        await pipe.sadd(self._api_key_names_key, name)
        await pipe.execute()

        return api_key

    async def get_api_key(self, key: str) -> EnhancedApiKey | None:
        """Get API key data.

        Args:
            key: API key to retrieve

        Returns:
            API key data if found, None otherwise
        """
        try:
            # Get from Redis
            key_data = await self.redis.hget(self._api_keys_key, key)
            if not key_data:
                return None

            # Parse JSON
            data = json.loads(key_data)
            return EnhancedApiKey(
                key=data["key"],
                name=data["name"],
                roles=data["roles"],
                user_id=data.get("user_id"),
                rate_limit=data.get("rate_limit", 60),
                expiration=data.get("expiration"),
                ip_whitelist=data.get("ip_whitelist", []),
                organization_id=data.get("organization_id"),
                metadata=data.get("metadata", {}),
                is_active=data.get("is_active", True),
            )
        except Exception as e:
            logger.error(f"Error retrieving API key: {e}")
            return None

    async def has_permission(
        self,
        api_key: str,
        permission: str,
        resource_type: str | None = None,
        resource_id: str | None = None,
    ) -> bool:
        """Check if an API key has a specific permission.

        Args:
            api_key: API key to check
            permission: Permission to check
            resource_type: Optional resource type
            resource_id: Optional resource ID

        Returns:
            True if the API key has the permission
        """
        try:
            # Get API key data
            api_key_data = await self.redis.hget(self._api_keys_key, api_key)
            if not api_key_data:
                return False

            # Parse API key data
            api_key_info = json.loads(api_key_data)
            if not api_key_info.get("is_active", True):
                return False

            # Check expiration
            expiration = api_key_info.get("expiration")
            if expiration and time.time() > expiration:
                return False

            # Get roles
            roles = api_key_info.get("roles", [])
            if not roles:
                return False

            # Check each role's permissions
            for role_name in roles:
                role = await self.get_role(role_name)
                if not role:
                    continue

                # Check direct permissions
                if permission in role.permissions:
                    return True

                # Check resource-specific permissions
                if resource_type and resource_id:
                    resource_permission = f"{permission}:{resource_type}:{resource_id}"
                    if resource_permission in role.permissions:
                        return True

                # Check parent roles
                for parent_role_name in role.parent_roles:
                    parent_role = await self.get_role(parent_role_name)
                    if parent_role and permission in parent_role.permissions:
                        return True

            return False
        except Exception as e:
            logger.error(f"Error checking permission: {e}")
            return False


# Default roles definition
DEFAULT_ROLES = [
    {
        "name": "admin",
        "description": "Administrator with full access",
        "permissions": ["*"],
        "resources": ["*"],
        "parent_roles": [],
    },
    {
        "name": "user",
        "description": "Standard user with limited access",
        "permissions": ["read", "execute"],
        "resources": ["workflow", "agent"],
        "parent_roles": [],
    },
    {
        "name": "api",
        "description": "API access for integrations",
        "permissions": ["read", "write", "execute"],
        "resources": ["workflow", "agent"],
        "parent_roles": [],
    },
    {
        "name": "guest",
        "description": "Guest with minimal access",
        "permissions": ["read"],
        "resources": ["workflow"],
        "parent_roles": [],
    },
]


async def initialize_rbac(redis_client: Redis) -> RBACManager:
    """Initialize the RBAC manager.

    Args:
        redis_client: Redis client instance

    Returns:
        Initialized RBAC manager
    """
    return RBACManager(redis_client)


async def check_permission(
    request: Request,
    permission: str,
    resource_type: str | None = None,
    resource_id: str | None = None,
) -> bool:
    """Check if the current request has the required permission.

    Args:
        request: Current request
        permission: Required permission
        resource_type: Optional resource type
        resource_id: Optional resource ID

    Returns:
        True if authorized, False otherwise
    """
    # Get RBAC manager from request state
    if not hasattr(request.state, "rbac_manager"):
        return False

    # Get API key from request state
    if not hasattr(request.state, "api_key"):
        return False

    return await request.state.rbac_manager.has_permission(
        request.state.api_key,
        permission,
        resource_type,
        resource_id,
    )
