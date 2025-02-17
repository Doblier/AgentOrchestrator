"""Rate limiting middleware for AgentOrchestrator.

Uses Redis to implement a sliding window rate limit.
"""
import time
from typing import Optional, Callable
from fastapi import Request, HTTPException, status
from redis import Redis
from pydantic import BaseModel


class RateLimitConfig(BaseModel):
    """Configuration for rate limiting."""
    requests_per_minute: int = 60
    burst_limit: int = 100
    enabled: bool = True


class RateLimiter:
    """Redis-based rate limiter using sliding window."""
    
    def __init__(self, app: Callable, redis_client: Redis, config: Optional[RateLimitConfig] = None):
        """Initialize rate limiter.
        
        Args:
            app: ASGI application
            redis_client: Redis client instance
            config: Rate limit configuration
        """
        self.app = app
        self.redis = redis_client
        self.config = config or RateLimitConfig()

    async def check_rate_limit(self, request: Request) -> None:
        """Check if request should be rate limited.
        
        Args:
            request: FastAPI request object
            
        Raises:
            HTTPException: If rate limit is exceeded
        """
        if not self.config.enabled:
            return

        # Get client IP
        client_ip = request.client.host
        current_time = int(time.time())
        key = f"rate_limit:{client_ip}"
        
        # Use pipeline for atomic operations
        pipe = self.redis.pipeline()
        
        # Clean old requests
        pipe.zremrangebyscore(key, 0, current_time - 60)
        
        # Count requests in last minute
        pipe.zcard(key)
        
        # Add current request
        pipe.zadd(key, {str(current_time): current_time})
        
        # Set expiry
        pipe.expire(key, 60)
        
        # Execute pipeline
        _, request_count, *_ = pipe.execute()
        
        if request_count > self.config.requests_per_minute:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "Rate limit exceeded",
                    "limit": self.config.requests_per_minute,
                    "reset": 60 - (current_time % 60)
                }
            )

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
        await self.check_rate_limit(request)
        return await self.app(scope, receive, send) 