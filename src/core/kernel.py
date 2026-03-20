"""Central coordinator for Open-Javis."""

import asyncio
from typing import Optional, AsyncIterator

from .config import JavisConfig
from .agent import Agent, AgentRegistry, AgentScheduler, AgentState
from .workspace import WorkspaceManager
from ..channels.base import ChannelAdapter, ChannelError
from ..channels.feishu import FeishuAdapter
from ..llm.driver import LiteLLMDriver
from ..memory.substrate import MemorySubstrate
from ..tools.base import ToolRegistry
from ..tools.mcp_client import MCPClient
from ..tools.skills import SkillRegistry
from ..runtime.agent_loop import AgentRuntime


class Kernel:
    """Central coordinator for Open-Javis.

    Manages all subsystems:
    - Agent lifecycle
    - Message dispatch and routing
    - Channel management
    - Tool and skill loading
    - Memory management
    - Graceful shutdown
    """

    def __init__(self, config: Optional[JavisConfig] = None):
        """Initialize the kernel.

        Args:
            config: Optional Javis configuration. If None, loads from file.
        """
        self.config = config or JavisConfig.load()

        # Initialize core subsystems
        self.workspace_manager = WorkspaceManager(self.config.workspace_dir)
        self.memory = MemorySubstrate(self.config.database.path, self.config.memory.session_max_messages)
        self.agent_registry = AgentRegistry()
        self.scheduler = AgentScheduler()
        self.tool_registry = ToolRegistry()
        self.runtime = AgentRuntime(
            self.config,
            self.memory,
            self.tool_registry,
            self.workspace_manager,
        )

        # Initialize MCP client
        self.mcp_client = MCPClient(self.tool_registry)

        # Initialize skill registry
        self.skill_registry = SkillRegistry(self.tool_registry, self.config.skills_dir)

        # Initialize channels
        self._channels: list[ChannelAdapter] = []

        # State
        self._running = False
        self._shutdown_event = asyncio.Event()

    async def start(self) -> None:
        """Start the kernel and all subsystems."""
        if self._running:
            return

        self._running = True
        self._shutdown_event.clear()

        # Load MCP servers if configured
        for server_name in self.config.mcp.enabled_servers:
            # MCP servers are configured as commands in the config
            # For now, we'll skip as the exact format needs to be defined
            pass

        # Load skills
        self.skill_registry.reload()

        # Initialize Feishu channel if configured
        if self.config.feishu.enabled and self.config.feishu.app_id:
            feishu = FeishuAdapter(
                app_id=self.config.feishu.app_id,
                app_secret=self.config.feishu.app_secret,
                region=self.config.feishu.region,
                verify_token=self.config.feishu.verify_token,
                encrypt_key=self.config.feishu.encrypt_key,
            )
            self._channels.append(feishu)

    async def stop(self) -> None:
        """Stop the kernel and all subsystems."""
        if not self._running:
            return

        self._running = False
        self._shutdown_event.set()

        # Stop all channels
        for channel in self._channels:
            await channel.stop()
        self._channels.clear()

        # Stop MCP servers
        await self.mcp_client.stop_all()

    async def run(self) -> None:
        """Run the kernel main loop.

        This starts all channels and processes incoming messages.
        """
        await self.start()

        try:
            # Create tasks for each channel
            tasks = []
            for channel in self._channels:
                tasks.append(asyncio.create_task(self._run_channel(channel)))

            # Wait for shutdown or channel tasks to complete
            done, pending = await asyncio.wait(
                tasks + [asyncio.create_task(self._shutdown_event.wait())],
                return_when=asyncio.FIRST_COMPLETED,
            )

            # Cancel pending tasks
            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        finally:
            await self.stop()

    async def _run_channel(self, channel: ChannelAdapter) -> None:
        """Run a channel and process messages.

        Args:
            channel: The channel to run.
        """
        try:
            async for message in channel.start():
                await self._dispatch_message(message, channel)
        except ChannelError as e:
            # Channel error, log and continue
            pass
        except Exception:
            # Unexpected error, log and continue
            pass

    async def _dispatch_message(
        self,
        message,
        channel: ChannelAdapter,
    ) -> None:
        """Dispatch a message to the appropriate agent.

        Args:
            message: The incoming message.
            channel: The channel that received the message.
        """
        # Find or create agent for the user
        user_id = message.user.id
        agent = await self.agent_registry.get_by_session(user_id)

        if not agent:
            # Create new agent for this user
            agent = Agent(
                name=f"user_{user_id}",
                workspace_manager=self.workspace_manager,
            )
            await self.agent_registry.register(agent)

        # Check if agent is running
        if agent.state != AgentState.RUNNING:
            return

        # Process message through agent
        await self.scheduler.schedule(
            agent.id,
            lambda: self._process_message_async(agent, message, channel),
        )

    async def _process_message_async(
        self,
        agent: Agent,
        message,
        channel: ChannelAdapter,
    ) -> None:
        """Process a message through an agent.

        Args:
            agent: The agent to use.
            message: The message to process.
            channel: The channel for sending responses.
        """
        try:
            # Collect response chunks
            response_chunks = []
            async for chunk in self.runtime.process_message(
                agent.id,
                message.text,
                agent.session_id,
            ):
                response_chunks.append(chunk)

            # Send response
            if response_chunks:
                await channel.send(message.user, "".join(response_chunks))

        except Exception:
            # Error processing message
            await channel.send(
                message.user,
                "Sorry, I encountered an error processing your message.",
            )

    async def spawn_agent(
        self,
        name: str = "assistant",
        permissions: Optional[list[str]] = None,
    ) -> Agent:
        """Spawn a new agent.

        Args:
            name: The agent name.
            permissions: Optional list of permissions.

        Returns:
            The spawned agent.
        """
        agent = Agent(
            name=name,
            permissions=permissions,
            workspace_manager=self.workspace_manager,
        )
        await self.agent_registry.register(agent)
        return agent

    async def kill_agent(self, agent_id: str) -> bool:
        """Kill an agent.

        Args:
            agent_id: The agent ID.

        Returns:
            True if agent was killed.
        """
        agent = await self.agent_registry.get(agent_id)
        if agent:
            agent.terminate()
            await self.agent_registry.remove(agent_id)
            self.workspace_manager.delete_workspace(agent_id)
            return True
        return False

    async def list_agents(self) -> list:
        """List all agents.

        Returns:
            List of agent info.
        """
        return await self.agent_registry.list_all()

    async def chat(
        self,
        message: str,
        agent_id: Optional[str] = None,
    ) -> AsyncIterator[str]:
        """Send a chat message and get a response.

        Args:
            message: The message to send.
            agent_id: Optional agent ID. If None, creates/uses a default agent.

        Yields:
            Response chunks.
        """
        # Get or create agent
        if agent_id:
            agent = await self.agent_registry.get(agent_id)
        else:
            # Create a default agent
            agent = await self.spawn_agent("default")

        if not agent:
            raise ValueError("Agent not found")

        # Process message
        async for chunk in self.runtime.process_message(
            agent.id,
            message,
            agent.session_id,
        ):
            yield chunk

    async def add_tool(self, tool_def) -> None:
        """Add a tool to the registry.

        Args:
            tool_def: The tool definition to add.
        """
        self.tool_registry.register(tool_def)

    async def list_tools(self) -> list:
        """List all available tools.

        Returns:
            List of tool definitions.
        """
        return self.tool_registry.list_all()

    def register_builtin_tools(self) -> None:
        """Register built-in tools."""
        from ..tools.builtin import register_builtin_tools
        register_builtin_tools(self.tool_registry)
