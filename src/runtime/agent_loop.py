"""Main agent execution loop."""

import asyncio
import re
from datetime import datetime
from pathlib import Path
from typing import Optional, AsyncIterator

from ..core.config import JavisConfig
from ..core.workspace import WorkspaceManager
from ..llm.driver import LiteLLMDriver
from ..llm.types import (
    Message,
    SystemMessage,
    UserMessage,
    AssistantMessage,
    ToolMessage,
    ToolCall,
    LLMResponse,
    LLMStreamChunk,
)
from ..memory.substrate import MemorySubstrate
from ..tools.base import ToolRegistry


class AgentLoop:
    """Main agent execution loop.

    Manages the lifecycle of an agent including:
    - Loading identity files
    - Building system prompt
    - Calling LLM
    - Executing tools
    - Managing session history
    """

    def __init__(
        self,
        agent_id: str,
        config: JavisConfig,
        memory: MemorySubstrate,
        tool_registry: ToolRegistry,
        workspace_manager: WorkspaceManager,
    ):
        """Initialize the agent loop.

        Args:
            agent_id: The unique agent identifier.
            config: Global Javis configuration.
            memory: Memory substrate for session and KV storage.
            tool_registry: Registry of available tools.
            workspace_manager: Manager for agent workspaces.
        """
        self.agent_id = agent_id
        self.config = config
        self.memory = memory
        self.tool_registry = tool_registry
        self.workspace_manager = workspace_manager

        self.llm = LiteLLMDriver(
            provider=config.llm.provider,
            model=config.llm.model,
            api_key=config.llm.api_key,
            base_url=config.llm.base_url,
            max_tokens=config.llm.max_tokens,
            temperature=config.llm.temperature,
            timeout=config.llm.timeout,
        )

        self.workspace = workspace_manager.get_workspace(agent_id)
        self.max_iterations = config.agents.max_iterations
        self.loop_guard_threshold = config.agents.loop_guard_threshold
        self._tool_call_history: list[str] = []

    def _build_system_prompt(self) -> str:
        """Build the system prompt from identity files.

        Returns:
            The complete system prompt string.
        """
        parts = []

        # Load each identity file
        soul = self.workspace.read_identity_file("SOUL.md") or ""
        user = self.workspace.read_identity_file("USER.md") or ""
        tools = self.workspace.read_identity_file("TOOLS.md") or ""
        memory = self.workspace.read_identity_file("MEMORY.md") or ""
        agents = self.workspace.read_identity_file("AGENTS.md") or ""
        identity = self.workspace.read_identity_file("IDENTITY.md") or ""
        heartbeat = self.workspace.read_identity_file("HEARTBEAT.md") or ""

        # Add identity first
        if identity:
            parts.append(f"IDENTITY:\n{identity}")

        # Add soul with code blocks stripped for security
        if soul:
            parts.append(f"PERSONALITY:\n{self._strip_code_blocks(soul)}")

        # Add other identity files
        if user:
            parts.append(f"USER:\n{user}")
        if tools:
            parts.append(f"TOOLS:\n{tools}")
        if memory:
            parts.append(f"MEMORY:\n{memory}")
        if agents:
            parts.append(f"AGENTS:\n{agents}")
        if heartbeat:
            parts.append(f"SCHEDULED TASKS:\n{heartbeat}")

        # Add default system prompt
        parts.append(f"DEFAULT INSTRUCTIONS:\n{self.config.agents.system_prompt}")

        return "\n\n".join(parts)

    @staticmethod
    def _strip_code_blocks(text: str) -> str:
        """Strip code blocks from text to prevent prompt injection.

        Args:
            text: The text to strip.

        Returns:
            Text with code blocks removed.
        """
        return re.sub(r'```[\s\S]*?```', '', text)

    async def _repair_session(self, session_id: str) -> None:
        """Repair orphaned messages in the session.

        Args:
            session_id: The session ID to repair.
        """
        messages = await self.memory.get_messages(session_id)
        if not messages:
            return

        # Find the last assistant message
        last_assistant_idx = None
        for i, msg in enumerate(messages):
            if msg.get("role") == "assistant":
                last_assistant_idx = i

        # If the last message is not from assistant, the session is orphaned
        if last_assistant_idx != len(messages) - 1:
            # Remove messages after the last assistant message
            orphaned_count = len(messages) - last_assistant_idx - 1
            if orphaned_count > 0:
                # For SQLite, we'd need to delete specific IDs
                # For now, we'll clear and rebuild up to the last assistant
                orphaned_messages = messages[last_assistant_idx + 1:]
                for _ in orphaned_messages:
                    # In a real implementation, we'd delete specific messages
                    pass

    def _check_loop_guard(self, tool_name: str) -> bool:
        """Check if we're in a tool call loop.

        Args:
            tool_name: The tool being called.

        Returns:
            True if loop guard triggers (should stop), False otherwise.
        """
        self._tool_call_history.append(tool_name)
        if len(self._tool_call_history) > self.loop_guard_threshold:
            recent_calls = self._tool_call_history[-self.loop_guard_threshold:]
            if len(set(recent_calls)) <= 2:  # Only 1-2 unique tools
                return True
        return False

    async def _execute_tool(self, tool_call: ToolCall) -> str:
        """Execute a tool call.

        Args:
            tool_call: The tool call to execute.

        Returns:
            The tool result as a string.
        """
        try:
            result = await self.tool_registry.call(tool_call.function, tool_call.arguments)
            return str(result)
        except Exception as e:
            return f"Error: {e}"

    def _prepare_messages(
        self,
        user_input: str,
        session_id: str,
        include_history: bool = True,
    ) -> list[Message]:
        """Prepare messages for the LLM.

        Args:
            user_input: The user's input.
            session_id: The session ID.
            include_history: Whether to include session history.

        Returns:
            List of messages ready for the LLM.
        """
        messages: list[Message] = []

        # Add system prompt
        system_prompt = self._build_system_prompt()
        messages.append(SystemMessage(content=system_prompt))

        # Add session history
        if include_history:
            history = await self.memory.get_messages(session_id)
            for msg in history:  # type: ignore
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if role == "system":
                    messages.append(SystemMessage(content=content))
                elif role == "user":
                    messages.append(UserMessage(content=content))
                elif role == "assistant":
                    messages.append(AssistantMessage(content=content))
                elif role == "tool":
                    tool_call_id = msg.get("metadata", {}).get("tool_call_id", "")
                    is_error = msg.get("metadata", {}).get("is_error", False)
                    messages.append(ToolMessage(
                        content=content,
                        tool_call_id=tool_call_id,
                        is_error=is_error,
                    ))

        # Add current user input
        messages.append(UserMessage(content=user_input))

        return messages

    async def process_message(
        self,
        user_input: str,
        session_id: str,
        stream_callback: Optional[callable] = None,
    ) -> AsyncIterator[str]:
        """Process a user message and yield responses.

        Args:
            user_input: The user's input message.
            session_id: The session ID for conversation history.
            stream_callback: Optional callback for streaming chunks.

        Yields:
            String chunks of the response.
        """
        # Save user message
        await self.memory.append_message(session_id, "user", user_input)

        # Prepare messages
        messages = self._prepare_messages(user_input, session_id)

        # Reset loop guard
        self._tool_call_history = []

        # Main loop
        for iteration in range(self.max_iterations):
            # Check for tool loop
            if iteration > 0 and self._check_loop_guard(""):
                yield "\n[Loop detected: stopping tool execution]"
                break

            # Get available tools
            tools = self.tool_registry.get_llm_tools()

            # Call LLM
            response: LLMResponse | AsyncIterator[LLMStreamChunk]
            if stream_callback:
                response = await self.llm.complete(messages, tools=tools, stream=True)
                content = ""
                async for chunk in response:
                    if chunk.delta:
                        content += chunk.delta
                        yield chunk.delta
                        if stream_callback:
                            stream_callback(chunk.delta)
                    if chunk.delta_reasoning and stream_callback:
                        stream_callback(chunk.delta_reasoning)

                response = LLMResponse(content=content)
            else:
                response = await self.llm.complete(messages, tools=tools, stream=False)

            # Save assistant message
            await self.memory.append_message(
                session_id,
                "assistant",
                response.content,
                metadata={"reasoning": response.reasoning},
            )

            # Check if we have tool calls
            if not response.tool_calls:
                break

            # Execute tools
            for tool_call in response.tool_calls:
                # Check loop guard
                if self._check_loop_guard(tool_call.function):
                    yield f"\n[Loop detected with tool {tool_call.function}]"
                    break

                # Save tool call
                await self.memory.append_message(
                    session_id,
                    "tool",
                    f"Calling tool: {tool_call.function} with args: {tool_call.arguments}",
                    metadata={"tool_call_id": tool_call.id},
                )

                # Execute tool
                result = await self._execute_tool(tool_call)

                # Save tool result
                await self.memory.append_message(
                    session_id,
                    "tool",
                    result,
                    metadata={"tool_call_id": tool_call.id, "is_error": False},
                )

                # Add to messages for next iteration
                messages.append(ToolMessage(
                    content=result,
                    tool_call_id=tool_call.id,
                ))

            # Update system prompt with fresh identity files
            # This allows hot-reloading of identity files
            messages[0] = SystemMessage(content=self._build_system_prompt())


