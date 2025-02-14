"""
LangGraph agent workflow for city facts generation.
"""

from typing import Dict, Any, TypedDict, Optional

from dotenv import load_dotenv, find_dotenv
from langgraph.graph import StateGraph
from langgraph.prebuilt import ToolExecutor
from langchain_google_genai import ChatGoogleGenerativeAI

_: bool = load_dotenv(find_dotenv())

model = ChatGoogleGenerativeAI(model="gemini-2.0-flash-exp")

class WorkflowState(TypedDict):
    """Type definition for workflow state."""
    country: str
    city: Optional[str]
    fun_fact: Optional[str]

def generate_city(state: WorkflowState) -> WorkflowState:
    """Generate a random city using an LLM call."""
    country = state["country"]
    response = model.invoke(
        f"""Return the name of a random city in {country}. Only return the name of the city."""
    )
    state["city"] = response.content.strip()
    return state

def generate_fun_fact(state: WorkflowState) -> WorkflowState:
    """Generate a fun fact about the given city."""
    city = state["city"]
    response = model.invoke(
        f"""Tell me a fun fact about {city}. Only return the fun fact."""
    )
    state["fun_fact"] = response.content.strip()
    return state

def create_workflow() -> StateGraph:
    """Create the workflow graph."""
    # Create a new graph with state schema
    workflow = StateGraph(state_schema=WorkflowState)

    # Add nodes for each step
    workflow.add_node("generate_city", generate_city)
    workflow.add_node("generate_fun_fact", generate_fun_fact)

    # Add edges to connect the steps
    workflow.add_edge("generate_city", "generate_fun_fact")
    workflow.set_entry_point("generate_city")
    workflow.set_finish_point("generate_fun_fact")

    # Compile the graph
    return workflow.compile()

# Create a singleton instance of the workflow
WORKFLOW = create_workflow()

def run_workflow(state: Dict[str, Any]) -> Dict[str, Any]:
    """Execute the workflow with the given state."""
    return WORKFLOW.invoke(state)