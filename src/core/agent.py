"""Agent lifecycle, registry, and scheduler."""

import asyncio
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Callable, Awaitable
from uuid import uuid4

from .workspace import WorkspaceManager


class AgentState(Enum):
    """Agent execution state."""

    RUNNING = "running"
    SUSPENDED = "suspended"
    TERMINATED = "terminated"


@dataclass
class AgentInfo:
    """Information about an agent."""

    id: str
    name: str
    state: AgentState
    session_id: str
    created_at: float
    permissions: list[str]

    def __str__(self) -> str:
        return f"Agent(id={self.id}, name={self.name}, state={self.state.value})"


class Permission:
    """Capability-based permission system."""

    # Permission categories
    CATEGORY_TOOLS = "tools"
    CATEGORY_LLM = "llm"
    CATEGORY_MEMORY = "memory"
    CATEGORY_CHANNELS = "channels"
    CATEGORY_FS = "filesystem"

    # Standard permissions
    ALL = "*"

    # Tool permissions
    TOOLS_BASIC = "tools.basic"  # Read-only tools
    TOOLS_EXEC = "tools.exec"    # Execute tools
    TOOLS_WRITE = "tools.write"  # Write tools
    TOOLS_SYSTEM = "tools.system"  # System-level tools

    # LLM permissions
    LLM_READ = "llm.read"
    LLM_WRITE = "llm.write"
    LLM_STREAM = "llm.stream"

    # Memory permissions
    MEMORY_READ = "memory.read"
    MEMORY_WRITE = "memory.write"
    MEMORY_DELETE = "memory.delete"

    # Channel permissions
    CHANNEL_READ = "channel.read"
    CHANNEL_WRITE = "channel.write"

    # Filesystem permissions
    FS_READ = "fs.read"
    FS_WRITE = "fs.write"
    FS_DELETE = "fs.delete"

    @staticmethod
    def has_permission(permissions: list[str], required: str) -> bool:
        """Check if a set of permissions includes the required permission.

        Args:
            permissions: List of granted permissions.
            required: The permission to check for.

        Returns:
            True if permission is granted.
        """
        # Wildcard grants all
        if Permission.ALL in permissions:
            return True

        # Exact match
        if required in permissions:
            return True

        # Category match (e.g., "tools.*" matches any tool permission)
        for perm in permissions:
            if perm.endswith(".*"):
                category = perm[:-2]
                if required.startswith(category + "."):
                    return True

        return False


class Agent:
    """Represents an agent in the system."""

    def __init__(
        self,
        name: str = "assistant",
        permissions: Optional[list[str]] = None,
        workspace_manager: Optional[WorkspaceManager] = None,
    ):
        """Initialize an agent.

        Args:
            name: The agent name.
            permissions: List of granted permissions.
            workspace_manager: Optional workspace manager.
        """
        self.id = str(uuid4())
        self.name = name
        self.state = AgentState.RUNNING
        self.session_id = str(uuid4())
        self.created_at = asyncio.get_event_loop().time()
        self.permissions = permissions or [Permission.ALL]

        if workspace_manager:
            self.workspace = workspace_manager.get_workspace(self.id)
        else:
            self.workspace = None

    @property
    def info(self) -> AgentInfo:
        """Get agent information."""
        return AgentInfo(
            id=self.id,
            name=self.name,
            state=self.state,
            session_id=self.session_id,
            created_at=self.created_at,
            permissions=self.permissions,
        )

    def has_permission(self, permission: str) -> bool:
        """Check if the agent has a specific permission.

        Args:
            permission: The permission to check.

        Returns:
            True if permission is granted.
        """
        return Permission.has_permission(self.permissions, permission)

    def set_state(self, state: AgentState) -> None:
        """Set the agent state.

        Args:
            state: The new state.
        """
        self.state = state

    def suspend(self) -> None:
        """Suspend the agent."""
        self.set_state(AgentState.SUSPENDED)

    def resume(self) -> None:
        """Resume the agent."""
        self.set_state(AgentState.RUNNING)

    def terminate(self) -> None:
        """Terminate the agent."""
        self.set_state(AgentState.TERMINATED)


