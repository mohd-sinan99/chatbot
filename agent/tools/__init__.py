"""
Tool Registry (📘 L2: 2–4 tools, clearly described)
Registers all agent tools and provides lookup by name.
"""

from typing import Dict, List, Any, Optional
from agent.tools.base import BaseTool, ToolResult
from agent.tools.destination_tool import DestinationSearchTool
from agent.tools.budget_tool import BudgetCalculatorTool
from agent.tools.transport_tool import TransportOptionsTool
from agent.tools.advisory_tool import TravelAdvisoryTool


class ToolRegistry:
    """Manages the 4 travel planning tools with schema generation and safe execution."""

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
        # Register the 4 core tools (📘 L2)
        self.register(DestinationSearchTool())
        self.register(BudgetCalculatorTool())
        self.register(TransportOptionsTool())
        self.register(TravelAdvisoryTool())

    def register(self, tool: BaseTool) -> None:
        """Register a tool instance."""
        self._tools[tool.name] = tool

    def get_tool(self, name: str) -> Optional[BaseTool]:
        """Lookup tool by name."""
        return self._tools.get(name)

    def list_tool_names(self) -> List[str]:
        """List registered tool names."""
        return list(self._tools.keys())

    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """Return schema definitions for all tools for LLM prompts."""
        return [tool.get_definition() for tool in self._tools.values()]

    def execute_tool(self, name: str, **kwargs) -> ToolResult:
        """
        Execute tool with error trapping and diagnostic feedback (📘 L2).
        """
        tool = self.get_tool(name)
        if not tool:
            return ToolResult(
                tool_name=name,
                status="ERROR",
                error=f"Tool '{name}' not found. Available tools: {', '.join(self.list_tool_names())}"
            )
        return tool.safe_execute(**kwargs)


__all__ = [
    "BaseTool",
    "ToolResult",
    "DestinationSearchTool",
    "BudgetCalculatorTool",
    "TransportOptionsTool",
    "TravelAdvisoryTool",
    "ToolRegistry",
]

