"""
Base state management for AgentOrchestrator.
"""

from abc import ABC, abstractmethod
from typing import Any


class StateManager(ABC):
    """Abstract base class for state management."""

    @abstractmethod
    async def get(self, key: str) -> Any | None:
        """Retrieve a value from the state store."""
        pass

    @abstractmethod
    async def set(self, key: str, value: Any) -> None:
        """Store a value in the state store."""
        pass

    @abstractmethod
    async def delete(self, key: str) -> None:
        """Delete a value from the state store."""
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if a key exists in the state store."""
        pass


class InMemoryStateManager(StateManager):
    """Simple in-memory state manager implementation."""

    def __init__(self):
        self._store: dict[str, Any] = {}

    async def get(self, key: str) -> Any | None:
        """Retrieve a value from the in-memory store."""
        return self._store.get(key)

    async def set(self, key: str, value: Any) -> None:
        """Store a value in the in-memory store."""
        self._store[key] = value

    async def delete(self, key: str) -> None:
        """Delete a value from the in-memory store."""
        self._store.pop(key, None)

    async def exists(self, key: str) -> bool:
        """Check if a key exists in the in-memory store."""
        return key in self._store
