"""
Main Agent - Global Governance Orchestrator
Corresponds to the Main Librarian concept from the Librarian Hierarchy.
Responsible for global schemas, templates, routing rules, security boundaries,
and creating/supervising Project Agents.
"""

import asyncio
import uuid
from typing import Dict, Any, List, Optional
from .base_agent import BaseAgent, AgentType, AgentStatus, AgentCapabilities, AgentMetadata


class MainAgent(BaseAgent):
    """
    Main Agent - Global Governance Layer
    The root agent that governs all metadata, lineage, routing, templates,
    schemas, and security boundaries for the entire multi-agent system.
    """

    def __init__(self, agent_id: Optional[str] = None):
        # Generate agent ID if not provided
        if agent_id is None:
            agent_id = f"main_agent_{uuid.uuid4().hex[:8]}"

        # Define Main Agent capabilities
        capabilities = AgentCapabilities(
            can_govern=True,
            can_specialize=True,
            can_execute_tasks=True,
            can_harvest_metadata=True,
            can_cache_results=True,
            can_scale_context=True,
            max_context_tokens=131072  # 128K tokens (XXL scale)
        )

        # Create metadata
        metadata = AgentMetadata(
            agent_id=agent_id,
            agent_type=AgentType.MAIN,
            capabilities=capabilities,
            status=AgentStatus.INITIALIZING,
            config={
                "governance_policies": {},
                "global_schemas": {},
                "global_templates": {},
                "routing_rules": {},
                "security_boundaries": {},
                "lineage_registry": {},
                "provider_metadata": {}
            }
        )

        super().__init__(metadata)
        self.project_agents: Dict[str, 'ProjectAgent'] = {}  # Track project agents
        self.assistant_agents: Dict[str, 'AssistantAgent'] = {}  # Track assistant agents
        self._maintenance_task: Optional[asyncio.Task] = None

    async def initialize(self) -> bool:
        """Initialize the Main Agent"""
        try:
            self.logger.info(f"Initializing Main Agent {self.metadata.agent_id}")
            self.metadata.status = AgentStatus.INITIALIZING

            # Initialize global governance structures
            await self._initialize_global_governance()

            # Start maintenance tasks
            self._maintenance_task = asyncio.create_task(self._maintenance_loop())

            self.metadata.status = AgentStatus.ACTIVE
            self.logger.info(f"Main Agent {self.metadata.agent_id} initialized successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to initialize Main Agent: {e}")
            self.metadata.status = AgentStatus.ERROR
            return False

    async def start(self) -> bool:
        """Start the Main Agent"""
        try:
            self.logger.info(f"Starting Main Agent {self.metadata.agent_id}")
            self.metadata.status = AgentStatus.ACTIVE
            self._is_running = True
            self.logger.info(f"Main Agent {self.metadata.agent_id} started")
            return True
        except Exception as e:
            self.logger.error(f"Failed to start Main Agent: {e}")
            self.metadata.status = AgentStatus.ERROR
            return False

    async def stop(self) -> bool:
        """Stop the Main Agent gracefully"""
        try:
            self.logger.info(f"Stopping Main Agent {self.metadata.agent_id}")
            self.metadata.status = AgentStatus.SHUTTING_DOWN
            self._is_running = False

            # Stop maintenance task
            if self._maintenance_task:
                self._maintenance_task.cancel()
                try:
                    await self._maintenance_task
                except asyncio.CancelledError:
                    pass

            # Stop all project and assistant agents
            for project_agent in self.project_agents.values():
                await project_agent.stop()

            for assistant_agent in self.assistant_agents.values():
                await assistant_agent.stop()

            self.metadata.status = AgentStatus.TERMINATED
            self.logger.info(f"Main Agent {self.metadata.agent_id} stopped")
            return True

        except Exception as e:
            self.logger.error(f"Error stopping Main Agent: {e}")
            self.metadata.status = AgentStatus.ERROR
            return False

    async def process_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Process incoming messages"""
        try:
            message_type = message.get("type", "unknown")
            self.logger.debug(f"Main Agent processing message type: {message_type}")

            # Handle via registered handlers
            if message_type in self._message_handlers:
                handler = self._message_handlers[message_type]
                return await handler(message)
            else:
                # Handle Main Agent specific messages
                return await self._handle_main_agent_message(message)

        except Exception as e:
            self.logger.error(f"Error processing message in Main Agent: {e}")
            return {
                "type": "error",
                "agent_id": self.metadata.agent_id,
                "error": str(e),
                "original_message": message
            }

    async def _handle_main_agent_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle Main Agent specific message types"""
        message_type = message.get("type")

        if message_type == "create_project_agent":
            return await self._handle_create_project_agent(message)
        elif message_type == "create_assistant_agent":
            return await self._handle_create_assistant_agent(message)
        elif message_type == "get_system_status":
            return await self._handle_get_system_status(message)
        elif message_type == "register_global_schema":
            return await self._handle_register_global_schema(message)
        elif message_type == "register_global_template":
            return await self._handle_register_global_template(message)
        elif message_type == "update_routing_rules":
            return await self._handle_update_routing_rules(message)
        elif message_type == "update_security_boundaries":
            return await self._handle_update_security_boundaries(message)
        else:
            return {
                "type": "unknown_message",
                "agent_id": self.metadata.agent_id,
                "message_type": message_type,
                "available_types": [
                    "create_project_agent", "create_assistant_agent", "get_system_status",
                    "register_global_schema", "register_global_template",
                    "update_routing_rules", "update_security_boundaries"
                ]
            }

    async def _handle_create_project_agent(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle request to create a new Project Agent"""
        project_id = message.get("project_id")
        if not project_id:
            return {
                "type": "error",
                "agent_id": self.metadata.agent_id,
                "error": "project_id is required to create Project Agent"
            }

        if project_id in self.project_agents:
            return {
                "type": "error",
                "agent_id": self.metadata.agent_id,
                "error": f"Project Agent for project_id '{project_id}' already exists"
            }

        try:
            # Create Project Agent
            project_agent = ProjectAgent(
                project_id=project_id,
                parent_agent_id=self.metadata.agent_id
            )

            # Initialize the project agent
            if await project_agent.initialize():
                self.project_agents[project_id] = project_agent
                self.logger.info(f"Created Project Agent for project '{project_id}'")

                # Store project agent info in memory
                await self.store_in_memory(
                    f"project_agent:{project_id}",
                    {
                        "agent_id": project_agent.agent_id,
                        "project_id": project_id,
                        "created_at": datetime.now().isoformat()
                    },
                    importance=0.8
                )

                return {
                    "type": "project_agent_created",
                    "main_agent_id": self.metadata.agent_id,
                    "project_agent_id": project_agent.agent_id,
                    "project_id": project_id
                }
            else:
                return {
                    "type": "error",
                    "agent_id": self.metadata.agent_id,
                    "error": f"Failed to initialize Project Agent for project '{project_id}'"
                }

        except Exception as e:
            self.logger.error(f"Error creating Project Agent: {e}")
            return {
                "type": "error",
                "agent_id": self.metadata.agent_id,
                "error": str(e)
            }

    async def _handle_create_assistant_agent(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle request to create a new Assistant Agent"""
        task_id = message.get("task_id")
        project_id = message.get("project_id")

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
                project_id=project_id,
                parent_agent_id=self.metadata.agent_id
            )

            # Initialize the assistant agent
            if await assistant_agent.initialize():
                agent_key = f"{project_id or 'global'}:{task_id}"
                self.assistant_agents[agent_key] = assistant_agent
                self.logger.info(f"Created Assistant Agent for task '{task_id}'")

                # Store assistant agent info in memory
                await self.store_in_memory(
                    f"assistant_agent:{task_id}",
                    {
                        "agent_id": assistant_agent.agent_id,
                        "task_id": task_id,
                        "project_id": project_id,
                        "created_at": datetime.now().isoformat()
                    },
                    importance=0.6
                )

                return {
                    "type": "assistant_agent_created",
                    "main_agent_id": self.metadata.agent_id,
                    "assistant_agent_id": assistant_agent.agent_id,
                    "task_id": task_id,
                    "project_id": project_id
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

    async def _handle_get_system_status(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle request for system-wide status"""
        project_statuses = {}
        for project_id, agent in self.project_agents.items():
            project_statuses[project_id] = {
                "agent_id": agent.agent_id,
                "status": agent.status.value,
                "uptime": (datetime.now() - agent.metadata.created_at).total_seconds()
            }

        assistant_statuses = {}
        for agent_key, agent in self.assistant_agents.items():
            assistant_statuses[agent_key] = {
                "agent_id": agent.agent_id,
                "status": agent.status.value,
                "task_id": agent.metadata.config.get("task_id"),
                "project_id": agent.metadata.config.get("project_id")
            }

        return {
            "type": "system_status",
            "main_agent_id": self.metadata.agent_id,
            "main_agent_status": self.metadata.status.value,
            "project_agents": project_statuses,
            "assistant_agents": assistant_statuses,
            "total_projects": len(self.project_agents),
            "total_assistants": len(self.assistant_agents),
            "timestamp": datetime.now().isoformat()
        }

    async def _handle_register_global_schema(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle registration of a global schema"""
        schema_name = message.get("schema_name")
        schema_definition = message.get("schema_definition")

        if not schema_name or not schema_definition:
            return {
                "type": "error",
                "agent_id": self.metadata.agent_id,
                "error": "schema_name and schema_definition are required"
            }

        self.metadata.config["global_schemas"][schema_name] = schema_definition
        self.logger.info(f"Registered global schema: {schema_name}")

        # Store in memory with high importance
        await self.store_in_memory(
            f"global_schema:{schema_name}",
            schema_definition,
            importance=0.9
        )

        return {
            "type": "global_schema_registered",
            "main_agent_id": self.metadata.agent_id,
            "schema_name": schema_name
        }

    async def _handle_register_global_template(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle registration of a global template"""
        template_name = message.get("template_name")
        template_content = message.get("template_content")

        if not template_name or not template_content:
            return {
                "type": "error",
                "agent_id": self.metadata.agent_id,
                "error": "template_name and template_content are required"
            }

        self.metadata.config["global_templates"][template_name] = template_content
        self.logger.info(f"Registered global template: {template_name}")

        # Store in memory with high importance
        await self.store_in_memory(
            f"global_template:{template_name}",
            template_content,
            importance=0.9
        )

        return {
            "type": "global_template_registered",
            "main_agent_id": self.metadata.agent_id,
            "template_name": template_name
        }

    async def _handle_update_routing_rules(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle update to routing rules"""
        routing_updates = message.get("routing_rules", {})
        self.metadata.config["routing_rules"].update(routing_updates)
        self.logger.info(f"Updated routing rules: {list(routing_updates.keys())}")

        # Store in memory
        await self.store_in_memory(
            "routing_rules",
            self.metadata.config["routing_rules"],
            importance=0.8
        )

        return {
            "type": "routing_rules_updated",
            "main_agent_id": self.metadata.agent_id,
            "updated_rules": list(routing_updates.keys())
        }

    async def _handle_update_security_boundaries(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle update to security boundaries"""
        security_updates = message.get("security_boundaries", {})
        self.metadata.config["security_boundaries"].update(security_updates)
        self.logger.info(f"Updated security boundaries: {list(security_updates.keys())}")

        # Store in memory
        await self.store_in_memory(
            "security_boundaries",
            self.metadata.config["security_boundaries"],
            importance=0.9  # High importance for security
        )

        return {
            "type": "security_boundaries_updated",
            "main_agent_id": self.metadata.agent_id,
            "updated_boundaries": list(security_updates.keys())
        }

    async def _initialize_global_governance(self):
        """Initialize global governance structures"""
        self.logger.info("Initializing global governance structures")

        # Load any existing governance data from memory
        # In a full implementation, this would load from persistent storage
        self.logger.debug("Loading global governance data from memory")

        # Set up default governance policies
        default_policies = {
            "max_concurrent_projects": 100,
            "max_agents_per_project": 50,
            "agent_idle_timeout_minutes": 30,
            "memory_retention_days": 365,
            "audit_logging_enabled": True
        }

        for policy, value in default_policies.items():
            if policy not in self.metadata.config["governance_policies"]:
                self.metadata.config["governance_policies"][policy] = value

        self.logger.info("Global governance structures initialized")

    async def _maintenance_loop(self):
        """Background maintenance loop for the Main Agent"""
        self.logger.info("Starting Main Agent maintenance loop")

        while self._is_running:
            try:
                # Perform periodic maintenance tasks
                await self._perform_maintenance_tasks()

                # Wait before next maintenance cycle
                await asyncio.sleep(60)  # Run maintenance every minute

            except asyncio.CancelledError:
                self.logger.info("Main Agent maintenance loop cancelled")
                break
            except Exception as e:
                self.logger.error(f"Error in Main Agent maintenance loop: {e}")
                await asyncio.sleep(10)  # Wait a bit before retrying

        self.logger.info("Main Agent maintenance loop stopped")

    async def _perform_maintenance_tasks(self):
        """Perform periodic maintenance tasks"""
        # Update heartbeats for all agents
        current_time = datetime.now()

        # Check for stale agents
        stale_threshold = current_time.timestamp() - (30 * 60)  # 30 minutes

        # Check project agents
        to_remove_projects = []
        for project_id, agent in self.project_agents.items():
            last_heartbeat = agent.metadata.last_heartbeat.timestamp()
            if last_heartbeat < stale_threshold:
                self.logger.warning(f"Project Agent {agent.agent_id} appears stale")
                # In a full implementation, we might attempt to restart or notify
                to_remove_projects.append(project_id)

        # Remove stale agents (in a real system, we'd be more careful)
        for project_id in to_remove_projects:
            agent = self.project_agents.pop(project_id)
            await agent.stop()
            self.logger.info(f"Removed stale Project Agent for project '{project_id}'")

        # Log maintenance completion
        self.logger.debug(f"Maintenance completed at {current_time.isoformat()}")

    # Delegation methods for interacting with Phase 2 memory systems
    async def store_global_knowledge(self, key: str, value: Any, importance: float = 0.8) -> bool:
        """Store knowledge that should be globally accessible"""
        return await self.store_in_memory(f"global_knowledge:{key}", value, importance)

    async def recall_global_knowledge(self, key: str) -> Any:
        """Recall globally accessible knowledge"""
        return await self.recall_from_memory(f"global_knowledge:{key}")

    async def search_global_knowledge(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Search global knowledge"""
        return await self.search_memory(f"global_knowledge:{query}", limit)