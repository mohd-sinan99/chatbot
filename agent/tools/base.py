"""
Base Tool Infrastructure (📘 L2: 2–4 tools, clearly described & fixing errors when a tool fails)
Provides abstract base tool with schema definitions, execution logging, and automated error catching.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, Optional
import traceback


@dataclass
class ToolResult:
    """Standardized result returned by all tools."""
    tool_name: str
    status: str  # "SUCCESS" or "ERROR"
    data: Any = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_observation_string(self) -> str:
        """Format the result into a clean observation string for the agent loop."""
        if self.status == "SUCCESS":
            return f"[Tool: {self.tool_name}] SUCCESS:\n{self.data}"
        else:
            return (
                f"[Tool: {self.tool_name}] ERROR: {self.error}\n"
                "Tip: Review tool parameters and self-correct on the next step."
            )


class BaseTool(ABC):
    """
    Abstract Base Class for agent tools.
    Subclasses must define name, description, parameters schema, and execute().
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier name for the tool."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Clear description of what the tool does and when to use it."""
        pass

    @property
    @abstractmethod
    def parameters_schema(self) -> Dict[str, Any]:
        """JSON schema describing tool arguments."""
        pass

    @abstractmethod
    def execute(self, **kwargs) -> Any:
        """Tool execution logic to be implemented by each tool."""
        pass

    def safe_execute(self, **kwargs) -> ToolResult:
        """
        Resilient execution wrapper (📘 L2: Fixing errors when a tool fails).
        Intercepts exceptions, prevents agent crash, and returns diagnostic error info.
        """
        try:
            # Basic validation against required parameters if defined in schema
            required_params = self.parameters_schema.get("required", [])
            missing = [p for p in required_params if p not in kwargs or kwargs[p] is None]
            if missing:
                return ToolResult(
                    tool_name=self.name,
                    status="ERROR",
                    error=f"Missing required parameter(s): {', '.join(missing)}."
                )

            result_data = self.execute(**kwargs)
            return ToolResult(
                tool_name=self.name,
                status="SUCCESS",
                data=result_data,
            )
        except Exception as e:
            error_details = f"{type(e).__name__}: {str(e)}"
            return ToolResult(
                tool_name=self.name,
                status="ERROR",
                error=f"Execution failed: {error_details}",
                metadata={"traceback": traceback.format_exc()}
            )

    def get_definition(self) -> Dict[str, Any]:
        """Returns the full tool documentation for the LLM system prompt."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters_schema,
        }

