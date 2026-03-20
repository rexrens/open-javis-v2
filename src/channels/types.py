"""Channel types and message structures."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional, Union
from datetime import datetime


class ChannelType(Enum):
    """Type of communication channel."""

    FEISHU = "feishu"
    LARK = "lark"
    CLI = "cli"
    WEB = "web"
    TELEGRAM = "telegram"
    SLACK = "slack"
    DISCORD = "discord"


class ContentType(Enum):
    """Type of message content."""

    TEXT = "text"
    POST = "post"
    IMAGE = "image"
    FILE = "file"
    AUDIO = "audio"
    VIDEO = "video"
    COMMAND = "command"


@dataclass
class ChannelUser:
    """Represents a user in a channel."""

    id: str
    name: str
    avatar: Optional[str] = None
    email: Optional[str] = None
    is_bot: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        return self.name


@dataclass
class ChannelContent:
    """Represents message content."""

    type: ContentType
    text: str = ""
    data: dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        return self.text or self.type.value


@dataclass
class ChannelMessage:
    """Represents a message from a channel."""

    id: str
    user: ChannelUser
    content: Union[ChannelContent, list[ChannelContent]]
    channel_type: ChannelType
    timestamp: datetime = field(default_factory=datetime.utcnow)
    reply_to: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def text(self) -> str:
        """Get the text content of the message."""
        if isinstance(self.content, list):
            return "".join(c.text for c in self.content if c.type == ContentType.TEXT)
        return self.content.text

    @property
    def first_text(self) -> str:
        """Get the first text content block."""
        if isinstance(self.content, list):
            for c in self.content:
                if c.type == ContentType.TEXT:
                    return c.text
            return ""
        return self.content.text if self.content.type == ContentType.TEXT else ""


@dataclass
class ChannelEvent:
    """Represents a channel event (typing, status, etc.)."""

    type: str
    user: ChannelUser
    timestamp: datetime = field(default_factory=datetime.utcnow)
    data: dict[str, Any] = field(default_factory=dict)
