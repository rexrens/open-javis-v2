"""Channel adapter abstract base class."""

import json
from abc import ABC, abstractmethod
from typing import AsyncIterator, Optional

from .types import ChannelMessage, ChannelUser, ChannelContent, ChannelEvent


class ChannelAdapter(ABC):
    """Abstract base class for channel adapters.

    A channel adapter connects Javis to a specific messaging platform
    (e.g., Feishu, Slack, Discord, etc.).
    """

    @abstractmethod
    async def start(self) -> AsyncIterator[ChannelMessage]:
        """Start the channel and yield incoming messages.

        Yields:
            ChannelMessage: Incoming messages from the channel.

        Raises:
            ChannelError: If the channel fails to start or encounters an error.
        """
        ...

    @abstractmethod
    async def send(
        self,
        user: ChannelUser,
        content: str | ChannelContent | list[ChannelContent],
        reply_to: Optional[str] = None,
    ) -> bool:
        """Send a message to a user.

        Args:
            user: The user to send the message to.
            content: The message content (string, ChannelContent, or list).
            reply_to: Optional message ID to reply to.

        Returns:
            bool: True if the message was sent successfully.
        """
        ...

    @abstractmethod
    async def send_typing(self, user: ChannelUser) -> bool:
        """Send a typing indicator to a user.

        Args:
            user: The user to send the typing indicator to.

        Returns:
            bool: True if the typing indicator was sent successfully.
        """
        ...

    @abstractmethod
    async def stop(self) -> None:
        """Stop the channel and clean up resources."""
        ...

    @property
    @abstractmethod
    def is_running(self) -> bool:
        """Check if the channel is currently running."""
        ...

    @property
    @abstractmethod
    def channel_type(self) -> str:
        """Get the channel type identifier."""
        ...


class ChannelError(Exception):
    """Base exception for channel-related errors."""

    pass


class AuthenticationError(ChannelError):
    """Raised when channel authentication fails."""

    pass


class RateLimitError(ChannelError):
    """Raised when channel rate limit is exceeded."""

    pass


class ConnectionError(ChannelError):
    """Raised when channel connection fails."""

    pass


def parse_content(content: str | ChannelContent | list[ChannelContent]) -> list[ChannelContent]:
    """Parse content into a list of ChannelContent objects.

    Args:
        content: Content to parse (string, ChannelContent, or list).

    Returns:
        List of ChannelContent objects.
    """
    if isinstance(content, str):
        return [ChannelContent(type="text", text=content)]
    elif isinstance(content, ChannelContent):
        return [content]
    elif isinstance(content, list):
        return content
    else:
        raise ValueError(f"Invalid content type: {type(content)}")
