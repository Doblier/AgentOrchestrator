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
from typing import Dict, Any, Type, Callable

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, create_model

def discover_agents() -> Dict[str, Any]:
    """Discover all agent modules in src/routes directory."""
    agents = {}
    routes_dir = os.path.join("src", "routes")
    
    # Skip if routes directory doesn't exist
    if not os.path.exists(routes_dir):
        print(f"Warning: Routes directory {routes_dir} does not exist")
        return agents
    
    # Look for agent directories
    for agent_dir in os.listdir(routes_dir):
        agent_path = os.path.join(routes_dir, agent_dir)
        ao_agent_path = os.path.join(agent_path, "ao_agent.py")
        
        if os.path.isdir(agent_path) and os.path.exists(ao_agent_path):
            try:
                # Force reload the module to ensure we get the latest version
                module_name = f"src.routes.{agent_dir}.ao_agent"
                if module_name in sys.modules:
                    del sys.modules[module_name]
                
                # Import the agent module
                module = importlib.import_module(module_name)
                importlib.reload(module)
                
                # Verify required components
                if not hasattr(module, "run_workflow"):
                    print(f"Warning: {agent_dir} missing run_workflow function")
                    continue
                    
                if not hasattr(module, "WorkflowState"):
                    print(f"Warning: {agent_dir} missing WorkflowState type")
                    continue
                
                agents[agent_dir] = module
                print(f"Successfully loaded agent: {agent_dir}")
            except Exception as e:
                print(f"Error loading agent {agent_dir}: {str(e)}")
                import traceback
                print(traceback.format_exc())
    
    if not agents:
        print("Warning: No valid agents found in src/routes")
    else:
        print(f"Discovered {len(agents)} agents: {', '.join(agents.keys())}")
    
    return agents

def create_response_model(agent_name: str, agent_module: Any) -> Type[BaseModel]:
    """Create a Pydantic model for the agent's response based on WorkflowState."""
    try:
        # Get WorkflowState if defined
        if hasattr(agent_module, "WorkflowState"):
            annotations = agent_module.WorkflowState.__annotations__
            return create_model(
                f"{agent_name.title()}Response",
                **{k: (v, ...) for k, v in annotations.items() if not k.startswith("_")}
            )
        else:
            print(f"Warning: No WorkflowState found for {agent_name}")
            return create_model(
                f"{agent_name.title()}Response",
                result=(Dict[str, Any], ...)
            )
    except Exception as e:
        print(f"Warning: Failed to create response model for {agent_name}: {e}")
        return create_model(
            f"{agent_name.title()}Response",
            result=(Dict[str, Any], ...)
        )

def get_input_params(agent_name: str, agent_module: Any) -> Dict[str, Any]:
    """Get input parameters for an agent based on its WorkflowState."""
    if not hasattr(agent_module, "WorkflowState"):
        print(f"Warning: No WorkflowState found for {agent_name}")
        return {}
        
    try:
        # Get required fields from WorkflowState
        annotations = agent_module.WorkflowState.__annotations__
        # Only include fields that don't have Optional type and use 'input' as parameter name
        required_fields = {
            'input': (str, Query(..., description=f"Input for {agent_name} agent"))
        }
        return required_fields
    except Exception as e:
        print(f"Warning: Failed to get input params for {agent_name}: {e}")
        return {}

def create_execute_function(name: str, module: Any) -> Callable:
    """Create an execution function for the agent."""
    # Create the function with a single 'input' parameter
    async def execute_agent(input: str = Query(..., description=f"Input for {name} agent")):
        try:
            # Get the first required field from WorkflowState
            if hasattr(module, "WorkflowState"):
                annotations = module.WorkflowState.__annotations__
                required_field = next((k for k, v in annotations.items() 
                                    if not str(v).startswith("typing.Optional")), None)
                if required_field:
                    # Execute workflow with the input mapped to the required field
                    state = {required_field: input}
                    result = module.run_workflow(state)
                    print(f"{name} workflow result: {result}")
                    return result
            
            raise HTTPException(status_code=400, detail="Invalid agent configuration")
        except Exception as e:
            import traceback
            error_detail = f"{str(e)}\n{traceback.format_exc()}"
            raise HTTPException(status_code=500, detail=error_detail)
    
    # Set the function name
    execute_agent.__name__ = f"execute_{name}"
    return execute_agent

def create_dynamic_router() -> APIRouter:
    """Create a FastAPI router with dynamically loaded agent routes."""
    # Clear any cached modules to ensure fresh loading
    for module_name in list(sys.modules.keys()):
        if module_name.startswith("src.routes."):
            del sys.modules[module_name]
    
    # Discover agents
    agents = discover_agents()
    
    if not agents:
        print("Warning: No agents discovered in src/routes")
        return APIRouter()
    
    # Create routes for each agent
    router = APIRouter()
    for agent_name, agent_module in agents.items():
        try:
            response_model = create_response_model(agent_name, agent_module)
            input_params = get_input_params(agent_name, agent_module)
            
            # Create the execution function with the correct parameters
            handler = create_execute_function(agent_name, agent_module)
            
            # Add the route with dynamic parameters
            router.add_api_route(
                f"/agent/{agent_name}",
                handler,
                response_model=response_model,
                methods=["GET"]
            )
            
            print(f"Registered route: /api/v1/agent/{agent_name} [GET] input=str")
        except Exception as e:
            print(f"Failed to register route for {agent_name}: {str(e)}")
            import traceback
            print(traceback.format_exc())
    
    return router 