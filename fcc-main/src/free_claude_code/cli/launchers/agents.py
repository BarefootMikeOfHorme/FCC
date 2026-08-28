"""
Agent launcher utilities.
Enhanced with terminal group awareness for monitoring orchestrator.
"""

def list_agents():
    """List all FCC agents."""
    agents = [
        "claude",
        "codex",
        "pi",
        "opencode",
        "cline",
        "hermes",
        "muse",
    ]
    print("[FCC] Agents:")
    for a in agents:
        print(f"- {a}")


def attach_agent_terminal_group():
    """Hook for orchestrator to attach monitors to agent terminal group."""
    print("[FCC] Agent terminal group ready for monitor attachment.")
