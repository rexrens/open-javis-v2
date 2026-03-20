"""Base memory trait/interface."""

from abc import ABC, abstractmethod
from typing import Any, Optional, Protocol


class KVStore(Protocol):
    """Protocol for key-value storage operations."""

    async def get(self, key: str, namespace: str = "") -> Optional[Any]:
        """Get a value by key."""
        ...

    async def set(self, key: str, value: Any, namespace: str = "") -> bool:
        """Set a value by key."""
        ...

    async def delete(self, key: str, namespace: str = "") -> bool:
        """Delete a value by key."""
        ...

    async def exists(self, key: str, namespace: str = "") -> bool:
        """Check if a key exists."""
        ...

    async def list_keys(self, namespace: str = "", prefix: str = "") -> list[str]:
        """List all keys, optionally filtered by prefix."""
        ...

    async def clear_namespace(self, namespace: str) -> bool:
        """Clear all keys in a namespace."""
        ...


class SessionStore(Protocol):
    """Protocol for session/conversation storage operations."""

    async def append_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[dict] = None,
    ) -> bool:
        """Append a message to a session."""
        ...

    async def get_messages(
        self, session_id: str, limit: Optional[int] = None
    ) -> list[dict]:
        """Get messages from a session."""
        ...

    async def get_message_count(self, session_id: str) -> int:
        """Get the number of messages in a session."""
        ...

    async def get_session_token_count(self, session_id: str) -> int:
        """Get estimated token count for a session."""
        ...

    async def clear_session(self, session_id: str) -> bool:
        """Clear all messages in a session."""
        ...

    async def delete_session(self, session_id: str) -> bool:
        """Delete a session entirely."""
        ...


class SemanticStore(Protocol):
    """Protocol for semantic/vector storage operations."""

    async def add(
        self,
        text: str,
        embedding: Optional[list[float]] = None,
        metadata: Optional[dict] = None,
    ) -> str:
        """Add a document to the vector store. Returns document ID."""
        ...

    async def search(
        self,
        query: str,
        top_k: int = 10,
        filter_metadata: Optional[dict] = None,
    ) -> list[dict]:
        """Search for similar documents."""
        ...

    async def delete(self, doc_id: str) -> bool:
        """Delete a document by ID."""
        ...


class KnowledgeStore(Protocol):
    """Protocol for knowledge graph storage operations."""

    async def add_entity(self, entity: str, attributes: Optional[dict] = None) -> bool:
        """Add an entity to the knowledge graph."""
        ...

    async def add_relation(
        self, subject: str, predicate: str, object: str
    ) -> bool:
        """Add a relation (triple) to the knowledge graph."""
        ...

    async def get_entity_relations(self, entity: str) -> list[dict]:
        """Get all relations for an entity."""
        ...

    async def query_triples(
        self,
        subject: Optional[str] = None,
        predicate: Optional[str] = None,
        object: Optional[str] = None,
    ) -> list[dict]:
        """Query the knowledge graph for matching triples."""
        ...


class Memory(ABC):
    """Abstract base class for unified memory substrate."""

    @abstractmethod
    async def get_kv(self, key: str, namespace: str = "") -> Optional[Any]:
        """Get a value from the key-value store."""
        ...

    @abstractmethod
    async def set_kv(self, key: str, value: Any, namespace: str = "") -> bool:
        """Set a value in the key-value store."""
        ...

    @abstractmethod
    async def delete_kv(self, key: str, namespace: str = "") -> bool:
        """Delete a value from the key-value store."""
        ...

    @abstractmethod
    async def kv_exists(self, key: str, namespace: str = "") -> bool:
        """Check if a key exists in the key-value store."""
        ...

    @abstractmethod
    async def list_kv_keys(self, namespace: str = "", prefix: str = "") -> list[str]:
        """List keys in the key-value store."""
        ...

    @abstractmethod
    async def append_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[dict] = None,
    ) -> bool:
        """Append a message to a session."""
        ...

    @abstractmethod
    async def get_messages(
        self, session_id: str, limit: Optional[int] = None
    ) -> list[dict]:
        """Get messages from a session."""
        ...

    @abstractmethod
    async def get_message_count(self, session_id: str) -> int:
        """Get the number of messages in a session."""
        ...

    @abstractmethod
    async def get_session_token_count(self, session_id: str) -> int:
        """Get estimated token count for a session."""
        ...

    @abstractmethod
    async def clear_session(self, session_id: str) -> bool:
        """Clear all messages in a session."""
        ...

    @abstractmethod
    async def delete_session(self, session_id: str) -> bool:
        """Delete a session entirely."""
        ...

    async def add_semantic(
        self,
        text: str,
        embedding: Optional[list[float]] = None,
        metadata: Optional[dict] = None,
    ) -> str:
        """Add a document to semantic store. Returns doc ID."""
        raise NotImplementedError("Semantic memory not enabled")

    async def search_semantic(
        self,
        query: str,
        top_k: int = 10,
        filter_metadata: Optional[dict] = None,
    ) -> list[dict]:
        """Search semantic store for similar documents."""
        raise NotImplementedError("Semantic memory not enabled")

    async def delete_semantic(self, doc_id: str) -> bool:
        """Delete a document from semantic store."""
        raise NotImplementedError("Semantic memory not enabled")

    async def add_entity(self, entity: str, attributes: Optional[dict] = None) -> bool:
        """Add an entity to the knowledge graph."""
        raise NotImplementedError("Knowledge memory not enabled")

    async def add_relation(
        self, subject: str, predicate: str, object: str
    ) -> bool:
        """Add a relation to the knowledge graph."""
        raise NotImplementedError("Knowledge memory not enabled")

    async def get_entity_relations(self, entity: str) -> list[dict]:
        """Get relations for an entity."""
        raise NotImplementedError("Knowledge memory not enabled")

    async def query_triples(
        self,
        subject: Optional[str] = None,
        predicate: Optional[str] = None,
        object: Optional[str] = None,
    ) -> list[dict]:
        """Query the knowledge graph."""
        raise NotImplementedError("Knowledge memory not enabled")
