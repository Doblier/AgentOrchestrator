"""
API routes for AgentOrchestrator.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.agent.ao_agent import run_workflow

router = APIRouter(prefix="/api/v1")

class HealthCheck(BaseModel):
    """Health check response model."""
    status: str
    version: str

class AgentResponse(BaseModel):
    """Agent execution response model."""
    fun_fact: str
    country: str
    city: str

@router.get("/health", response_model=HealthCheck)
async def health_check():
    """Health check endpoint."""
    from agentorchestrator import __version__
    return HealthCheck(
        status="healthy",
        version=__version__
    )

@router.get("/agent/execute", response_model=AgentResponse)
async def execute_agent(country: str):
    """Execute the agent workflow."""
    try:
        # Initialize workflow state
        initial_state = {"country": country}
        
        # Execute workflow
        result = run_workflow(initial_state)
        
        # Log the result for debugging
        print(f"Workflow result: {result}")
        
        # Ensure we have all required fields
        if not all(key in result for key in ["fun_fact", "country", "city"]):
            raise ValueError(f"Workflow result missing required fields. Got: {result}")
        
        return AgentResponse(
            fun_fact=result["fun_fact"],
            country=result["country"],
            city=result["city"]
        )
    except Exception as e:
        import traceback
        error_detail = f"{str(e)}\n{traceback.format_exc()}"
        raise HTTPException(status_code=500, detail=error_detail)

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