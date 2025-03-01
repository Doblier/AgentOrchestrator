"""Test configuration."""

import os
import sys
import pytest
from unittest.mock import MagicMock, patch

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)


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
