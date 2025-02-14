from typing import Any, Union
from pydantic import BaseModel, ValidationError


class TopicInput(BaseModel):
    topic: str


def validate_route_input(route_name: str, input_data: Any) -> Union[str, dict]:
    """Validate input data based on route name."""
    if route_name == "fun_fact_city":
        if not isinstance(input_data, str):
            raise ValidationError("Input must be a string (country name) for fun_fact_city route")
        return input_data
    
    elif route_name == "cityfacts":
        if isinstance(input_data, dict):
            validated_data = TopicInput(**input_data)
            return validated_data.model_dump()
        raise ValidationError("Input must be a dictionary with 'topic' key for cityfacts route")
    
    else:
        raise ValueError(f"Unknown route: {route_name}") 