"""Agent workspace and identity files management."""

import os
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from uuid import uuid4
from pathlib import Path

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

    # Default templates directory relative to project root
    TEMPLATES_DIR = Path(__file__).parent.parent.parent / "templates"

    def __init__(self, agent_id: str, workspace_dir: str, copy_templates: bool = False):
        """Initialize a workspace.

        Args:
            agent_id: The agent ID.
            workspace_dir: Base directory for workspaces.
            copy_templates: If True, copy default templates to the workspace.
        """
        self.agent_id = agent_id
        self.path = Path(workspace_dir) / agent_id

        # Create workspace directory if it doesn't exist
        if not self.exists():
            self.path.mkdir(parents=True, exist_ok=True)
            # Create skills folder
            (self.path / "skills").mkdir(exist_ok=True)

        # Copy templates if requested
        if copy_templates:
            self._copy_templates()

        # Ensure identity files exist (only if not using templates)
        if not copy_templates:
            self._ensure_identity_files()

    def exists(self) -> bool:
        """Check if this workspace exists.

        Returns:
            True if the workspace exists, False otherwise.
        """
        return self.path.exists()

    @staticmethod
    def workspace_exists(agent_id: str, workspace_dir: str) -> bool:
        """Check if a workspace exists.

        Args:
            agent_id: The agent ID.
            workspace_dir: Base directory for workspaces.

        Returns:
            True if the workspace exists, False otherwise.
        """
        return (Path(workspace_dir) / agent_id).exists()

    def _copy_templates(self) -> None:
        """Copy default templates to the workspace."""
        templates_dir = self.TEMPLATES_DIR

        # Copy identity files from templates if they exist in templates
        template_files = ["SOUL.md", "USER.md", "TOOLS.md", "AGENTS.md", "HEARTBEAT.md"]
        for filename in template_files:
            template_path = templates_dir / filename
            if template_path.exists():
                dest_path = self.path / filename
                if not dest_path.exists():
                    shutil.copy(template_path, dest_path)

        # Copy memory/MEMORY.md if it exists
        memory_template = templates_dir / "memory" / "MEMORY.md"
        if memory_template.exists():
            memory_dir = self.path / "memory"
            memory_dir.mkdir(exist_ok=True)
            dest_path = memory_dir / "MEMORY.md"
            if not dest_path.exists():
                shutil.copy(memory_template, dest_path)

    def _ensure_identity_files(self) -> None:
        """Ensure all identity files exist."""
        for filename, info in IDENTITY_FILES.items():
            file_path = self.path / filename
            if not file_path.exists():
                # Check if it's MEMORY.md (needs parent directory)
                if filename == "MEMORY.md":
                    memory_dir = self.path / "memory"
                    memory_dir.mkdir(exist_ok=True)
                    file_path = memory_dir / filename
                file_path.write_text("")

    def read_identity_file(self, name: str) -> Optional[str]:
        """Read an identity file.

        Args:
            name: The name of the identity file (e.g., "SOUL.md").

        Returns:
            The file contents or None if file doesn't exist.
        """
        # Handle MEMORY.md which is in memory/ subdirectory
        if name == "MEMORY.md":
            file_path = self.path / "memory" / name
        else:
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

        # Handle MEMORY.md which is in memory/ subdirectory
        if name == "MEMORY.md":
            memory_dir = self.path / "memory"
            memory_dir.mkdir(exist_ok=True)
            file_path = memory_dir / name
        else:
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
    WORKSPACES_DIR = Path(__file__).parent.parent.parent / "workspaces"

    def __init__(self, base_dir: str | None = None):
        """Initialize the workspace manager.

        Args:
            base_dir: Base directory for all workspaces. Defaults to WORKSPACES_DIR.
        """
        self.base_dir = Path(base_dir).expanduser() if base_dir else self.WORKSPACES_DIR
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._workspaces: dict[str, Workspace] = {}
        self._load_existing_workspaces()

    def _load_existing_workspaces(self) -> None:
        """Load all existing workspaces from base_dir."""
        if self.base_dir.exists():
            for item in self.base_dir.iterdir():
                if item.is_dir():
                    agent_id = item.name
                    # Load workspace without copying templates
                    self._workspaces[agent_id] = Workspace(agent_id, str(self.base_dir), copy_templates=False)

    def get_workspace(self, agent_id: str, copy_templates: bool = False) -> Workspace:
        """Get or create a workspace for an agent.

        Args:
            agent_id: The agent ID.
            copy_templates: If True, copy default templates to the workspace.

        Returns:
            The Workspace instance.
        """
        if agent_id not in self._workspaces:
            self._workspaces[agent_id] = Workspace(agent_id, str(self.base_dir), copy_templates=copy_templates)
        return self._workspaces[agent_id]

    def create_workspace(self, agent_id:str, copy_templates: bool = False) -> str:
        """Create a new workspace with a generated ID.

        Args:
            copy_templates: If True, copy default templates to the workspace.

        Returns:
            The new agent ID.
        """
        # Create the workspace immediately
        self.get_workspace(agent_id, copy_templates=copy_templates)
        return agent_id

    def exists(self, agent_id: str) -> bool:
        """Check if a workspace exists.

        Args:
            agent_id: The agent ID.

        Returns:
            True if the workspace exists, False otherwise.
        """
        return Workspace.workspace_exists(agent_id, str(self.base_dir))

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
