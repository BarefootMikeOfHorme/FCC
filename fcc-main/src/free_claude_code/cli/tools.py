from free_claude_code.core.anthropic.tools import TOOL_REGISTRY

def list_tools():
    """List all tools, MCPs, scripts, assets, active/inactive."""
    print("[FCC] Tools:")
    for name, tool in TOOL_REGISTRY.items():
        print(f"- {name}: {tool}")
