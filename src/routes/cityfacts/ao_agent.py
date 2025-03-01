"""
City Facts Poetry Agent

This agent generates creative poems about given topics with a random number of sentences.
The workflow consists of three steps:
1. Generate a random sentence count (1-5)
2. Generate a poem about the topic with the specified number of sentences
3. Save the generated poem to a file

Input: A dictionary containing:
    - topic: The topic to generate a poem about (e.g., {"topic": "Vertical AI Agents"})
Output: A dictionary containing:
    - sentence_count: Number of sentences in the poem
    - poem: The generated poem
    - status: Save status message
"""

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
    """Define the input and output state for the workflow.

    Attributes:
        input: Dictionary containing the topic to write about
        sentence_count: Number of sentences in the generated poem
        poem: The generated poem text
        status: Status message about saving the poem
    """

    input: Dict[str, Any]  # The input dictionary with topic
    sentence_count: int  # Number of sentences in the poem
    poem: str  # The generated poem
    status: str  # Save status message


@task
def generate_sentence_count() -> int:
    """Generate a random sentence count for the poem.

    Returns:
        int: A random number between 1 and 5
    """
    return randint(1, 5)


@task
def generate_poem(sentence_count: int, topic: str) -> str:
    """Generate a poem based on the sentence count using the AI model.

    Args:
        sentence_count: Number of sentences to include in the poem
        topic: The topic to write the poem about

    Returns:
        str: The generated poem text
    """
    prompt = f"""Write a beautiful and engaging poem about {
        topic} with exactly {sentence_count} sentences."""
    response = model.invoke(prompt)
    return response.content


@task
def save_poem(poem: str) -> str:
    """Save the poem to a file in a correct directory to avoid path errors.

    Args:
        poem: The poem text to save

    Returns:
        str: Status message indicating where the poem was saved

    Raises:
        IOError: If there's an error creating the directory or saving the file
    """
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)  # Ensure the directory exists
    file_path = os.path.join(output_dir, "poem.txt")

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(poem)

    return f"Poem saved successfully at {file_path}"


@entrypoint()
def workflow(input: Dict[str, Any]) -> Dict[str, Any]:
    """Workflow to generate and save a poem.

    Args:
        input: Dictionary containing:
            - topic: The topic to generate a poem about

    Returns:
        dict: A dictionary containing:
            - sentence_count: Number of sentences in the poem
            - poem: The generated poem
            - status: Save status message

    Raises:
        ValidationError: If the input is not a valid dictionary with a topic key
    """
    # Validate input
    validated_input = validate_route_input("cityfacts", input)

    sentence_count = generate_sentence_count().result()
    poem = generate_poem(sentence_count, validated_input["topic"]).result()
    save_status = save_poem(poem).result()

    return {"sentence_count": sentence_count, "poem": poem, "status": save_status}


# Create the workflow instance
run_workflow = workflow
