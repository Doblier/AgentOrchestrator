"""Authentication middleware for AgentOrchestrator.

Implements API key authentication with role-based access control.
"""

import json
from typing import Optional, Callable, List, Dict, Any
from fastapi import Request, HTTPException, status
from redis import Redis
from pydantic import BaseModel


class AuthConfig(BaseModel):
    """Configuration for authentication."""

    enabled: bool = True
    public_paths: List[str] = [
        "/",
        "/api/v1/health",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/openapi.json/",
    ]
    api_key_header: str = "X-API-Key"
    cache_ttl: int = 300  # 5 minutes


class ApiKey(BaseModel):
    """API key model with role-based access."""

    key: str
    name: str
    roles: List[str] = ["read"]
    rate_limit: int = 60  # requests per minute


class AuthMiddleware:
    """API key authentication middleware."""

    def __init__(
        self, app: Callable, redis_client: Redis, config: Optional[AuthConfig] = None
    ):
        """Initialize auth middleware.

        Args:
            app: ASGI application
            redis_client: Redis client instance
            config: Auth configuration
        """
        self.app = app
        self.redis = redis_client
        self.config = config or AuthConfig()

    def _get_cache_key(self, api_key: str) -> str:
        """Generate cache key for API key.

        Args:
            api_key: API key to cache

        Returns:
            str: Cache key
        """
        return f"auth:api_key:{api_key}"

    async def validate_api_key(self, api_key: str) -> Optional[Dict[str, Any]]:
        """Validate API key and return associated data.

        Args:
            api_key: API key to validate

        Returns:
            Optional[Dict[str, Any]]: API key data if valid
        """
        try:
            # Check cache first
            cache_key = self._get_cache_key(api_key)
            cached = self.redis.get(cache_key)

            if cached:
                return json.loads(cached)

            # Check against stored API keys
            key_data = self.redis.hget("api_keys", api_key)
            if key_data:
                api_key_data = json.loads(key_data)
                # Cache for future requests
                self.redis.setex(cache_key, self.config.cache_ttl, key_data)
                return api_key_data

            return None
        except json.JSONDecodeError:
            return None

    async def check_auth(self, request: Request) -> Optional[Dict[str, Any]]:
        """Check if request is authenticated.

        Args:
            request: FastAPI request

        Returns:
            Optional[Dict[str, Any]]: API key data if authenticated

        Raises:
            HTTPException: If authentication fails
        """
        if not self.config.enabled:
            return None

        # Skip auth for public paths and OPTIONS requests
        if request.url.path in self.config.public_paths or request.method == "OPTIONS":
            return None

        # Get API key from header
        api_key = request.headers.get(self.config.api_key_header)
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing API key"
            )

        # Validate API key
        api_key_data = await self.validate_api_key(api_key)
        if not api_key_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key"
            )

        return api_key_data

    async def __call__(self, scope, receive, send):
        """ASGI middleware handler.

        Args:
            scope: ASGI scope
            receive: ASGI receive function
            send: ASGI send function

        Returns:
            Response from next middleware
        """
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        request = Request(scope)

        try:
            api_key_data = await self.check_auth(request)

            # Add API key data to request state if authenticated
            if api_key_data:
                request.state.api_key = api_key_data

            return await self.app(scope, receive, send)

        except HTTPException as exc:
            # Handle unauthorized response
            response = {"detail": exc.detail, "status_code": exc.status_code}

            await send(
                {
                    "type": "http.response.start",
                    "status": exc.status_code,
                    "headers": [
                        (b"content-type", b"application/json"),
                    ],
                }
            )

            await send(
                {
                    "type": "http.response.body",
                    "body": json.dumps(response).encode(),
                }
            )
            return
