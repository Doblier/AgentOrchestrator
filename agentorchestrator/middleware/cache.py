"""Caching middleware for AgentOrchestrator.

Implements response caching using Redis.
"""

import json
from collections.abc import Callable
from typing import Any

from fastapi import Request
from pydantic import BaseModel
from redis import Redis
from starlette.types import Message


class CacheConfig(BaseModel):
    """Configuration for caching."""

    ttl: int = 300  # 5 minutes
    enabled: bool = True
    excluded_paths: list[str] = ["/api/v1/health"]


class ResponseCache:
    """Redis-based response cache."""

    def __init__(
        self,
        app: Callable,
        redis_client: Redis,
        config: CacheConfig | None = None,
    ):
        """Initialize cache.

        Args:
            app: ASGI application
            redis_client: Redis client instance
            config: Cache configuration
        """
        self.app = app
        self.redis = redis_client
        self.config = config or CacheConfig()

    async def _get_request_body(self, request: Request) -> str:
        """Get request body as string.

        Args:
            request: FastAPI request

        Returns:
            str: Request body as string
        """
        body = await request.body()
        return body.decode() if body else ""

    async def _get_cache_key(self, request: Request) -> str:
        """Generate cache key from request.

        Args:
            request: FastAPI request

        Returns:
            str: Cache key
        """
        # Include API key in cache key to ensure different keys get different caches
        api_key = request.headers.get("X-API-Key", "")

        # For POST/PUT requests, include body in cache key
        body = ""
        if request.method in ["POST", "PUT"]:
            body = await self._get_request_body(request)

        return f"cache:{api_key}:{request.method}:{request.url.path}:{request.query_params}:{body}"

    async def get_cached_response(self, request: Request) -> dict[str, Any] | None:
        """Get cached response if available.

        Args:
            request: FastAPI request

        Returns:
            Optional[Dict[str, Any]]: Cached response data if found
        """
        if not self.config.enabled:
            return None

        if request.url.path in self.config.excluded_paths:
            return None

        key = await self._get_cache_key(request)
        cached = self.redis.get(key)

        if cached:
            return json.loads(cached)
        return None

    async def cache_response(
        self,
        request: Request,
        response_data: dict[str, Any],
    ) -> None:
        """Cache response for future requests.

        Args:
            request: FastAPI request
            response_data: Response data to cache
        """
        if not self.config.enabled:
            return

        if request.url.path in self.config.excluded_paths:
            return

        key = await self._get_cache_key(request)
        self.redis.setex(key, self.config.ttl, json.dumps(response_data))

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
        cached_data = await self.get_cached_response(request)

        if cached_data:

            async def cached_send(message: Message) -> None:
                if message["type"] == "http.response.start":
                    message.update(
                        {
                            "status": cached_data["status_code"],
                            "headers": [
                                (k.encode(), v.encode())
                                for k, v in cached_data["headers"].items()
                            ],
                        },
                    )
                elif message["type"] == "http.response.body":
                    message.update({"body": cached_data["content"].encode()})
                await send(message)

            return await self.app(scope, receive, cached_send)

        # Store the original request body
        body = []

        async def receive_with_store():
            message = await receive()
            if message["type"] == "http.request":
                body.append(message.get("body", b""))
            return message

        response_body = []
        response_headers = []
        response_status = 0

        async def capture_response(message: Message) -> None:
            if message["type"] == "http.response.start":
                nonlocal response_status, response_headers
                response_status = message["status"]
                response_headers = message["headers"]
            elif message["type"] == "http.response.body":
                response_body.append(message["body"])
            await send(message)

        await self.app(scope, receive_with_store, capture_response)

        # Only cache successful responses
        if response_status < 400:
            response_data = {
                "content": b"".join(response_body).decode(),
                "status_code": response_status,
                "headers": {k.decode(): v.decode() for k, v in response_headers},
                "media_type": "application/json",
            }
            await self.cache_response(request, response_data)
