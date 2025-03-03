"""
Base API routes for AORBIT.
"""

from fastapi import APIRouter, Request, Response, status
from pydantic import BaseModel

# Create the base router
router = APIRouter()


class HealthCheck(BaseModel):
    """Health check response model."""

    status: str
    version: str


@router.get("/api/v1/health", response_model=HealthCheck)
async def health_check():
    """Health check endpoint for AORBIT."""
    from agentorchestrator import __version__

    return HealthCheck(status="healthy", version=__version__)

@router.post("/api/v1/logout")
async def logout(request: Request, response: Response):
    """Logout endpoint to invalidate the current API key session."""
    # The auth middleware will handle the actual invalidation
    # We just need to return a success response
    response.status_code = status.HTTP_200_OK
    return {"message": "Successfully logged out"} 