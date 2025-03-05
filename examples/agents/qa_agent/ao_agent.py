"""
Question Answering Agent

This agent answers natural language questions using Google's Gemini model.
It provides detailed, factual responses to a wide range of questions.
"""

import os
from typing import Any

from dotenv import load_dotenv
from langchain_core.output_parsers import StrOutputParser
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.func import entrypoint, task

# Load environment variables
load_dotenv()

# Initialize the Gemini model
model = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash-exp",
    google_api_key=os.getenv("GOOGLE_API_KEY"),
    temperature=0.2,
)


@task
def answer_question(question: str) -> dict[str, Any]:
    """
    Generate an answer to the user's question using Gemini AI.

    Args:
        question: The natural language question to answer

    Returns:
        Dict containing the question, answer, and metadata
    """
    # Create a prompt that instructs the model to give accurate information
    prompt = f"""
    You are a helpful AI assistant that provides accurate, factual information.
    
    Question: {question}
    
    Please provide a clear, concise answer based on factual information.
    If you're unsure about something, acknowledge the uncertainty rather than making up information.
    When relevant, mention your sources of information.
    """

    # Get the response from the model
    response = model.invoke(prompt)
    answer = StrOutputParser().invoke(response)

    # Return the question, answer, and metadata
    return {
        "question": question,
        "answer": answer,
        "metadata": {
            "model": "gemini-2.0-flash-exp",
            "temperature": 0.2,
            "tokens_used": len(answer.split()) * 2,  # Rough estimate
        },
    }


@entrypoint()
def run_workflow(question: str) -> dict[str, Any]:
    """
    Main entry point for the question answering workflow.

    Args:
        question: The natural language question to answer

    Returns:
        Dict containing the question, answer, and metadata
    """
    result = answer_question(question).result()
    return result
