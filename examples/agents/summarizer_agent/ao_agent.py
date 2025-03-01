"""
Text Summarization Agent

This agent summarizes text content with configurable parameters for length and style.
It can be used to create concise summaries of articles, documents, or other long-form content.
"""

import os
from typing import Dict, Any, TypedDict, Optional
from dotenv import load_dotenv
from langgraph.func import entrypoint, task
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.output_parsers import StrOutputParser

# Load environment variables
load_dotenv()

# Initialize the model
model = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash-exp",
    google_api_key=os.getenv("GOOGLE_API_KEY"),
    temperature=0.2,
)


class SummaryInput(TypedDict):
    """Input type for the summarization agent."""

    text: str
    max_sentences: Optional[int]  # Default will be 3 if not provided
    style: Optional[str]  # Default will be "concise" if not provided


@task
def summarize_text(input_data: SummaryInput) -> Dict[str, Any]:
    """
    Generate a summary of the input text with customizable parameters.

    Args:
        input_data: Dictionary containing the text to summarize and optional parameters
            - text: The text content to summarize
            - max_sentences: Maximum number of sentences in the summary (default: 3)
            - style: Summary style - "concise", "bullet", "detailed" (default: "concise")

    Returns:
        Dict containing the original text, summary, and metadata
    """
    # Extract parameters with defaults
    text = input_data["text"]
    max_sentences = input_data.get("max_sentences", 3)
    style = input_data.get("style", "concise")

    # Validate max_sentences
    if not isinstance(max_sentences, int) or max_sentences < 1:
        max_sentences = 3

    # Validate style
    valid_styles = ["concise", "bullet", "detailed"]
    if style not in valid_styles:
        style = "concise"

    # Create a prompt based on the style
    if style == "concise":
        prompt_template = f"""
        Summarize the following text in {max_sentences} sentences or fewer.
        Keep the summary clear, accurate, and focused on the main points.
        
        TEXT:
        {text}
        
        SUMMARY:
        """
    elif style == "bullet":
        prompt_template = f"""
        Summarize the following text as a bullet list with {max_sentences} points or fewer.
        Each bullet should capture a key point from the text.
        
        TEXT:
        {text}
        
        BULLET SUMMARY:
        """
    else:  # detailed
        prompt_template = f"""
        Create a detailed summary of the following text in {max_sentences} sentences or fewer.
        Include the most important details while maintaining clarity and accuracy.
        
        TEXT:
        {text}
        
        DETAILED SUMMARY:
        """

    # Get the response from the model
    response = model.invoke(prompt_template)
    summary = StrOutputParser().invoke(response)

    # Return the summary and metadata
    return {
        "original_text": (
            text[:100] + "..." if len(text) > 100 else text
        ),  # Truncate for response
        "summary": summary,
        "metadata": {
            "model": "gemini-2.0-flash-exp",
            "temperature": 0.2,
            "max_sentences": max_sentences,
            "style": style,
            "original_length": len(text),
            "summary_length": len(summary),
        },
    }


@entrypoint()
def run_workflow(input_data: SummaryInput) -> Dict[str, Any]:
    """
    Main entry point for the summarization workflow.

    Args:
        input_data: Dictionary containing the text to summarize and optional parameters
            - text: The text content to summarize
            - max_sentences: Maximum number of sentences (optional)
            - style: Summary style (optional)

    Returns:
        Dict containing the summary and metadata
    """
    # If input is just a string, assume it's the text to summarize
    if isinstance(input_data, str):
        input_data = {"text": input_data}

    result = summarize_text(input_data).result()
    return result
