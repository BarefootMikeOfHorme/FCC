from free_claude_code.runtime.provider_manager import ProviderManager

def provider_cli():
    """Provider management."""
    pm = ProviderManager()
    print("[FCC] Providers:")
    for provider in pm.providers:
        print(f"- {provider}")
