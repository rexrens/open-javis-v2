"""Configuration management for Open-Javis."""

import os
import tomli
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


@dataclass
class LLMConfig:
    """LLM provider configuration."""

    provider: str = "anthropic"
    model: str = "claude-sonnet-4-20250514"
    api_key: str = ""
    api_key_env: str = "ANTHROPIC_API_KEY"
    base_url: Optional[str] = None
    max_tokens: int = 4096
    temperature: float = 0.7
    timeout: int = 120

    def __post_init__(self):
        """Load API key from environment if not set directly."""
        if not self.api_key and self.api_key_env:
            self.api_key = os.environ.get(self.api_key_env, "")


@dataclass
class FeishuConfig:
    """Feishu/Lark channel configuration."""

    app_id: str = ""
    app_secret: str = ""
    app_secret_env: str = "FEISHU_APP_SECRET"
    region: str = "cn"  # "cn" for Feishu, "intl" for Lark
    verify_token: str = ""
    encrypt_key: str = ""
    enabled: bool = False

    def __post_init__(self):
        """Load app secret from environment if not set directly."""
        if not self.app_secret and self.app_secret_env:
            self.app_secret = os.environ.get(self.app_secret_env, "")

    @property
    def api_base(self) -> str:
        """Get the API base URL based on region."""
        if self.region == "intl":
            return "https://open.larksuite.com"
        return "https://open.feishu.cn"

    @property
    def ws_base(self) -> str:
        """Get the WebSocket base URL based on region."""
        if self.region == "intl":
            return "wss://open.larksuite.com"
        return "wss://open.feishu.cn"


@dataclass
class DatabaseConfig:
    """Database configuration."""

    path: str = "~/.javis/javis.db"

    def __post_init__(self):
        """Expand tilde to home directory."""
        self.path = os.path.expanduser(self.path)


@dataclass
class AgentConfig:
    """Default agent configuration."""

    system_prompt: str = "You are a helpful personal assistant."
    max_iterations: int = 100
    loop_guard_threshold: int = 50


@dataclass
class MemoryConfig:
    """Memory configuration."""

    session_max_messages: int = 200
    semantic_enabled: bool = False
    semantic_provider: str = "qdrant"
    semantic_url: str = "http://localhost:6333"
    knowledge_enabled: bool = False


@dataclass
class MCPConfig:
    """MCP (Model Context Protocol) configuration."""

    enabled_servers: list[str] = field(default_factory=list)
    timeout: int = 30


@dataclass
class JavisConfig:
    """Main Open-Javis configuration."""

    llm: LLMConfig = field(default_factory=LLMConfig)
    feishu: FeishuConfig = field(default_factory=FeishuConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    agents: AgentConfig = field(default_factory=AgentConfig)
    memory: MemoryConfig = field(default_factory=MemoryConfig)
    mcp: MCPConfig = field(default_factory=MCPConfig)

    workspace_dir: str = "~/.javis/workspaces"
    agents_dir: str = "agents"
    skills_dir: str = "skills"

    def __post_init__(self):
        """Expand tilde paths."""
        self.workspace_dir = os.path.expanduser(self.workspace_dir)
        self.agents_dir = os.path.expanduser(self.agents_dir)
        self.skills_dir = os.path.expanduser(self.skills_dir)

    @classmethod
    def load(cls, path: Optional[str] = None) -> "JavisConfig":
        """Load configuration from a TOML file.

        Args:
            path: Path to config file. If None, looks for config/javis.toml.

        Returns:
            JavisConfig instance.

        Raises:
            FileNotFoundError: If config file not found.
        """
        if path is None:
            path = "config/javis.toml"

        config_path = Path(path)
        if not config_path.exists():
            return cls()

        with open(config_path, "rb") as f:
            data = tomli.load(f)

        return cls._from_dict(data)

    @classmethod
    def _from_dict(cls, data: dict[str, Any]) -> "JavisConfig":
        """Create config from dictionary."""
        config = cls()

        if "llm" in data:
            llm_data = data["llm"]
            config.llm = LLMConfig(
                provider=llm_data.get("provider", config.llm.provider),
                model=llm_data.get("model", config.llm.model),
                api_key=llm_data.get("api_key", ""),
                api_key_env=llm_data.get("api_key_env", config.llm.api_key_env),
                base_url=llm_data.get("base_url"),
                max_tokens=llm_data.get("max_tokens", config.llm.max_tokens),
                temperature=llm_data.get("temperature", config.llm.temperature),
                timeout=llm_data.get("timeout", config.llm.timeout),
            )

        if "channels" in data and "feishu" in data["channels"]:
            feishu_data = data["channels"]["feishu"]
            config.feishu = FeishuConfig(
                app_id=feishu_data.get("app_id", ""),
                app_secret=feishu_data.get("app_secret", ""),
                app_secret_env=feishu_data.get("app_secret_env", config.feishu.app_secret_env),
                region=feishu_data.get("region", config.feishu.region),
                verify_token=feishu_data.get("verify_token", ""),
                encrypt_key=feishu_data.get("encrypt_key", ""),
                enabled=feishu_data.get("enabled", True),
            )

        if "database" in data:
            db_data = data["database"]
            config.database = DatabaseConfig(
                path=db_data.get("path", config.database.path),
            )

        if "agents" in data:
            agents_data = data["agents"]
            if "default" in agents_data:
                default_data = agents_data["default"]
                config.agents = AgentConfig(
                    system_prompt=default_data.get("system_prompt", config.agents.system_prompt),
                    max_iterations=default_data.get("max_iterations", config.agents.max_iterations),
                    loop_guard_threshold=default_data.get(
                        "loop_guard_threshold", config.agents.loop_guard_threshold
                    ),
                )

        if "memory" in data:
            memory_data = data["memory"]
            config.memory = MemoryConfig(
                session_max_messages=memory_data.get("session_max_messages", config.memory.session_max_messages),
                semantic_enabled=memory_data.get("semantic_enabled", config.memory.semantic_enabled),
                semantic_provider=memory_data.get("semantic_provider", config.memory.semantic_provider),
                semantic_url=memory_data.get("semantic_url", config.memory.semantic_url),
                knowledge_enabled=memory_data.get("knowledge_enabled", config.memory.knowledge_enabled),
            )

        if "mcp" in data:
            mcp_data = data["mcp"]
            config.mcp = MCPConfig(
                enabled_servers=mcp_data.get("enabled_servers", []),
                timeout=mcp_data.get("timeout", config.mcp.timeout),
            )

        return config
