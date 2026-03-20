"""Vector embedding and semantic search for memory."""

import asyncio
from typing import Any, Optional, List
from abc import ABC, abstractmethod


class EmbeddingProvider(ABC):
    """Abstract base class for embedding providers."""

    @abstractmethod
    async def embed(self, text: str) -> List[float]:
        """Generate embedding for text.

        Args:
            text: The text to embed.

        Returns:
            The embedding vector.
        """
        ...

    @abstractmethod
    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts.

        Args:
            texts: The texts to embed.

        Returns:
            List of embedding vectors.
        """
        ...


class SentenceTransformerProvider(EmbeddingProvider):
    """Sentence Transformer embedding provider.

    Uses sentence-transformers for local embeddings.
    """

    def __init__(self, model: str = "all-MiniLM-L6-v2"):
        """Initialize the provider.

        Args:
            model: The model name to use.
        """
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(model)
            self._loop = asyncio.get_event_loop()
        except ImportError:
            raise ImportError(
                "sentence-transformers is required for semantic memory. "
                "Install with: pip install sentence-transformers"
            )

    async def embed(self, text: str) -> List[float]:
        """Generate embedding for text."""
        return await self._loop.run_in_executor(
            None,
            lambda: self.model.encode(text, convert_to_numpy=True).tolist(),
        )

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        return await self._loop.run_in_executor(
            None,
            lambda: self.model.encode(texts, convert_to_numpy=True).tolist(),
        )


class LiteLLMEmbeddingProvider(EmbeddingProvider):
    """LiteLLM-based embedding provider.

    Supports OpenAI, Anthropic, Cohere, and other providers.
    """

    def __init__(
        self,
        provider: str = "openai",
        model: str = "text-embedding-3-small",
        api_key: str = "",
    ):
        """Initialize the provider.

        Args:
            provider: The embedding provider.
            model: The embedding model.
            api_key: The API key.
        """
        self.provider = provider
        self.model = model
        self.api_key = api_key

    async def embed(self, text: str) -> List[float]:
        """Generate embedding for text."""
        return (await self.embed_batch([text]))[0]

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        try:
            import litellm
        except ImportError:
            raise ImportError("litellm is required for embeddings. Install with: pip install litellm")

        response = await litellm.aembedding(
            model=f"{self.provider}/{self.model}" if "/" not in self.model else self.model,
            input=texts,
            api_key=self.api_key,
        )

        return [item["embedding"] for item in response["data"]]


class VectorStore(ABC):
    """Abstract base class for vector stores."""

    @abstractmethod
    async def add(
        self,
        doc_id: str,
        embedding: List[float],
        metadata: Optional[dict] = None,
    ) -> bool:
        """Add a document to the store.

        Args:
            doc_id: Unique document identifier.
            embedding: The embedding vector.
            metadata: Optional metadata.

        Returns:
            True if added successfully.
        """
        ...

    @abstractmethod
    async def search(
        self,
        query_embedding: List[float],
        top_k: int = 10,
        filter_metadata: Optional[dict] = None,
    ) -> List[dict]:
        """Search for similar documents.

        Args:
            query_embedding: The query embedding.
            top_k: Number of results to return.
            filter_metadata: Optional metadata filter.

        Returns:
            List of results with doc_id, score, and metadata.
        """
        ...

    @abstractmethod
    async def delete(self, doc_id: str) -> bool:
        """Delete a document.

        Args:
            doc_id: The document identifier.

        Returns:
            True if deleted successfully.
        """
        ...


class QdrantStore(VectorStore):
    """Qdrant vector store implementation."""

    def __init__(
        self,
        url: str = "http://localhost:6333",
        collection_name: str = "javis_memory",
        vector_size: int = 384,
    ):
        """Initialize the Qdrant store.

        Args:
            url: Qdrant server URL.
            collection_name: Name of the collection.
            vector_size: Size of embedding vectors.
        """
        try:
            from qdrant_client import QdrantClient, models
            from qdrant_client.async_client import AsyncQdrantClient

            self._QdrantClient = QdrantClient
            self._AsyncQdrantClient = AsyncQdrantClient
            self._models = models
        except ImportError:
            raise ImportError(
                "qdrant-client is required for Qdrant store. "
                "Install with: pip install qdrant-client"
            )

        self.url = url
        self.collection_name = collection_name
        self.vector_size = vector_size
        self._client: Optional[AsyncQdrantClient] = None

    async def _get_client(self) -> "AsyncQdrantClient":
        """Get or create the Qdrant client."""
        if self._client is None:
            self._client = self._AsyncQdrantClient(url=self.url)

        # Ensure collection exists
        collections = await self._client.get_collections()
        collection_names = [c.name for c in collections.collections]

        if self.collection_name not in collection_names:
            await self._client.create_collection(
                collection_name=self.collection_name,
                vectors_config=self._models.VectorParams(
                    size=self.vector_size,
                    distance=self._models.Distance.COSINE,
                ),
            )

        return self._client

    async def add(
        self,
        doc_id: str,
        embedding: List[float],
        metadata: Optional[dict] = None,
    ) -> bool:
        """Add a document to the store."""
        client = await self._get_client()

        await client.upsert(
            collection_name=self.collection_name,
            points=[self._models.PointStruct(
                id=doc_id,
                vector=embedding,
                payload=metadata or {},
            )],
        )

        return True

    async def search(
        self,
        query_embedding: List[float],
        top_k: int = 10,
        filter_metadata: Optional[dict] = None,
    ) -> List[dict]:
        """Search for similar documents."""
        client = await self._get_client()

        # Build filter if provided
        query_filter = None
        if filter_metadata:
            conditions = []
            for key, value in filter_metadata.items():
                conditions.append(
                    self._models.FieldCondition(
                        key=key,
                        match=self._models.MatchValue(value=value),
                    )
                )
            query_filter = self._models.Filter(must=conditions)

        results = await client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            limit=top_k,
            query_filter=query_filter,
        )

        return [
            {
                "doc_id": r.id,
                "score": r.score,
                "metadata": r.payload,
            }
            for r in results
        ]

    async def delete(self, doc_id: str) -> bool:
        """Delete a document."""
        client = await self._get_client()

        await client.delete(
            collection_name=self.collection_name,
            points_selector=self._models.PointIdsList(points=[doc_id]),
        )

        return True


class InMemoryVectorStore(VectorStore):
    """In-memory vector store for testing/simple use."""

    def __init__(self):
        """Initialize the in-memory store."""
        self._vectors: dict[str, tuple[List[float], dict]] = {}

    async def add(
        self,
        doc_id: str,
        embedding: List[float],
        metadata: Optional[dict] = None,
    ) -> bool:
        """Add a document."""
        self._vectors[doc_id] = (embedding, metadata or {})
        return True

    async def search(
        self,
        query_embedding: List[float],
        top_k: int = 10,
        filter_metadata: Optional[dict] = None,
    ) -> List[dict]:
        """Search for similar documents."""
        results = []

        for doc_id, (embedding, metadata) in self._vectors.items():
            # Apply metadata filter
            if filter_metadata:
                match = True
                for key, value in filter_metadata.items():
                    if metadata.get(key) != value:
                        match = False
                        break
                if not match:
                    continue

            # Calculate cosine similarity
            score = self._cosine_similarity(query_embedding, embedding)
            results.append({"doc_id": doc_id, "score": score, "metadata": metadata})

        # Sort by score and return top_k
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    @staticmethod
    def _cosine_similarity(a: List[float], b: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        import math
        dot_product = sum(x * y for x, y in zip(a, b))
        magnitude_a = math.sqrt(sum(x * x for x in a))
        magnitude_b = math.sqrt(sum(y * y for y in b))

        if magnitude_a == 0 or magnitude_b == 0:
            return 0.0

        return dot_product / (magnitude_a * magnitude_b)

    async def delete(self, doc_id: str) -> bool:
        """Delete a document."""
        if doc_id in self._vectors:
            del self._vectors[doc_id]
            return True
        return False


class SemanticMemory:
    """Semantic memory using vector embeddings."""

    def __init__(
        self,
        embedding_provider: Optional[EmbeddingProvider] = None,
        vector_store: Optional[VectorStore] = None,
    ):
        """Initialize semantic memory.

        Args:
            embedding_provider: The embedding provider to use.
            vector_store: The vector store to use.
        """
        self.embedding_provider = embedding_provider or SentenceTransformerProvider()
        self.vector_store = vector_store or InMemoryVectorStore()
        self._doc_counter = 0

    async def add(
        self,
        text: str,
        metadata: Optional[dict] = None,
        doc_id: Optional[str] = None,
    ) -> str:
        """Add a document to semantic memory.

        Args:
            text: The text to add.
            metadata: Optional metadata.
            doc_id: Optional document ID. If None, one is generated.

        Returns:
            The document ID.
        """
        if doc_id is None:
            self._doc_counter += 1
            doc_id = f"doc_{self._doc_counter}"

        embedding = await self.embedding_provider.embed(text)
        await self.vector_store.add(doc_id, embedding, metadata)

        return doc_id

    async def search(
        self,
        query: str,
        top_k: int = 10,
        filter_metadata: Optional[dict] = None,
    ) -> List[dict]:
        """Search for similar documents.

        Args:
            query: The search query.
            top_k: Number of results.
            filter_metadata: Optional metadata filter.

        Returns:
            List of results with doc_id, score, and metadata.
        """
        query_embedding = await self.embedding_provider.embed(query)
        return await self.vector_store.search(query_embedding, top_k, filter_metadata)

    async def delete(self, doc_id: str) -> bool:
        """Delete a document.

        Args:
            doc_id: The document ID.

        Returns:
            True if deleted successfully.
        """
        return await self.vector_store.delete(doc_id)
