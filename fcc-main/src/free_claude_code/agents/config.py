"""
Agent Configuration System
Defines configuration schemas and management for agent behavior and roles.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum
import json
import os
from pathlib import Path


class AgentRole(Enum):
    """Defines common agent roles in the system"""
    GOVERNOR = "governor"          # Sets policies, rules, global governance
    ORCHESTRATOR = "orchestrator"  # Coordinates workflows, manages resources
    SPECIALIST = "specialist"      # Performs specialized tasks
    WORKER = "worker"              # Executes assigned work
    HARVESTER = "harvester"        # Collects and processes metadata
    CACHE_WORKER = "cache_worker"  # Manages caching and retrieval
    MONITOR = "monitor"            # Watches system health and performance
    ANALYZER = "analyzer"          # Analyzes data and provides insights
    COMMUNICATOR = "communicator"  # Handles communication between components


@dataclass
class AgentBehaviorConfig:
    """Configuration for agent behavior"""
    # Lifecycle settings
    auto_start: bool = True
    auto_restart: bool = True
    max_restart_attempts: int = 3
    restart_delay_seconds: float = 5.0

    # Performance settings
    max_concurrent_tasks: int = 10
    task_timeout_seconds: float = 300.0  # 5 minutes
    heartbeat_interval_seconds: float = 30.0

    # Resource limits
    max_memory_mb: int = 512
    max_cpu_percent: float = 80.0

    # Communication settings
    message_queue_size: int = 1000
    message_timeout_seconds: float = 10.0

    # Memory settings
    memory_importance_threshold: float = 0.5
    memory_cleanup_interval_hours: float = 24.0
    memory_max_age_days: int = 30

    # Logging settings
    log_level: str = "INFO"
    log_to_file: bool = False
    log_file_path: Optional[str] = None


@dataclass
class AgentRoleConfig:
    """Configuration for a specific agent role"""
    role: AgentRole
    enabled: bool = True
    priority: int = 0  # Higher priority = higher importance
    permissions: List[str] = field(default_factory=list)
    restrictions: List[str] = field(default_factory=list)
    behavior_overrides: AgentBehaviorConfig = field(default_factory=AgentBehaviorConfig)


@dataclass
class AgentHierarchyConfig:
    """Configuration for the entire agent hierarchy"""
    # Main Agent settings
    main_agent: AgentBehaviorConfig = field(default_factory=AgentBehaviorConfig)

    # Project Agent defaults
    project_agent_defaults: AgentBehaviorConfig = field(default_factory=AgentBehaviorConfig)

    # Assistant Agent defaults
    assistant_agent_defaults: AgentBehaviorConfig = field(default_factory=AgentBehaviorConfig)

    # Role-specific configurations
    role_configs: Dict[AgentRole, AgentRoleConfig] = field(default_factory=dict)

    # Hierarchy rules
    max_projects_per_main: int = 100
    max_assistants_per_project: int = 50
    max_concurrent_assistants: int = 20

    # Communication settings
    enable_inter_agent_communication: bool = True
    communication_encryption: bool = False

    # Monitoring and health
    health_check_interval_seconds: float = 60.0
    agent_registration_ttl_seconds: float = 300.0  # 5 minutes

    # Persistence settings
    persist_agent_state: bool = True
    state_persistence_path: Optional[str] = None
    state_save_interval_seconds: float = 300.0  # 5 minutes


class AgentConfigManager:
    """Manages agent configuration loading, saving, and validation"""

    def __init__(self, config_path: Optional[str] = None):
        self.logger = logging.getLogger(f"{__name__}.AgentConfigManager")
        self.config_path = config_path or self._get_default_config_path()
        self.config: AgentHierarchyConfig = AgentHierarchyConfig()
        self._load_default_role_configs()

        # Try to load existing configuration
        self.load_configuration()

    def _get_default_config_path(self) -> str:
        """Get the default configuration file path"""
        # Use ~/.free_claude_code/agents_config.json
        home_dir = Path.home()
        config_dir = home_dir / ".free_claude_code"
        config_dir.mkdir(exist_ok=True)
        return str(config_dir / "agents_config.json")

    def _load_default_role_configs(self):
        """Load default role configurations"""
        # Main Agent role (Governor/Orchestrator)
        self.config.role_configs[AgentRole.GOVERNOR] = AgentRoleConfig(
            role=AgentRole.GOVERNOR,
            enabled=True,
            priority=100,
            permissions=[
                "set_global_policies",
                "create_project_agents",
                "access_all_memory",
                "modify_system_configuration",
                "audit_all_agents"
            ],
            restrictions=[],
            behavior_overrides=AgentBehaviorConfig(
                auto_start=True,
                max_concurrent_tasks=50,
                memory_importance_threshold=0.8,  # High importance for governance data
                log_level="INFO"
            )
        )

        self.config.role_configs[AgentRole.ORCHESTRATOR] = AgentRoleConfig(
            role=AgentRole.ORCHESTRATOR,
            enabled=True,
            priority=90,
            permissions=[
                "coordinate_workflows",
                "manage_agent_lifecycle",
                "route_messages",
                "monitor_system_health",
                "allocate_resources"
            ],
            restrictions=[
                "set_global_policies",  # Cannot set global policies
                "access_all_memory"     # Limited memory access
            ],
            behavior_overrides=AgentBehaviorConfig(
                auto_start=True,
                max_concurrent_tasks=30,
                memory_importance_threshold=0.6,
                log_level="INFO"
            )
        )

        # Project Agent roles
        self.config.role_configs[AgentRole.SPECIALIST] = AgentRoleConfig(
            role=AgentRole.SPECIALIST,
            enabled=True,
            priority=80,
            permissions=[
                "specialize_in_domain",
                "access_project_memory",
                "create_assistant_agents",
                "execute_specialized_tasks"
            ],
            restrictions=[
                "set_global_policies",
                "access_other_projects_memory",
                "create_project_agents"
            ],
            behavior_overrides=AgentBehaviorConfig(
                auto_start=True,
                max_concurrent_tasks=20,
                memory_importance_threshold=0.7,
                log_level="INFO"
            )
        )

        # Worker roles
        self.config.role_configs[AgentRole.WORKER] = AgentRoleConfig(
            role=AgentRole.WORKER,
            enabled=True,
            priority=60,
            permissions=[
                "execute_assigned_tasks",
                "report_progress",
                "request_assistance"
            ],
            restrictions=[
                "create_agents",
                "modify_system_configuration",
                "access_global_policies"
            ],
            behavior_overrides=AgentBehaviorConfig(
                auto_start=True,
                max_concurrent_tasks=10,
                memory_importance_threshold=0.5,
                log_level="WARNING"
            )
        )

        # Harvester/Cache Worker roles (Assistant Agents)
        self.config.role_configs[AgentRole.HARVESTER] = AgentRoleConfig(
            role=AgentRole.HARVESTER,
            enabled=True,
            priority=70,
            permissions=[
                "scan_directories",
                "extract_metadata",
                "harvest_file_information",
                "update_metadata_cache"
            ],
            restrictions=[
                "execute_general_tasks",
                "modify_system_configuration"
            ],
            behavior_overrides=AgentBehaviorConfig(
                auto_start=True,
                max_concurrent_tasks=15,
                task_timeout_seconds=600.0,  # Longer for harvesting
                memory_importance_threshold=0.4,
                log_level="INFO"
            )
        )

        self.config.role_configs[AgentRole.CACHE_WORKER] = AgentRoleConfig(
            role=AgentRole.CACHE_WORKER,
            enabled=True,
            priority=65,
            permissions=[
                "manage_cache_store",
                "optimize_cache_performance",
                "cleanup_expired_cache",
                "prefetch_likely_data"
            ],
            restrictions=[
                "create_agents",
                "modify_system_configuration"
            ],
            behavior_overrides=AgentBehaviorConfig(
                auto_start=True,
                max_concurrent_tasks=20,
                memory_importance_threshold=0.5,
                log_level="INFO"
            )
        )

        # Monitor role
        self.config.role_configs[AgentRole.MONITOR] = AgentRoleConfig(
            role=AgentRole.MONITOR,
            enabled=True,
            priority=75,
            permissions=[
                "monitor_system_health",
                "collect_metrics",
                "generate_health_reports",
                "trigger_alerts"
            ],
            restrictions=[
                "modify_system_configuration",
                "create_agents",
                "execute_user_tasks"
            ],
            behavior_overrides=AgentBehaviorConfig(
                auto_start=True,
                max_concurrent_tasks=10,
                heartbeat_interval_seconds=15.0,  # More frequent heartbeat
                memory_importance_threshold=0.6,
                log_level="INFO"
            )
        )

        # Analyzer role
        self.config.role_configs[AgentRole.ANALYZER] = AgentRoleConfig(
            role=AgentRole.ANALYZER,
            enabled=True,
            priority=85,
            permissions=[
                "analyze_data_patterns",
                "generate_insights",
                "create_reports",
                "suggest_optimizations"
            ],
            restrictions=[
                "modify_system_configuration",
                "create_agents",
                "execute_real_time_tasks"
            ],
            behavior_overrides=AgentBehaviorConfig(
                auto_start=True,
                max_concurrent_tasks=15,
                memory_importance_threshold=0.7,  # High importance for analytical insights
                log_level="INFO"
            )
        )

        # Communicator role
        self.config.role_configs[AgentRole.COMMUNICATOR] = AgentRoleConfig(
            role=AgentRole.COMMUNICATOR,
            enabled=True,
            priority=70,
            permissions=[
                "route_messages",
                "translate_protocols",
                "manage_message_queues",
                "ensure_message_delivery"
            ],
            restrictions=[
                "modify_message_content",  # Cannot alter message content
                "create_agents",
                "access_user_data"
            ],
            behavior_overrides=AgentBehaviorConfig(
                auto_start=True,
                max_concurrent_tokens=25,
                memory_importance_threshold=0.5,
                log_level="INFO"
            )
        )

    def load_configuration(self) -> bool:
        """Load configuration from file"""
        try:
            if not os.path.exists(self.config_path):
                self.logger.info(f"Configuration file not found: {self.config_path}")
                return False

            with open(self.config_path, 'r') as f:
                config_data = json.load(f)

            # TODO: Implement proper deserialization from JSON to AgentHierarchyConfig
            # For now, we'll log that we found a config file
            self.logger.info(f"Loaded agent configuration from: {self.config_path}")
            # In a full implementation, we would parse config_data into self.config

            return True

        except Exception as e:
            self.logger.error(f"Error loading agent configuration: {e}")
            return False

    def save_configuration(self) -> bool:
        """Save configuration to file"""
        try:
            config_dir = os.path.dirname(self.config_path)
            if config_dir:
                os.makedirs(config_dir, exist_ok=True)

            # TODO: Implement proper serialization of AgentHierarchyConfig to JSON
            # For now, we'll save a basic structure
            config_data = {
                "version": "1.0.0",
                "saved_at": datetime.now().isoformat(),
                "main_agent": {
                    "auto_start": self.config.main_agent.auto_start,
                    "max_concurrent_tasks": self.config.main_agent.max_concurrent_tasks
                },
                "role_configs": {
                    role.value: {
                        "enabled": role_config.enabled,
                        "priority": role_config.priority,
                        "permissions": role_config.permissions,
                        "restrictions": role_config.restrictions
                    }
                    for role, role_config in self.config.role_configs.items()
                }
            }

            with open(self.config_path, 'w') as f:
                json.dump(config_data, f, indent=2)

            self.logger.info(f"Saved agent configuration to: {self.config_path}")
            return True

        except Exception as e:
            self.logger.error(f"Error saving agent configuration: {e}")
            return False

    def get_role_config(self, role: AgentRole) -> AgentRoleConfig:
        """Get configuration for a specific role"""
        return self.config.role_configs.get(role, AgentRoleConfig(role=role))

    def update_role_config(self, role: AgentRole, config_updates: Dict[str, Any]) -> bool:
        """Update configuration for a specific role"""
        try:
            if role not in self.config.role_configs:
                self.config.role_configs[role] = AgentRoleConfig(role=role)

            role_config = self.config.role_configs[role]

            # Update fields
            for key, value in config_updates.items():
                if hasattr(role_config, key):
                    setattr(role_config, key, value)
                elif hasattr(role_config.behavior_overrides, key):
                    setattr(role_config.behavior_overrides, key, value)

            self.logger.info(f"Updated configuration for role: {role.value}")
            return True

        except Exception as e:
            self.logger.error(f"Error updating role configuration: {e}")
            return False

    def validate_configuration(self) -> List[str]:
        """Validate the current configuration and return list of errors"""
        errors = []

        # Validate main agent config
        if self.config.main_agent.max_concurrent_tasks < 1:
            errors.append("main_agent.max_concurrent_tasks must be >= 1")

        if self.config.main_agent.memory_importance_threshold < 0 or self.config.main_agent.memory_importance_threshold > 1:
            errors.append("main_agent.memory_importance_threshold must be between 0 and 1")

        # Validate role configs
        for role, role_config in self.config.role_configs.items():
            if role_config.priority < 0:
                errors.append(f"{role.value}.priority must be >= 0")

            # Check for conflicting permissions/restrictions
            conflicting = set(role_config.permissions) & set(role_config.restrictions)
            if conflicting:
                errors.append(f"{role.value} has conflicting permissions and restrictions: {conflicting}")

        # Validate hierarchy rules
        if self.config.max_projects_per_main < 1:
            errors.append("max_projects_per_main must be >= 1")

        if self.config.max_assistants_per_project < 1:
            errors.append("max_assistants_per_project must be >= 1")

        return errors


# Global configuration manager instance
_global_config_manager: Optional[AgentConfigManager] = None


def get_agent_config_manager() -> AgentConfigManager:
    """Get the global agent configuration manager instance"""
    global _global_config_manager
    if _global_config_manager is None:
        _global_config_manager = AgentConfigManager()
    return _global_config_manager


# Convenience functions
def get_role_config(role: AgentRole) -> AgentRoleConfig:
    """Get configuration for a specific agent role"""
    return get_agent_config_manager().get_role_config(role)


def update_role_config(role: AgentRole, config_updates: Dict[str, Any]) -> bool:
    """Update configuration for a specific agent role"""
    return get_agent_config_manager().update_role_config(role, config_updates)


def load_agent_configuration(config_path: Optional[str] = None) -> bool:
    """Load agent configuration from file"""
    manager = AgentConfigManager(config_path) if config_path else get_agent_config_manager()
    return manager.load_configuration()


def save_agent_configuration(config_path: Optional[str] = None) -> bool:
    """Save agent configuration to file"""
    if config_path:
        manager = AgentConfigManager(config_path)
        return manager.save_configuration()
    else:
        return get_agent_config_manager().save_configuration()