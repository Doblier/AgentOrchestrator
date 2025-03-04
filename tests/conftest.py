"""Test configuration."""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Apply mock for Google AI early, before any tests are loaded
# This prevents errors during test collection
mock_gemini = MagicMock()
mock_gemini_response = MagicMock()
mock_gemini_response.content = "This is a mocked response from Gemini AI"
mock_gemini.invoke.return_value = mock_gemini_response

# Apply the mock immediately
patch("langchain_google_genai.ChatGoogleGenerativeAI", return_value=mock_gemini).start()
os.environ["GOOGLE_API_KEY"] = "test_key"


@pytest.fixture(autouse=True)
def setup_env(monkeypatch):
    """Set up test environment."""
    monkeypatch.setenv("GOOGLE_API_KEY", "test_key")


@pytest.fixture
def mock_gemini_response():
    """Create a mock Gemini response."""

    def _create_response(content: str):
        return MagicMock(content=content)

    return _create_response


@pytest.fixture(scope="session", autouse=True)
def mock_langchain_gemini():
    """Mock the ChatGoogleGenerativeAI class to prevent API calls in tests."""
    with patch("langchain_google_genai.ChatGoogleGenerativeAI") as mock_class:
        # Configure the mock to return a properly structured response
        mock_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "This is a mocked response from Gemini AI"
        mock_instance.invoke.return_value = mock_response

        # Make the mock class return our configured instance
        mock_class.return_value = mock_instance

        yield mock_class
