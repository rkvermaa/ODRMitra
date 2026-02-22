"""Tool Registry — manages core and skill-specific tools."""

from typing import Any
import importlib

from src.core.logging import log
from src.tools.base import BaseTool
from src.tools.core import CORE_TOOLS


class ToolRegistry:
    """Registry for managing agent tools."""

    def __init__(self):
        self.enabled_tools: set[str] = set()
        self._tool_instances: dict[str, BaseTool] = {}
        self._tool_classes: dict[str, type[BaseTool]] = {}

        self._tool_classes.update(CORE_TOOLS)

    def load_skill_tools(self, skill_slug: str) -> list[str]:
        """Load tools from a skill's tools folder."""
        loaded_tools = []

        try:
            module_path = f"src.skills.builtin.{skill_slug}.tools"
            module = importlib.import_module(module_path)
            skill_tools = getattr(module, "SKILL_TOOLS", {})

            for tool_name, tool_class in skill_tools.items():
                if tool_name not in self._tool_classes:
                    self._tool_classes[tool_name] = tool_class
                    loaded_tools.append(tool_name)
                    log.debug(f"Loaded skill tool: {tool_name} from {skill_slug}")

        except ImportError:
            log.debug(f"No tools module for skill: {skill_slug}")
        except Exception as e:
            log.warning(f"Error loading tools for skill {skill_slug}: {e}")

        return loaded_tools

    def enable_tools_for_skill(self, allowed_tools: list[str], skill_slug: str = None) -> int:
        """Enable tools specified in skill's allowed-tools."""
        if skill_slug:
            self.load_skill_tools(skill_slug)

        enabled_count = 0
        for tool_name in allowed_tools:
            if self.enable_tool(tool_name):
                enabled_count += 1
        return enabled_count

    def enable_tool(self, name: str) -> bool:
        """Enable a tool by name."""
        if name not in self._tool_classes:
            log.warning(f"Unknown tool: {name}")
            return False
        self.enabled_tools.add(name)
        return True

    def get_tool(self, name: str) -> BaseTool | None:
        """Get a tool instance by name."""
        if name not in self.enabled_tools:
            return None
        if name not in self._tool_instances:
            tool_class = self._tool_classes.get(name)
            if tool_class:
                self._tool_instances[name] = tool_class()
        return self._tool_instances.get(name)

    def get_tool_definitions(self) -> list[dict[str, Any]]:
        """Get definitions for all enabled tools (for LLM)."""
        definitions = []
        for name in self.enabled_tools:
            tool = self.get_tool(name)
            if tool:
                definitions.append(tool.get_definition())
        return definitions

    def get_enabled_tools(self) -> list[str]:
        """Get list of currently enabled tool names."""
        return list(self.enabled_tools)

    async def execute_tool(
        self,
        name: str,
        arguments: dict[str, Any],
        context: dict[str, Any],
    ) -> Any:
        """Execute a tool by name."""
        tool = self.get_tool(name)
        if not tool:
            raise ValueError(f"Tool not found or not enabled: {name}")
        log.info(f"Executing tool: {name}")
        return await tool.execute(arguments, context)
