"""Input validation for agent routes."""

from typing import Any

from pydantic import BaseModel, ValidationError


class TopicInput(BaseModel):
    """Input model for topic-based agents."""

    topic: str


class AgentValidationError(Exception):
    """Custom exception for agent input validation errors."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


def validate_route_input(
    route_name: str,
    input_data: Any,
) -> str | dict[str, Any]:
    """Validate input data based on route name.

    Args:
        route_name: Name of the route/agent
        input_data: Input data to validate

    Returns:
        Validated and typed input data

    Raises:
        AgentValidationError: If input validation fails
    """
    try:
        if route_name == "fun_fact_city":
            if not isinstance(input_data, str):
                raise AgentValidationError(
                    "Invalid input: Expected a string (country name) for fun_fact_city route",
                )
            return input_data

        if route_name == "cityfacts":
            if not isinstance(input_data, dict):
                raise AgentValidationError(
                    "Invalid input: Expected a dictionary with 'topic' key for cityfacts route",
                )
            try:
                validated_data = TopicInput(**input_data)
                return validated_data.model_dump()
            except ValidationError as e:
                raise AgentValidationError(f"Invalid input structure: {str(e)}")

        else:
            raise AgentValidationError(f"Unknown route: {route_name}")

    except Exception as e:
        if isinstance(e, AgentValidationError):
            raise
        raise AgentValidationError(f"Validation error: {str(e)}")
