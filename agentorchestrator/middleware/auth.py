"""Authentication middleware for AgentOrchestrator.

Implements API key authentication with role-based access control.
"""

import json
import logging
from collections.abc import Callable
from typing import Any

from fastapi import HTTPException, Request, status
from pydantic import BaseModel
from redis import Redis

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # Enable debug logging


class AuthConfig(BaseModel):
    """Configuration for authentication."""

    enabled: bool = True
    public_paths: list[str] = [
        "/",
        "/api/v1/health",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/openapi.json/",
    ]
    api_key_header: str = "X-API-Key"
    debug: bool = True  # Enable debug by default


class ApiKey(BaseModel):
    """API key model with role-based access."""

    key: str
    name: str
    roles: list[str] = ["read"]
    rate_limit: int = 60  # requests per minute


class AuthMiddleware:
    """API key authentication middleware."""

    def __init__(
        self,
        app: Callable,
        redis_client: Redis,
        config: AuthConfig | None = None,
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
        self.logger = logger

        # Verify Redis connection on initialization
        try:
            if not self.redis or not self.redis.ping():
                self.logger.error("Redis connection not available")
                raise ConnectionError("Redis connection not available")
        except Exception as e:
            self.logger.error(f"Redis error during initialization: {str(e)}")
            raise ConnectionError("Redis connection error")

    def invalidate_api_key(self, api_key: str) -> None:
        """Remove API key from Redis completely."""
        try:
            self.logger.debug(f"Attempting to invalidate API key: {api_key[:5]}...")

            # Check if key exists before removal
            exists_traditional = self.redis.hexists("api_keys", api_key)
            exists_enterprise = self.redis.exists(f"apikey:{api_key}")

            self.logger.debug(f"Key exists in traditional store: {exists_traditional}")
            self.logger.debug(f"Key exists in enterprise store: {exists_enterprise}")

            # Remove from traditional API keys store
            if exists_traditional:
                self.redis.hdel("api_keys", api_key)

            # Remove from enterprise security framework if it exists
            if exists_enterprise:
                self.redis.delete(f"apikey:{api_key}")
                self.redis.delete(f"apikey:{api_key}:metadata")

            self.logger.info(f"Successfully removed API key: {api_key[:5]}...")
        except Exception as e:
            self.logger.error(f"Error removing API key: {str(e)}")

    async def validate_api_key(self, api_key: str) -> dict[str, Any] | None:
        """Validate an API key directly against Redis on every call."""
        try:
            if not api_key:
                self.logger.debug("No API key provided")
                return None

            # Verify Redis connection
            if not self.redis.ping():
                self.logger.error("Redis connection failed")
                return None

            self.logger.debug(f"Validating API key: {api_key[:5]}...")

            # Check if key exists in either store first
            key_exists = self.redis.hexists("api_keys", api_key) or self.redis.exists(
                f"apikey:{api_key}"
            )
            if not key_exists:
                self.logger.warning(f"API key {api_key[:5]}... not found in any store")
                return None

            # Check traditional API keys store
            self.logger.debug("Checking traditional API keys store...")
            key_data = self.redis.hget("api_keys", api_key)

            if key_data:
                try:
                    parsed_data = json.loads(key_data)
                    if not isinstance(parsed_data, dict) or "key" not in parsed_data:
                        self.logger.error(
                            "Invalid key data format in traditional store"
                        )
                        return None
                    if parsed_data.get("key") != api_key:
                        self.logger.error("Key mismatch in traditional store")
                        return None
                    self.logger.debug("Found valid key in traditional store")
                    return parsed_data
                except json.JSONDecodeError:
                    self.logger.error("Invalid JSON in traditional store")
                    return None

            # Check enterprise security framework
            self.logger.debug("Checking enterprise security framework...")
            enterprise_key = self.redis.get(f"apikey:{api_key}")

            if not enterprise_key:
                self.logger.debug("Key not found in enterprise framework")
                return None

            metadata = self.redis.get(f"apikey:{api_key}:metadata")
            if not metadata:
                self.logger.debug("No metadata found for enterprise key")
                return None

            try:
                metadata_dict = json.loads(metadata)
                if not isinstance(metadata_dict, dict):
                    self.logger.error("Invalid metadata format in enterprise store")
                    return None

                key_data = {
                    "key": api_key,  # Store the original key for verification
                    "name": metadata_dict.get("name", "unknown"),
                    "roles": [metadata_dict.get("role", "user")],
                    "rate_limit": 100,
                }
                self.logger.debug(f"Found valid key in enterprise store: {key_data}")
                return key_data

            except json.JSONDecodeError:
                self.logger.error("Invalid JSON in enterprise metadata")
                return None

        except Exception as e:
            self.logger.error(f"Error validating API key: {str(e)}")
            return None

        return None

    async def check_auth(self, request: Request) -> dict[str, Any] | None:
        """Check if request is authenticated.

        Args:
            request: FastAPI request object

        Returns:
            Optional[Dict[str, Any]]: API key data if authenticated

        Raises:
            HTTPException: If authentication fails
        """
        try:
            # Skip auth for public paths
            if request.url.path in self.config.public_paths:
                self.logger.debug(f"Skipping auth for public path: {request.url.path}")
                return None

            # Check for API key in header
            api_key = request.headers.get(self.config.api_key_header)
            if not api_key:
                self.logger.warning(
                    f"Missing API key for {request.method} {request.url.path}",
                )
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="API key is missing",
                )

            self.logger.debug(
                f"Processing request {request.method} {request.url.path} with key: {api_key[:5]}..."
            )

            # Handle logout - remove key and return unauthorized
            if request.url.path.endswith("/logout"):
                self.logger.debug("Processing logout request")
                self.invalidate_api_key(api_key)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Logged out successfully",
                )

            # Validate API key directly against Redis
            api_key_data = await self.validate_api_key(api_key)
            if not api_key_data:
                self.logger.warning(
                    f"Invalid API key {api_key[:5]}... for {request.method} {request.url.path}",
                )
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid API key",
                )

            # Verify the key in the data matches the provided key
            if api_key_data.get("key") != api_key:
                self.logger.warning(
                    "Key mismatch: stored key does not match provided key"
                )
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid API key",
                )

            self.logger.debug(
                f"Successfully authenticated request with key: {api_key[:5]}..."
            )
            return api_key_data

        except Exception as e:
            if not isinstance(e, HTTPException):
                self.logger.error(f"Authentication error: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Authentication system error",
                )
            raise

    async def send_error_response(
        self, send: Callable, status_code: int, detail: str
    ) -> None:
        """Send an error response and properly close the connection."""
        response = {
            "success": False,
            "error": {
                "code": status_code,
                "message": detail,
            },
        }

        # Send response headers
        await send(
            {
                "type": "http.response.start",
                "status": status_code,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"Cache-Control", b"no-store, no-cache, must-revalidate, private"),
                    (b"Pragma", b"no-cache"),
                    (b"Expires", b"0"),
                ],
            }
        )

        # Send response body
        await send(
            {
                "type": "http.response.body",
                "body": json.dumps(response).encode(),
                "more_body": False,
            }
        )

    async def __call__(self, scope, receive, send):
        """Process a request.

        Args:
            scope: ASGI scope
            receive: ASGI receive function
            send: ASGI send function
        """
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        request = Request(scope)

        try:
            # First check if it's a public path
            if request.url.path in self.config.public_paths:
                self.logger.debug(f"Skipping auth for public path: {request.url.path}")

                # Add basic security headers even for public paths
                async def public_send_wrapper(message):
                    if message["type"] == "http.response.start":
                        headers = list(message.get("headers", []))
                        headers.extend(
                            [
                                (
                                    b"Cache-Control",
                                    b"no-store, no-cache, must-revalidate, private",
                                ),
                                (b"Pragma", b"no-cache"),
                                (b"Expires", b"0"),
                            ]
                        )
                        message["headers"] = headers
                    await send(message)

                return await self.app(scope, receive, public_send_wrapper)

            # For all other paths, authentication is required
            api_key = request.headers.get(self.config.api_key_header)
            if not api_key:
                self.logger.warning(
                    f"Missing API key for {request.method} {request.url.path}"
                )
                response = {
                    "success": False,
                    "error": {
                        "code": status.HTTP_401_UNAUTHORIZED,
                        "message": "API key is missing",
                    },
                }
                await send(
                    {
                        "type": "http.response.start",
                        "status": status.HTTP_401_UNAUTHORIZED,
                        "headers": [
                            (b"content-type", b"application/json"),
                            (
                                b"Cache-Control",
                                b"no-store, no-cache, must-revalidate, private",
                            ),
                            (b"Pragma", b"no-cache"),
                            (b"Expires", b"0"),
                        ],
                    }
                )
                await send(
                    {
                        "type": "http.response.body",
                        "body": json.dumps(response).encode(),
                    }
                )
                return None

            # Direct Redis check for the key
            try:
                # Verify Redis connection first
                if not self.redis.ping():
                    self.logger.error("Redis connection failed")
                    response = {
                        "success": False,
                        "error": {
                            "code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                            "message": "Authentication system error",
                        },
                    }
                    await send(
                        {
                            "type": "http.response.start",
                            "status": status.HTTP_500_INTERNAL_SERVER_ERROR,
                            "headers": [
                                (b"content-type", b"application/json"),
                                (
                                    b"Cache-Control",
                                    b"no-store, no-cache, must-revalidate, private",
                                ),
                                (b"Pragma", b"no-cache"),
                                (b"Expires", b"0"),
                            ],
                        }
                    )
                    await send(
                        {
                            "type": "http.response.body",
                            "body": json.dumps(response).encode(),
                        }
                    )
                    return None

                # Check if key exists in either store
                key_exists = self.redis.hexists(
                    "api_keys", api_key
                ) or self.redis.exists(f"apikey:{api_key}")
                if not key_exists:
                    self.logger.warning(
                        f"API key {api_key[:5]}... not found in any store"
                    )
                    response = {
                        "success": False,
                        "error": {
                            "code": status.HTTP_401_UNAUTHORIZED,
                            "message": "Invalid API key",
                        },
                    }
                    await send(
                        {
                            "type": "http.response.start",
                            "status": status.HTTP_401_UNAUTHORIZED,
                            "headers": [
                                (b"content-type", b"application/json"),
                                (
                                    b"Cache-Control",
                                    b"no-store, no-cache, must-revalidate, private",
                                ),
                                (b"Pragma", b"no-cache"),
                                (b"Expires", b"0"),
                            ],
                        }
                    )
                    await send(
                        {
                            "type": "http.response.body",
                            "body": json.dumps(response).encode(),
                        }
                    )
                    return None

                # Validate API key
                api_key_data = await self.validate_api_key(api_key)
                if not api_key_data:
                    self.logger.warning(
                        f"Invalid API key {api_key[:5]}... for {request.method} {request.url.path}"
                    )
                    response = {
                        "success": False,
                        "error": {
                            "code": status.HTTP_401_UNAUTHORIZED,
                            "message": "Invalid API key",
                        },
                    }
                    await send(
                        {
                            "type": "http.response.start",
                            "status": status.HTTP_401_UNAUTHORIZED,
                            "headers": [
                                (b"content-type", b"application/json"),
                                (
                                    b"Cache-Control",
                                    b"no-store, no-cache, must-revalidate, private",
                                ),
                                (b"Pragma", b"no-cache"),
                                (b"Expires", b"0"),
                            ],
                        }
                    )
                    await send(
                        {
                            "type": "http.response.body",
                            "body": json.dumps(response).encode(),
                        }
                    )
                    return None

                # Store API key data in request state
                request.state.api_key = api_key_data

                # Wrap the send function to add security headers
                async def send_wrapper(message):
                    if message["type"] == "http.response.start":
                        headers = list(message.get("headers", []))
                        headers.extend(
                            [
                                (
                                    b"Cache-Control",
                                    b"no-store, no-cache, must-revalidate, private",
                                ),
                                (b"Pragma", b"no-cache"),
                                (b"Expires", b"0"),
                                (b"X-Content-Type-Options", b"nosniff"),
                                (b"X-Frame-Options", b"DENY"),
                                (b"X-XSS-Protection", b"1; mode=block"),
                            ]
                        )
                        message["headers"] = headers
                    await send(message)

                # Proceed with the request
                return await self.app(scope, receive, send_wrapper)

            except Exception as e:
                self.logger.error(f"Redis error during authentication: {str(e)}")
                response = {
                    "success": False,
                    "error": {
                        "code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                        "message": "Authentication system error",
                    },
                }
                await send(
                    {
                        "type": "http.response.start",
                        "status": status.HTTP_500_INTERNAL_SERVER_ERROR,
                        "headers": [
                            (b"content-type", b"application/json"),
                            (
                                b"Cache-Control",
                                b"no-store, no-cache, must-revalidate, private",
                            ),
                            (b"Pragma", b"no-cache"),
                            (b"Expires", b"0"),
                        ],
                    }
                )
                await send(
                    {
                        "type": "http.response.body",
                        "body": json.dumps(response).encode(),
                    }
                )
                return None

        except Exception as e:
            self.logger.error(f"Unexpected error during authentication: {str(e)}")
            response = {
                "success": False,
                "error": {
                    "code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                    "message": "Internal server error",
                },
            }
            await send(
                {
                    "type": "http.response.start",
                    "status": status.HTTP_500_INTERNAL_SERVER_ERROR,
                    "headers": [
                        (b"content-type", b"application/json"),
                        (
                            b"Cache-Control",
                            b"no-store, no-cache, must-revalidate, private",
                        ),
                        (b"Pragma", b"no-cache"),
                        (b"Expires", b"0"),
                    ],
                }
            )
            await send(
                {
                    "type": "http.response.body",
                    "body": json.dumps(response).encode(),
                }
            )
            return None
