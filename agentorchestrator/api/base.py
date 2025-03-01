"""
Base API routes for AgentOrchestrator.
"""

from fastapi import APIRouter
from pydantic import BaseModel

# Create the base router
router = APIRouter()


class HealthCheck(BaseModel):
    """Health check response model."""

    status: str
    version: str


@router.get("/api/v1/health", response_model=HealthCheck)
async def health_check():
    """Health check endpoint."""
    from agentorchestrator import __version__

    return HealthCheck(status="healthy", version=__version__) 