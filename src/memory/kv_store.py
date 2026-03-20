"""SQLite-backed key-value storage."""

import aiosqlite
import json
from pathlib import Path
from typing import Any, Optional

from .base import KVStore


class SQLiteKVStore(KVStore):
    """SQLite-based key-value storage implementation."""

    def __init__(self, db_path: str):
        """Initialize the KV store.

        Args:
            db_path: Path to the SQLite database file.
        """
        self.db_path = Path(db_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    async def _get_connection(self) -> aiosqlite.Connection:
        """Get a database connection with the schema initialized."""
        conn = await aiosqlite.connect(str(self.db_path))
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS kv_store (
                namespace TEXT NOT NULL,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (namespace, key)
            )
        """)
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_kv_namespace ON kv_store(namespace)"
        )
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_kv_key ON kv_store(key)"
        )
        await conn.commit()
        return conn

    async def get(self, key: str, namespace: str = "") -> Optional[Any]:
        """Get a value by key."""
        async with await self._get_connection() as conn:
            cursor = await conn.execute(
                "SELECT value FROM kv_store WHERE namespace = ? AND key = ?",
                (namespace, key),
            )
            row = await cursor.fetchone()
            if row:
                try:
                    return json.loads(row[0])
                except json.JSONDecodeError:
                    return row[0]
            return None

    async def set(self, key: str, value: Any, namespace: str = "") -> bool:
        """Set a value by key."""
        try:
            value_json = json.dumps(value) if not isinstance(value, str) else value
        except (TypeError, ValueError):
            # Fallback to string representation
            value_json = str(value)

        async with await self._get_connection() as conn:
            await conn.execute(
                """
                INSERT INTO kv_store (namespace, key, value)
                VALUES (?, ?, ?)
                ON CONFLICT(namespace, key) DO UPDATE SET
                    value = excluded.value,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (namespace, key, value_json),
            )
            await conn.commit()
        return True

    async def delete(self, key: str, namespace: str = "") -> bool:
        """Delete a value by key."""
        async with await self._get_connection() as conn:
            cursor = await conn.execute(
                "DELETE FROM kv_store WHERE namespace = ? AND key = ?",
                (namespace, key),
            )
            await conn.commit()
            return cursor.rowcount > 0

    async def exists(self, key: str, namespace: str = "") -> bool:
        """Check if a key exists."""
        async with await self._get_connection() as conn:
            cursor = await conn.execute(
                "SELECT 1 FROM kv_store WHERE namespace = ? AND key = ?",
                (namespace, key),
            )
            return await cursor.fetchone() is not None

    async def list_keys(self, namespace: str = "", prefix: str = "") -> list[str]:
        """List all keys, optionally filtered by prefix."""
        async with await self._get_connection() as conn:
            if namespace and prefix:
                cursor = await conn.execute(
                    "SELECT key FROM kv_store WHERE namespace = ? AND key LIKE ?",
                    (namespace, f"{prefix}%"),
                )
            elif namespace:
                cursor = await conn.execute(
                    "SELECT key FROM kv_store WHERE namespace = ?",
                    (namespace,),
                )
            elif prefix:
                cursor = await conn.execute(
                    "SELECT key FROM kv_store WHERE key LIKE ?",
                    (f"{prefix}%",),
                )
            else:
                cursor = await conn.execute("SELECT key FROM kv_store")

            rows = await cursor.fetchall()
            return [row[0] for row in rows]

    async def clear_namespace(self, namespace: str) -> bool:
        """Clear all keys in a namespace."""
        async with await self._get_connection() as conn:
            await conn.execute(
                "DELETE FROM kv_store WHERE namespace = ?",
                (namespace,),
            )
            await conn.commit()
        return True

    async def close(self) -> None:
        """Close the database connection."""
        # Connections are created per-call, so nothing to close
        pass
