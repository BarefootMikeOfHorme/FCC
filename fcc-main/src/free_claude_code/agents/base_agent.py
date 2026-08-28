"""
Base Agent Interface for Free Claude Code Agent Hierarchy
Defines the common interface and behaviors for all agents in the system.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from enum import Enum
import logging
from dataclasses import dataclass, field
from datetime import datetime

# Import Phase 2 persistent memory system
try:
    from free_claude_code.messaging.memory import PersistentMemoryStore, MemoryItem
    from free_claude_code.config.settings import Settings as FCCSettings
    PHASE_2_MEMORY_AVAILABLE = True
except ImportError:
    PHASE_2_MEMORY_AVAILABLE = False
    logging.warning("Phase 2 persistent memory not available - using placeholder implementations")


class AgentType(Enum):
    """Types of agents in the hierarchy"""
    MAIN = "main"          # Global governance agent
    PROJECT = "project"    # Project-specific agent
    ASSISTANT = "assistant" # Task-specific worker agent


class AgentStatus(Enum):
    """Status of an agent"""
    INITIALIZING = "initializing"
    ACTIVE = "active"
    BUSY = "busy"
    IDLE = "idle"
    SHUTTING_DOWN = "shutting_down"
    TERMINATED = "terminated"
    ERROR = "error"


@dataclass
class AgentCapabilities:
    """Defines what an agent can do"""
    can_govern: bool = False           # Can set policies and rules
    can_specialize: bool = False       # Can create specialized agents
    can_execute_tasks: bool = False    # Can perform work tasks
    can_harvest_metadata: bool = False # Can collect and process metadata
    can_cache_results: bool = False    # Can cache computation results
    can_scale_context: bool = False    # Can adjust context size based on task
    max_context_tokens: int = 8000     # Maximum context tokens this agent can handle


@dataclass
class AgentMetadata:
    """Metadata about an agent"""
    agent_id: str
    agent_type: AgentType
    parent_id: Optional[str] = None
    project_id: Optional[str] = None
    capabilities: AgentCapabilities = field(default_factory=AgentCapabilities)
    status: AgentStatus = AgentStatus.INITIALIZING
    created_at: datetime = field(default_factory=datetime.now)
    last_heartbeat: datetime = field(default_factory=datetime.now)
    config: Dict[str, Any] = field(default_factory=dict)


class BaseAgent(ABC):
    """
    Base class for all agents in the Free Claude Code hierarchy.
    Provides common functionality for lifecycle management, communication,
    and integration with the Phase 2 memory systems.
    """

    def __init__(self, metadata: AgentMetadata):
        self.metadata = metadata
        self.logger = logging.getLogger(f"{__name__}.{metadata.agent_id}")
        self._message_handlers: Dict[str, callable] = {}
        self._is_running = False

        # Initialize persistent memory store if available
        self._persistent_store: Optional[PersistentMemoryStore] = None
        if PHASE_2_MEMORY_AVAILABLE:
            try:
                # Get settings and initialize persistent memory store
                settings = FCCSettings()
                self._persistent_store = PersistentMemoryStore(settings)
                self.logger.debug("Persistent memory store initialized")
            except Exception as e:
                self.logger.warning(f"Failed to initialize persistent memory store: {e}")
                self._persistent_store = None

        # Register default message handlers
        self._register_default_handlers()

    def _register_default_handlers(self):
        """Register default message handlers"""
        self._message_handlers.update({
            "ping": self._handle_ping,
            "get_status": self._handle_get_status,
            "shutdown": self._handle_shutdown,
            "update_config": self._handle_update_config,
        })

    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize the agent. Returns True if successful."""
        pass

    @abstractmethod
    async def start(self) -> bool:
        """Start the agent's main processing loop. Returns True if successful."""
        pass

    @abstractmethod
    async def stop(self) -> bool:
        """Stop the agent gracefully. Returns True if successful."""
        pass

    @abstractmethod
    async def process_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Process an incoming message and return a response."""
        pass

    def send_message(self, target_agent_id: str, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send a message to another agent.
        In a full implementation, this would use a message broker or direct communication.
        """
        # Placeholder for inter-agent communication
        self.logger.debug(f"Sending message to {target_agent_id}: {message}")
        # In reality, this would go through a message bus or direct IPC
        return {"status": "sent", "to": target_agent_id, "message": message}

    def broadcast_message(self, message: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Broadcast a message to all known agents.
        """
        # Placeholder for broadcasting
        self.logger.debug(f"Broadcasting message: {message}")
        return [{"status": "broadcast", "message": message}]

    # Default message handlers
    async def _handle_ping(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle ping message"""
        self.metadata.last_heartbeat = datetime.now()
        return {
            "type": "pong",
            "agent_id": self.metadata.agent_id,
            "timestamp": datetime.now().isoformat(),
            "status": self.metadata.status.value
        }

    async def _handle_get_status(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle get status message"""
        return {
            "type": "status_response",
            "agent_id": self.metadata.agent_id,
            "agent_type": self.metadata.agent_type.value,
            "status": self.metadata.status.value,
            "capabilities": {
                "can_govern": self.metadata.capabilities.can_govern,
                "can_specialize": self.metadata.capabilities.can_specialize,
                "can_execute_tasks": self.metadata.capabilities.can_execute_tasks,
                "can_harvest_metadata": self.metadata.capabilities.can_harvest_metadata,
                "can_cache_results": self.metadata.capabilities.can_cache_results,
                "can_scale_context": self.metadata.capabilities.can_scale_context,
                "max_context_tokens": self.metadata.capabilities.max_context_tokens
            },
            "uptime_seconds": (datetime.now() - self.metadata.created_at).total_seconds()
        }

    async def _handle_shutdown(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle shutdown message"""
        self.logger.info(f"Received shutdown signal for agent {self.metadata.agent_id}")
        await self.stop()
        return {"type": "shutdown_ack", "agent_id": self.metadata.agent_id}

    async def _handle_update_config(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle configuration update"""
        config_updates = message.get("config", {})
        self.metadata.config.update(config_updates)
        self.logger.info(f"Updated config for agent {self.metadata.agent_id}: {config_updates}")
        return {"type": "config_updated", "agent_id": self.metadata.agent_id}

    # Memory integration methods (using Phase 2 systems)
    async def store_in_memory(self, key: str, value: Any, importance: float = 0.5) -> bool:
        """
        Store information in the Phase 2 persistent memory system.
        """
        if not PHASE_2_MEMORY_AVAILABLE or not self._persistent_store:
            # Fallback to placeholder
            self.logger.debug(f"Storing in memory (placeholder): {key} = {value} (importance: {importance})")
            return True

        try:
            # Convert value to string for storage
            if isinstance(value, (dict, list)):
                content = json.dumps(value)
            else:
                content = str(value)

            # Create memory item
            memory_item = MemoryItem(
                id=f"{self.metadata.agent_id}:{key}:{hash(content) % 10000}",
                content=content,
                metadata={
                    "agent_id": self.metadata.agent_id,
                    "agent_type": self.metadata.agent_type.value,
                    "stored_by": "agent_storage",
                    "importance": importance
                },
                importance_score=importance,
                tags=[self.metadata.agent_type.value, "agent_storage"]
            )

            # Store in persistent memory
            success = self._persistent_store.store_memory_item(memory_item)
            if success:
                self.logger.debug(f"Stored in memory: {key} (importance: {importance})")
            else:
                self.logger.warning(f"Failed to store in memory: {key}")

            return success

        except Exception as e:
            self.logger.error(f"Error storing in memory: {e}")
            return False

    async def recall_from_memory(self, key: str, similarity_threshold: float = 0.7) -> Any:
        """
        Recall information from the Phase 2 persistent memory system.
        """
        if not PHASE_2_MEMORY_AVAILABLE or not self._persistent_store:
            # Fallback to placeholder
            self.logger.debug(f"Recalling from memory (placeholder): {key} (threshold: {similarity_threshold})")
            return None

        try:
            # Search for the memory item by ID pattern or content
            # For simplicity, we'll search by exact ID match first
            memory_id = f"{self.metadata.agent_id}:{key}:"

            # In a full implementation, we'd have more sophisticated search
            # For now, we'll do a basic search and return the first match
            results = self._persistent_store.search_memories(
                query=key,
                limit=5,
                min_importance=similarity_threshold
            )

            if results:
                # Return the content of the first (most relevant) result
                best_match = results[0]
                content = best_match.get("content", "")

                # Try to parse as JSON if it looks like JSON
                if content.startswith("{") and content.endswith("}"):
                    try:
                        return json.loads(content)
                    except json.JSONDecodeError:
                        pass  # Return as string if not valid JSON
                elif content.startswith("[") and content.endswith("]"):
                    try:
                        return json.loads(content)
                    except json.JSONDecodeError:
                        pass  # Return as string if not valid JSON

                return content
            else:
                self.logger.debug(f"No memory found for key: {key}")
                return None

        except Exception as e:
            self.logger.error(f"Error recalling from memory: {e}")
            return None

    async def search_memory(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search the Phase 2 persistent memory system.
        """
        if not PHASE_2_MEMORY_AVAILABLE or not self._persistent_store:
            # Fallback to placeholder
            self.logger.debug(f"Searching memory (placeholder): {query} (limit: {limit})")
            return []

        try:
            results = self._persistent_store.search_memories(
                query=query,
                limit=limit,
                min_importance=0.1  # Low threshold to get more results
            )

            # Format results for consistency
            formatted_results = []
            for result in results:
                formatted_results.append({
                    "id": result.get("id", ""),
                    "content": result.get("content", ""),
                    "metadata": result.get("metadata", {}),
                    "importance": result.get("importance_score", 0.5),
                    "tags": result.get("tags", []),
                    "created_at": result.get("created_at", ""),
                    "accessed_at": result.get("accessed_at", "")
                })

            self.logger.debug(f"Found {len(formatted_results)} memories for query: {query}")
            return formatted_results

        except Exception as e:
            self.logger.error(f"Error searching memory: {e}")
            return []

    def determine_context_scale(self, task_complexity: str) -> str:
        """
        Determine appropriate context scale based on task complexity.
        Maps to the XS-XXL scales from Phase 2.
        """
        complexity_mapping = {
            "low": "XS",        # 1K-4K tokens
            "medium_low": "S",  # 4K-8K tokens
            "medium": "M",      # 8K-16K tokens
            "medium_high": "L", # 16K-32K tokens
            "high": "XL",       # 32K-64K tokens
            "very_high": "XXL"  # 64K-128K tokens
        }
        return complexity_mapping.get(task_complexity, "S")

    @property
    def agent_id(self) -> str:
        return self.metadata.agent_id

    @property
    def agent_type(self) -> AgentType:
        return self.metadata.agent_type

    @property
    def status(self) -> AgentStatus:
        return self.metadata.status

    def is_running(self) -> bool:
        return self._is_running