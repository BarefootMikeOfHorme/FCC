"""
Agent Manager for Free Claude Code Agent System
Handles spawning, supervision, and lifecycle management of agents.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from .base_agent import BaseAgent, AgentType, AgentStatus, AgentMetadata

logger = logging.getLogger(__name__)


class AgentSupervisor:
    """Supervises and manages the lifecycle of agents in the system."""

    def __init__(self):
        self._agents: Dict[str, BaseAgent] = {}
        self._is_supervising = False
        logger.debug("AgentSupervisor initialized")

    async def spawn_main_agent(self) -> Optional[BaseAgent]:
        """Spawn a Main Agent (global governance/orchestrator)."""
        try:
            # Import here to avoid circular dependencies
            from .main_agent import MainAgent

            metadata = AgentMetadata(
                agent_id=f"main_agent_{datetime.now().timestamp()}",
                agent_type=AgentType.MAIN,
                capabilities=AgentCapabilities(  # Get default capabilities
                    can_govern=True,
                    can_specialize=True,
                    max_context_tokens=32000
                )
            )

            agent = MainAgent(metadata)
            success = await agent.initialize()
            if success:
                success = await agent.start()

            if success:
                self._agents[agent.agent_id] = agent
                logger.info(f"Spawned Main Agent: {agent.agent_id}")
                return agent
            else:
                logger.error("Failed to initialize/start Main Agent")
                return None
        except Exception as e:
            logger.error(f"Error spawning Main Agent: {e}")
            return None

    async def spawn_project_agent(self, project_id: str, parent_agent_id: Optional[str] = None) -> Optional[BaseAgent]:
        """Spawn a Project Agent (project-specific specialization)."""
        try:
            # Import here to avoid circular dependencies
            from .project_agent import ProjectAgent

            metadata = AgentMetadata(
                agent_id=f"project_agent_{project_id}_{datetime.now().timestamp()}",
                agent_type=AgentType.PROJECT,
                project_id=project_id,
                parent_id=parent_agent_id,
                capabilities=AgentCapabilities(  # Get default capabilities
                    can_specialize=True,
                    can_execute_tasks=True,
                    max_context_tokens=16000
                )
            )

            agent = ProjectAgent(metadata)
            success = await agent.initialize()
            if success:
                success = await agent.start()

            if success:
                self._agents[agent.agent_id] = agent
                logger.info(f"Spawned Project Agent: {agent.agent_id} for project {project_id}")
                return agent
            else:
                logger.error(f"Failed to initialize/start Project Agent for project {project_id}")
                return None
        except Exception as e:
            logger.error(f"Error spawning Project Agent: {e}")
            return None

    async def spawn_assistant_agent(self, task_id: str, project_id: str, parent_agent_id: Optional[str] = None) -> Optional[BaseAgent]:
        """Spawn an Assistant Agent (metadata harvesting/caching)."""
        try:
            # Import here to avoid circular dependencies
            from .assistant_agent import AssistantAgent

            metadata = AgentMetadata(
                agent_id=f"assistant_agent_{task_id}_{datetime.now().timestamp()}",
                agent_type=AgentType.ASSISTANT,
                project_id=project_id,
                parent_id=parent_agent_id,
                config={
                    "task_id": task_id,
                    "project_id": project_id
                },
                capabilities=AgentCapabilities(  # Get default capabilities
                    can_execute_tasks=True,
                    can_harvest_metadata=True,
                    can_cache_results=True,
                    max_context_tokens=8000
                )
            )

            agent = AssistantAgent(metadata)
            success = await agent.initialize()
            if success:
                success = await agent.start()

            if success:
                self._agents[agent.agent_id] = agent
                logger.info(f"Spawned Assistant Agent: {agent.agent_id} for task {task_id}")
                return agent
            else:
                logger.error(f"Failed to initialize/start Assistant Agent for task {task_id}")
                return None
        except Exception as e:
            logger.error(f"Error spawning Assistant Agent: {e}")
            return None

    async def get_agent_status(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get the status of an agent."""
        agent = self._agents.get(agent_id)
        if not agent:
            return None

        return {
            "agent_id": agent.agent_id,
            "agent_type": agent.agent_type.value,
            "status": agent.status.value,
            "is_running": agent.is_running(),
            "uptime_seconds": (datetime.now() - agent.metadata.created_at).total_seconds()
        }

    async def stop_agent(self, agent_id: str) -> bool:
        """Stop an agent gracefully."""
        agent = self._agents.get(agent_id)
        if not agent:
            logger.warning(f"Agent {agent_id} not found")
            return False

        try:
            success = await agent.stop()
            if success:
                del self._agents[agent_id]
                logger.info(f"Stopped Agent: {agent_id}")
            return success
        except Exception as e:
            logger.error(f"Error stopping agent {agent_id}: {e}")
            return False

    async def list_managed_agents(self) -> List[Dict[str, Any]]:
        """List all managed agents."""
        agents = []
        for agent in self._agents.values():
            agents.append({
                "agent_id": agent.agent_id,
                "agent_type": agent.agent_type.value,
                "status": agent.status.value,
                "is_running": agent.is_running()
            })
        return agents

    def get_supervision_stats(self) -> Dict[str, Any]:
        """Get supervision statistics."""
        status_distribution = {}
        for agent in self._agents.values():
            status = agent.status.value
            status_distribution[status] = status_distribution.get(status, 0) + 1

        return {
            "total_managed_agents": len(self._agents),
            "is_supervising": self._is_supervising,
            "status_distribution": status_distribution
        }

    async def _emit_lifecycle_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Emit a lifecycle event (placeholder for event system)."""
        logger.debug(f"Lifecycle event: {event_type}, data: {data}")


# Global supervisor instance
_supervisor: Optional[AgentSupervisor] = None


def get_agent_supervisor() -> AgentSupervisor:
    """Get the global agent supervisor instance."""
    global _supervisor
    if _supervisor is None:
        _supervisor = AgentSupervisor()
    return _supervisor


async def spawn_main_agent() -> Optional[BaseAgent]:
    """Convenience function to spawn a Main Agent."""
    supervisor = get_agent_supervisor()
    return await supervisor.spawn_main_agent()


async def spawn_project_agent(project_id: str, parent_agent_id: Optional[str] = None) -> Optional[BaseAgent]:
    """Convenience function to spawn a Project Agent."""
    supervisor = get_agent_supervisor()
    return await supervisor.spawn_project_agent(project_id, parent_agent_id)


async def spawn_assistant_agent(task_id: str, project_id: str, parent_agent_id: Optional[str] = None) -> Optional[BaseAgent]:
    """Convenience function to spawn an Assistant Agent."""
    supervisor = get_agent_supervisor()
    return await supervisor.spawn_assistant_agent(task_id, project_id, parent_agent_id)