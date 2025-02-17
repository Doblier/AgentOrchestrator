"""
Main entry point for the AgentOrchestrator application.
"""

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, status
from pydantic_settings import BaseSettings
from redis import Redis

from agentorchestrator.api.route_loader import create_dynamic_router
from agentorchestrator.middleware.rate_limiter import RateLimiter, RateLimitConfig
from agentorchestrator.middleware.cache import ResponseCache, CacheConfig

# Load environment variables
env_path = Path(".env")
load_dotenv(dotenv_path=env_path)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    """Application settings."""
    app_name: str = "AgentOrchestrator"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8000

settings = Settings()

# Create Redis client
redis_client = Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", "6379")),
    db=int(os.getenv("REDIS_DB", "0")),
    decode_responses=True
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan events for the FastAPI application."""
    # Startup
    logger.info("Starting AgentOrchestrator...")
    yield
    # Shutdown
    logger.info("Shutting down AgentOrchestrator...")

app = FastAPI(
    title=settings.app_name,
    description="A powerful agent orchestration framework",
    version="0.1.0",
    debug=settings.debug,
    lifespan=lifespan
)

# Add middlewares
rate_limit_config = RateLimitConfig(
    requests_per_minute=int(os.getenv("RATE_LIMIT_RPM", "60")),
    burst_limit=int(os.getenv("RATE_LIMIT_BURST", "100")),
    enabled=os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
)

cache_config = CacheConfig(
    ttl=int(os.getenv("CACHE_TTL", "300")),
    enabled=os.getenv("CACHE_ENABLED", "true").lower() == "true",
    excluded_paths=["/api/v1/health"]
)

app.add_middleware(RateLimiter, redis_client=redis_client, config=rate_limit_config)
app.add_middleware(ResponseCache, redis_client=redis_client, config=cache_config)

# Include API routes
app.include_router(create_dynamic_router(), prefix="/api/v1")

@app.get("/", status_code=status.HTTP_200_OK)
async def read_root():
    """Root endpoint."""
    return {"message": "Welcome to AgentOrchestrator"}

def run_server():
    """Run the uvicorn server."""
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )

if __name__ == "__main__":
    run_server()