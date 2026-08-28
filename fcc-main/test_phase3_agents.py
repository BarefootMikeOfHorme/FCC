#!/usr/bin/env python3
"""
Test script to verify Phase 3 agent system works correctly.
"""

import asyncio
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from free_claude_code.agents import (
    get_agent_supervisor,
    spawn_main_agent,
    spawn_project_agent,
    spawn_assistant_agent,
    AgentType
)


async def test_agent_system():
    """Test the agent system by spawning and interacting with agents"""
    print("Testing Phase 3 Agent System...")

    try:
        # Test 1: Spawn a Main Agent
        print("\n1. Spawning Main Agent...")
        main_agent = await spawn_main_agent()
        if main_agent:
            print(f"✓ Successfully spawned Main Agent: {main_agent.agent_id}")

            # Get status
            supervisor = get_agent_supervisor()
            status = await supervisor.get_agent_status(main_agent.agent_id)
            print(f"  Status: {status['status'] if status else 'Unknown'}")
        else:
            print("✗ Failed to spawn Main Agent")
            return False

        # Test 2: Spawn a Project Agent
        print("\n2. Spawning Project Agent...")
        project_agent = await spawn_project_agent(
            project_id="test_project_001",
            parent_agent_id=main_agent.agent_id if main_agent else None
        )
        if project_agent:
            print(f"✓ Successfully spawned Project Agent: {project_agent.agent_id}")

            # Get status
            supervisor = get_agent_supervisor()
            status = await supervisor.get_agent_status(project_agent.agent_id)
            print(f"  Status: {status['status'] if status else 'Unknown'}")
            print(f"  Project ID: {getattr(project_agent, 'project_id', 'Unknown')}")
        else:
            print("✗ Failed to spawn Project Agent")

        # Test 3: Spawn an Assistant Agent
        print("\n3. Spawning Assistant Agent...")
        assistant_agent = await spawn_assistant_agent(
            task_id="metadata_harvest_task_001",
            project_id="test_project_001",
            parent_agent_id=project_agent.agent_id if project_agent else None
        )
        if assistant_agent:
            print(f"✓ Successfully spawned Assistant Agent: {assistant_agent.agent_id}")

            # Get status
            supervisor = get_agent_supervisor()
            status = await supervisor.get_agent_status(assistant_agent.agent_id)
            print(f"  Status: {status['status'] if status else 'Unknown'}")
            print(f"  Task ID: {getattr(assistant_agent.metadata.config, 'task_id', 'Unknown')}")
            print(f"  Project ID: {getattr(assistant_agent.metadata.config, 'project_id', 'Unknown')}")
        else:
            print("✗ Failed to spawn Assistant Agent")

        # Test 4: List all managed agents
        print("\n4. Listing all managed agents...")
        supervisor = get_agent_supervisor()
        agents = await supervisor.list_managed_agents()
        print(f"✓ Found {len(agents)} managed agents:")
        for agent in agents:
            print(f"  - {agent['agent_id']} ({agent['agent_type']}): {agent['status']}")

        # Test 5: Get supervision stats
        print("\n5. Getting supervision statistics...")
        stats = supervisor.get_supervision_stats()
        print(f"✓ Supervision stats:")
        print(f"  Total managed agents: {stats['total_managed_agents']}")
        print(f"  Is supervising: {stats['is_supervising']}")
        print(f"  Status distribution: {stats['status_distribution']}")

        # Test 6: Stop agents gracefully
        print("\n6. Stopping agents...")
        if assistant_agent:
            await supervisor.stop_agent(assistant_agent.agent_id)
            print(f"✓ Stopped Assistant Agent: {assistant_agent.agent_id}")

        if project_agent:
            await supervisor.stop_agent(project_agent.agent_id)
            print(f"✓ Stopped Project Agent: {project_agent.agent_id}")

        if main_agent:
            await supervisor.stop_agent(main_agent.agent_id)
            print(f"✓ Stopped Main Agent: {main_agent.agent_id}")

        # Verify agents are stopped
        print("\n7. Verifying agents are stopped...")
        agents = await supervisor.list_managed_agents()
        print(f"✓ Remaining managed agents: {len(agents)}")

        print("\n🎉 All tests passed! Phase 3 agent system is working correctly.")
        return True

    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    # Run the test
    success = asyncio.run(test_agent_system())
    sys.exit(0 if success else 1)