"""Tool definition and registry."""

import inspect
import json
from dataclasses import dataclass
from typing import Any, Callable, Optional, get_type_hints
from enum import Enum


class ToolCategory(Enum):
    """Tool capability categories."""

    GENERAL = "general"
    CODE = "code"
    FILE = "file"
    WEB = "web"
    DATABASE = "database"
    SYSTEM = "system"
    MCP = "mcp"
    SKILL = "skill"


@dataclass
class ToolDefinition:
    """Definition of a tool available to the LLM."""

    name: str
    description: str
    parameters: dict[str, Any]
    category: ToolCategory = ToolCategory.GENERAL
    function: Optional[Callable] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for LLM API calls."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


class ToolResult:
    """Result from a tool execution."""

    def __init__(
        self,
        content: str,
        is_error: bool = False,
        metadata: Optional[dict] = None,
    ):
        """Initialize a tool result.

        Args:
            content: The result content.
            is_error: Whether this is an error result.
            metadata: Optional metadata.
        """
        self.content = content
        self.is_error = is_error
        self.metadata = metadata or {}

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "content": self.content,
            "is_error": self.is_error,
            "metadata": self.metadata,
        }


def tool(
    name: Optional[str] = None,
    description: Optional[str] = None,
    category: ToolCategory = ToolCategory.GENERAL,
):
    """Decorator to register a function as a tool.

    Args:
        name: Optional tool name. Defaults to function name.
        description: Optional description. Defaults to function docstring.
        category: Tool category.

    Returns:
        Decorator function.
    """
    def decorator(func: Callable) -> Callable:
        # Store tool metadata on the function
        func._tool_name = name or func.__name__
        func._tool_description = description or inspect.getdoc(func) or ""
        func._tool_category = category
        func._is_tool = True
        return func
    return decorator


def infer_parameters(func: Callable) -> dict[str, Any]:
    """Infer JSON schema parameters from a function signature.

    Args:
        func: The function to analyze.

    Returns:
        JSON Schema parameters dictionary.
    """
    sig = inspect.signature(func)
    type_hints = get_type_hints(func)

    properties: dict[str, dict] = {}
    required: list[str] = []

    for name, param in sig.parameters.items():
        param_type = type_hints.get(name, str)

        # Build property schema
        prop_schema: dict[str, Any] = {"type": _type_to_json_schema(param_type)}

        # Get default value
        if param.default is not inspect.Parameter.empty:
            prop_schema["default"] = param.default
        else:
            required.append(name)

        # Add description from docstring
        docstring = inspect.getdoc(func)
        if docstring:
            # Simple parsing of args from docstring
            lines = docstring.split("\n")
            for line in lines:
                line = line.strip()
                if line.startswith(f"{name}:"):
                    prop_schema["description"] = line[len(name):].strip()

        properties[name] = prop_schema

    return {
        "type": "object",
        "properties": properties,
        "required": required,
    }


def _type_to_json_schema(py_type: type) -> str:
    """Convert Python type to JSON Schema type.

    Args:
        py_type: Python type.

    Returns:
        JSON Schema type string.
    """
    if py_type == str:
        return "string"
    elif py_type == int:
        return "integer"
    elif py_type == float:
        return "number"
    elif py_type == bool:
        return "boolean"
    elif py_type == list:
        return "array"
    elif py_type == dict:
        return "object"
    elif py_type == Any:
        return "string"
    else:
        return "string"


class ToolRegistry:
    """Registry for discovering and invoking tools."""

    def __init__(self):
        """Initialize the tool registry."""
        self._tools: dict[str, ToolDefinition] = {}
        self._functions: dict[str, Callable] = {}

    def register(self, tool_def: ToolDefinition) -> None:
        """Register a tool definition.

        Args:
            tool_def: The tool definition to register.
        """
        self._tools[tool_def.name] = tool_def
        if tool_def.function:
            self._functions[tool_def.name] = tool_def.function

    def register_function(self, func: Callable) -> None:
        """Register a function as a tool.

        Args:
            func: The function to register.
        """
        name = getattr(func, "_tool_name", func.__name__)
        description = getattr(func, "_tool_description", inspect.getdoc(func) or "")
        category = getattr(func, "_tool_category", ToolCategory.GENERAL)

        tool_def = ToolDefinition(
            name=name,
            description=description,
            parameters=infer_parameters(func),
            category=category,
            function=func,
        )

        self.register(tool_def)

    def get(self, name: str) -> Optional[ToolDefinition]:
        """Get a tool definition by name.

        Args:
            name: The tool name.

        Returns:
            The tool definition or None if not found.
        """
        return self._tools.get(name)

    def list_all(self) -> list[ToolDefinition]:
        """List all registered tools.

        Returns:
            List of tool definitions.
        """
        return list(self._tools.values())

    def list_by_category(self, category: ToolCategory) -> list[ToolDefinition]:
        """List tools by category.

        Args:
            category: The tool category.

        Returns:
            List of tool definitions.
        """
        return [t for t in self._tools.values() if t.category == category]

    async def call(self, name: str, arguments: dict[str, Any]) -> ToolResult:
        """Call a tool.

        Args:
            name: The tool name.
            arguments: Tool arguments.

        Returns:
            ToolResult from execution.
        """
        tool_def = self.get(name)
        if not tool_def:
            return ToolResult(content=f"Tool '{name}' not found", is_error=True)

        if not tool_def.function:
            return ToolResult(content=f"Tool '{name}' has no implementation", is_error=True)

        try:
            # Check if function is async
            if inspect.iscoroutinefunction(tool_def.function):
                result = await tool_def.function(**arguments)
            else:
                result = tool_def.function(**arguments)

            # Convert result to string
            if isinstance(result, ToolResult):
                return result
            elif result is None:
                return ToolResult(content="")
            else:
                return ToolResult(content=str(result))

        except Exception as e:
            return ToolResult(
                content=f"Error executing tool '{name}': {e}",
                is_error=True,
                metadata={"error_type": type(e).__name__},
            )

    def get_llm_tools(self) -> list[dict[str, Any]]:
        """Get tools in LLM-compatible format.

        Returns:
            List of tool dictionaries for LLM API.
        """
        return [tool.to_dict() for tool in self._tools.values()]

    def remove(self, name: str) -> bool:
        """Remove a tool from the registry.

        Args:
            name: The tool name.

        Returns:
            True if tool was removed, False if not found.
        """
        if name in self._tools:
            del self._tools[name]
            if name in self._functions:
                del self._functions[name]
            return True
        return False

    def clear(self) -> None:
        """Clear all registered tools."""
        self._tools.clear()
        self._functions.clear()
