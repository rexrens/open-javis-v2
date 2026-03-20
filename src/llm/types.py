"""LLM message types."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional, Union
from json import dumps as json_dumps


class MessageRole(Enum):
    """Role of a message in the conversation."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass
class ToolCall:
    """Represents a tool/function call from the LLM."""

    id: str
    function: str
    arguments: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API calls."""
        return {
            "id": self.id,
            "type": "function",
            "function": {
                "name": self.function,
                "arguments": json_dumps(self.arguments),
            },
        }


@dataclass
class ToolResult:
    """Represents the result of a tool execution."""

    tool_call_id: str
    content: str
    is_error: bool = False

    def to_message(self) -> "ToolMessage":
        """Convert to a ToolMessage."""
        return ToolMessage(
            role=MessageRole.TOOL,
            tool_call_id=self.tool_call_id,
            content=self.content,
            is_error=self.is_error,
        )


@dataclass
class BaseMessage:
    """Base class for all LLM messages."""

    role: MessageRole


@dataclass
class SystemMessage(BaseMessage):
    """System message that sets context and behavior."""

    content: str

    def to_dict(self) -> dict[str, str]:
        """Convert to dictionary for API calls."""
        return {"role": self.role.value, "content": self.content}


@dataclass
class UserMessage(BaseMessage):
    """User message."""

    content: str
    name: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API calls."""
        result: dict[str, Any] = {"role": self.role.value, "content": self.content}
        if self.name:
            result["name"] = self.name
        return result


@dataclass
class AssistantMessage(BaseMessage):
    """Assistant message."""

    content: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    reasoning: Optional[str] = None  # For models with reasoning output

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API calls."""
        result: dict[str, Any] = {"role": self.role.value}
        if self.content:
            result["content"] = self.content
        if self.tool_calls:
            result["tool_calls"] = [tc.to_dict() for tc in self.tool_calls]
        if self.reasoning:
            result["reasoning"] = self.reasoning
        return result


@dataclass
class ToolMessage(BaseMessage):
    """Tool result message."""

    tool_call_id: str
    content: str
    is_error: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API calls."""
        return {
            "role": self.role.value,
            "tool_call_id": self.tool_call_id,
            "content": self.content,
        }


Message = Union[SystemMessage, UserMessage, AssistantMessage, ToolMessage]


@dataclass
class ToolDefinition:
    """Definition of a tool available to the LLM."""

    name: str
    description: str
    parameters: dict[str, Any]
    function: Optional[callable] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API calls."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


@dataclass
class LLMResponse:
    """Response from an LLM."""

    content: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    reasoning: Optional[str] = None
    usage: dict[str, int] = field(default_factory=dict)
    model: str = ""
    finish_reason: str = "stop"


@dataclass
class LLMStreamChunk:
    """A chunk of streaming LLM response."""

    delta: str
    delta_reasoning: Optional[str] = None
    tool_calls: list[ToolCall] = field(default_factory=list)
    finish_reason: Optional[str] = None


class LLMError(Exception):
    """Base exception for LLM-related errors."""

    pass


class AuthenticationError(LLMError):
    """Raised when authentication fails."""

    pass


class RateLimitError(LLMError):
    """Raised when rate limit is exceeded."""

    pass


class APIError(LLMError):
    """Raised when an API error occurs."""

    pass


class TimeoutError(LLMError):
    """Raised when a request times out."""

    pass
