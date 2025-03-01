"""
Base tools module for AgentOrchestrator.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class Tool(ABC):
    """Abstract base class for tools."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Get the name of the tool."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Get the description of the tool."""
        pass

    @abstractmethod
    async def execute(self, **kwargs: Any) -> Any:
        """Execute the tool with the given parameters."""
        pass

    @property
    @abstractmethod
    def parameters(self) -> Dict[str, Dict[str, Any]]:
        """Get the parameters schema for the tool."""
        pass


class ToolRegistry:
    """Registry for managing available tools."""

    def __init__(self):
        self._tools: Dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        """Register a new tool."""
        self._tools[tool.name] = tool

    def get_tool(self, name: str) -> Optional[Tool]:
        """Get a tool by name."""
        return self._tools.get(name)

    def list_tools(self) -> List[str]:
        """List all registered tool names."""
        return list(self._tools.keys())

    def get_tool_schema(self, name: str) -> Optional[Dict[str, Any]]:
        """Get the schema for a tool."""
        tool = self.get_tool(name)
        if tool:
            return {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters,
            }
        return None
