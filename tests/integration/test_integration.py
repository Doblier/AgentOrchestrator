"""
Integration test for the API endpoints.
"""

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_health_check():
    """Test that the health check endpoint returns 200."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert "status" in response.json()
    assert "version" in response.json()
    assert response.json()["status"] == "healthy"
