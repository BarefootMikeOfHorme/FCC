"""Persistent memory subsystem for Free Claude Code.

This package provides long-term memory storage capabilities using ChromaDB
and SentenceTransformers for vector storage and similarity search.
"""

from .persistent import (
    PersistentMemoryStore,
    MemoryItem,
    get_persistent_memory_store,
    initialize_persistent_memory
)

__all__ = [
    "PersistentMemoryStore",
    "MemoryItem",
    "get_persistent_memory_store",
    "initialize_persistent_memory"
]