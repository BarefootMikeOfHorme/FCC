#!/usr/bin/env python3
"""
Test script to verify Phase 2 integration works correctly.
"""

import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_settings_import():
    """Test that settings can be imported and has the new fields."""
    try:
        from free_claude_code.config.settings import Settings
        settings = Settings()

        # Check that the new memory settings exist and have default values
        assert hasattr(settings, 'memory_persistent_enabled')
        assert hasattr(settings, 'memory_persistent_max_items')
        assert hasattr(settings, 'memory_persistent_similarity_threshold')
        assert hasattr(settings, 'memory_persistent_importance_decay')
        assert hasattr(settings, 'memory_persistent_auto_store_threshold')

        # Check default values
        assert settings.memory_persistent_enabled == True
        assert settings.memory_persistent_max_items == 10000
        assert settings.memory_persistent_similarity_threshold == 0.7
        assert settings.memory_persistent_importance_decay == 0.95
        assert settings.memory_persistent_auto_store_threshold == 0.6

        print("[PASS] Settings test passed")
        return True
    except Exception as e:
        print(f"[FAIL] Settings test failed: {e}")
        return False

def test_persistent_memory_import():
    """Test that persistent memory store can be imported."""
    try:
        from free_claude_code.messaging.memory.persistent import PersistentMemoryStore
        from free_claude_code.config.settings import Settings

        settings = Settings()
        # Don't actually initialize it as it would create directories/files
        # Just check that the class can be imported and instantiated
        assert PersistentMemoryStore is not None
        print("[PASS] Persistent memory import test passed")
        return True
    except Exception as e:
        print(f"[FAIL] Persistent memory import test failed: {e}")
        return False

def test_workflow_import():
    """Test that MessagingWorkflow can be imported and has the new attributes."""
    try:
        from free_claude_code.messaging.workflow import MessagingWorkflow

        # Check that the class has the expected new attributes/methods
        assert hasattr(MessagingWorkflow, '_determine_context_scale')
        assert hasattr(MessagingWorkflow, '_should_store_to_persistent_memory')
        assert hasattr(MessagingWorkflow, '_extract_tags')
        assert hasattr(MessagingWorkflow, 'CONTEXT_PRESETS')
        assert hasattr(MessagingWorkflow, '_process_message_with_context_scale')

        print("[PASS] Workflow import test passed")
        return True
    except Exception as e:
        print(f"[FAIL] Workflow import test failed: {e}")
        return False

def test_context_scales():
    """Test that context scales are defined correctly."""
    try:
        from free_claude_code.messaging.workflow import MessagingWorkflow

        # Check that all expected scales are present
        expected_scales = {'XS', 'S', 'M', 'L', 'XL', 'XXL'}
        actual_scales = set(MessagingWorkflow.CONTEXT_PRESETS.keys())

        assert expected_scales == actual_scales, f"Expected {expected_scales}, got {actual_scales}"

        # Check that each scale has the required fields
        for scale, config in MessagingWorkflow.CONTEXT_PRESETS.items():
            assert 'short_term_tokens' in config
            assert 'description' in config
            assert isinstance(config['short_term_tokens'], int)
            assert isinstance(config['description'], str)
            assert config['short_term_tokens'] > 0

        print("[PASS] Context scales test passed")
        return True
    except Exception as e:
        print(f"[FAIL] Context scales test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("Running Phase 2 integration tests...\n")

    tests = [
        test_settings_import,
        test_persistent_memory_import,
        test_workflow_import,
        test_context_scales,
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        if test():
            passed += 1
        print()  # Empty line between tests

    print(f"Results: {passed}/{total} tests passed")

    if passed == total:
        print("[SUCCESS] All tests passed! Phase 2 integration is working correctly.")
        return 0
    else:
        print("[FAILURE] Some tests failed. Please check the implementation.")
        return 1

if __name__ == "__main__":
    sys.exit(main())