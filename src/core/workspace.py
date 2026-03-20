"""Agent workspace and identity files management."""

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from uuid import uuid4


@dataclass
class IdentityFileInfo:
    """Information about an identity file."""

    name: str
    description: str
    max_size: int
    required: bool


# Identity file definitions with their constraints
IDENTITY_FILES = {
    "SOUL.md": IdentityFileInfo(
        name="SOUL.md",
        description="Agent personality and character (1,000 chars)",
        max_size=1000,
        required=False,
    ),
    "USER.md": IdentityFileInfo(
        name="USER.md",
        description="User preferences and context (500 chars)",
        max_size=500,
        required=False,
    ),
    "TOOLS.md": IdentityFileInfo(
        name="TOOLS.md",
        description="Tool usage preferences (500 chars)",
        max_size=500,
        required=False,
    ),
    "MEMORY.md": IdentityFileInfo(
        name="MEMORY.md",
        description="Memory retrieval preferences (500 chars)",
        max_size=500,
        required=False,
    ),
    "AGENTS.md": IdentityFileInfo(
        name="AGENTS.md",
        description="Agent delegation preferences (2,000 chars)",
        max_size=2000,
        required=False,
    ),
    "BOOTSTRAP.md": IdentityFileInfo(
        name="BOOTSTRAP.md",
        description="Initial setup instructions",
        max_size=32000,
        required=False,
    ),
    "IDENTITY.md": IdentityFileInfo(
        name="IDENTITY.md",
        description="Agent identity (500 chars)",
        max_size=500,
        required=False,
    ),
    "HEARTBEAT.md": IdentityFileInfo(
        name="HEARTBEAT.md",
        description="Scheduled tasks (1,000 chars)",
        max_size=1000,
        required=False,
    ),
}

# Maximum file size to prevent stuffing
MAX_FILE_SIZE = 32 * 1024  # 32KB


class Workspace:
    """Represents an agent's workspace directory."""

    def __init__(self, agent_id: str, workspace_dir: str):
        """Initialize a workspace.

        Args:
            agent_id: The agent ID.
            workspace_dir: Base directory for workspaces.
        """
        self.agent_id = agent_id
        self.path = Path(workspace_dir) / agent_id
        self.path.mkdir(parents=True, exist_ok=True)

        # Create identity files if they don't exist
        self._ensure_identity_files()

    def _ensure_identity_files(self) -> None:
        """Ensure all identity files exist."""
        for filename, info in IDENTITY_FILES.items():
            file_path = self.path / filename
            if not file_path.exists():
                file_path.write_text("")

    def read_identity_file(self, name: str) -> Optional[str]:
        """Read an identity file.

        Args:
            name: The name of the identity file (e.g., "SOUL.md").

        Returns:
            The file contents or None if file doesn't exist.
        """
        file_path = self.path / name
        if not file_path.exists():
            return None

        # Check file size
        size = file_path.stat().st_size
        if size > MAX_FILE_SIZE:
            raise ValueError(f"Identity file {name} exceeds maximum size of {MAX_FILE_SIZE} bytes")

        content = file_path.read_text(encoding="utf-8")

        # Check specific file size limits
        if name in IDENTITY_FILES:
            info = IDENTITY_FILES[name]
            if len(content) > info.max_size:
                # Truncate to max size
                content = content[:info.max_size]

        # Strip code blocks from SOUL.md for security
        if name == "SOUL.md":
            content = self._strip_code_blocks(content)

        return content

    def write_identity_file(self, name: str, content: str) -> None:
        """Write to an identity file.

        Args:
            name: The name of the identity file.
            content: The content to write.
        """
        # Validate file name
        if name not in IDENTITY_FILES:
            raise ValueError(f"Unknown identity file: {name}")

        # Validate size
        info = IDENTITY_FILES[name]
        if len(content) > MAX_FILE_SIZE:
            raise ValueError(f"Content exceeds maximum file size of {MAX_FILE_SIZE} bytes")

        if len(content) > info.max_size:
            # Truncate to max size
            content = content[:info.max_size]

        file_path = self.path / name
        file_path.write_text(content, encoding="utf-8")

    @staticmethod
    def _strip_code_blocks(text: str) -> str:
        """Strip code blocks from text to prevent prompt injection.

        Args:
            text: The text to strip.

        Returns:
            Text with code blocks removed.
        """
        return re.sub(r'```[\s\S]*?```', '', text)

    def list_files(self) -> list[str]:
        """List all files in the workspace.

        Returns:
            List of file paths relative to workspace.
        """
        files = []
        for item in self.path.iterdir():
            if item.is_file():
                files.append(item.name)
        return files

    def delete_file(self, name: str) -> bool:
        """Delete a file from the workspace.

        Args:
            name: The name of the file to delete.

        Returns:
            True if file was deleted, False if it didn't exist.
        """
        file_path = self.path / name
        if file_path.exists():
            file_path.unlink()
            return True
        return False

    def get_path(self, name: Optional[str] = None) -> Path:
        """Get the workspace path or a specific file path.

        Args:
            name: Optional file name.

        Returns:
            The path object.
        """
        if name:
            return self.path / name
        return self.path


class WorkspaceManager:
    """Manages agent workspaces."""

    def __init__(self, base_dir: str = "~/.javis/workspaces"):
        """Initialize the workspace manager.

        Args:
            base_dir: Base directory for all workspaces.
        """
        self.base_dir = Path(base_dir).expanduser()
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._workspaces: dict[str, Workspace] = {}

    def get_workspace(self, agent_id: str) -> Workspace:
        """Get or create a workspace for an agent.

        Args:
            agent_id: The agent ID.

        Returns:
            The Workspace instance.
        """
        if agent_id not in self._workspaces:
            self._workspaces[agent_id] = Workspace(agent_id, str(self.base_dir))
        return self._workspaces[agent_id]

    def create_workspace(self) -> str:
        """Create a new workspace with a generated ID.

        Returns:
            The new agent ID.
        """
        agent_id = str(uuid4())
        return agent_id

    def delete_workspace(self, agent_id: str) -> bool:
        """Delete a workspace.

        Args:
            agent_id: The agent ID.

        Returns:
            True if workspace was deleted, False if it didn't exist.
        """
        if agent_id in self._workspaces:
            del self._workspaces[agent_id]

        workspace_path = self.base_dir / agent_id
        if workspace_path.exists():
            import shutil
            shutil.rmtree(workspace_path)
            return True
        return False

    def list_workspaces(self) -> list[str]:
        """List all workspace IDs.

        Returns:
            List of agent IDs.
        """
        workspaces = []
        for item in self.base_dir.iterdir():
            if item.is_dir():
                workspaces.append(item.name)
        return workspaces

    def get_workspace_info(self, agent_id: str) -> Optional[dict]:
        """Get information about a workspace.

        Args:
            agent_id: The agent ID.

        Returns:
            Dictionary with workspace info or None.
        """
        workspace_path = self.base_dir / agent_id
        if not workspace_path.exists():
            return None

        stat = workspace_path.stat()
        return {
            "agent_id": agent_id,
            "path": str(workspace_path),
            "created": stat.st_ctime,
            "modified": stat.st_mtime,
            "size": sum(f.stat().st_size for f in workspace_path.rglob("*") if f.is_file()),
        }
