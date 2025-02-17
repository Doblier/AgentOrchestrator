from typing import Any, Union, Dict, TypeVar
from pydantic import BaseModel, ValidationError

T = TypeVar('T', str, Dict[str, Any])

class TopicInput(BaseModel):
    """Input model for topic-based agents."""
    topic: str

class ValidationResult(BaseModel):
    """Standard validation result model."""
    success: bool
    data: T
    error: str | None = None

def validate_route_input(route_name: str, input_data: Any) -> T:
    """Validate input data based on route name.
    
    Args:
        route_name: Name of the route/agent
        input_data: Input data to validate
        
    Returns:
        Validated and typed input data
        
    Raises:
        ValidationError: If input data is invalid
    """
    if route_name == "fun_fact_city":
        if not isinstance(input_data, str):
            raise ValidationError("Input must be a string (country name) for fun_fact_city route")
        return input_data
    
    elif route_name == "cityfacts":
        if not isinstance(input_data, dict):
            raise ValidationError("Input must be a dictionary with 'topic' key for cityfacts route")
        validated_data = TopicInput(**input_data)
        return validated_data.model_dump()
    
    else:
        raise ValueError(f"Unknown route: {route_name}") 