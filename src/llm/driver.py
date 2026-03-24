"""LiteLLM driver for unified LLM provider interface."""

import asyncio
from typing import Any, Optional, AsyncIterator, Union

import litellm
from litellm import (
    completion,
    acompletion,
    get_supported_openai_params,
)

from .types import (
    Message,
    SystemMessage,
    UserMessage,
    AssistantMessage,
    ToolMessage,
    ToolCall,
    ToolDefinition,
    LLMResponse,
    LLMStreamChunk,
    LLMError,
    AuthenticationError,
    RateLimitError,
    APIError,
    TimeoutError,
)


class LiteLLMDriver:
    """Driver for LiteLLM with streaming and tool calling support.

    Provides a unified interface to multiple LLM providers including:
    - OpenAI (GPT-3.5, GPT-4, etc.)
    - Anthropic (Claude)
    - Google (Gemini)
    - DeepSeek (deepseek-chat, deepseek-coder, deepseek-reasoner)
    - OpenAI Compatible (vLLM, Ollama, LM Studio, etc.)
    - And 100+ other providers via LiteLLM

    OpenAI Compatible Usage:
        Set provider="openai" and base_url to your service endpoint.
        Example: provider="openai", base_url="http://localhost:8000/v1"
    """

    def __init__(
        self,
        provider: str = "anthropic",
        model: str = "claude-sonnet-4-20250514",
        api_key: str = "",
        base_url: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        timeout: int = 120,
    ):
        """Initialize the LiteLLM driver.

        Args:
            provider: The LLM provider name (e.g., "anthropic", "openai").
            model: The model identifier (e.g., "claude-sonnet-4-20250514", "gpt-4").
            api_key: The API key for the provider.
            base_url: Optional custom base URL for the API.
            max_tokens: Maximum tokens in the response.
            temperature: Sampling temperature (0-2).
            timeout: Request timeout in seconds.
        """
        self.provider = provider
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.timeout = timeout

        # Configure LiteLLM
        litellm.set_verbose = False
        litellm.drop_params = True  # Drop unsupported params
        litellm.api_key = api_key
        if base_url:
            litellm.api_base = base_url

    def _convert_message(self, message: Message) -> dict[str, Any]:
        """Convert a Message to LiteLLM format.

        Args:
            message: The message to convert.

        Returns:
            Dictionary in LiteLLM message format.
        """
        msg_dict = message.to_dict()

        # Handle tool messages
        if isinstance(message, ToolMessage):
            msg_dict["tool_call_id"] = message.tool_call_id

        return msg_dict

    def _convert_messages(self, messages: list[Message]) -> list[dict[str, Any]]:
        """Convert a list of Messages to LiteLLM format.

        Args:
            messages: The messages to convert.

        Returns:
            List of dictionaries in LiteLLM message format.
        """
        return [self._convert_message(msg) for msg in messages]

    def _convert_tools(self, tools: list[ToolDefinition]) -> list[dict[str, Any]]:
        """Convert ToolDefinitions to LiteLLM format.

        Args:
            tools: The tool definitions to convert.

        Returns:
            List of dictionaries in LiteLLM tool format.
        """
        return [tool.to_dict() for tool in tools]

    def _parse_tool_calls(self, response: Any) -> list[ToolCall]:
        """Parse tool calls from a LiteLLM response.

        Args:
            response: The LiteLLM response object.

        Returns:
            List of ToolCall objects.
        """
        tool_calls = []

        if hasattr(response, "choices") and response.choices:
            choice = response.choices[0]
            if hasattr(choice, "message") and hasattr(choice.message, "tool_calls"):
                for tc in choice.message.tool_calls or []:
                    tool_calls.append(ToolCall(
                        id=tc.id,
                        function=tc.function.name,
                        arguments=self._parse_tool_arguments(tc.function.arguments),
                    ))

        return tool_calls

    @staticmethod
    def _parse_tool_arguments(args_str: str) -> dict[str, Any]:
        """Parse tool arguments from JSON string.

        Args:
            args_str: JSON string of arguments.

        Returns:
            Parsed arguments dictionary.
        """
        import json
        try:
            return json.loads(args_str)
        except json.JSONDecodeError:
            return {}

    def _handle_error(self, error: Exception) -> LLMError:
        """Handle LiteLLM exceptions and convert to appropriate error types.

        Args:
            error: The exception to handle.

        Returns:
            An LLMError subclass.
        """
        error_str = str(error).lower()

        if "authentication" in error_str or "api key" in error_str or "401" in error_str:
            return AuthenticationError(str(error))
        elif "rate limit" in error_str or "429" in error_str:
            return RateLimitError(str(error))
        elif "timeout" in error_str:
            return TimeoutError(str(error))
        else:
            return APIError(str(error))

    async def complete(
        self,
        messages: list[Message],
        tools: Optional[list[ToolDefinition]] = None,
        tool_choice: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        stream: bool = False,
        **kwargs,
    ) -> Union[LLMResponse, AsyncIterator[LLMStreamChunk]]:
        """Complete a conversation with the LLM.

        Args:
            messages: List of conversation messages.
            tools: Optional list of available tools.
            tool_choice: Optional tool choice strategy ("auto", "none", "required", or tool name).
            max_tokens: Optional override for max_tokens.
            temperature: Optional override for temperature.
            stream: Whether to stream the response.
            **kwargs: Additional parameters for the LLM.

        Returns:
            LLMResponse if stream=False, or AsyncIterator[LLMStreamChunk] if stream=True.

        Raises:
            LLMError: If the request fails.
        """
        litellm_messages = self._convert_messages(messages)

        request_params: dict[str, Any] = {
            "model": f"{self.provider}/{self.model}" if "/" not in self.model else self.model,
            "messages": litellm_messages,
            "max_tokens": max_tokens or self.max_tokens,
            "temperature": temperature if temperature is not None else self.temperature,
            "timeout": self.timeout,
            **kwargs,
        }

        if tools:
            request_params["tools"] = self._convert_tools(tools)

        if tool_choice:
            request_params["tool_choice"] = tool_choice

        if stream:
            return self._stream_completion(request_params)
        else:
            return self._complete_sync(request_params)

    async def _stream_completion(
        self, request_params: dict[str, Any]
    ) -> AsyncIterator[LLMStreamChunk]:
        """Stream the LLM completion.

        Args:
            request_params: The request parameters.

        Yields:
            LLMStreamChunk objects as they arrive.
        """
        try:
            response = await acompletion(**request_params, stream=True)

            current_tool_calls: dict[str, dict] = {}

            async for chunk in response:
                if hasattr(chunk, "choices") and chunk.choices:
                    choice = chunk.choices[0]

                    # Get delta content
                    delta_content = ""
                    if hasattr(choice, "delta"):
                        delta = choice.delta
                        if hasattr(delta, "content"):
                            delta_content = delta.content or ""

                    # Get reasoning delta (for models with reasoning)
                    delta_reasoning = None
                    if hasattr(choice, "delta") and hasattr(choice.delta, "reasoning"):
                        delta_reasoning = choice.delta.reasoning

                    # Handle streaming tool calls
                    if hasattr(choice, "delta") and hasattr(choice.delta, "tool_calls"):
                        for tc in choice.delta.tool_calls or []:
                            tool_id = tc.id
                            if tool_id and tool_id not in current_tool_calls:
                                current_tool_calls[tool_id] = {"id": tool_id, "function": "", "arguments": ""}

                            if hasattr(tc, "function"):
                                fn = tc.function
                                if hasattr(fn, "name"):
                                    current_tool_calls[tool_id]["function"] = fn.name or ""
                                if hasattr(fn, "arguments"):
                                    current_tool_calls[tool_id]["arguments"] += fn.arguments or ""

                    finish_reason = getattr(choice, "finish_reason", None)

                    # Check if we have complete tool calls
                    tool_calls = []
                    if finish_reason == "tool_calls":
                        for tc_data in current_tool_calls.values():
                            tool_calls.append(ToolCall(
                                id=tc_data["id"],
                                function=tc_data["function"],
                                arguments=self._parse_tool_arguments(tc_data["arguments"]),
                            ))

                    yield LLMStreamChunk(
                        delta=delta_content,
                        delta_reasoning=delta_reasoning,
                        tool_calls=tool_calls,
                        finish_reason=finish_reason,
                    )

        except Exception as e:
            raise self._handle_error(e)

    async def _complete_sync(
        self, request_params: dict[str, Any]
    ) -> LLMResponse:
        """Perform a synchronous (non-streaming) completion.

        Args:
            request_params: The request parameters.

        Returns:
            LLMResponse object.
        """
        try:
            response = await acompletion(**request_params, stream=False)

            # Parse response
            content = ""
            if response.choices:
                content = response.choices[0].message.content or ""

            # Parse tool calls
            tool_calls = self._parse_tool_calls(response)

            # Parse reasoning (if available)
            reasoning = None
            if hasattr(response.choices[0].message, "reasoning"):
                reasoning = response.choices[0].message.reasoning

            # Get usage info
            usage = {}
            if hasattr(response, "usage"):
                usage = {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                }

            return LLMResponse(
                content=content,
                tool_calls=tool_calls,
                reasoning=reasoning,
                usage=usage,
                model=response.model,
                finish_reason=response.choices[0].finish_reason,
            )

        except Exception as e:
            raise self._handle_error(e)

    async def count_tokens(self, messages: list[Message]) -> int:
        """Count tokens in a list of messages.

        Args:
            messages: The messages to count tokens for.

        Returns:
            Estimated token count.
        """
        try:
            from litellm import token_counter

            litellm_messages = self._convert_messages(messages)

            return token_counter(
                model=f"{self.provider}/{self.model}" if "/" not in self.model else self.model,
                messages=litellm_messages,
            )
        except Exception:
            # Fallback to rough estimation
            total_chars = sum(len(msg.to_dict().get("content", "")) for msg in messages)
            return total_chars // 4


def create_driver(
    provider: str = "anthropic",
    model: str = "claude-sonnet-4-20250514",
    api_key: str = "",
    **kwargs,
) -> LiteLLMDriver:
    """Factory function to create a LiteLLM driver.

    Args:
        provider: The LLM provider name.
        model: The model identifier.
        api_key: The API key for the provider.
        **kwargs: Additional driver configuration.

    Returns:
        Configured LiteLLMDriver instance.
    """
    return LiteLLMDriver(
        provider=provider,
        model=model,
        api_key=api_key,
        **kwargs,
    )
