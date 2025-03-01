"""
Dynamic route loader for AgentOrchestrator.

This module automatically discovers and loads agent workflows from src/routes directory.
Each agent must follow the standard pattern:
1. Be in a directory under src/routes
2. Have an ao_agent.py file with run_workflow function
3. Have proper state typing
"""

import importlib
import os
import sys
import json
import logging
from typing import Dict, Any, Callable

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field
from src.routes.validation import AgentValidationError

# Configure logging
logger = logging.getLogger(__name__)

class AgentResponse(BaseModel):
    """Standard response model for all agents."""
    success: bool = Field(
        description="Whether the agent execution was successful"
    )
    data: Dict[str, Any] = Field(
        description="The output data from the agent workflow"
    )
    error: str | None = Field(
        default=None,
        description="Error message if the execution failed"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "data": {
                    "fun_fact": "Example fun fact about a city",
                    "city": "Example City",
                    "country": "Example Country"
                },
                "error": None
            }
        }

def discover_agents() -> Dict[str, Any]:
    """Discover all agent modules in src/routes directory."""
    agents = {}
    routes_dir = os.path.join("src", "routes")
    
    if not os.path.exists(routes_dir):
        logger.warning(f"Routes directory {routes_dir} does not exist")
        return agents
    
    for agent_dir in os.listdir(routes_dir):
        if agent_dir.startswith("__"):  # Skip __pycache__ and similar
            continue
            
        agent_path = os.path.join(routes_dir, agent_dir)
        ao_agent_path = os.path.join(agent_path, "ao_agent.py")
        
        if os.path.isdir(agent_path) and os.path.exists(ao_agent_path):
            try:
                # Force reload the module
                module_name = f"src.routes.{agent_dir}.ao_agent"
                if module_name in sys.modules:
                    del sys.modules[module_name]
                
                module = importlib.import_module(module_name)
                importlib.reload(module)
                
                if not all(hasattr(module, attr) for attr in ["run_workflow", "WorkflowState"]):
                    logger.warning(f"Agent {agent_dir} missing required components")
                    continue
                
                agents[agent_dir] = module
                logger.info(f"Successfully loaded agent: {agent_dir}")
            except Exception as e:
                logger.error(f"Error loading agent {agent_dir}: {str(e)}", exc_info=True)
    
    if agents:
        logger.info(f"Discovered {len(agents)} agents: {', '.join(agents.keys())}")
    else:
        logger.warning("No valid agents found in src/routes")
    
    return agents

def get_agent_description(module: Any) -> str:
    """Extract agent description from module docstring."""
    if module.__doc__:
        return module.__doc__.strip()
    return "No description available"

def get_agent_examples(agent_name: str) -> Dict[str, Any]:
    """Get example inputs for an agent."""
    examples = {
        "fun_fact_city": {
            "summary": "Get fun fact about a city in a country",
            "description": "Returns a random city and fun fact from the specified country",
            "value": "Pakistan"
        },
        "cityfacts": {
            "summary": "Generate a poem about a topic",
            "description": "Generates a poem with random number of sentences about the given topic",
            "value": {"topic": "Vertical AI Agents"}
        }
    }
    return examples.get(agent_name, {
        "summary": "Example input",
        "description": "Example input for this agent",
        "value": "example"
    })

def create_execute_function(name: str, module: Any) -> Callable:
    """Create an execution function for the agent."""
    async def execute_agent(
        input: str = Query(
            ...,
            description=get_agent_description(module),
            examples=[get_agent_examples(name)]
        )
    ):
        """Execute the agent workflow.
        
        Args:
            input: Input data for the agent. Can be a string or JSON object depending on the agent.
            
        Returns:
            AgentResponse: The standardized response containing the workflow result
            
        Raises:
            HTTPException: If the workflow execution fails
        """
        try:
            # Parse input as JSON if possible
            try:
                input_data = json.loads(input)
            except json.JSONDecodeError:
                input_data = input
                
            # Execute workflow
            result = module.run_workflow.invoke(input_data)
            return AgentResponse(success=True, data=result)
            
        except AgentValidationError as e:
            logger.warning(f"Validation error in agent {name}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        except Exception as e:
            logger.error(f"Error executing agent {name}: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Internal server error: {str(e)}"
            )
    
    execute_agent.__name__ = f"execute_{name}"
    return execute_agent

def create_dynamic_router() -> APIRouter:
    """Create a FastAPI router with dynamically loaded agent routes."""
    # Clear cached modules
    for module_name in list(sys.modules.keys()):
        if module_name.startswith("src.routes."):
            del sys.modules[module_name]
    
    agents = discover_agents()
    if not agents:
        return APIRouter()
    
    router = APIRouter(
        prefix="/agent",
        tags=["Agents"],
        responses={
            status.HTTP_500_INTERNAL_SERVER_ERROR: {
                "description": "Internal server error",
                "content": {
                    "application/json": {
                        "example": {
                            "detail": "Error message"
                        }
                    }
                }
            }
        }
    )
    
    for agent_name, agent_module in agents.items():
        try:
            handler = create_execute_function(agent_name, agent_module)
            
            router.add_api_route(
                f"/{agent_name}",
                handler,
                response_model=AgentResponse,
                methods=["GET"],
                summary=f"Execute {agent_name} agent",
                description=get_agent_description(agent_module),
                response_description="The agent workflow result"
            )
            
            logger.info(f"Registered route: /agent/{agent_name} [GET]")
        except Exception as e:
            logger.error(f"Failed to register route for {agent_name}: {str(e)}", exc_info=True)
    
    return router 