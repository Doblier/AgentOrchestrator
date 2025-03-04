"""
Main entry point for the AgentOrchestrator application.
"""

import json
import logging
import os
import signal
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Security, status
from fastapi.security import APIKeyHeader
from pydantic_settings import BaseSettings
from redis import Redis
from redis.exceptions import ConnectionError

from agentorchestrator.api.base import router as base_router
from agentorchestrator.api.routes import router as api_router
from agentorchestrator.batch.processor import BatchProcessor
from agentorchestrator.middleware.auth import AuthConfig, AuthMiddleware
from agentorchestrator.middleware.cache import CacheConfig, ResponseCache
from agentorchestrator.middleware.metrics import MetricsConfig, MetricsMiddleware
from agentorchestrator.middleware.rate_limiter import RateLimitConfig, RateLimiter

# Load environment variables
env_path = Path(".env")
load_dotenv(dotenv_path=env_path)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# API Key security scheme
API_KEY_NAME = os.getenv("AUTH_API_KEY_HEADER", "X-API-Key")
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=True)


class Settings(BaseSettings):
    """Application settings."""

    app_name: str = "AORBIT"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8000


settings = Settings()


def initialize_api_keys(redis_client: Redis) -> None:
    """Initialize default API key in Redis.

    Args:
        redis_client: Redis client instance
    """
    default_key = os.getenv("AUTH_DEFAULT_KEY")
    if not default_key:
        logger.warning("No default API key configured")
        return

    # Create default API key
    api_key = {
        "key": default_key,
        "name": "default",
        "roles": ["read", "write"],
        "rate_limit": 100,
    }

    try:
        # Store in Redis
        redis_client.hset("api_keys", default_key, json.dumps(api_key))
        # Verify storage
        stored_key = redis_client.hget("api_keys", default_key)
        if stored_key:
            logger.info("Successfully initialized default API key")
        else:
            logger.error("Failed to store API key in Redis")
    except Exception as e:
        logger.error(f"Error initializing API key: {str(e)}")
        raise


def create_redis_client(max_retries=5, retry_delay=2):
    """Create Redis client with retries.

    Args:
        max_retries: Maximum number of connection attempts
        retry_delay: Delay between retries in seconds

    Returns:
        Redis: Connected Redis client

    Raises:
        ConnectionError: If unable to connect after retries
    """
    for attempt in range(max_retries):
        try:
            client = Redis(
                host=os.getenv("REDIS_HOST", "localhost"),
                port=int(os.getenv("REDIS_PORT", "6379")),
                db=int(os.getenv("REDIS_DB", "0")),
                decode_responses=True,
            )
            # Test connection
            client.ping()
            logger.info("Successfully connected to Redis")
            return client
        except ConnectionError:
            if attempt == max_retries - 1:
                logger.error(
                    "Failed to connect to Redis after %d attempts",
                    max_retries,
                )
                raise
            logger.warning(
                "Redis connection attempt %d failed, retrying in %d seconds...",
                attempt + 1,
                retry_delay,
            )
            time.sleep(retry_delay)


# Create Redis client
try:
    redis_client = create_redis_client()
    if not redis_client:
        logger.error("Failed to create Redis client")
        raise ConnectionError("Redis client creation failed")

    # Test connection
    if not redis_client.ping():
        logger.error("Redis ping failed")
        raise ConnectionError("Redis ping failed")

    # Initialize API keys
    initialize_api_keys(redis_client)
    # Create batch processor
    batch_processor = BatchProcessor(redis_client)
    logger.info("Redis features initialized successfully")
except ConnectionError as e:
    logger.error(f"Redis connection error: {str(e)}")
    logger.warning(
        "Starting without Redis features (auth, cache, rate limiting, batch processing)",
    )
    redis_client = None
    batch_processor = None
except Exception as e:
    logger.error(f"Unexpected error during Redis initialization: {str(e)}")
    logger.warning(
        "Starting without Redis features (auth, cache, rate limiting, batch processing)",
    )
    redis_client = None
    batch_processor = None


# Handle graceful shutdown
def handle_shutdown(signum, frame):
    """Handle shutdown signals."""
    logger.info("Received shutdown signal, stopping server...")
    sys.exit(0)


