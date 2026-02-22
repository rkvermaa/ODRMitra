"""Base tool class"""

from abc import ABC, abstractmethod
from typing import Any


class BaseTool(ABC):
    """Abstract base class for all agent tools."""

    name: str = ""
    description: str = ""

    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {},
        "required": [],
    }

    @abstractmethod
    async def execute(
        self,
        arguments: dict[str, Any],
        context: dict[str, Any],
    ) -> Any:
        """Execute the tool.

        Args:
            arguments: Tool arguments from LLM.
            context: Execution context (user_id, session_id, dispute_id, etc.)

        Returns:
            Tool result (converted to string for LLM).
        """
        pass

    def get_definition(self) -> dict[str, Any]:
        """Get tool definition for LLM."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }
