#!/usr/bin/env python3
"""Simple test to verify imports and basic functionality."""

import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

def test_imports():
    """Test that all required modules can be imported."""
    print("Testing imports...")

    # Test settings
    from free_claude_code.config.settings import Settings
    print("[OK] Settings import successful")

    # Test persistent memory
    from free_claude_code.messaging.memory.persistent import PersistentMemoryStore, MemoryItem
    print("[OK] PersistentMemoryStore import successful")

    # Test workflow
    from free_claude_code.messaging.workflow import MessagingWorkflow
    print("[OK] MessagingWorkflow import successful")

    return True

def test_settings():
    """Test settings configuration."""
    print("\nTesting settings...")

    from free_claude_code.config.settings import Settings
    settings = Settings()

    # Check that memory settings exist
    assert hasattr(settings, 'memory_short_term_max_tokens')
    assert hasattr(settings, 'memory_persistent_enabled')
    assert hasattr(settings, 'memory_persistent_max_items')
    assert hasattr(settings, 'memory_persistent_similarity_threshold')
    assert hasattr(settings, 'memory_persistent_importance_decay')
    assert hasattr(settings, 'memory_persistent_auto_store_threshold')

    print(f"[OK] memory_short_term_max_tokens: {settings.memory_short_term_max_tokens}")
    print(f"[OK] memory_persistent_enabled: {settings.memory_persistent_enabled}")
    print(f"[OK] memory_persistent_max_items: {settings.memory_persistent_max_items}")
    print(f"[OK] memory_persistent_similarity_threshold: {settings.memory_persistent_similarity_threshold}")
    print(f"[OK] memory_persistent_importance_decay: {settings.memory_persistent_importance_decay}")
    print(f"[OK] memory_persistent_auto_store_threshold: {settings.memory_persistent_auto_store_threshold}")

    return True

def test_persistent_memory():
    """Test persistent memory store basic operations."""
    print("\nTesting persistent memory store...")

    from free_claude_code.config.settings import Settings
    from free_claude_code.messaging.memory.persistent import PersistentMemoryStore

    settings = Settings()
    store = PersistentMemoryStore(settings)

    # Test storing a memory
    memory_id = store.store_memory(
        content="Test memory content",
        tags=["test"],
        importance_score=0.7,
        source="test"
    )
    assert memory_id is not None
    print(f"[OK] Stored memory with ID: {memory_id}")

    # Test retrieving the memory
    retrieved = store.get_memory(memory_id)
    assert retrieved is not None
    assert retrieved.content == "Test memory content"
    assert retrieved.importance_score == 0.7
    print(f"[OK] Retrieved memory: {retrieved.content[:20]}...")

    # Test search
    results = store.search_memories("Test memory", limit=5)
    assert len(results) > 0
    print(f"[OK] Found {len(results)} memories via search")

    return True

def test_workflow_initialization():
    """Test MessagingWorkflow initialization with memory systems."""
    print("\nTesting MessagingWorkflow initialization...")

    from free_claude_code.config.settings import Settings
    from free_claude_code.messaging.workflow import MessagingWorkflow

    # Create mock classes for dependencies
    class MockOutboundMessenger:
        async def queue_send_message(self, *args, **kwargs):
            return "test_msg_id"
        async def queue_edit_message(self, *args, **kwargs):
            pass
        async def queue_delete_messages(self, *args, **kwargs):
            pass
        def fire_and_forget(self, coro):
            import asyncio
            asyncio.create_task(coro)

    class MockSessionManager:
        async def stop_all(self):
            pass

    class MockSessionStore:
        def load_conversation_snapshot(self):
            from free_claude_code.messaging.trees import ConversationSnapshot
            return ConversationSnapshot(is_empty=True, trees={})
        def flush_pending_save(self):
            pass
        def save_tree_snapshot(self, snapshot):
            pass
        def remove_tree_snapshot(self, snapshot_id):
            pass
        def record_message_id(self, *args, **kwargs):
            pass
        def get_tracked_message_ids_for_chat(self, *args, **kwargs):
            return []
        def forget_tracked_message_ids(self, *args, **kwargs):
            pass

    settings = Settings()

    # Create workflow
    workflow = MessagingWorkflow(
        outbound=MockOutboundMessenger(),
        cli_manager=MockSessionManager(),
        session_store=MockSessionStore(),
        settings=settings,
        platform_name="test"
    )

    assert workflow is not None
    assert workflow.short_term_memory is not None
    assert workflow.persistent_memory is not None  # Should be enabled by default

    print("[OK] MessagingWorkflow created successfully")
    print(f"[OK] Short-term memory: {type(workflow.short_term_memory).__name__}")
    print(f"[OK] Persistent memory: {type(workflow.persistent_memory).__name__}")
    print(f"[OK] Persistent memory enabled: {workflow.persistent_memory is not None}")

    # Test context scale determination
    scale = workflow._determine_context_scale("Hello world")
    assert scale in ['XS', 'S', 'M', 'L', 'XL', 'XXL']
    print(f"[OK] Context scale determination works: 'Hello world' -> {scale}")

    # Test memory storage decision
    should_store, importance = workflow._should_store_to_persistent_memory(
        "I've decided to implement this feature",
        {"scale": "M"},
        "test_chat"
    )
    print(f"[OK] Memory storage decision: should_store={should_store}, importance={importance:.2f}")

    return True

def main():
    """Run all tests."""
    print("=" * 50)
    print("SIMPLE PHASE 2 INTEGRATION TEST")
    print("=" * 50)

    try:
        test_imports()
        test_settings()
        test_persistent_memory()
        test_workflow_initialization()

        print("\n" + "=" * 50)
        print("[SUCCESS] ALL TESTS PASSED!")
        print("[OK] Phase 2 memory systems are properly integrated")
        print("=" * 50)
        return True

    except Exception as e:
        print(f"\n[ERROR] TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)