"""
Test suite for the main application.
"""

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)

def test_read_root():
    """Test the root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to AgentOrchestrator"}

def test_app_startup():
    """Test application startup configuration."""
    assert app.title == "AgentOrchestrator"
    assert app.version == "0.1.0"