"""Conversation session management with token tracking."""

import aiosqlite
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from .base import SessionStore


class SQLiteSessionStore(SessionStore):
    """SQLite-based session store with token tracking."""

    def __init__(self, db_path: str, max_messages: int = 200):
        """Initialize the session store.

        Args:
            db_path: Path to the SQLite database file.
            max_messages: Maximum messages to keep per session (for pruning).
        """
        self.db_path = Path(db_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.max_messages = max_messages

    async def _get_connection(self) -> aiosqlite.Connection:
        """Get a database connection with the schema initialized."""
        conn = await aiosqlite.connect(str(self.db_path))
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                token_count INTEGER DEFAULT 0,
                message_count INTEGER DEFAULT 0
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                metadata TEXT,
                token_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
            )
        """)
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id)"
        )
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_messages_created ON messages(created_at)"
        )
        await conn.commit()
        return conn

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        """Estimate token count from text (rough approximation)."""
        # Simple approximation: ~4 characters per token for English
        # This is a rough estimate; actual tokenization depends on the model
        return max(1, len(text) // 4)

    async def _prune_old_messages(self, conn: aiosqlite.Connection, session_id: str) -> None:
        """Prune old messages if exceeding max_messages limit."""
        cursor = await conn.execute(
            "SELECT COUNT(*) FROM messages WHERE session_id = ?",
            (session_id,),
        )
        count = (await cursor.fetchone())[0]

        if count > self.max_messages:
            # Delete oldest messages beyond the limit
            delete_count = count - self.max_messages
            await conn.execute(
                """
                DELETE FROM messages
                WHERE id IN (
                    SELECT id FROM messages
                    WHERE session_id = ?
                    ORDER BY created_at ASC
                    LIMIT ?
                )
                """,
                (session_id, delete_count),
            )

    async def append_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[dict] = None,
    ) -> bool:
        """Append a message to a session."""
        token_count = self._estimate_tokens(content)
        metadata_json = json.dumps(metadata) if metadata else None

        async with await self._get_connection() as conn:
            # Ensure session exists
            await conn.execute(
                """
                INSERT OR IGNORE INTO sessions (id)
                VALUES (?)
                """,
                (session_id,),
            )

            # Insert the message
            await conn.execute(
                """
                INSERT INTO messages (session_id, role, content, metadata, token_count)
                VALUES (?, ?, ?, ?, ?)
                """,
                (session_id, role, content, metadata_json, token_count),
            )

            # Update session stats
            await conn.execute(
                """
                UPDATE sessions
                SET token_count = token_count + ?,
                    message_count = message_count + 1,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (token_count, session_id),
            )

            # Prune if needed
            await self._prune_old_messages(conn, session_id)

            await conn.commit()
        return True

    async def get_messages(
        self, session_id: str, limit: Optional[int] = None
    ) -> list[dict]:
        """Get messages from a session."""
        async with await self._get_connection() as conn:
            if limit:
                cursor = await conn.execute(
                    """
                    SELECT role, content, metadata, created_at
                    FROM messages
                    WHERE session_id = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (session_id, limit),
                )
            else:
                cursor = await conn.execute(
                    """
                    SELECT role, content, metadata, created_at
                    FROM messages
                    WHERE session_id = ?
                    ORDER BY created_at ASC
                    """,
                    (session_id,),
                )

            rows = await cursor.fetchall()

            # Reverse if we limited and got newest first
            if limit:
                rows = list(reversed(rows))

            messages = []
            for row in rows:
                metadata = json.loads(row[2]) if row[2] else None
                messages.append({
                    "role": row[0],
                    "content": row[1],
                    "metadata": metadata,
                    "created_at": row[3],
                })

            return messages

    async def get_message_count(self, session_id: str) -> int:
        """Get the number of messages in a session."""
        async with await self._get_connection() as conn:
            cursor = await conn.execute(
                "SELECT message_count FROM sessions WHERE id = ?",
                (session_id,),
            )
            row = await cursor.fetchone()
            return row[0] if row else 0

    async def get_session_token_count(self, session_id: str) -> int:
        """Get estimated token count for a session."""
        async with await self._get_connection() as conn:
            cursor = await conn.execute(
                "SELECT token_count FROM sessions WHERE id = ?",
                (session_id,),
            )
            row = await cursor.fetchone()
            return row[0] if row else 0

    async def clear_session(self, session_id: str) -> bool:
        """Clear all messages in a session."""
        async with await self._get_connection() as conn:
            await conn.execute(
                "DELETE FROM messages WHERE session_id = ?",
                (session_id,),
            )
            await conn.execute(
                """
                UPDATE sessions
                SET token_count = 0,
                    message_count = 0,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (session_id,),
            )
            await conn.commit()
        return True

    async def delete_session(self, session_id: str) -> bool:
        """Delete a session entirely."""
        async with await self._get_connection() as conn:
            cursor = await conn.execute(
                "DELETE FROM sessions WHERE id = ?",
                (session_id,),
            )
            await conn.commit()
            return cursor.rowcount > 0

    async def list_sessions(self) -> list[dict]:
        """List all sessions."""
        async with await self._get_connection() as conn:
            cursor = await conn.execute(
                """
                SELECT id, created_at, updated_at, token_count, message_count
                FROM sessions
                ORDER BY updated_at DESC
                """
            )
            rows = await cursor.fetchall()
            return [{
                "id": row[0],
                "created_at": row[1],
                "updated_at": row[2],
                "token_count": row[3],
                "message_count": row[4],
            } for row in rows]
