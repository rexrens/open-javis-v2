"""Unified memory substrate implementing all memory stores."""

from typing import Any, Optional

from .base import Memory
from .kv_store import SQLiteKVStore
from .session import SQLiteSessionStore


class MemorySubstrate(Memory):
    """Unified memory substrate combining KV store and session management."""

    def __init__(
        self,
        db_path: str = "~/.javis/javis.db",
        max_session_messages: int = 200,
    ):
        """Initialize the memory substrate.

        Args:
            db_path: Path to the SQLite database file.
            max_session_messages: Maximum messages per session before pruning.
        """
        self.db_path = db_path
        self.kv_store = SQLiteKVStore(db_path)
        self.session_store = SQLiteSessionStore(db_path, max_session_messages)

    async def get_kv(self, key: str, namespace: str = "") -> Optional[Any]:
        """Get a value from the key-value store."""
        return await self.kv_store.get(key, namespace)

    async def set_kv(self, key: str, value: Any, namespace: str = "") -> bool:
        """Set a value in the key-value store."""
        return await self.kv_store.set(key, value, namespace)

    async def delete_kv(self, key: str, namespace: str = "") -> bool:
        """Delete a value from the key-value store."""
        return await self.kv_store.delete(key, namespace)

    async def kv_exists(self, key: str, namespace: str = "") -> bool:
        """Check if a key exists in the key-value store."""
        return await self.kv_store.exists(key, namespace)

    async def list_kv_keys(self, namespace: str = "", prefix: str = "") -> list[str]:
        """List keys in the key-value store."""
        return await self.kv_store.list_keys(namespace, prefix)

    async def append_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[dict] = None,
    ) -> bool:
        """Append a message to a session."""
        return await self.session_store.append_message(session_id, role, content, metadata)

    async def get_messages(
        self, session_id: str, limit: Optional[int] = None
    ) -> list[dict]:
        """Get messages from a session."""
        return await self.session_store.get_messages(session_id, limit)

    async def get_message_count(self, session_id: str) -> int:
        """Get the number of messages in a session."""
        return await self.session_store.get_message_count(session_id)

    async def get_session_token_count(self, session_id: str) -> int:
        """Get estimated token count for a session."""
        return await self.session_store.get_session_token_count(session_id)

    async def clear_session(self, session_id: str) -> bool:
        """Clear all messages in a session."""
        return await self.session_store.clear_session(session_id)

    async def delete_session(self, session_id: str) -> bool:
        """Delete a session entirely."""
        return await self.session_store.delete_session(session_id)

    async def close(self) -> None:
        """Close all database connections."""
        await self.kv_store.close()


# Create singleton instance for backward compatibility
_default_memory: Optional[MemorySubstrate] = None


def get_memory(db_path: str = "~/.javis/javis.db", max_session_messages: int = 200) -> MemorySubstrate:
    """Get or create the default memory substrate instance."""
    global _default_memory
    if _default_memory is None:
        _default_memory = MemorySubstrate(db_path, max_session_messages)
    return _default_memory
