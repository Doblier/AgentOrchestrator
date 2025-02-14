"""
Poem Generation Agent - Creates poems about given topics.

This is a stateless agent that follows the standard AgentOrchestrator workflow pattern.
"""

import os
from typing import Dict, Any, TypedDict, Optional
from random import randint

from dotenv import load_dotenv, find_dotenv
from langgraph.graph import StateGraph
from langchain_google_genai import ChatGoogleGenerativeAI

_: bool = load_dotenv(find_dotenv())

class WorkflowState(TypedDict):
    """Type definition for workflow state."""
    topic: str
    sentence_count: Optional[int]
    poem: Optional[str]
    status: Optional[str]

def create_llm():
    """Create LLM instance - separated for better testing and mocking."""
    return ChatGoogleGenerativeAI(model="gemini-2.0-flash-exp")

def generate_sentence_count(state: WorkflowState) -> WorkflowState:
    """Generate a random sentence count for the poem."""
    state["sentence_count"] = randint(1, 5)
    return state

def generate_poem(state: WorkflowState) -> WorkflowState:
    """Generate a poem based on the sentence count using the AI model."""
    model = create_llm()
    prompt = f"""Write a beautiful and engaging poem about {state["topic"]} with exactly {state["sentence_count"]} sentences."""
    response = model.invoke(prompt)
    state["poem"] = response.content.strip()
    return state

def save_poem(state: WorkflowState) -> WorkflowState:
    """Save the poem to a file in a correct directory to avoid path errors."""
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)  # Ensure the directory exists
    file_path = os.path.join(output_dir, "poem.txt")

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(state["poem"])

    state["status"] = f"Poem saved successfully at {file_path}"
    return state

def create_workflow() -> StateGraph:
    """Create the workflow graph."""
    workflow = StateGraph(state_schema=WorkflowState)

    # Add nodes for each step
    workflow.add_node("generate_sentence_count", generate_sentence_count)
    workflow.add_node("generate_poem", generate_poem)
    workflow.add_node("save_poem", save_poem)

    # Add edges to connect the steps
    workflow.add_edge("generate_sentence_count", "generate_poem")
    workflow.add_edge("generate_poem", "save_poem")

    # Set entry and finish points
    workflow.set_entry_point("generate_sentence_count")
    workflow.set_finish_point("save_poem")

    return workflow.compile()

# Create singleton workflow instance
WORKFLOW = create_workflow()

def run_workflow(state: Dict[str, Any]) -> Dict[str, Any]:
    """Execute the workflow with the given state."""
    return WORKFLOW.invoke(state)