import os
from random import randint
from dotenv import load_dotenv, find_dotenv
from typing import TypedDict, Dict, Any
from langgraph.func import entrypoint, task
from langchain_google_genai import ChatGoogleGenerativeAI
from ..validation import validate_route_input

_: bool = load_dotenv(find_dotenv())

model = ChatGoogleGenerativeAI(model="gemini-2.0-flash-exp")


class WorkflowState(TypedDict):
    """Define the input and output state for the workflow."""
    input: Dict[str, Any]  # The input dictionary with topic
    sentence_count: int  # Number of sentences in the poem
    poem: str  # The generated poem
    status: str  # Save status message


@task
def generate_sentence_count() -> int:
    """Generate a random sentence count for the poem."""
    return randint(1, 5)


@task
def generate_poem(sentence_count: int, topic: str) -> str:
    """Generate a poem based on the sentence count using the AI model."""
    prompt = f"""Write a beautiful and engaging poem about {
        topic} with exactly {sentence_count} sentences."""
    response = model.invoke(prompt)
    return response.content


@task
def save_poem(poem: str) -> str:
    """Save the poem to a file in a correct directory to avoid path errors."""
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)  # Ensure the directory exists
    file_path = os.path.join(output_dir, "poem.txt")

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(poem)

    return f"Poem saved successfully at {file_path}"


@entrypoint()
def workflow(input: Dict[str, Any]) -> Dict[str, Any]:
    """Workflow to generate and save a poem."""
    # Validate input
    validated_input = validate_route_input("cityfacts", input)
    
    sentence_count = generate_sentence_count().result()
    poem = generate_poem(sentence_count, validated_input["topic"]).result()
    save_status = save_poem(poem).result()

    return {"sentence_count": sentence_count, "poem": poem, "status": save_status}


# Create the workflow instance
run_workflow = workflow