signal.signal(signal.SIGINT, handle_shutdown)
signal.signal(signal.SIGTERM, handle_shutdown)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan events for the FastAPI application."""
    # Startup
    logger.info("Starting AORBIT...")

    # Initialize enterprise security framework
    if redis_client:
        from agentorchestrator.security.integration import initialize_security

        security = initialize_security(redis_client)
        app.state.security = security
        logger.info("Enterprise security framework initialized")
    else:
        logger.warning("Redis client not available, security features will be limited")

    # Start batch processor if available
    if batch_processor:
        # Start batch processor
        async def get_workflow_func(agent_name: str):
            """Get workflow function for agent."""
            try:
                module = __import__(
                    f"src.routes.{agent_name}.ao_agent",
                    fromlist=["workflow"],
                )
                return module.workflow
            except ImportError:
                return None

        await batch_processor.start_processing(get_workflow_func)
        logger.info("Batch processor started")

    # Startup complete
    yield

    # Shutdown
    logger.info("Shutting down AORBIT...")

    # Stop batch processor if it was started
    if batch_processor:
        await batch_processor.stop_processing()
        logger.info("Batch processor stopped")


app = FastAPI(
    title=settings.app_name,
    description="A powerful agent orchestration framework for financial applications",
    version="0.2.0",
    debug=settings.debug,
    lifespan=lifespan,
    openapi_tags=[
        {"name": "Agents", "description": "Agent workflow operations"},
        {"name": "Finance", "description": "Financial operations"},
    ],
)

# Add security scheme to OpenAPI
app.add_api_key_to_swagger = True


async def get_api_key(api_key: str = Security(api_key_header)) -> str:
    """Dependency for API key authentication."""
    return api_key


# Add middlewares only if Redis is available
if redis_client:
    auth_config = AuthConfig(
        enabled=os.getenv("AUTH_ENABLED", "true").lower() == "true",
        api_key_header=API_KEY_NAME,
        public_paths=[
            "/",
            "/api/v1/health",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/openapi.json/",
            "/metrics",
        ],
    )

    rate_limit_config = RateLimitConfig(
        requests_per_minute=int(os.getenv("RATE_LIMIT_RPM", "60")),
        burst_limit=int(os.getenv("RATE_LIMIT_BURST", "100")),
        enabled=os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true",
    )

    cache_config = CacheConfig(
        ttl=int(os.getenv("CACHE_TTL", "300")),
        enabled=os.getenv("CACHE_ENABLED", "true").lower() == "true",
        excluded_paths=["/api/v1/health", "/metrics"],
    )

    # Add middlewares in correct order - auth must be first
    app.add_middleware(AuthMiddleware, redis_client=redis_client, config=auth_config)
    app.add_middleware(RateLimiter, redis_client=redis_client, config=rate_limit_config)
    app.add_middleware(ResponseCache, redis_client=redis_client, config=cache_config)

# Add metrics middleware (doesn't require Redis)
metrics_config = MetricsConfig(
    enabled=os.getenv("METRICS_ENABLED", "true").lower() == "true",
    prefix=os.getenv("METRICS_PREFIX", "ao"),
)
app.add_middleware(MetricsMiddleware, config=metrics_config)

# Initialize enterprise security framework after middleware setup
if redis_client:
    from agentorchestrator.security.integration import initialize_security

    security = initialize_security(redis_client)
    app.state.security = security
    logger.info("Enterprise security framework initialized")

# Add security dependency to all routes in the API router
for route in api_router.routes:
    route.dependencies.append(Depends(get_api_key))

# Add security to dynamic agent routes
for route in api_router.routes:
    if hasattr(route, "routes"):  # This is a router (like the dynamic_router)
        for subroute in route.routes:
            subroute.dependencies.append(Depends(get_api_key))

app.include_router(api_router)

# Include the base router which has the health endpoint
app.include_router(base_router)


@app.get("/", status_code=status.HTTP_200_OK)
async def read_root():
    """Root endpoint."""
    return {"message": "Welcome to AORBIT"}


def run_server():
    """Run the uvicorn server."""
    try:
        uvicorn.run(
            "main:app",
            host=settings.host,
            port=settings.port,
            reload=settings.debug,
            reload_dirs=["src"],  # Only watch the src directory for changes
            workers=1,  # Use single worker in debug mode
            log_level="info",
        )
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        logger.error("Server error: %s", str(e))
        raise
    finally:
        if batch_processor and batch_processor._processing:
            import asyncio

            asyncio.run(batch_processor.stop_processing())


if __name__ == "__main__":
    run_server()
