"""Skill system for loading and managing skills."""

from dataclasses import dataclass
import os
import re
import yaml
from pathlib import Path
from typing import Optional, List, Dict, Any

from .base import ToolDefinition, ToolRegistry, ToolCategory, ToolResult


class PromptInjectionError(Exception):
    """Raised when potential prompt injection is detected."""

    pass


def scan_for_prompt_injection(text: str) -> bool:
    """Scan text for potential prompt injection patterns.

    Args:
        text: The text to scan.

    Returns:
        True if potential injection detected.
    """
    # Check for common injection patterns
    injection_patterns = [
        r"(ignore|override|disregard)\s+(previous|above|all)\s+(instructions?|prompts?|commands?)",
        r"(new|updated|revised)\s+(instructions?|prompt|system\s+message)",
        r"act\s+as\s+(?:a|an)\s+.*?(?:assistant|ai|bot)",
        r"<\|.*?\|>",  # Special token patterns
        r"<<.*?>>",      # Another special token pattern
    ]

    text_lower = text.lower()
    for pattern in injection_patterns:
        if re.search(pattern, text_lower, re.IGNORECASE):
            return True

    return False


@dataclass
class Skill:
    """Represents a loaded skill."""

    name: str
    description: str
    content: str
    frontmatter: Dict[str, Any]
    path: Path

    def to_tool_definition(self) -> ToolDefinition:
        """Convert to a ToolDefinition.

        Returns:
            ToolDefinition for this skill.
        """
        return ToolDefinition(
            name=f"skill_{self.name}",
            description=self.description,
            parameters={
                "type": "object",
                "properties": {},
                "required": [],
            },
            category=ToolCategory.SKILL,
        )


class SkillLoader:
    """Loads and manages skills from a directory."""

    def __init__(self, skills_dir: str = "skills"):
        """Initialize the skill loader.

        Args:
            skills_dir: Directory containing skill files.
        """
        self.skills_dir = Path(skills_dir).expanduser()
        self.skills_dir.mkdir(parents=True, exist_ok=True)
        self._skills: Dict[str, Skill] = {}

    def load_all(self) -> List[Skill]:
        """Load all skills from the skills directory.

        Returns:
            List of loaded skills.
        """
        skills = []

        for skill_file in self.skills_dir.glob("*.md"):
            try:
                skill = self.load_file(skill_file)
                if skill:
                    skills.append(skill)
            except Exception:
                continue

        self._skills = {s.name: s for s in skills}
        return skills

    def load_file(self, path: Path) -> Optional[Skill]:
        """Load a skill from a file.

        Args:
            path: Path to the skill file.

        Returns:
            Loaded Skill or None if invalid.
        """
        content = path.read_text(encoding="utf-8")

        # Parse YAML frontmatter
        frontmatter: Dict[str, Any] = {}
        body = content

        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 2:
                try:
                    frontmatter = yaml.safe_load(parts[1]) or {}
                    body = parts[2].lstrip("\n")
                except yaml.YAMLError:
                    body = content

        # Extract skill metadata
        name = frontmatter.get("name", path.stem)
        description = frontmatter.get("description", "")

        # Scan for prompt injection
        if scan_for_prompt_injection(body):
            raise PromptInjectionError(f"Potential prompt injection in skill: {name}")

        return Skill(
            name=name,
            description=description,
            content=body,
            frontmatter=frontmatter,
            path=path,
        )

    def get_skill(self, name: str) -> Optional[Skill]:
        """Get a skill by name.

        Args:
            name: The skill name.

        Returns:
            The Skill or None if not found.
        """
        return self._skills.get(name)

    def list_skills(self) -> List[str]:
        """List all skill names.

        Returns:
            List of skill names.
        """
        return list(self._skills.keys())

    def get_all(self) -> List[Skill]:
        """Get all loaded skills.

        Returns:
            List of all skills.
        """
        return list(self._skills.values())


class SkillRegistry:
    """Registry that integrates skills with the tool system."""

    def __init__(self, tool_registry: ToolRegistry, skills_dir: str = "skills"):
        """Initialize the skill registry.

        Args:
            tool_registry: The tool registry to register skills with.
            skills_dir: Directory containing skill files.
        """
        self.tool_registry = tool_registry
        self.loader = SkillLoader(skills_dir)
        self._reload()

    def _reload(self) -> None:
        """Reload all skills."""
        skills = self.loader.load_all()

        # Remove existing skill tools
        for tool in self.tool_registry.list_by_category(ToolCategory.SKILL):
            self.tool_registry.remove(tool.name)

        # Register new skill tools
        for skill in skills:
            # Skills are context/prompts, not executable tools
            # We store them in KV storage instead
            pass

    def get_skill_content(self, name: str) -> Optional[str]:
        """Get the content of a skill.

        Args:
            name: The skill name.

        Returns:
            The skill content or None.
        """
        skill = self.loader.get_skill(name)
        if skill:
            return skill.content
        return None

    def get_skill_prompt(self, name: str) -> Optional[str]:
        """Get the full prompt for a skill (name + content).

        Args:
            name: The skill name.

        Returns:
            The skill prompt or None.
        """
        skill = self.loader.get_skill(name)
        if skill:
            return f"# {skill.name}\n\n{skill.content}"
        return None

    def list_skills(self) -> List[str]:
        """List all available skill names.

        Returns:
            List of skill names.
        """
        return self.loader.list_skills()

    def reload(self) -> None:
        """Reload skills from disk."""
        self._reload()
