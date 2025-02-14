# Agent Routes Directory

This directory contains all agent workflows following the AgentOrchestrator standard pattern.

## Directory Structure

```
src/routes/
├── agent_name/           # Directory for each agent (e.g., cityfacts)
│   ├── ao_agent.py      # Main agent workflow file
│   ├── prompts.py       # (Optional) Prompt templates
│   ├── models.py        # (Optional) Data models
│   └── utils.py         # (Optional) Helper functions
└── README.md            # This file
```

## Creating a New Agent Route

1. Create a new directory under `src/routes/` with your agent name
2. Create `ao_agent.py` with the following components:
   - `WorkflowState` TypedDict defining input/output fields
   - Task functions that transform the state
   - `create_workflow()` function to build the StateGraph
   - `run_workflow(state: Dict)` function as the entry point

## Example Agent Structure

```python
# src/routes/your_agent/ao_agent.py

from typing import Dict, Any, TypedDict

class WorkflowState(TypedDict):
    """Define required inputs and generated outputs."""
    input_field: str
    output_field: Optional[str]

def your_task(state: WorkflowState) -> WorkflowState:
    """Transform the state."""
    # Your logic here
    return state

def create_workflow() -> StateGraph:
    """Create the workflow graph."""
    workflow = StateGraph(state_schema=WorkflowState)
    # Add nodes and edges
    return workflow.compile()

WORKFLOW = create_workflow()

def run_workflow(state: Dict[str, Any]) -> Dict[str, Any]:
    """Standard entry point."""
    return WORKFLOW.invoke(state)
```

## Adding an API Endpoint

Add your agent's endpoint in `agentorchestrator/api/routes.py`:

```python
@router.get("/agent/your_agent", response_model=YourResponse)
async def execute_agent(input_param: str):
    """Execute your agent workflow."""
    result = run_workflow({"input_field": input_param})
    return YourResponse(**result)
```

## Testing

Each agent should have corresponding tests in `tests/routes/your_agent/`. 