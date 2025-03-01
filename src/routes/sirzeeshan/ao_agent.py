from dotenv import load_dotenv, find_dotenv

from langgraph.func import entrypoint, task
from langchain_google_genai import ChatGoogleGenerativeAI
from typing import TypedDict

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
    """Generate a random city using an LLM call."""

    response = model.invoke(
        f"""Return the name of a random city in the {country}. Only return the name of the city.""")
    random_city = response.content
    return random_city


@task
def generate_fun_fact(city: str) -> str:
    """Generate a fun fact about the given city."""

    response = model.invoke(f"""Tell me a fun fact about {
                            city}. Only return the fun fact.""")
    fun_fact = response.content
    return fun_fact


@entrypoint()
def run_workflow(country: str) -> dict:
    """Main workflow that generates a random city and fetches a fun fact about it."""
    city = generate_city(country).result()
    fact = generate_fun_fact(city).result()

    return {"fun_fact": fact, "country": country, "city": city}