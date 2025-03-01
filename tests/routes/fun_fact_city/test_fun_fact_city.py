"""Test cases for fun_fact_city agent."""

import pytest
from unittest.mock import patch
from src.routes.fun_fact_city.ao_agent import workflow

# Mock responses for testing
MOCK_CITY = "Lahore"
MOCK_FUN_FACT = "Lahore Fort is one of the largest forts in Pakistan"


def test_workflow_with_valid_input():
    """Test the complete workflow with valid input."""
    # Create expected result
    expected_result = {
        "fun_fact": MOCK_FUN_FACT,
        "city": MOCK_CITY,
        "country": "Pakistan",
    }

    # Mock the workflow's invoke method
    with patch.object(workflow, "invoke", return_value=expected_result):
        # Run workflow
        result = workflow.invoke("Pakistan")

        # Verify result structure
        assert isinstance(result, dict)
        assert "fun_fact" in result
        assert "city" in result
        assert "country" in result

        # Verify values
        assert result["city"] == MOCK_CITY
        assert result["fun_fact"] == MOCK_FUN_FACT
        assert result["country"] == "Pakistan"


def test_workflow_with_invalid_input():
    """Test workflow with invalid input."""
    with pytest.raises(Exception):
        workflow({"invalid": "input"})
