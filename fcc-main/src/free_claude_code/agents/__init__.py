"""
Free Claude Code Agents Module
"""
from .base_agent import AgentType, AgentStatus
from .agent_manager import (
    get_agent_supervisor,
    spawn_main_agent,
    spawn_project_agent,
    spawn_assistant_agent
)

__all__ = [
    "AgentType",
    "AgentStatus",
    "get_agent_supervisor",
    "spawn_main_agent",
    "spawn_project_agent",
    "spawn_assistant_agent"
]