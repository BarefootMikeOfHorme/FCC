"""Persistent memory store using ChromaDB and SentenceTransformers for long-term memory storage."""

import os
import json
import hashlib
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, asdict

import chromadb
from chromadb.config import Settings as ChromaSettings
from sentence_transformers import SentenceTransformer

from free_claude_code.config.settings import Settings as FCCSettings
from free_claude_code.core.security import encrypt_api_key, decrypt_api_key

logger = logging.getLogger(__name__)


@dataclass
class MemoryItem:
    """Represents a single memory item with metadata."""
    id: str
    content: str
    embedding: Optional[List[float]] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: Optional[str] = None
    accessed_at: Optional[str] = None
    access_count: int = 0
    importance_score: float = 0.5  # 0.0 to 1.0
    tags: Optional[List[str]] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.tags is None:
            self.tags = []
        if self.created_at is None:
            self.created_at = datetime.utcnow().isoformat()
        if self.accessed_at is None:
            self.accessed_at = self.created_at


class PersistentMemoryStore:
    """
    Persistent memory store for long-term storage of conversations, facts, decisions, and preferences.

    Uses ChromaDB for vector storage and SentenceTransformers for local embedding generation.
    Designed for GDPR compliance with secure deletion capabilities.
    """

    def __init__(self, settings: FCCSettings):
        """Initialize the persistent memory store.

        Args:
            settings: Application settings instance
        """
        self.settings = settings
        self._embedding_model: Optional[SentenceTransformer] = None
        self._chroma_client: Optional[chromadb.PersistentClient] = None
        self._collection: Optional[chromadb.Collection] = None

        # Initialize storage directory
        self._storage_dir = Path.home() / ".fcc" / "memory"
        self._storage_dir.mkdir(parents=True, exist_ok=True)

        # ChromaDB directory
        self._chroma_dir = self._storage_dir / "chroma"
        self._chroma_dir.mkdir(parents=True, exist_ok=True)

        # Collection name
        self._collection_name = "fcc_persistent_memory"

        logger.info(f"Persistent memory store initialized at {self._storage_dir}")

    def _get_embedding_model(self) -> SentenceTransformer:
        """Lazy load the SentenceTransformer model."""
        if self._embedding_model is None:
            logger.info("Loading SentenceTransformer model for embeddings...")
            # Use a lightweight, efficient model for local embeddings
            model_name = "all-MiniLM-L6-v2"  # Good balance of speed and quality
            self._embedding_model = SentenceTransformer(model_name)
            logger.info(f"Loaded embedding model: {model_name}")
        return self._embedding_model

    def _get_chroma_client(self) -> chromadb.PersistentClient:
        """Lazy initialize ChromaDB client."""
        if self._chroma_client is None:
            logger.info("Initializing ChromaDB client...")
            self._chroma_client = chromadb.PersistentClient(
                path=str(self._chroma_dir),
                settings=ChromaSettings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            logger.info(f"ChromaDB client initialized at {self._chroma_dir}")
        return self._chroma_client

    def _get_collection(self) -> chromadb.Collection:
        """Get or create the ChromaDB collection."""
        if self._collection is None:
            client = self._get_chroma_client()
            try:
                # Try to get existing collection
                self._collection = client.get_collection(name=self._collection_name)
                logger.info(f"Retrieved existing ChromaDB collection: {self._collection_name}")
            except Exception:
                # Create new collection if it doesn't exist
                self._collection = client.create_collection(
                    name=self._collection_name,
                    metadata={"description": "Free Claude Code persistent memory store"}
                )
                logger.info(f"Created new ChromaDB collection: {self._collection_name}")
        return self._collection

    def _generate_content_hash(self, content: str) -> str:
        """Generate a hash for content deduplication."""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]

    def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text using SentenceTransformer."""
        model = self._get_embedding_model()
        embedding = model.encode(text, convert_to_tensor=False)
        return embedding.tolist()

    def _prepare_metadata(self,
                         content: str,
                         tags: Optional[List[str]] = None,
                         importance_score: float = 0.5,
                         source: Optional[str] = None,
                         **kwargs) -> Dict[str, Any]:
        """Prepare metadata for storage."""
        metadata = {
            "content_hash": self._generate_content_hash(content),
            "importance_score": max(0.0, min(1.0, importance_score)),  # Clamp to 0-1
            "source": source or "unknown",
            "stored_at": datetime.utcnow().isoformat(),
            **kwargs
        }

        if tags:
            metadata["tags"] = ",".join(tags)  # ChromaDB doesn't support list types natively

        # Add any additional metadata
        metadata.update(kwargs)

        return metadata

    def store_memory(self,
                    content: str,
                    tags: Optional[List[str]] = None,
                    importance_score: float = 0.5,
                    source: Optional[str] = None,
                    memory_id: Optional[str] = None,
                    skip_duplicates: bool = True,
                    **metadata) -> str:
        """Store a memory item in the persistent store.

        Args:
            content: The text content to store
            tags: List of tags for categorization
            importance_score: Importance score from 0.0 to 1.0
            source: Source of the memory (e.g., "conversation", "user_input", "system")
            memory_id: Optional custom ID (if not provided, generates one)
            skip_duplicates: If True, skip storing if content hash already exists
            **metadata: Additional metadata fields

        Returns:
            str: The ID of the stored memory item
        """
        if not content.strip():
            raise ValueError("Content cannot be empty")

        # Generate ID if not provided
        if memory_id is None:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            content_hash = self._generate_content_hash(content)
            memory_id = f"mem_{timestamp}_{content_hash}"

        # Check for duplicates if requested
        if skip_duplicates:
            content_hash = self._generate_content_hash(content)
            existing = self.get_by_content_hash(content_hash)
            if existing:
                logger.debug(f"Skipping duplicate content (hash: {content_hash})")
                # Update access time and count for existing item
                self._update_access(existing.id)
                return existing.id

        # Generate embedding
        embedding = self._generate_embedding(content)

        # Prepare metadata
        prepared_metadata = self._prepare_metadata(
            content=content,
            tags=tags,
            importance_score=importance_score,
            source=source,
            **metadata
        )

        # Store in ChromaDB
        collection = self._get_collection()
        collection.add(
            embeddings=[embedding],
            documents=[content],
            metadatas=[prepared_metadata],
            ids=[memory_id]
        )

        logger.info(f"Stored memory item: {memory_id} (importance: {importance_score})")
        return memory_id

    def get_memory(self, memory_id: str) -> Optional[MemoryItem]:
        """Retrieve a memory item by ID.

        Args:
            memory_id: The ID of the memory item to retrieve

        Returns:
            MemoryItem if found, None otherwise
        """
        try:
            collection = self._get_collection()
            results = collection.get(
                ids=[memory_id],
                include=["documents", "metadatas", "embeddings"]
            )

            if not results["ids"] or len(results["ids"]) == 0:
                return None

            # Update access tracking
            self._update_access(memory_id)

            # Construct MemoryItem
            item_data = {
                "id": results["ids"][0],
                "content": results["documents"][0],
                "embedding": results["embeddings"][0] if results["embeddings"] else None,
                "metadata": results["metadatas"][0] if results["metadatas"] else {}
            }

            # Parse tags from metadata if present
            metadata = item_data["metadata"]
            if "tags" in metadata and isinstance(metadata["tags"], str):
                metadata["tags"] = metadata["tags"].split(",") if metadata["tags"] else []
            elif "tags" not in metadata:
                metadata["tags"] = []

            return MemoryItem(**item_data)

        except Exception as e:
            logger.warning(f"Failed to retrieve memory {memory_id}: {e}")
            return None

    def get_by_content_hash(self, content_hash: str) -> Optional[MemoryItem]:
        """Retrieve a memory item by its content hash.

        Args:
            content_hash: The SHA256 hash of the content (first 16 chars)

        Returns:
            MemoryItem if found, None otherwise
        """
        try:
            collection = self._get_collection()
            results = collection.get(
                where={"content_hash": content_hash},
                include=["documents", "metadatas", "embeddings"]
            )

            if not results["ids"] or len(results["ids"]) == 0:
                return None

            # Update access tracking
            self._update_access(results["ids"][0])

            # Construct MemoryItem
            item_data = {
                "id": results["ids"][0],
                "content": results["documents"][0],
                "embedding": results["embeddings"][0] if results["embeddings"] else None,
                "metadata": results["metadatas"][0] if results["metadatas"] else {}
            }

            # Parse tags from metadata if present
            metadata = item_data["metadata"]
            if "tags" in metadata and isinstance(metadata["tags"], str):
                metadata["tags"] = metadata["tags"].split(",") if metadata["tags"] else []
            elif "tags" not in metadata:
                metadata["tags"] = []

            return MemoryItem(**item_data)

        except Exception as e:
            logger.warning(f"Failed to retrieve memory by hash {content_hash}: {e}")
            return None

    def search_memories(self,
                       query: str,
                       limit: int = 10,
                       min_importance: float = 0.0,
                       tags: Optional[List[str]] = None,
                       source: Optional[str] = None) -> List[MemoryItem]:
        """Search for memories using semantic similarity.

        Args:
            query: The search query text
            limit: Maximum number of results to return
            min_importance: Minimum importance score (0.0 to 1.0)
            tags: Filter by tags (any match)
            source: Filter by source

        Returns:
            List of MemoryItem objects sorted by relevance
        """
        if not query.strip():
            return []

        # Generate query embedding
        query_embedding = self._generate_embedding(query)

        # Build where clause for filtering
        where_clause: Dict[str, Any] = {}
        if min_importance > 0.0:
            where_clause["importance_score"] = {"$gte": min_importance}
        if source:
            where_clause["source"] = source
        if tags:
            # ChromaDB doesn't have direct array contains, we'll filter post-query for now
            pass

        try:
            collection = self._get_collection()
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=limit,
                where=where_clause if where_clause else None,
                include=["documents", "metadatas", "embeddings", "distances"]
            )

            if not results["ids"] or len(results["ids"][0]) == 0:
                return []

            # Construct MemoryItems
            memories = []
            for i, memory_id in enumerate(results["ids"][0]):
                # Update access tracking
                self._update_access(memory_id)

                item_data = {
                    "id": memory_id,
                    "content": results["documents"][0][i],
                    "embedding": results["embeddings"][0][i] if results["embeddings"] else None,
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                    "importance_score": results["metadatas"][0][i].get("importance_score", 0.5) if results["metadatas"] else 0.5
                }

                # Parse tags from metadata if present
                metadata = item_data["metadata"]
                if "tags" in metadata and isinstance(metadata["tags"], str):
                    metadata["tags"] = metadata["tags"].split(",") if metadata["tags"] else []
                elif "tags" not in metadata:
                    metadata["tags"] = []

                # Filter by tags if specified
                if tags:
                    memory_tags = set(metadata.get("tags", []))
                    search_tags = set(tags)
                    if not memory_tags.intersection(search_tags):
                        continue  # Skip if no tag match

                memories.append(MemoryItem(**item_data))

            # Update access counts
            for memory in memories:
                self._increment_access_count(memory.id)

            logger.debug(f"Found {len(memories)} memories for query: {query[:50]}...")
            return memories

        except Exception as e:
            logger.error(f"Failed to search memories: {e}")
            return []

    def update_memory(self,
                     memory_id: str,
                     content: Optional[str] = None,
                     tags: Optional[List[str]] = None,
                     importance_score: Optional[float] = None,
                     **metadata) -> bool:
        """Update an existing memory item.

        Args:
            memory_id: The ID of the memory item to update
            content: New content (if provided, will regenerate embedding)
            tags: New tags
            importance_score: New importance score
            **metadata: Additional metadata to update

        Returns:
            bool: True if updated, False if not found
        """
        # Get existing item
        existing = self.get_memory(memory_id)
        if not existing:
            logger.warning(f"Cannot update memory {memory_id}: not found")
            return False

        # Prepare update data
        update_content = content if content is not None else existing.content
        update_tags = tags if tags is not None else existing.tags
        update_importance = importance_score if importance_score is not None else existing.importance_score

        # If content changed, regenerate embedding
        if content is not None and content != existing.content:
            embedding = self._generate_embedding(update_content)
        else:
            embedding = existing.embedding

        # Prepare metadata
        prepared_metadata = self._prepare_metadata(
            content=update_content,
            tags=update_tags,
            importance_score=update_importance,
            source=existing.metadata.get("source", "unknown"),
            **{**existing.metadata, **metadata}
        )

        # Update in ChromaDB
        try:
            collection = self._get_collection()
            collection.update(
                ids=[memory_id],
                embeddings=[embedding] if embedding else None,
                documents=[update_content],
                metadatas=[prepared_metadata]
            )

            logger.info(f"Updated memory item: {memory_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to update memory {memory_id}: {e}")
            return False

    def delete_memory(self, memory_id: str) -> bool:
        """Delete a memory item (GDPR-compliant deletion).

        Args:
            memory_id: The ID of the memory item to delete

        Returns:
            bool: True if deleted, False if not found
        """
        try:
            collection = self._get_collection()
            collection.delete(ids=[memory_id])

            logger.info(f"Deleted memory item: {memory_id}")
            return True

        except Exception as e:
            logger.warning(f"Failed to delete memory {memory_id}: {e}")
            return False

    def delete_by_content_hash(self, content_hash: str) -> int:
        """Delete all memory items with a specific content hash.

        Args:
            content_hash: The SHA256 hash of the content (first 16 chars)

        Returns:
            int: Number of items deleted
        """
        try:
            collection = self._get_collection()
            # First get matching IDs
            results = collection.get(
                where={"content_hash": content_hash},
                include=["metadatas"]
            )

            if not results["ids"]:
                return 0

            # Delete all matching items
            collection.delete(ids=results["ids"])

            count = len(results["ids"])
            logger.info(f"Deleted {count} memory items with hash: {content_hash}")
            return count

        except Exception as e:
            logger.error(f"Failed to delete memories by hash {content_hash}: {e}")
            return 0

    def clear_all(self, confirm: bool = False) -> bool:
        """Clear all memories from the store.

        Args:
            confirm: Must be True to actually clear (safety mechanism)

        Returns:
            bool: True if cleared, False otherwise
        """
        if not confirm:
            logger.warning("Clear all memories called without confirmation")
            return False

        try:
            client = self._get_chroma_client()
            client.delete_collection(name=self._collection_name)
            self._collection = None

            # Recreate empty collection
            self._collection = client.create_collection(
                name=self._collection_name,
                metadata={"description": "Free Claude Code persistent memory store"}
            )

            logger.info("Cleared all memories from persistent store")
            return True

        except Exception as e:
            logger.error(f"Failed to clear all memories: {e}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the memory store.

        Returns:
            Dictionary containing storage statistics
        """
        try:
            collection = self._get_collection()
            count = collection.count()

            # Get sample of items to compute averages
            sample_size = min(100, count)
            if sample_size > 0:
                results = collection.get(
                    limit=sample_size,
                    include=["metadatas"]
                )

                importance_scores = []
                sources = {}
                tags_set = set()

                if results["metadatas"]:
                    for metadata in results["metadatas"]:
                        if "importance_score" in metadata:
                            importance_scores.append(metadata["importance_score"])
                        source = metadata.get("source", "unknown")
                        sources[source] = sources.get(source, 0) + 1
                        if "tags" in metadata and isinstance(metadata["tags"], str):
                            tags = metadata["tags"].split(",") if metadata["tags"] else []
                            tags_set.update(tags)

                avg_importance = sum(importance_scores) / len(importance_scores) if importance_scores else 0.0
            else:
                avg_importance = 0.0
                sources = {}
                tags_set = set()

            return {
                "total_items": count,
                "storage_directory": str(self._storage_dir),
                "chroma_directory": str(self._chroma_dir),
                "collection_name": self._collection_name,
                "average_importance": round(avg_importance, 3),
                "sources": dict(list(sources.items())[:10]),  # Top 10 sources
                "unique_tags": len(tags_set),
                "sample_size": sample_size
            }

        except Exception as e:
            logger.error(f"Failed to get memory stats: {e}")
            return {"error": str(e)}

    def _update_access(self, memory_id: str) -> None:
        """Update the access time for a memory item."""
        try:
            collection = self._get_collection()
            # Update accessed_at timestamp
            collection.update(
                ids=[memory_id],
                metadatas=[{"accessed_at": datetime.utcnow().isoformat()}]
            )
        except Exception as e:
            logger.debug(f"Failed to update access time for {memory_id}: {e}")

    def _increment_access_count(self, memory_id: str) -> None:
        """Increment the access count for a memory item."""
        try:
            collection = self._get_collection()
            # First get current count
            results = collection.get(
                ids=[memory_id],
                include=["metadatas"]
            )

            if results["metadatas"] and len(results["metadatas"]) > 0:
                current_count = results["metadatas"][0].get("access_count", 0)
                new_count = current_count + 1

                collection.update(
                    ids=[memory_id],
                    metadatas=[{"access_count": new_count}]
                )
        except Exception as e:
            logger.debug(f"Failed to increment access count for {memory_id}: {e}")

    def store_conversation_summary(self,
                                  conversation_id: str,
                                  summary: str,
                                  key_points: Optional[List[str]] = None,
                                  decisions: Optional[List[str]] = None,
                                  participants: Optional[List[str]] = None) -> str:
        """Store a conversation summary with structured metadata.

        Args:
            conversation_id: Unique identifier for the conversation
            summary: Summary of the conversation
            key_points: List of key points discussed
            decisions: List of decisions made
            participants: List of participants involved

        Returns:
            str: The ID of the stored memory item
        """
        metadata = {
            "conversation_id": conversation_id,
            "memory_type": "conversation_summary",
            "key_points": key_points or [],
            "decisions": decisions or [],
            "participants": participants or [],
            "timestamp": datetime.utcnow().isoformat()
        }

        # Higher importance for conversation summaries
        importance = 0.7

        return self.store_memory(
            content=summary,
            tags=["conversation", "summary"] + (key_points or []),
            importance_score=importance,
            source="conversation",
            memory_id=f"conv_{conversation_id}_{int(datetime.utcnow().timestamp())}",
            **metadata
        )

    def store_user_preference(self,
                             preference_key: str,
                             preference_value: Any,
                             context: Optional[str] = None) -> str:
        """Store a user preference.

        Args:
            preference_key: The preference key/name
            preference_value: The preference value
            context: Optional context for the preference

        Returns:
            str: The ID of the stored memory item
        """
        content = f"User preference: {preference_key} = {preference_value}"
        if context:
            content += f" (context: {context})"

        metadata = {
            "preference_key": preference_key,
            "preference_value": str(preference_value),
            "context": context or "",
            "memory_type": "user_preference",
            "timestamp": datetime.utcnow().isoformat()
        }

        # Medium-high importance for user preferences
        importance = 0.8

        return self.store_memory(
            content=content,
            tags=["preference", preference_key.replace(" ", "_")],
            importance_score=importance,
            source="user_preference",
            memory_id=f"pref_{preference_key}_{int(datetime.utcnow().timestamp())}",
            **metadata
        )

    def store_decision(self,
                      decision: str,
                      rationale: Optional[str] = None,
                      alternatives: Optional[List[str]] = None,
                      confidence: float = 0.8,
                      tags: Optional[List[str]] = None) -> str:
        """Store a decision made during a conversation or task.

        Args:
            decision: The decision that was made
            rationale: Explanation for the decision
            alternatives: Alternative options considered
            confidence: Confidence level in the decision (0.0 to 1.0)
            tags: Tags for categorization

        Returns:
            str: The ID of the stored memory item
        """
        content = f"Decision: {decision}"
        if rationale:
            content += f"\nRationale: {rationale}"
        if alternatives:
            content += f"\nAlternatives considered: {', '.join(alternatives)}"

        metadata = {
            "decision": decision,
            "rationale": rationale or "",
            "alternatives": alternatives or [],
            "confidence": max(0.0, min(1.0, confidence)),
            "memory_type": "decision",
            "timestamp": datetime.utcnow().isoformat()
        }

        # High importance for decisions
        importance = 0.9

        return self.store_memory(
            content=content,
            tags=tags or ["decision"],
            importance_score=importance,
            source="decision",
            memory_id=f"dec_{int(datetime.utcnow().timestamp())}",
            **metadata
        )

    def get_relevant_memories(self,
                             current_context: str,
                             limit: int = 5,
                             min_importance: float = 0.3) -> List[MemoryItem]:
        """Get memories relevant to the current context.

        Args:
            current_context: The current conversation/task context
            limit: Maximum number of memories to return
            min_importance: Minimum importance threshold

        Returns:
            List of relevant MemoryItem objects
        """
        # Search for memories related to current context
        memories = self.search_memories(
            query=current_context,
            limit=limit,
            min_importance=min_importance
        )

        # Also get some high-importance memories for broader context
        high_importance = self.search_memories(
            query="",  # Empty query to get all
            limit=limit,
            min_importance=0.8
        )

        # Combine and deduplicate
        seen_ids = set()
        combined = []

        for memory in memories + high_importance:
            if memory.id not in seen_ids:
                seen_ids.add(memory.id)
                combined.append(memory)

        return combined[:limit]


# Global instance for easy access
_persistent_memory_store: Optional[PersistentMemoryStore] = None


def get_persistent_memory_store(settings: Optional[FCCSettings] = None) -> PersistentMemoryStore:
    """Get or create the global persistent memory store instance.

    Args:
        settings: Optional settings instance (will create default if not provided)

    Returns:
        PersistentMemoryStore instance
    """
    global _persistent_memory_store

    if _persistent_memory_store is None:
        if settings is None:
            # Create default settings if none provided
            settings = FCCSettings()
        _persistent_memory_store = PersistentMemoryStore(settings)

    return _persistent_memory_store


def initialize_persistent_memory(settings: FCCSettings) -> PersistentMemoryStore:
    """Initialize the persistent memory store with given settings.

    Args:
        settings: Application settings instance

    Returns:
        PersistentMemoryStore instance
    """
    global _persistent_memory_store
    _persistent_memory_store = PersistentMemoryStore(settings)
    return _persistent_memory_store