"""
Main entry point for the AgentOrchestrator application.
"""

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic_settings import BaseSettings

from agentorchestrator.api.routes import router as api_router

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

# Include API routes
app.include_router(api_router)

@app.get("/")
async def root():
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