class AgentRuntime:
    """Manages the runtime lifecycle of agents."""

    def __init__(
        self,
        config: JavisConfig,
        memory: MemorySubstrate,
        tool_registry: ToolRegistry,
        workspace_manager: WorkspaceManager,
    ):
        """Initialize the agent runtime.

        Args:
            config: Global Javis configuration.
            memory: Memory substrate.
            tool_registry: Registry of available tools.
            workspace_manager: Manager for agent workspaces.
        """
        self.config = config
        self.memory = memory
        self.tool_registry = tool_registry
        self.workspace_manager = workspace_manager
        self._loops: dict[str, AgentLoop] = {}

    def get_loop(self, agent_id: str) -> AgentLoop:
        """Get or create an agent loop.

        Args:
            agent_id: The agent ID.

        Returns:
            The AgentLoop instance.
        """
        if agent_id not in self._loops:
            self._loops[agent_id] = AgentLoop(
                agent_id,
                self.config,
                self.memory,
                self.tool_registry,
                self.workspace_manager,
            )
        return self._loops[agent_id]

    async def process_message(
        self,
        agent_id: str,
        user_input: str,
        session_id: str,
        stream_callback: Optional[callable] = None,
    ) -> AsyncIterator[str]:
        """Process a message through an agent.

        Args:
            agent_id: The agent ID.
            user_input: The user's input.
            session_id: The session ID.
            stream_callback: Optional callback for streaming.

        Yields:
            Response chunks.
        """
        loop = self.get_loop(agent_id)
        async for chunk in loop.process_message(user_input, session_id, stream_callback):
            yield chunk
