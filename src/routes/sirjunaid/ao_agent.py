"""
Fun Fact City Agent

This agent generates fun facts about random cities in a specified country.
It uses a two-step process:
1. Generate a random city from the given country
2. Generate an interesting fun fact about that city

Input: A string containing the country name (e.g., "Pakistan")
Output: A dictionary containing:
    - fun_fact: The generated fun fact
    - city: The randomly selected city
    - country: The input country name
"""

from typing import TypedDict

from dotenv import find_dotenv, load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.func import entrypoint, task

from ..validation import validate_route_input

_: bool = load_dotenv(find_dotenv())

model = ChatGoogleGenerativeAI(model="gemini-2.0-flash-exp")


class WorkflowState(TypedDict):
    """Define the input and output state for the workflow.

    Attributes:
        input: The country name to generate facts about
        fun_fact: The generated fun fact about the city
        city: The randomly selected city
    """

    input: str  # The country name
    fun_fact: str  # The generated fun fact
    city: str  # The selected city


@task
def generate_city(country: str) -> str:
    """Generate a random city using an LLM call.

    Args:
        country: Name of the country to get a city from

    Returns:
        str: Name of a random city in the specified country
    """
    response = model.invoke(
        f"""Return the name of a random city in the {country}. Only return the name of the city.""",
    )
    random_city = response.content
    return random_city


@task
def generate_fun_fact(city: str) -> str:
    """Generate a fun fact about the given city.

    Args:
        city: Name of the city to generate a fun fact about

    Returns:
        str: An interesting fun fact about the city
    """
    response = model.invoke(
        f"""Tell me a fun fact about {city}. Only return the fun fact.""",
    )
    fun_fact = response.content
    return fun_fact


@entrypoint()
def workflow(input: str) -> dict:
    """Main workflow that generates a random city and fetches a fun fact about it.

    Args:
        input: The country name to generate facts about

    Returns:
        dict: A dictionary containing:
            - fun_fact: The generated fun fact
            - city: The randomly selected city
            - country: The input country name

    Raises:
        ValidationError: If the input is not a valid string
    """
    # Validate input
    country = validate_route_input("fun_fact_city", input)

    # Execute workflow
    city = generate_city(country).result()
    fact = generate_fun_fact(city).result()

    return {"fun_fact": fact, "country": country, "city": city}


# Create the workflow instance
run_workflow = workflow
