"""Test configuration."""

import os
import sys
import pytest
from unittest.mock import MagicMock

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