class AgentRegistry:
    """Registry for managing active agents.

    Similar to Rust's DashMap for concurrent access.
    """

    def __init__(self):
        """Initialize the agent registry."""
        self._agents: dict[str, Agent] = {}
        self._lock = asyncio.Lock()

    async def register(self, agent: Agent) -> Agent:
        """Register an agent.

        Args:
            agent: The agent to register.

        Returns:
            The registered agent.
        """
        async with self._lock:
            self._agents[agent.id] = agent
            return agent

    async def get(self, agent_id: str) -> Optional[Agent]:
        """Get an agent by ID.

        Args:
            agent_id: The agent ID.

        Returns:
            The agent or None if not found.
        """
        async with self._lock:
            return self._agents.get(agent_id)

    async def get_by_session(self, session_id: str) -> Optional[Agent]:
        """Get an agent by session ID.

        Args:
            session_id: The session ID.

        Returns:
            The agent or None if not found.
        """
        async with self._lock:
            for agent in self._agents.values():
                if agent.session_id == session_id:
                    return agent
            return None

    async def remove(self, agent_id: str) -> bool:
        """Remove an agent from the registry.

        Args:
            agent_id: The agent ID.

        Returns:
            True if agent was removed, False if not found.
        """
        async with self._lock:
            if agent_id in self._agents:
                del self._agents[agent_id]
                return True
            return False

    async def list_all(self) -> list[AgentInfo]:
        """List all registered agents.

        Returns:
            List of agent information.
        """
        async with self._lock:
            return [agent.info for agent in self._agents.values()]

    async def list_by_state(self, state: AgentState) -> list[AgentInfo]:
        """List agents by state.

        Args:
            state: The state to filter by.

        Returns:
            List of agent information.
        """
        async with self._lock:
            return [agent.info for agent in self._agents.values() if agent.state == state]

    async def count(self) -> int:
        """Count all registered agents.

        Returns:
            Number of agents.
        """
        async with self._lock:
            return len(self._agents)


class QuotaTracker:
    """Tracks and enforces resource quotas."""

    def __init__(
        self,
        max_concurrent: int = 10,
        max_requests_per_minute: int = 100,
    ):
        """Initialize the quota tracker.

        Args:
            max_concurrent: Maximum concurrent operations.
            max_requests_per_minute: Maximum requests per minute.
        """
        self.max_concurrent = max_concurrent
        self.max_requests_per_minute = max_requests_per_minute
        self._active = 0
        self._lock = asyncio.Lock()
        self._request_timestamps: list[float] = []

    async def acquire(self) -> bool:
        """Acquire a quota slot.

        Returns:
            True if quota was acquired, False otherwise.
        """
        async with self._lock:
            # Check concurrent limit
            if self._active >= self.max_concurrent:
                return False

            # Clean old timestamps (older than 1 minute)
            now = asyncio.get_event_loop().time()
            self._request_timestamps = [
                ts for ts in self._request_timestamps
                if now - ts < 60
            ]

            # Check rate limit
            if len(self._request_timestamps) >= self.max_requests_per_minute:
                return False

            # Acquire quota
            self._active += 1
            self._request_timestamps.append(now)
            return True

    async def release(self) -> None:
        """Release a quota slot."""
        async with self._lock:
            self._active = max(0, self._active - 1)


class AgentScheduler:
    """Scheduler for managing agent execution with throttling."""

    def __init__(
        self,
        quota_tracker: Optional[QuotaTracker] = None,
    ):
        """Initialize the scheduler.

        Args:
            quota_tracker: Optional quota tracker.
        """
        self.quota = quota_tracker or QuotaTracker()

    async def schedule(self, agent_id: str, task: Callable[[], Awaitable]) -> None:
        """Schedule a task for an agent.

        Args:
            agent_id: The agent ID.
            task: The task to execute.
        """
        while not await self.quota.acquire():
            # Wait for quota to become available
            await asyncio.sleep(0.1)

        try:
            await task()
        finally:
            await self.quota.release()

    async def schedule_with_callback(
        self,
        agent_id: str,
        task: Callable[[], Awaitable],
        callback: Callable[[], Awaitable],
    ) -> None:
        """Schedule a task with a completion callback.

        Args:
            agent_id: The agent ID.
            task: The task to execute.
            callback: Callback to run after task completion.
        """
        await self.schedule(agent_id, task)
        await callback()
