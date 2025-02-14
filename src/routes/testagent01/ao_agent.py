"""
Test Agent - Generates city facts using a different approach.

This is a stateless agent that follows the standard AgentOrchestrator workflow pattern.
"""

from typing import Dict, Any, TypedDict, Optional

from dotenv import load_dotenv, find_dotenv
from langgraph.graph import StateGraph
from langchain_google_genai import ChatGoogleGenerativeAI

_: bool = load_dotenv(find_dotenv())

class WorkflowState(TypedDict):
    """Type definition for workflow state."""
    country: str
    city: Optional[str]
    fun_fact: Optional[str]

def create_llm():
    """Create LLM instance - separated for better testing and mocking."""
    return ChatGoogleGenerativeAI(model="gemini-2.0-flash-exp")

def initialize_state(state: WorkflowState) -> WorkflowState:
    """Initialize the workflow state with input values."""
    # The country is already in the state from the input
    # We just need to ensure it's properly set
    return state

def generate_city(state: WorkflowState) -> WorkflowState:
    """Generate a random city using an LLM call."""
    model = create_llm()
    response = model.invoke(
        f"""Return the name of a random city in {state["country"]}. Only return the name of the city."""
    )
    state["city"] = response.content.strip()
    return state

def generate_fun_fact(state: WorkflowState) -> WorkflowState:
    """Generate a fun fact about the given city."""
    model = create_llm()
    response = model.invoke(
        f"""Tell me a fun fact about {state["city"]}. Only return the fun fact."""
    )
    state["fun_fact"] = response.content.strip()
    return state

def create_workflow() -> StateGraph:
    """Create the workflow graph."""
    workflow = StateGraph(state_schema=WorkflowState)

    # Add nodes for each step
    workflow.add_node("initialize", initialize_state)
    workflow.add_node("generate_city", generate_city)
    workflow.add_node("generate_fun_fact", generate_fun_fact)

    # Add edges to connect the steps
    workflow.add_edge("initialize", "generate_city")
    workflow.add_edge("generate_city", "generate_fun_fact")

    # Set entry and finish points
    workflow.set_entry_point("initialize")
    workflow.set_finish_point("generate_fun_fact")

    return workflow.compile()

# Create singleton workflow instance
WORKFLOW = create_workflow()

def run_workflow(state: Dict[str, Any]) -> Dict[str, Any]:
    """Execute the workflow with the given state."""
    return WORKFLOW.invoke(state)