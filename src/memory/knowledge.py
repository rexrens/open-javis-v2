"""Entity-relation knowledge graph for memory."""

from dataclasses import dataclass, field
from typing import Any, Optional, List, Dict, Tuple
from enum import Enum


class RelationType(Enum):
    """Types of relations in the knowledge graph."""

    # Basic relations
    IS_A = "is_a"
    HAS = "has"
    PART_OF = "part_of"
    RELATED_TO = "related_to"

    # Social/person relations
    KNOWS = "knows"
    FRIEND_OF = "friend_of"
    WORKS_WITH = "works_with"
    FAMILY_OF = "family_of"

    # Temporal relations
    BEFORE = "before"
    AFTER = "after"
    DURING = "during"

    # Spatial relations
    LOCATED_AT = "located_at"
    NEAR = "near"

    # Attribute relations
    HAS_ATTRIBUTE = "has_attribute"
    HAS_PROPERTY = "has_property"

    # Causal relations
    CAUSED_BY = "caused_by"
    CAUSES = "causes"

    # Preference relations
    LIKES = "likes"
    DISLIKES = "dislikes"
    PREFERS = "prefers"


@dataclass
class Entity:
    """Represents an entity in the knowledge graph."""

    id: str
    name: str
    entity_type: str = "default"
    attributes: Dict[str, Any] = field(default_factory=dict)
    created_at: float = 0

    def __post_init__(self):
        """Set created_at if not provided."""
        import asyncio
        if self.created_at == 0:
            self.created_at = asyncio.get_event_loop().time()


@dataclass
class Relation:
    """Represents a relation between entities."""

    id: str
    subject: str  # Entity ID
    predicate: str  # Relation type or custom predicate
    object: str  # Entity ID or literal value
    weight: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = 0

    def __post_init__(self):
        """Set created_at if not provided."""
        import asyncio
        if self.created_at == 0:
            self.created_at = asyncio.get_event_loop().time()

    @property
    def is_entity_relation(self) -> bool:
        """Check if this is a relation between entities."""
        return self.predicate.startswith("is_") or self.predicate.startswith("has_")


@dataclass
class Triple:
    """Represents a knowledge triple (subject, predicate, object)."""

    subject: str
    predicate: str
    object: Any

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "subject": self.subject,
            "predicate": self.predicate,
            "object": self.object,
        }


