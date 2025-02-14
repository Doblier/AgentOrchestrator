"""
API routes for AgentOrchestrator.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from agentorchestrator.api.route_loader import create_dynamic_router

# Create the base router
router = APIRouter(prefix="/api/v1")

class HealthCheck(BaseModel):
    """Health check response model."""
    status: str
    version: str

@router.get("/health", response_model=HealthCheck)
async def health_check():
    """Health check endpoint."""
    from agentorchestrator import __version__
    return HealthCheck(
        status="healthy",
        version=__version__
    )

@router.get("/tools")
async def list_tools():
    """List available tools."""
    from agentorchestrator.tools.base import ToolRegistry
    registry = ToolRegistry()
    return {
        "tools": registry.list_tools()
    }

@router.get("/tools/{tool_name}")
async def get_tool_schema(tool_name: str):
    """Get schema for a specific tool."""
    from agentorchestrator.tools.base import ToolRegistry
    registry = ToolRegistry()
    schema = registry.get_tool_schema(tool_name)
    if not schema:
        raise HTTPException(status_code=404, detail="Tool not found")
    return schema

# Include dynamically loaded agent routes
dynamic_router = create_dynamic_router()
router.include_router(dynamic_router) 