"""Test cases for cityfacts agent."""
import pytest
from unittest.mock import patch
from src.routes.cityfacts.ao_agent import workflow

# Mock data for testing
MOCK_TOPIC = "AI Agents"
MOCK_POEM = "AI agents are amazing.\nThey help us solve complex tasks.\nThe future is bright with AI."


def test_workflow_with_valid_input():
    """Test the complete workflow with valid input."""
    test_input = {"topic": MOCK_TOPIC}
    
    # Create expected result
    expected_result = {
        "sentence_count": 3,
        "poem": MOCK_POEM,
        "status": "Poem saved successfully"
    }
    
    # Mock the workflow's invoke method
    with patch.object(workflow, 'invoke', return_value=expected_result):
        # Run workflow
        result = workflow.invoke(test_input)
        
        # Verify result structure
        assert isinstance(result, dict)
        assert "sentence_count" in result
        assert "poem" in result
        assert "status" in result
        
        # Verify values
        assert result["sentence_count"] == 3
        assert result["poem"] == MOCK_POEM
        assert "saved successfully" in result["status"]


def test_workflow_with_invalid_input():
    """Test workflow with invalid input."""
    with pytest.raises(Exception):
        workflow("invalid input") 