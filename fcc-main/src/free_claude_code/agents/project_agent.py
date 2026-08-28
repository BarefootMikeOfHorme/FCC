"""
Project Agent - Project-Specific Specialization
Corresponds to the Project Librarian concept from the Librarian Hierarchy.
Manages project-specific metadata, lineage, dependencies, summaries, and templates.
"""

import asyncio
import uuid
from typing import Dict, Any, List, Optional
from .base_agent import BaseAgent, AgentType, AgentStatus, AgentCapabilities, AgentMetadata
from datetime import datetime


class ProjectAgent(BaseAgent):
    """
    Project Agent - Project-Specific Layer
    Inherits global schemas and templates from the Main Agent but specializes
    itself based on the project's needs. Manages all project-specific metadata,
    lineage, routing, dependencies, and summaries.
    """

    def __init__(self, project_id: str, parent_agent_id: str):
        # Generate agent ID
        agent_id = f"project_agent_{project_id}_{uuid.uuid4().hex[:8]}"

        # Define Project Agent capabilities
        capabilities = AgentCapabilities(
            can_govern=False,  # Cannot set global policies
            can_specialize=True,  # Can create specialized assistants for this project
            can_execute_tasks=True,
            can_harvest_metadata=True,
            can_cache_results=True,
            can_scale_context=True,
            max_context_tokens=65536  # 64K tokens (XL scale)
        )

        # Create metadata
        metadata = AgentMetadata(
            agent_id=agent_id,
            agent_type=AgentType.PROJECT,
            parent_id=parent_agent_id,
            project_id=project_id,
            capabilities=capabilities,
            status=AgentStatus.INITIALIZING,
            config={
                "project_id": project_id,
                "project_constitution": {},  # MD file content parsed
                "project_index": {},         # JSONC project index
                "project_lineage": {},       # Project-specific lineage
                "project_dependencies": {},  # Dependencies and versions
                "project_routing": {},       # Project-specific routing (CBOR)
                "project_summaries": {},     # Summaries of project components
                "project_constraints": {},   # Project-specific constraints
                "project_templates": {},     # Project-specific templates
                "inherited_from_main": {}    # What we inherited from Main Agent
            }
        )

        super().__init__(metadata)
        self.assistant_agents: Dict[str, 'AssistantAgent'] = {}  # Track assistant agents for this project
        self._maintenance_task: Optional[asyncio.Task] = None
        self.main_agent_id = parent_agent_id

    async def initialize(self) -> bool:
        """Initialize the Project Agent"""
        try:
            self.logger.info(f"Initializing Project Agent {self.metadata.agent_id} for project {self.metadata.project_id}")
            self.metadata.status = AgentStatus.INITIALIZING

            # Initialize project-specific structures
            await self._initialize_project_structures()

            # Inherit from Main Agent (request global schemas/templates)
            await self._inherit_from_main_agent()

            # Start maintenance tasks
            self._maintenance_task = asyncio.create_task(self._maintenance_loop())

            self.metadata.status = AgentStatus.ACTIVE
            self.logger.info(f"Project Agent {self.metadata.agent_id} initialized successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to initialize Project Agent: {e}")
            self.metadata.status = AgentStatus.ERROR
            return False

    async def start(self) -> bool:
        """Start the Project Agent"""
        try:
            self.logger.info(f"Starting Project Agent {self.metadata.agent_id}")
            self.metadata.status = AgentStatus.ACTIVE
            self._is_running = True
            self.logger.info(f"Project Agent {self.metadata.agent_id} started")
            return True
        except Exception as e:
            self.logger.error(f"Failed to start Project Agent: {e}")
            self.metadata.status = AgentStatus.ERROR
            return False

    async def stop(self) -> bool:
        """Stop the Project Agent gracefully"""
        try:
            self.logger.info(f"Stopping Project Agent {self.metadata.agent_id}")
            self.metadata.status = AgentStatus.SHUTTING_DOWN
            self._is_running = False

            # Stop maintenance task
            if self._maintenance_task:
                self._maintenance_task.cancel()
                try:
                    await self._maintenance_task
                except asyncio.CancelledError:
                    pass

            # Stop all assistant agents for this project
            for assistant_agent in self.assistant_agents.values():
                await assistant_agent.stop()

            self.metadata.status = AgentStatus.TERMINATED
            self.logger.info(f"Project Agent {self.metadata.agent_id} stopped")
            return True

        except Exception as e:
            self.logger.error(f"Error stopping Project Agent: {e}")
            self.metadata.status = AgentStatus.ERROR
            return False

    async def process_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Process incoming messages"""
        try:
            message_type = message.get("type", "unknown")
            self.logger.debug(f"Project Agent processing message type: {message_type}")

            # Handle via registered handlers
            if message_type in self._message_handlers:
                handler = self._message_handlers[message_type]
                return await handler(message)
            else:
                # Handle Project Agent specific messages
                return await self._handle_project_agent_message(message)

        except Exception as e:
            self.logger.error(f"Error processing message in Project Agent: {e}")
            return {
                "type": "error",
                "agent_id": self.metadata.agent_id,
                "error": str(e),
                "original_message": message
            }

    async def _handle_project_agent_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle Project Agent specific message types"""
        message_type = message.get("type")

        if message_type == "create_assistant_agent":
            return await self._handle_create_assistant_agent(message)
        elif message_type == "get_project_status":
            return await self._handle_get_project_status(message)
        elif message_type == "store_project_constitution":
            return await self._handle_store_project_constitution(message)
        elif message_type == "store_project_index":
            return await self._handle_store_project_index(message)
        elif message_type == "store_project_dependencies":
            return await self._handle_store_project_dependencies(message)
        elif message_type == "store_project_summary":
            return await self._handle_store_project_summary(message)
        elif message_type == "register_project_template":
            return await self._handle_register_project_template(message)
        elif message_type == "update_project_constraints":
            return await self._handle_update_project_constraints(message)
        elif message_type == "request_inheritance":
            return await self._handle_request_inheritance(message)
        elif message_type == "sync_with_main":
            return await self._handle_sync_with_main(message)
        else:
            return {
                "type": "unknown_message",
                "agent_id": self.metadata.agent_id,
                "message_type": message_type,
                "available_types": [
                    "create_assistant_agent", "get_project_status", "store_project_constitution",
                    "store_project_index", "store_project_dependencies", "store_project_summary",
                    "register_project_template", "update_project_constraints", "request_inheritance",
                    "sync_with_main"
                ]
            }

    async def _handle_create_assistant_agent(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle request to create a new Assistant Agent for this project"""
        task_id = message.get("task_id")

        if not task_id:
            return {
                "type": "error",
                "agent_id": self.metadata.agent_id,
                "error": "task_id is required to create Assistant Agent"
            }

        try:
            # Create Assistant Agent
            assistant_agent = AssistantAgent(
                task_id=task_id,
                project_id=self.metadata.project_id,
                parent_agent_id=self.metadata.agent_id
            )

            # Initialize the assistant agent
            if await assistant_agent.initialize():
                agent_key = task_id
                self.assistant_agents[agent_key] = assistant_agent
                self.logger.info(f"Created Assistant Agent for task '{task_id}' in project '{self.metadata.project_id}'")

                # Store assistant agent info in memory
                await self.store_in_memory(
                    f"project_assistant:{self.metadata.project_id}:{task_id}",
                    {
                        "agent_id": assistant_agent.agent_id,
                        "task_id": task_id,
                        "project_id": self.metadata.project_id,
                        "created_at": datetime.now().isoformat()
                    },
                    importance=0.7
                )

                return {
                    "type": "assistant_agent_created",
                    "project_agent_id": self.metadata.agent_id,
                    "assistant_agent_id": assistant_agent.agent_id,
                    "task_id": task_id,
                    "project_id": self.metadata.project_id
                }
            else:
                return {
                    "type": "error",
                    "agent_id": self.metadata.agent_id,
                    "error": f"Failed to initialize Assistant Agent for task '{task_id}'"
                }

        except Exception as e:
            self.logger.error(f"Error creating Assistant Agent: {e}")
            return {
                "type": "error",
                "agent_id": self.metadata.agent_id,
                "error": str(e)
            }

    async def _handle_get_project_status(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle request for project-specific status"""
        assistant_statuses = {}
        for task_id, agent in self.assistant_agents.items():
            assistant_statuses[task_id] = {
                "agent_id": agent.agent_id,
                "status": agent.status.value,
                "task_id": agent.metadata.config.get("task_id")
            }

        return {
            "type": "project_status",
            "project_agent_id": self.metadata.agent_id,
            "project_id": self.metadata.project_id,
            "project_status": self.metadata.status.value,
            "assistant_agents": assistant_statuses,
            "project_config_keys": list(self.metadata.config.keys()),
            "uptime": (datetime.now() - self.metadata.created_at).total_seconds(),
            "timestamp": datetime.now().isoformat()
        }

    async def _handle_store_project_constitution(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle storing project constitution (MD file content)"""
        constitution_data = message.get("constitution_data")
        if not constitution_data:
            return {
                "type": "error",
                "agent_id": self.metadata.agent_id,
                "error": "constitution_data is required"
            }

        self.metadata.config["project_constitution"] = constitution_data
        self.logger.info(f"Stored project constitution for project {self.metadata.project_id}")

        # Store in memory with high importance
        await self.store_in_memory(
            f"project_constitution:{self.metadata.project_id}",
            constitution_data,
            importance=0.9
        )

        return {
            "type": "project_constitution_stored",
            "project_agent_id": self.metadata.agent_id,
            "project_id": self.metadata.project_id
        }

    async def _handle_store_project_index(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle storing project index (JSONC)"""
        index_data = message.get("index_data")
        if not index_data:
            return {
                "type": "error",
                "agent_id": self.metadata.agent_id,
                "error": "index_data is required"
            }

        self.metadata.config["project_index"] = index_data
        self.logger.info(f"Stored project index for project {self.metadata.project_id}")

        # Store in memory with high importance
        await self.store_in_memory(
            f"project_index:{self.metadata.project_id}",
            index_data,
            importance=0.9
        )

        return {
            "type": "project_index_stored",
            "project_agent_id": self.metadata.agent_id,
            "project_id": self.metadata.project_id
        }

    async def _handle_store_project_dependencies(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle storing project dependencies"""
        dependencies_data = message.get("dependencies_data")
        if not dependencies_data:
            return {
                "type": "error",
                "agent_id": self.metadata.agent_id,
                "error": "dependencies_data is required"
            }

        self.metadata.config["project_dependencies"] = dependencies_data
        self.logger.info(f"Stored project dependencies for project {self.metadata.project_id}")

        # Store in memory with medium-high importance
        await self.store_in_memory(
            f"project_dependencies:{self.metadata.project_id}",
            dependencies_data,
            importance=0.8
        )

        return {
            "type": "project_dependencies_stored",
            "project_agent_id": self.metadata.agent_id,
            "project_id": self.metadata.project_id
        }

    async def _handle_store_project_summary(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle storing project summary"""
        summary_data = message.get("summary_data")
        summary_type = message.get("summary_type", "general")
        if not summary_data:
            return {
                "type": "error",
                "agent_id": self.metadata.agent_id,
                "error": "summary_data is required"
            }

        # Store under project summaries with type key
        if "project_summaries" not in self.metadata.config:
            self.metadata.config["project_summaries"] = {}
        self.metadata.config["project_summaries"][summary_type] = summary_data
        self.logger.info(f"Stored project summary '{summary_type}' for project {self.metadata.project_id}")

        # Store in memory with medium importance
        await self.store_in_memory(
            f"project_summary:{self.metadata.project_id}:{summary_type}",
            summary_data,
            importance=0.7
        )

        return {
            "type": "project_summary_stored",
            "project_agent_id": self.metadata.agent_id,
            "project_id": self.metadata.project_id,
            "summary_type": summary_type
        }

    async def _handle_register_project_template(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle registration of a project-specific template"""
        template_name = message.get("template_name")
        template_content = message.get("template_content")

        if not template_name or not template_content:
            return {
                "type": "error",
                "agent_id": self.metadata.agent_id,
                "error": "template_name and template_content are required"
            }

        if "project_templates" not in self.metadata.config:
            self.metadata.config["project_templates"] = {}
        self.metadata.config["project_templates"][template_name] = template_content
        self.logger.info(f"Registered project template '{template_name}' for project {self.metadata.project_id}")

        # Store in memory with high importance
        await self.store_in_memory(
            f"project_template:{self.metadata.project_id}:{template_name}",
            template_content,
            importance=0.8
        )

        return {
            "type": "project_template_registered",
            "project_agent_id": self.metadata.agent_id,
            "project_id": self.metadata.project_id,
            "template_name": template_name
        }

    async def _handle_update_project_constraints(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle update to project constraints"""
        constraints_updates = message.get("constraints", {})
        self.metadata.config["project_constraints"].update(constraints_updates)
        self.logger.info(f"Updated project constraints: {list(constraints_updates.keys())}")

        # Store in memory
        await self.store_in_memory(
            f"project_constraints:{self.metadata.project_id}",
            self.metadata.config["project_constraints"],
            importance=0.8
        )

        return {
            "type": "project_constraints_updated",
            "project_agent_id": self.metadata.agent_id,
            "project_id": self.metadata.project_id,
            "updated_constraints": list(constraints_updates.keys())
        }

    async def _handle_request_inheritance(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle request for inheritance from Main Agent"""
        inheritance_types = message.get("types", ["schemas", "templates", "routing_rules", "security_boundaries"])
        inherited_data = {}

        # Request each type of inheritance from Main Agent
        for inheritance_type in inheritance_types:
            if inheritance_type == "schemas":
                data = await self.recall_global_knowledge("global_schemas")
                if data:
                    inherited_data["schemas"] = data
            elif inheritance_type == "templates":
                data = await self.recall_global_knowledge("global_templates")
                if data:
                    inherited_data["templates"] = data
            elif inheritance_type == "routing_rules":
                data = await self.recall_global_knowledge("routing_rules")
                if data:
                    inherited_data["routing_rules"] = data
            elif inheritance_type == "security_boundaries":
                data = await self.recall_global_knowledge("security_boundaries")
                if data:
                    inherited_data["security_boundaries"] = data

        # Store inherited data
        self.metadata.config["inherited_from_main"] = inherited_data
        self.logger.info(f"Received inheritance from Main Agent: {list(inherited_data.keys())}")

        return {
            "type": "inheritance_received",
            "project_agent_id": self.metadata.agent_id,
            "project_id": self.metadata.project_id,
            "inherited_types": list(inherited_data.keys())
        }

    async def _handle_sync_with_main(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle synchronization request with Main Agent"""
        try:
            # Send sync request to Main Agent
            sync_message = {
                "type": "sync_project_data",
                "project_id": self.metadata.project_id,
                "project_data": {
                    "constitution": self.metadata.config.get("project_constitution"),
                    "index": self.metadata.config.get("project_index"),
                    "dependencies": self.metadata.config.get("project_dependencies"),
                    "summaries": self.metadata.config.get("project_summaries", {}),
                    "templates": self.metadata.config.get("project_templates", {}),
                    "constraints": self.metadata.config.get("project_constraints", {}),
                    "lineage": self.metadata.config.get("project_lineage", {})
                }
            }

            # In a full implementation, this would send via message bus to Main Agent
            # For now, we'll simulate by storing the sync data
            await self.store_in_memory(
                f"project_sync:{self.metadata.project_id}",
                sync_message["project_data"],
                importance=0.8
            )

            self.logger.info(f"Synced project data with Main Agent for project {self.metadata.project_id}")

            return {
                "type": "project_synced",
                "project_agent_id": self.metadata.agent_id,
                "project_id": self.metadata.project_id,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            self.logger.error(f"Error syncing with Main Agent: {e}")
            return {
                "type": "error",
                "agent_id": self.metadata.agent_id,
                "error": str(e)
            }

    async def _initialize_project_structures(self):
        """Initialize project-specific structures"""
        self.logger.info(f"Initializing project structures for project {self.metadata.project_id}")

        # Load any existing project data from memory
        self.logger.debug(f"Loading project data from memory for project {self.metadata.project_id}")

        # Set up default project configuration
        default_config = {
            "project_id": self.metadata.project_id,
            "created_at": datetime.now().isoformat(),
            "version": "1.0.0",
            "description": f"Project {self.metadata.project_id}",
            "tags": []
        }

        for key, value in default_config.items():
            if key not in self.metadata.config:
                self.metadata.config[key] = value

        self.logger.info(f"Project structures initialized for project {self.metadata.project_id}")

    async def _inherit_from_main_agent(self):
        """Request inheritance of global schemas, templates, etc. from Main Agent"""
        self.logger.info(f"Requesting inheritance from Main Agent for project {self.metadata.project_id}")

        # Request core inheritance
        inheritance_message = {
            "type": "request_inheritance",
            "project_id": self.metadata.project_id,
            "types": ["schemas", "templates", "routing_rules", "security_boundaries"]
        }

        # Process the inheritance request (in full impl, this goes to Main Agent)
        inheritance_result = await self._handle_request_inheritance(inheritance_message)
        self.logger.info(f"Inheritance result: {inheritance_result.get('type')}")

    async def _maintenance_loop(self):
        """Background maintenance loop for the Project Agent"""
        self.logger.info(f"Starting Project Agent maintenance loop for project {self.metadata.project_id}")

        while self._is_running:
            try:
                # Perform periodic maintenance tasks
                await self._perform_maintenance_tasks()

                # Wait before next maintenance cycle
                await asyncio.sleep(60)  # Run maintenance every minute

            except asyncio.CancelledError:
                self.logger.info(f"Project Agent maintenance loop cancelled for project {self.metadata.project_id}")
                break
            except Exception as e:
                self.logger.error(f"Error in Project Agent maintenance loop: {e}")
                await asyncio.sleep(10)  # Wait a bit before retrying

        self.logger.info(f"Project Agent maintenance loop stopped for project {self.metadata.project_id}")

    async def _perform_maintenance_tasks(self):
        """Perform periodic maintenance tasks"""
        # Update heartbeats and check for stale assistants
        current_time = datetime.now()
        stale_threshold = current_time.timestamp() - (20 * 60)  # 20 minutes for assistants

        # Check assistant agents
        to_remove_assistants = []
        for task_id, agent in self.assistant_agents.items():
            last_heartbeat = agent.metadata.last_heartbeat.timestamp()
            if last_heartbeat < stale_threshold:
                self.logger.warning(f"Assistant Agent {agent.agent_id} for task '{task_id}' appears stale")
                to_remove_assistants.append(task_id)

        # Remove stale assistants
        for task_id in to_remove_assistants:
            agent = self.assistant_agents.pop(task_id)
            await agent.stop()
            self.logger.info(f"Removed stale Assistant Agent for task '{task_id}' in project {self.metadata.project_id}")

        # Periodically sync with Main Agent
        if int(current_time.timestamp()) % 300 == 0:  # Every 5 minutes
            await self._handle_sync_with_main({})

        self.logger.debug(f"Project {self.metadata.project_id} maintenance completed at {current_time.isoformat()}")

    # Delegation methods for interacting with Phase 2 memory systems
    async def store_project_knowledge(self, key: str, value: Any, importance: float = 0.7) -> bool:
        """Store knowledge specific to this project"""
        return await self.store_in_memory(f"project_knowledge:{self.metadata.project_id}:{key}", value, importance)

    async def recall_project_knowledge(self, key: str) -> Any:
        """Recall project-specific knowledge"""
        return await self.recall_from_memory(f"project_knowledge:{self.metadata.project_id}:{key}")

    async def search_project_knowledge(self, query: str, limit: int = 15) -> List[Dict[str, Any]]:
        """Search project-specific knowledge"""
        return await self.search_memory(f"project_knowledge:{self.metadata.project_id}:{query}", limit)