class KnowledgeStore:
    """In-memory knowledge graph store."""

    def __init__(self):
        """Initialize the knowledge store."""
        self._entities: Dict[str, Entity] = {}
        self._relations: Dict[str, List[Relation]] = {}
        self._relation_counter = 0

    async def add_entity(
        self,
        name: str,
        entity_type: str = "default",
        attributes: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Add an entity to the knowledge graph.

        Args:
            name: The entity name.
            entity_type: The entity type.
            attributes: Optional entity attributes.

        Returns:
            The entity ID.
        """
        import hashlib
        entity_id = hashlib.md5(name.encode()).hexdigest()

        if entity_id not in self._entities:
            self._entities[entity_id] = Entity(
                id=entity_id,
                name=name,
                entity_type=entity_type,
                attributes=attributes or {},
            )
        else:
            # Update attributes if entity exists
            if attributes:
                self._entities[entity_id].attributes.update(attributes)

        return entity_id

    async def get_entity(self, entity_id: str) -> Optional[Entity]:
        """Get an entity by ID.

        Args:
            entity_id: The entity ID.

        Returns:
            The entity or None.
        """
        return self._entities.get(entity_id)

    async def get_entity_by_name(self, name: str) -> Optional[Entity]:
        """Get an entity by name.

        Args:
            name: The entity name.

        Returns:
            The entity or None.
        """
        import hashlib
        entity_id = hashlib.md5(name.encode()).hexdigest()
        return self._entities.get(entity_id)

    async def list_entities(self, entity_type: Optional[str] = None) -> List[Entity]:
        """List all entities, optionally filtered by type.

        Args:
            entity_type: Optional entity type filter.

        Returns:
            List of entities.
        """
        entities = list(self._entities.values())
        if entity_type:
            entities = [e for e in entities if e.entity_type == entity_type]
        return entities

    async def add_relation(
        self,
        subject: str,
        predicate: str,
        object: Any,
        weight: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Add a relation to the knowledge graph.

        Args:
            subject: Subject entity ID or name.
            predicate: The relation predicate.
            object: Object entity ID, name, or literal value.
            weight: Optional weight for the relation.
            metadata: Optional metadata.

        Returns:
            The relation ID.
        """
        self._relation_counter += 1
        relation_id = f"rel_{self._relation_counter}"

        # Resolve subject
        if subject in self._entities:
            subject_id = subject
        else:
            # Try to find entity by name
            entity = await self.get_entity_by_name(subject)
            subject_id = entity.id if entity else subject

        # Resolve object
        if isinstance(object, str) and object in self._entities:
            object_id = object
        else:
            entity = await self.get_entity_by_name(object) if isinstance(object, str) else None
            object_id = entity.id if entity else object

        relation = Relation(
            id=relation_id,
            subject=subject_id,
            predicate=predicate,
            object=object_id,
            weight=weight,
            metadata=metadata or {},
        )

        if subject_id not in self._relations:
            self._relations[subject_id] = []

        self._relations[subject_id].append(relation)

        return relation_id

    async def get_entity_relations(self, entity_id: str) -> List[Tuple[Relation, Optional[Entity]]]:
        """Get all relations for an entity.

        Args:
            entity_id: The entity ID.

        Returns:
            List of (relation, related_entity) tuples.
        """
        results: List[Tuple[Relation, Optional[Entity]]] = []

        # Outgoing relations (subject = entity_id)
        if entity_id in self._relations:
            for relation in self._relations[entity_id]:
                related = self._entities.get(str(relation.object)) if isinstance(relation.object, str) else None
                results.append((relation, related))

        # Incoming relations (object = entity_id)
        for subj_id, relations in self._relations.items():
            for relation in relations:
                if str(relation.object) == entity_id:
                    related = self._entities.get(subj_id)
                    results.append((relation, related))

        return results

    async def query_triples(
        self,
        subject: Optional[str] = None,
        predicate: Optional[str] = None,
        object: Optional[Any] = None,
    ) -> List[Triple]:
        """Query the knowledge graph for matching triples.

        Args:
            subject: Optional subject filter.
            predicate: Optional predicate filter.
            object: Optional object filter.

        Returns:
            List of matching triples.
        """
        triples: List[Triple] = []

        for subj_id, relations in self._relations.items():
            subj_entity = self._entities.get(subj_id)
            subj_name = subj_entity.name if subj_entity else subj_id

            for relation in relations:
                # Check subject filter
                if subject is not None:
                    if subj_id != subject and subj_name != subject:
                        continue

                # Check predicate filter
                if predicate is not None and relation.predicate != predicate:
                    continue

                # Check object filter
                if object is not None:
                    obj_entity = self._entities.get(str(relation.object)) if isinstance(relation.object, str) else None
                    obj_name = obj_entity.name if obj_entity else None

                    if relation.object != object and obj_name != object:
                        continue

                # Add matching triple
                obj_value = relation.object
                if isinstance(relation.object, str):
                    obj_entity = self._entities.get(relation.object)
                    if obj_entity:
                        obj_value = obj_entity.name

                triples.append(Triple(
                    subject=subj_name,
                    predicate=relation.predicate,
                    object=obj_value,
                ))

        return triples

    async def find_path(
        self,
        start: str,
        end: str,
        max_depth: int = 3,
    ) -> Optional[List[Triple]]:
        """Find a path between two entities.

        Args:
            start: Start entity name or ID.
            end: End entity name or ID.
            max_depth: Maximum path length.

        Returns:
            List of triples representing the path, or None.
        """
        from collections import deque

        # Resolve start and end
        start_entity = await self.get_entity_by_name(start) if isinstance(start, str) else None
        end_entity = await self.get_entity_by_name(end) if isinstance(end, str) else None

        start_id = start_entity.id if start_entity else start
        end_id = end_entity.id if end_entity else end

        # BFS search
        queue = deque([(start_id, [])])
        visited = {start_id}

        while queue:
            current, path = queue.popleft()

            if current == end_id and path:
                return path

            if len(path) >= max_depth:
                continue

            # Get outgoing relations
            for relation in self._relations.get(current, []):
                next_id = relation.object
                if not isinstance(next_id, str) or next_id in visited:
                    continue

                visited.add(next_id)

                # Build triple
                subj_name = (self._entities.get(current) or type("obj", (), {"name": current})).name
                obj_name = (self._entities.get(next_id) or type("obj", (), {"name": next_id})).name

                new_path = path + [Triple(subj_name, relation.predicate, obj_name)]
                queue.append((next_id, new_path))

        return None

    async def delete_entity(self, entity_id: str) -> bool:
        """Delete an entity and all its relations.

        Args:
            entity_id: The entity ID.

        Returns:
            True if deleted successfully.
        """
        if entity_id not in self._entities:
            return False

        # Remove entity
        del self._entities[entity_id]

        # Remove relations where entity is subject
        if entity_id in self._relations:
            del self._relations[entity_id]

        # Remove relations where entity is object
        for subj_id, relations in self._relations.items():
            self._relations[subj_id] = [
                r for r in relations if str(r.object) != entity_id
            ]

        return True

    async def clear(self) -> None:
        """Clear all entities and relations."""
        self._entities.clear()
        self._relations.clear()
        self._relation_counter = 0
