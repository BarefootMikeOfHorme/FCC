"""
Assistant Agent - Metadata Harvester and Cache Worker
Corresponds to the Assistant Librarian concept from the Librarian Hierarchy.
Lightweight crawler and metadata harvester for specific tasks such as scanning
directories, collecting AST snapshots, harvesting metadata, updating caches,
and refreshing routing hints.
"""

import asyncio
import uuid
from typing import Dict, Any, List, Optional
from .base_agent import BaseAgent, AgentType, AgentStatus, AgentCapabilities, AgentMetadata
from datetime import datetime


class AssistantAgent(BaseAgent):
    """
    Assistant Agent - Lightweight Crawler/Metadata Harvester
    Intentionally small, fast, and safe. Spawned for specific tasks such as
    scanning directories, collecting AST snapshots, harvesting metadata,
    updating caches, and refreshing routing hints.
    """

    def __init__(self, task_id: str, project_id: Optional[str] = None, parent_agent_id: Optional[str] = None):
        # Generate agent ID
        if project_id:
            agent_id = f"assistant_agent_{project_id}_{task_id}_{uuid.uuid4().hex[:6]}"
        else:
            agent_id = f"assistant_agent_global_{task_id}_{uuid.uuid4().hex[:6]}"

        # Define Assistant Agent capabilities
        capabilities = AgentCapabilities(
            can_govern=False,  # Cannot set policies
            can_specialize=False,  # Cannot create other agents
            can_execute_tasks=True,  # Can perform work tasks
            can_harvest_metadata=True,  # Primary function: metadata harvesting
            can_cache_results=True,  # Can cache computation results
            can_scale_context=False,  # Typically uses minimal context
            max_context_tokens=4096  # 4K tokens (XS/S scale) - lightweight
        )

        # Create metadata
        metadata = AgentMetadata(
            agent_id=agent_id,
            agent_type=AgentType.ASSISTANT,
            parent_id=parent_agent_id,
            project_id=project_id,
            capabilities=capabilities,
            status=AgentStatus.INITIALIZING,
            config={
                "task_id": task_id,
                "project_id": project_id,
                "task_type": "metadata_harvesting",  # Default task type
                "harvested_metadata": {},
                "cache_store": {},
                "routing_hints": {},
                "ast_snapshots": {},
                "diff_history": {},
                "helper_caches": {},
                "scan_directories": [],
                "file_extensions": [],
                "last_scan_time": None
            }
        )

        super().__init__(metadata)
        self._maintenance_task: Optional[asyncio.Task] = None
        self._harvest_task: Optional[asyncio.Task] = None
        self.main_agent_id = parent_agent_id

    async def initialize(self) -> bool:
        """Initialize the Assistant Agent"""
        try:
            self.logger.info(f"Initializing Assistant Agent {self.metadata.agent_id} for task {self.metadata.config['task_id']}")
            self.metadata.status = AgentStatus.INITIALIZING

            # Initialize task-specific structures
            await self._initialize_task_structures()

            # Start background tasks
            self._maintenance_task = asyncio.create_task(self._maintenance_loop())

            self.metadata.status = AgentStatus.ACTIVE
            self.logger.info(f"Assistant Agent {self.metadata.agent_id} initialized successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to initialize Assistant Agent: {e}")
            self.metadata.status = AgentStatus.ERROR
            return False

    async def start(self) -> bool:
        """Start the Assistant Agent"""
        try:
            self.logger.info(f"Starting Assistant Agent {self.metadata.agent_id}")
            self.metadata.status = AgentStatus.ACTIVE
            self._is_running = True
            self.logger.info(f"Assistant Agent {self.metadata.agent_id} started")
            return True
        except Exception as e:
            self.logger.error(f"Failed to start Assistant Agent: {e}")
            self.metadata.status = AgentStatus.ERROR
            return False

    async def stop(self) -> bool:
        """Stop the Assistant Agent gracefully"""
        try:
            self.logger.info(f"Stopping Assistant Agent {self.metadata.agent_id}")
            self.metadata.status = AgentStatus.SHUTTING_DOWN
            self._is_running = False

            # Stop background tasks
            if self._maintenance_task:
                self._maintenance_task.cancel()
                try:
                    await self._maintenance_task
                except asyncio.CancelledError:
                    pass

            if self._harvest_task and not self._harvest_task.done():
                self._harvest_task.cancel()
                try:
                    await self._harvest_task
                except asyncio.CancelledError:
                    pass

            self.metadata.status = AgentStatus.TERMINATED
            self.logger.info(f"Assistant Agent {self.metadata.agent_id} stopped")
            return True

        except Exception as e:
            self.logger.error(f"Error stopping Assistant Agent: {e}")
            self.metadata.status = AgentStatus.ERROR
            return False

    async def process_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Process incoming messages"""
        try:
            message_type = message.get("type", "unknown")
            self.logger.debug(f"Assistant Agent processing message type: {message_type}")

            # Handle via registered handlers
            if message_type in self._message_handlers:
                handler = self._message_handlers[message_type]
                return await handler(message)
            else:
                # Handle Assistant Agent specific messages
                return await self._handle_assistant_agent_message(message)

        except Exception as e:
            self.logger.error(f"Error processing message in Assistant Agent: {e}")
            return {
                "type": "error",
                "agent_id": self.metadata.agent_id,
                "error": str(e),
                "original_message": message
            }

    async def _handle_assistant_agent_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle Assistant Agent specific message types"""
        message_type = message.get("type")

        if message_type == "start_metadata_harvest":
            return await self._handle_start_metadata_harvest(message)
        elif message_type == "stop_metadata_harvest":
            return await self._handle_stop_metadata_harvest(message)
        elif message_type == "get_harvest_status":
            return await self._handle_get_harvest_status(message)
        elif message_type == "store_harvested_metadata":
            return await self._handle_store_harvested_metadata(message)
        elif message_type == "recall_harvested_metadata":
            return await self._handle_recall_harvested_metadata(message)
        elif message_type == "store_ast_snapshot":
            return await self._handle_store_ast_snapshot(message)
        elif message_type == "recall_ast_snapshot":
            return await self._handle_recall_ast_snapshot(message)
        elif message_type == "store_diff_history":
            return await self._handle_store_diff_history(message)
        elif message_type == "update_routing_hints":
            return await self._handle_update_routing_hints(message)
        elif message_type == "store_helper_cache":
            return await self._handle_store_helper_cache(message)
        elif message_type == "recall_helper_cache":
            return await self._handle_recall_helper_cache(message)
        elif message_type == "scan_directory":
            return await self._handle_scan_directory(message)
        elif message_type == "get_cache_stats":
            return await self._handle_get_cache_stats(message)
        elif message_type == "cleanup_cache":
            return await self._handle_cleanup_cache(message)
        else:
            return {
                "type": "unknown_message",
                "agent_id": self.metadata.agent_id,
                "message_type": message_type,
                "available_types": [
                    "start_metadata_harvest", "stop_metadata_harvest", "get_harvest_status",
                    "store_harvested_metadata", "recall_harvested_metadata", "store_ast_snapshot",
                    "recall_ast_snapshot", "store_diff_history", "update_routing_hints",
                    "store_helper_cache", "recall_helper_cache", "scan_directory",
                    "get_cache_stats", "cleanup_cache"
                ]
            }

    async def _handle_start_metadata_harvest(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle request to start metadata harvesting"""
        directories = message.get("directories", [])
        file_extensions = message.get("file_extensions", [])
        harvest_type = message.get("harvest_type", "general")

        if not directories:
            return {
                "type": "error",
                "agent_id": self.metadata.agent_id,
                "error": "directories list is required to start metadata harvest"
            }

        # Update configuration
        self.metadata.config["scan_directories"] = directories
        self.metadata.config["file_extensions"] = file_extensions
        self.metadata.config["harvest_type"] = harvest_type
        self.metadata.config["last_scan_time"] = None

        self.logger.info(f"Starting metadata harvest for task {self.metadata.config['task_id']} on {len(directories)} directories")

        # Start the harvest task if not already running
        if not self._harvest_task or self._harvest_task.done():
            self._harvest_task = asyncio.create_task(self._metadata_harvest_loop())

        return {
            "type": "metadata_harvest_started",
            "assistant_agent_id": self.metadata.agent_id,
            "task_id": self.metadata.config["task_id"],
            "directories": directories,
            "file_extensions": file_extensions,
            "harvest_type": harvest_type
        }

    async def _handle_stop_metadata_harvest(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle request to stop metadata harvesting"""
        if self._harvest_task and not self._harvest_task.done():
            self._harvest_task.cancel()
            try:
                await self._harvest_task
            except asyncio.CancelledError:
                pass
            self._harvest_task = None

        self.logger.info(f"Stopped metadata harvest for task {self.metadata.config['task_id']}")

        return {
            "type": "metadata_harvest_stopped",
            "assistant_agent_id": self.metadata.agent_id,
            "task_id": self.metadata.config["task_id"]
        }

    async def _handle_get_harvest_status(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle request for harvest status"""
        last_scan = self.metadata.config.get("last_scan_time")
        harvest_count = len(self.metadata.config.get("harvested_metadata", {}))

        return {
            "type": "harvest_status",
            "assistant_agent_id": self.metadata.agent_id,
            "task_id": self.metadata.config["task_id"],
            "is_harvesting": self._harvest_task is not None and not self._harvest_task.done(),
            "last_scan_time": last_scan,
            "directories_configured": len(self.metadata.config.get("scan_directories", [])),
            "file_extensions_configured": len(self.metadata.config.get("file_extensions", [])),
            "harvested_items_count": harvest_count,
            "cache_size": len(self.metadata.config.get("cache_store", {})),
            "timestamp": datetime.now().isoformat()
        }

    async def _handle_store_harvested_metadata(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle storing harvested metadata"""
        metadata_key = message.get("metadata_key")
        metadata_value = message.get("metadata_value")
        importance = message.get("importance", 0.5)

        if not metadata_key or metadata_value is None:
            return {
                "type": "error",
                "agent_id": self.metadata.agent_id,
                "error": "metadata_key and metadata_value are required"
            }

        # Store in harvested metadata cache
        self.metadata.config["harvested_metadata"][metadata_key] = {
            "value": metadata_value,
            "timestamp": datetime.now().isoformat(),
            "importance": importance
        }

        self.logger.debug(f"Stored harvested metadata: {metadata_key}")

        # Also store in persistent memory with specified importance
        await self.store_in_memory(
            f"harvested_metadata:{self.metadata.config['task_id']}:{metadata_key}",
            metadata_value,
            importance
        )

        return {
            "type": "harvested_metadata_stored",
            "assistant_agent_id": self.metadata.agent_id,
            "metadata_key": metadata_key
        }

    async def _handle_recall_harvested_metadata(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle request to recall harvested metadata"""
        metadata_key = message.get("metadata_key")
        if not metadata_key:
            return {
                "type": "error",
                "agent_id": self.metadata.agent_id,
                "error": "metadata_key is required"
            }

        # Check local cache first
        cached = self.metadata.config.get("harvested_metadata", {}).get(metadata_key)
        if cached:
            return {
                "type": "harvested_metadata_recalled",
                "assistant_agent_id": self.metadata.agent_id,
                "metadata_key": metadata_key,
                "metadata_value": cached["value"],
                "from_cache": True,
                "timestamp": cached["timestamp"]
            }

        # Fall back to persistent memory
        value = await self.recall_from_memory(
            f"harvested_metadata:{self.metadata.config['task_id']}:{metadata_key}"
        )

        if value is not None:
            return {
                "type": "harvested_metadata_recalled",
                "assistant_agent_id": self.metadata.agent_id,
                "metadata_key": metadata_key,
                "metadata_value": value,
                "from_cache": False,
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "type": "harvested_metadata_not_found",
                "assistant_agent_id": self.metadata.agent_id,
                "metadata_key": metadata_key
            }

    async def _handle_store_ast_snapshot(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle storing AST snapshot"""
        file_path = message.get("file_path")
        ast_data = message.get("ast_data")
        importance = message.get("importance", 0.6)

        if not file_path or not ast_data:
            return {
                "type": "error",
                "agent_id": self.metadata.agent_id,
                "error": "file_path and ast_data are required"
            }

        # Store in AST snapshots cache
        if "ast_snapshots" not in self.metadata.config:
            self.metadata.config["ast_snapshots"] = {}
        self.metadata.config["ast_snapshots"][file_path] = {
            "data": ast_data,
            "timestamp": datetime.now().isoformat(),
            "importance": importance
        }

        self.logger.debug(f"Stored AST snapshot for {file_path}")

        # Store in persistent memory
        await self.store_in_memory(
            f"ast_snapshot:{self.metadata.config['task_id']}:{file_path}",
            ast_data,
            importance
        )

        return {
            "type": "ast_snapshot_stored",
            "assistant_agent_id": self.metadata.agent_id,
            "file_path": file_path
        }

    async def _handle_recall_ast_snapshot(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle request to recall AST snapshot"""
        file_path = message.get("file_path")
        if not file_path:
            return {
                "type": "error",
                "agent_id": self.metadata.agent_id,
                "error": "file_path is required"
            }

        # Check local cache first
        cached = self.metadata.config.get("ast_snapshots", {}).get(file_path)
        if cached:
            return {
                "type": "ast_snapshot_recalled",
                "assistant_agent_id": self.metadata.agent_id,
                "file_path": file_path,
                "ast_data": cached["data"],
                "from_cache": True,
                "timestamp": cached["timestamp"]
            }

        # Fall back to persistent memory
        data = await self.recall_from_memory(
            f"ast_snapshot:{self.metadata.config['task_id']}:{file_path}"
        )

        if data is not None:
            return {
                "type": "ast_snapshot_recalled",
                "assistant_agent_id": self.metadata.agent_id,
                "file_path": file_path,
                "ast_data": data,
                "from_cache": False,
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "type": "ast_snapshot_not_found",
                "assistant_agent_id": self.metadata.agent_id,
                "file_path": file_path
            }

    async def _handle_store_diff_history(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle storing diff history"""
        file_path = message.get("file_path")
        diff_data = message.get("diff_data")
        if not file_path or not diff_data:
            return {
                "type": "error",
                "agent_id": self.metadata.agent_id,
                "error": "file_path and diff_data are required"
            }

        # Store in diff history cache
        if "diff_history" not in self.metadata.config:
            self.metadata.config["diff_history"] = {}
        if file_path not in self.metadata.config["diff_history"]:
            self.metadata.config["diff_history"][file_path] = []
        self.metadata.config["diff_history"][file_path].append({
            "data": diff_data,
            "timestamp": datetime.now().isoformat()
        })

        # Keep only last 10 diffs per file
        if len(self.metadata.config["diff_history"][file_path]) > 10:
            self.metadata.config["diff_history"][file_path] = self.metadata.config["diff_history"][file_path][-10:]

        self.logger.debug(f"Stored diff history for {file_path}")

        # Store in persistent memory
        await self.store_in_memory(
            f"diff_history:{self.metadata.config['task_id']}:{file_path}",
            diff_data,
            importance=0.5
        )

        return {
            "type": "diff_history_stored",
            "assistant_agent_id": self.metadata.agent_id,
            "file_path": file_path
        }

    async def _handle_update_routing_hints(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle updating routing hints"""
        hint_key = message.get("hint_key")
        hint_value = message.get("hint_value")

        if not hint_key or hint_value is None:
            return {
                "type": "error",
                "agent_id": self.metadata.agent_id,
                "error": "hint_key and hint_value are required"
            }

        self.metadata.config["routing_hints"][hint_key] = {
            "value": hint_value,
            "timestamp": datetime.now().isoformat()
        }

        self.logger.debug(f"Updated routing hint: {hint_key}")

        # Store in persistent memory
        await self.store_in_memory(
            f"routing_hint:{self.metadata.config['task_id']}:{hint_key}",
            hint_value,
            importance=0.6
        )

        return {
            "type": "routing_hint_updated",
            "assistant_agent_id": self.metadata.agent_id,
            "hint_key": hint_key
        }

    async def _handle_store_helper_cache(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle storing helper cache data"""
        cache_key = message.get("cache_key")
        cache_value = message.get("cache_value")
        importance = message.get("importance", 0.4)

        if not cache_key or cache_value is None:
            return {
                "type": "error",
                "agent_id": self.metadata.agent_id,
                "error": "cache_key and cache_value are required"
            }

        self.metadata.config["helper_caches"][cache_key] = {
            "value": cache_value,
            "timestamp": datetime.now().isoformat(),
            "importance": importance
        }

        self.logger.debug(f"Stored helper cache: {cache_key}")

        # Store in persistent memory
        await self.store_in_memory(
            f"helper_cache:{self.metadata.config['task_id']}:{cache_key}",
            cache_value,
            importance
        )

        return {
            "type": "helper_cache_stored",
            "assistant_agent_id": self.metadata.agent_id,
            "cache_key": cache_key
        }

    async def _handle_recall_helper_cache(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle request to recall helper cache data"""
        cache_key = message.get("cache_key")
        if not cache_key:
            return {
                "type": "error",
                "agent_id": self.metadata.agent_id,
                "error": "cache_key is required"
            }

        # Check local cache first
        cached = self.metadata.config.get("helper_caches", {}).get(cache_key)
        if cached:
            return {
                "type": "helper_cache_recalled",
                "assistant_agent_id": self.metadata.agent_id,
                "cache_key": cache_key,
                "cache_value": cached["value"],
                "from_cache": True,
                "timestamp": cached["timestamp"]
            }

        # Fall back to persistent memory
        value = await self.recall_from_memory(
            f"helper_cache:{self.metadata.config['task_id']}:{cache_key}"
        )

        if value is not None:
            return {
                "type": "helper_cache_recalled",
                "assistant_agent_id": self.metadata.agent_id,
                "cache_key": cache_key,
                "cache_value": value,
                "from_cache": False,
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "type": "helper_cache_not_found",
                "assistant_agent_id": self.metadata.agent_id,
                "cache_key": cache_key
            }

    async def _handle_scan_directory(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle request to scan a specific directory"""
        directory = message.get("directory")
        if not directory:
            return {
                "type": "error",
                "agent_id": self.metadata.agent_id,
                "error": "directory is required"
            }

        file_extensions = message.get("file_extensions", self.metadata.config.get("file_extensions", []))
        recursive = message.get("recursive", True)

        self.logger.info(f"Scanning directory {directory} for extensions {file_extensions} (recursive: {recursive})")

        # Simulate directory scanning (in real implementation, this would scan actual files)
        scan_results = {
            "directory": directory,
            "files_found": [],
            "total_files": 0,
            "scan_time": datetime.now().isoformat(),
            "recursive": recursive,
            "extensions_searched": file_extensions
        }

        # Store scan results
        await self.store_harvested_metadata({
            "metadata_key": f"scan_result:{directory}:{uuid.uuid4().hex[:8]}",
            "metadata_value": scan_results,
            "importance": 0.3
        })

        return {
            "type": "directory_scan_completed",
            "assistant_agent_id": self.metadata.agent_id,
            "directory": directory,
            "files_found": len(scan_results["files_found"]),
            "scan_time": scan_results["scan_time"]
        }

    async def _handle_get_cache_stats(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle request for cache statistics"""
        harvested_count = len(self.metadata.config.get("harvested_metadata", {}))
        ast_count = len(self.metadata.config.get("ast_snapshots", {}))
        diff_count = sum(len(v) for v in self.metadata.config.get("diff_history", {}).values())
        hint_count = len(self.metadata.config.get("routing_hints", {}))
        helper_count = len(self.metadata.config.get("helper_caches", {}))

        return {
            "type": "cache_stats",
            "assistant_agent_id": self.metadata.agent_id,
            "task_id": self.metadata.config["task_id"],
            "harvested_metadata_count": harvested_count,
            "ast_snapshots_count": ast_count,
            "diff_history_entries": diff_count,
            "routing_hints_count": hint_count,
            "helper_cache_entries": helper_count,
            "total_cache_entries": harvested_count + ast_count + diff_count + hint_count + helper_count,
            "timestamp": datetime.now().isoformat()
        }

    async def _handle_cleanup_cache(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle request to cleanup cache"""
        max_age_hours = message.get("max_age_hours", 24)
        cache_types = message.get("cache_types", ["harvested_metadata", "ast_snapshots", "diff_history", "routing_hints", "helper_caches"])

        cutoff_time = datetime.now().timestamp() - (max_age_hours * 3600)
        cleaned_counts = {}

        for cache_type in cache_types:
            if cache_type == "harvested_metadata":
                cache = self.metadata.config.get("harvested_metadata", {})
                to_remove = []
                for key, value in cache.items():
                    try:
                        timestamp = datetime.fromisoformat(value["timestamp"]).timestamp()
                        if timestamp < cutoff_time:
                            to_remove.append(key)
                    except:
                        to_remove.append(key)  # Remove malformed entries

                for key in to_remove:
                    del cache[key]
                cleaned_counts["harvested_metadata"] = len(to_remove)

            elif cache_type == "ast_snapshots":
                cache = self.metadata.config.get("ast_snapshots", {})
                to_remove = []
                for key, value in cache.items():
                    try:
                        timestamp = datetime.fromisoformat(value["timestamp"]).timestamp()
                        if timestamp < cutoff_time:
                            to_remove.append(key)
                    except:
                        to_remove.append(key)

                for key in to_remove:
                    del cache[key]
                cleaned_counts["ast_snapshots"] = len(to_remove)

            elif cache_type == "diff_history":
                cache = self.metadata.config.get("diff_history", {})
                total_removed = 0
                for file_path, diffs in cache.items():
                    original_count = len(diffs)
                    filtered_diffs = [
                        diff for diff in diffs
                        if datetime.fromisoformat(diff["timestamp"]).timestamp() >= cutoff_time
                    ]
                    removed = original_count - len(filtered_diffs)
                    if removed > 0:
                        self.metadata.config["diff_history"][file_path] = filtered_diffs
                        total_removed += removed
                cleaned_counts["diff_history"] = total_removed

            elif cache_type == "routing_hints":
                cache = self.metadata.config.get("routing_hints", {})
                to_remove = []
                for key, value in cache.items():
                    try:
                        timestamp = datetime.fromisoformat(value["timestamp"]).timestamp()
                        if timestamp < cutoff_time:
                            to_remove.append(key)
                    except:
                        to_remove.append(key)

                for key in to_remove:
                    del cache[key]
                cleaned_counts["routing_hints"] = len(to_remove)

            elif cache_type == "helper_caches":
                cache = self.metadata.config.get("helper_caches", {})
                to_remove = []
                for key, value in cache.items():
                    try:
                        timestamp = datetime.fromisoformat(value["timestamp"]).timestamp()
                        if timestamp < cutoff_time:
                            to_remove.append(key)
                    except:
                        to_remove.append(key)

                for key in to_remove:
                    del cache[key]
                cleaned_counts["helper_caches"] = len(to_remove)

        total_cleaned = sum(cleaned_counts.values())
        self.logger.info(f"Cache cleanup completed: {total_cleaned} entries removed")

        return {
            "type": "cache_cleanup_completed",
            "assistant_agent_id": self.metadata.agent_id,
            "task_id": self.metadata.config["task_id"],
            "max_age_hours": max_age_hours,
            "cleaned_counts": cleaned_counts,
            "total_cleaned": total_cleaned,
            "timestamp": datetime.now().isoformat()
        }

    async def _initialize_task_structures(self):
        """Initialize task-specific structures"""
        self.logger.info(f"Initializing task structures for task {self.metadata.config['task_id']}")

        # Load any existing task data from memory
        self.logger.debug(f"Loading task data from memory for task {self.metadata.config['task_id']}")

        # Set up default task configuration
        default_config = {
            "task_id": self.metadata.config["task_id"],
            "created_at": datetime.now().isoformat(),
            "status": "initialized",
            "priority": "normal"
        }

        for key, value in default_config.items():
            if key not in self.metadata.config:
                self.metadata.config[key] = value

        self.logger.info(f"Task structures initialized for task {self.metadata.config['task_id']}")

    async def _metadata_harvest_loop(self):
        """Background metadata harvesting loop"""
        self.logger.info(f"Starting metadata harvest loop for task {self.metadata.config['task_id']}")

        while self._is_running:
            try:
                # Perform metadata harvesting based on configuration
                await self._perform_metadata_harvest()

                # Wait before next harvest cycle (configurable)
                harvest_interval = self.metadata.config.get("harvest_interval_seconds", 300)  # 5 minutes default
                await asyncio.sleep(harvest_interval)

            except asyncio.CancelledError:
                self.logger.info(f"Metadata harvest loop cancelled for task {self.metadata.config['task_id']}")
                break
            except Exception as e:
                self.logger.error(f"Error in metadata harvest loop: {e}")
                await asyncio.sleep(30)  # Wait a bit before retrying

        self.logger.info(f"Metadata harvest loop stopped for task {self.metadata.config['task_id']}")

    async def _perform_metadata_harvest(self):
        """Perform actual metadata harvesting"""
        directories = self.metadata.config.get("scan_directories", [])
        file_extensions = self.metadata.config.get("file_extensions", [])

        if not directories:
            self.logger.warning("No directories configured for metadata harvesting")
            return

        self.logger.info(f"Performing metadata harvest on {len(directories)} directories")

        # In a real implementation, this would scan actual files and extract metadata
        # For now, we'll simulate the process

        harvest_results = {
            "directories_scanned": len(directories),
            "files_processed": 0,
            "metadata_items_harvested": 0,
            "start_time": datetime.now().isoformat()
        }

        # Simulate scanning each directory
        for directory in directories:
            # In reality, we'd walk the directory tree and process files
            # For simulation, we'll just log what we would do
            self.logger.debug(f"Would scan directory {directory} for extensions {file_extensions}")

            # Simulate finding some files
            simulated_files = [
                f"{directory}/file1.py",
                f"{directory}/file2.js",
                f"{directory}/README.md"
            ] if directory.endswith("/src") or directory.endswith("/") else [
                f"{directory}/config.json",
                f"{directory}/main.py"
            ]

            for file_path in simulated_files:
                # Check if file matches extensions (simplified)
                if not file_extensions or any(file_path.endswith(ext) for ext in file_extensions):
                    # Simulate harvesting metadata from this file
                    metadata_item = {
                        "file_path": file_path,
                        "file_type": file_path.split(".")[-1] if "." in file_path else "unknown",
                        "size": 1024,  # Simulated size
                        "lines": 50,   # Simulated line count
                        "harvested_at": datetime.now().isoformat()
                    }

                    # Store the harvested metadata
                    await self.store_harvested_metadata({
                        "metadata_key": f"file_metadata:{uuid.uuid4().hex[:8]}",
                        "metadata_value": metadata_item,
                        "importance": 0.4
                    })

                    harvest_results["files_processed"] += 1
                    harvest_results["metadata_items_harvested"] += 1

        harvest_results["end_time"] = datetime.now().isoformat()
        self.metadata.config["last_scan_time"] = harvest_results["end_time"]

        self.logger.info(f"Metadata harvest completed: {harvest_results['metadata_items_harvested']} items from {harvest_results['files_processed']} files")

    async def _maintenance_loop(self):
        """Background maintenance loop for the Assistant Agent"""
        self.logger.info(f"Starting Assistant Agent maintenance loop for task {self.metadata.config['task_id']}")

        while self._is_running:
            try:
                # Perform periodic maintenance tasks
                await self._perform_maintenance_tasks()

                # Wait before next maintenance cycle
                await asyncio.sleep(30)  # Run maintenance every 30 seconds (more frequent for assistants)

            except asyncio.CancelledError:
                self.logger.info(f"Assistant Agent maintenance loop cancelled for task {self.metadata.config['task_id']}")
                break
            except Exception as e:
                self.logger.error(f"Error in Assistant Agent maintenance loop: {e}")
                await asyncio.sleep(10)  # Wait a bit before retrying

        self.logger.info(f"Assistant Agent maintenance loop stopped for task {self.metadata.config['task_id']}")

    async def _perform_maintenance_tasks(self):
        """Perform periodic maintenance tasks"""
        # Update heartbeat
        self.metadata.last_heartbeat = datetime.now()

        # Periodically store cache to persistent memory
        current_time = datetime.now()
        if int(current_time.timestamp()) % 60 == 0:  # Every minute
            # Store harvested metadata summary
            harvest_summary = {
                "task_id": self.metadata.config["task_id"],
                "total_harvested": len(self.metadata.config.get("harvested_metadata", {})),
                "last_scan": self.metadata.config.get("last_scan_time"),
                "timestamp": current_time.isoformat()
            }
            await self.store_in_memory(
                f"harvest_summary:{self.metadata.config['task_id']}",
                harvest_summary,
                importance=0.5
            )

        self.logger.debug(f"Assistant Agent {self.metadata.agent_id} maintenance completed at {current_time.isoformat()}")

    # Delegation methods for interacting with Phase 2 memory systems
    async def store_temporary_data(self, key: str, value: Any, importance: float = 0.3) -> bool:
        """Store temporary data with low importance (likely to be cleaned up)"""
        return await self.store_in_memory(f"temp:{self.metadata.config['task_id']}:{key}", value, importance)

    async def recall_temporary_data(self, key: str) -> Any:
        """Recall temporary data"""
        return await self.recall_from_memory(f"temp:{self.metadata.config['task_id']}:{key}")

    async def store_task_knowledge(self, key: str, value: Any, importance: float = 0.6) -> bool:
        """Store knowledge specific to this task"""
        return await self.store_in_memory(f"task_knowledge:{self.metadata.config['task_id']}:{key}", value, importance)

    async def recall_task_knowledge(self, key: str) -> Any:
        """Recall task-specific knowledge"""
        return await self.recall_from_memory(f"task_knowledge:{self.metadata.config['task_id']}:{key}")