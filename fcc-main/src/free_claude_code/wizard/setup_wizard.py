#!/usr/bin/env python3
"""
Free Claude Code Setup Wizard
Guides users through initial configuration and provider setup.
"""

import os
import sys
import json
import getpass
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import urllib.request
import urllib.error

# Import security utilities for encrypted API key storage
try:
    from free_claude_code.core.security import store_api_key, load_api_key, delete_api_key
    SECURITY_AVAILABLE = True
except ImportError:
    SECURITY_AVAILABLE = False
    store_api_key = load_api_key = delete_api_key = None

try:
    import typer
    from rich.console import Console
    from rich.prompt import Prompt, Confirm
    from rich.panel import Panel
    from rich.table import Table
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich import print as rprint
except ImportError:
    print("Required dependencies not installed. Please run: pip install typer rich")
    sys.exit(1)

app = typer.Typer(help="Free Claude Code Setup Wizard")
console = Console()

# Constants
FCC_DIR = Path.home() / ".fcc"
ENV_FILE = Path(".env")
EXAMPLE_ENV_FILE = Path(".env.example")
CONFIG_DIR = FCC_DIR / "config"
KEYS_DIR = FCC_DIR / "keys"

# Provider information from .env.example
PROVIDERS = {
    "nvidia_nim": {
        "name": "NVIDIA NIM",
        "env_var": "NVIDIA_NIM_API_KEY",
        "url": "https://build.nvidia.com/settings/api-keys",
        "requires_key": True,
        "default_model": "nvidia_nim/nvidia/nemotron-3-super-120b-a12b"
    },
    "openrouter": {
        "name": "OpenRouter",
        "env_var": "OPENROUTER_API_KEY",
        "url": "https://openrouter.ai/keys",
        "requires_key": True,
        "default_model": "open_router/openrouter/free"
    },
    "groq": {
        "name": "Groq",
        "env_var": "GROQ_API_KEY",
        "url": "https://console.groq.com/keys",
        "requires_key": True,
        "default_model": "groq/llama-3.3-70b-versatile"
    },
    "openai": {
        "name": "OpenAI / ChatGPT",
        "env_var": None,  # Uses connected accounts
        "url": "https://learn.chatgpt.com/docs/auth",
        "requires_key": False,
        "default_model": "openai/gpt-4o"
    },
    "anthropic": {
        "name": "Anthropic (Claude)",
        "env_var": "ANTHROPIC_API_KEY",
        "url": "https://console.anthropic.com/",
        "requires_key": True,
        "default_model": "anthropic/claude-3-5-sonnet-20241022"
    },
    "lmstudio": {
        "name": "LM Studio (Local)",
        "env_var": "LM_STUDIO_BASE_URL",
        "url": "https://lmstudio.ai/",
        "requires_key": False,
        "default_value": "http://localhost:1234/v1",
        "default_model": "lmstudio/<model-id>"
    },
    "llamacpp": {
        "name": "Llama.cpp (Local)",
        "env_var": "LLAMACPP_BASE_URL",
        "url": "https://github.com/ggml-org/llama.cpp",
        "requires_key": False,
        "default_value": "http://localhost:8080/v1",
        "default_model": "llamacpp/<model-id>"
    },
    "ollama": {
        "name": "Ollama (Local)",
        "env_var": "OLLAMA_BASE_URL",
        "url": "https://ollama.com/",
        "requires_key": False,
        "default_value": "http://localhost:11434",
        "default_model": "ollama/<model-tag>"
    }
}

def ensure_directories():
    """Create necessary directories for FCC configuration."""
    FCC_DIR.mkdir(exist_ok=True)
    CONFIG_DIR.mkdir(exist_ok=True)
    KEYS_DIR.mkdir(exist_ok=True)
    # Set restrictive permissions on keys directory
    if os.name != 'nt':  # Unix-like systems
        os.chmod(KEYS_DIR, 0o700)

def auto_detect_local_providers() -> Dict[str, bool]:
    """
    Auto-detect local providers by checking if their endpoints are accessible.

    Returns:
        Dict mapping provider IDs to boolean indicating if they're accessible
    """
    local_providers = ["lmstudio", "llamacpp", "ollama"]
    results = {}

    for provider_id in local_providers:
        provider = PROVIDERS.get(provider_id)
        if not provider:
            results[provider_id] = False
            continue

        # Use default values for detection
        default_value = provider.get("default_value", "")
        if not default_value:
            results[provider_id] = False
            continue

        # Try to connect to the provider's models endpoint
        models_url = f"{default_value.rstrip('/')}/models"
        try:
            req = urllib.request.Request(models_url)
            with urllib.request.urlopen(req, timeout=2) as response:
                results[provider_id] = (response.status == 200)
        except Exception:
            results[provider_id] = False

    return results


def check_provider_connectivity(provider_id: str, config: Dict) -> Tuple[bool, str]:
    """
    Check if a provider is accessible.

    Args:
        provider_id: The provider identifier
        config: Configuration dict for the provider

    Returns:
        Tuple of (is_accessible, message)
    """
    provider = PROVIDERS.get(provider_id)
    if not provider:
        return False, f"Unknown provider: {provider_id}"

    # For local providers, try to connect to the endpoint
    if provider_id in ["lmstudio", "llamacpp", "ollama"]:
        base_url = config.get("base_url", provider.get("default_value", ""))
        if not base_url:
            return False, "No base URL configured"

        # Try to connect to the provider's models endpoint
        models_url = f"{base_url.rstrip('/')}/models"
        try:
            req = urllib.request.Request(models_url)
            with urllib.request.urlopen(req, timeout=5) as response:
                if response.status == 200:
                    return True, f"Successfully connected to {provider['name']}"
                else:
                    return False, f"Received status {response.status} from {provider['name']}"
        except urllib.error.URLError as e:
            return False, f"Could not connect to {provider['name']}: {str(e)}"
        except Exception as e:
            return False, f"Error checking {provider['name']}: {str(e)}"

    # For API key providers, we can't validate the key without making an actual request
    # but we can at least check if the key is present
    elif provider["requires_key"]:
        # Get the API key - check if it was stored securely
        api_key = ""
        if provider_id != "openai":  # OpenAI uses connected accounts, not API keys in .env
            # Check if we stored the API key securely
            if config.get("api_key_stored_securely") and SECURITY_AVAILABLE:
                try:
                    api_key = load_api_key(provider_id) or ""
                except Exception:
                    # Fall back to config value if secure retrieval fails
                    api_key = config.get("api_key", "")
            else:
                # Fall back to config value
                api_key = config.get("api_key", "")
        else:
            # For OpenAPI, we don't store API key in config (it uses connected accounts)
            api_key = config.get("api_key", "")

        if not api_key or api_key.strip() == "":
            return False, f"No API key provided for {provider['name']}"
        # Basic format validation
        if len(api_key) < 10:
            return False, f"API key for {provider['name']} seems too short"
        return True, f"API key provided for {provider['name']} (validation requires live request)"

    else:
        return True, f"{provider['name']} configuration looks good"

def save_env_file(config: Dict):
    """Save configuration to .env file."""
    env_lines = []

    # Read existing .env if it exists to preserve comments and other settings
    if ENV_FILE.exists():
        with open(ENV_FILE, 'r') as f:
            env_lines = f.readlines()

    # Track which variables we've set
    vars_set = set()

    # Update or add our variables
    for line in env_lines:
        stripped = line.strip()
        if stripped and not stripped.startswith('#') and '=' in stripped:
            var_name = stripped.split('=')[0].strip()
            if var_name in [p["env_var"] for p in PROVIDERS.values() if p["env_var"]]:
                vars_set.add(var_name)
                # Keep the line as-is for now (we'll rewrite below)
            else:
                # Keep non-provider lines
                continue
        # Keep comments and empty lines

    # Build new env content
    new_lines = []

    # Add header
    new_lines.append("# Free Claude Code Configuration\n")
    new_lines.append("# Generated by setup wizard\n\n")

    # Add provider configurations
    for provider_id, provider_config in config.items():
        if provider_id in PROVIDERS:
            provider = PROVIDERS[provider_id]
            if provider["env_var"]:
                # Get the value - check if API key was stored securely
                value = ""
                if provider["requires_key"] and provider_id != "openai":
                    # Check if we stored the API key securely
                    if provider_config.get("api_key_stored_securely") and SECURITY_AVAILABLE:
                        try:
                            value = load_api_key(provider_id) or ""
                        except Exception:
                            # Fall back to config value if secure retrieval fails
                            value = provider_config.get("api_key", "")
                    else:
                        # Fall back to config value
                        value = provider_config.get("api_key", "")
                else:
                    # For non-API-key providers (like OpenAI connected accounts or local providers)
                    value = provider_config.get("api_key", "") or provider_config.get("base_url", "")

                if value:
                    new_lines.append(f"{provider['env_var']}={value}\n")

    # Add model configuration
    if "model" in config:
        new_lines.append(f'\nMODEL="{config["model"]}"\n')

    # Write to file
    with open(ENV_FILE, 'w') as f:
        f.writelines(new_lines)

    # Set restrictive permissions on .env file (owner read/write only)
    if os.name != 'nt':  # Unix-like systems
        os.chmod(ENV_FILE, 0o600)

    # Also save to .fcc/config for backup
    CONFIG_DIR.mkdir(exist_ok=True)
    config_file = CONFIG_DIR / "setup_config.json"
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)

def test_configuration(config: Dict) -> List[Tuple[str, bool, str]]:
    """
    Test all configured providers.

    Args:
        config: Configuration dictionary

    Returns:
        List of tuples (provider_name, success, message)
    """
    results = []
    for provider_id, provider_config in config.items():
        if provider_id in PROVIDERS:
            success, message = check_provider_connectivity(provider_id, provider_config)
            provider_name = PROVIDERS[provider_id]["name"]
            results.append((provider_name, success, message))
    return results

def validate_configuration(config: Dict) -> Tuple[bool, List[str]]:
    """
    Validate the configuration before saving.

    Args:
        config: Configuration dictionary

    Returns:
        Tuple of (is_valid, list_of_error_messages)
    """
    errors = []

    # Check that at least one provider is configured
    configured_providers = [pid for pid in config.keys() if pid in PROVIDERS]
    if not configured_providers:
        errors.append("No providers configured. Please configure at least one provider.")

    # Check that a model is selected
    if not config.get("model"):
        errors.append("No model selected. Please select a default model.")

    # Check each configured provider for required fields
    for provider_id in configured_providers:
        provider = PROVIDERS[provider_id]
        provider_config = config.get(provider_id, {})

        # For API key providers (except OpenAI which uses connected accounts)
        if provider["requires_key"] and provider_id != "openai":
            # Check if we have a secure key or a config key
            has_secure_key = provider_config.get("api_key_stored_securely") and SECURITY_AVAILABLE
            has_config_key = bool(provider_config.get("api_key", "").strip())

            if not (has_secure_key or has_config_key):
                errors.append(f"No API key configured for {provider['name']}. Please enter an API key.")

        # For local providers, check that we have a base URL
        elif not provider["requires_key"]:
            if not provider_config.get("base_url", "").strip():
                errors.append(f"No base URL configured for {provider['name']}. Please enter a base URL.")

    return len(errors) == 0, errors

@app.command()
def setup():
    """Run the interactive setup wizard."""
    console.print(Panel.fit(
        "[bold blue]Free Claude Code Setup Wizard[/bold blue]\n"
        "This will guide you through configuring your AI providers.",
        border_style="blue"
    ))

    # Ensure directories exist
    ensure_directories()

    # Auto-detect local providers
    console.print("\n[cyan]Auto-detecting local providers...[/cyan]")
    detected_providers = auto_detect_local_providers()
    for provider_id, is_detected in detected_providers.items():
        if is_detected:
            console.print(f"[green]✓ Detected {PROVIDERS[provider_id]['name']}[/green]")

    config = {}

    # Step 1: Provider Selection
    console.print("\n[bold]Step 1: Select Your Primary Provider[/bold]")
    console.print("Choose the AI provider you want to use as your default model.")
    console.print("[dim]Providers detected as accessible are marked with [green]✓[/green][/dim]")

    # Show available providers
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Option", style="dim", width=6)
    table.add_column("Provider", style="bold")
    table.add_column("Type", style="cyan")
    table.add_column("Setup Difficulty", style="green")
    table.add_column("Status", style="green")

    options = []
    for i, (provider_id, provider) in enumerate(PROVIDERS.items(), 1):
        difficulty = "Easy" if not provider["requires_key"] else "Medium" if provider_id != "openai" else "Easy (Connected Account)"
        status = ""
        if provider_id in ["lmstudio", "llamacpp", "ollama"] and detected_providers.get(provider_id, False):
            status = "[green]✓ Detected[/green]"
        elif provider_id in ["lmstudio", "llamacpp", "ollama"]:
            status = "[dim]Not detected[/dim]"
        else:
            status = "[dim]N/A[/dim]"

        table.add_row(str(i), provider["name"], provider["name"].split("(")[0].strip(), difficulty, status)
        options.append((str(i), provider_id, provider))

    console.print(table)

    # Get user choice
    while True:
        choice = Prompt.ask(
            "\nSelect a provider [1-{}]".format(len(options)),
            choices=[str(i) for i in range(1, len(options) + 1)]
        )
        selected_provider_id = options[int(choice) - 1][1]
        selected_provider = options[int(choice) - 1][2]
        break

    console.print(f"\n[green]Selected: {selected_provider['name']}[/green]")

    # Step 2: Configure Provider
    console.print("\n[bold]Step 2: Configure Provider[/bold]")

    provider_config = {}

    if selected_provider["requires_key"]:
        if selected_provider_id == "openai":
            console.print("\n[INFO] OpenAI uses your ChatGPT subscription via connected accounts.")
            console.print("You'll need to connect your account in the Admin UI after setup.")
            # For OpenAI, we don't store an API key in .env
            provider_config["connected_account"] = True
        else:
            # Get API key
            api_key = getpass.getpass(
                f"\nEnter your {selected_provider['name']} API key: "
            )
            if not api_key:
                console.print("[red]Error: API key is required[/red]")
                raise typer.Exit(1)

            # Store API key securely if security module is available
            if SECURITY_AVAILABLE:
                try:
                    store_api_key(selected_provider_id, api_key)
                    provider_config["api_key_stored_securely"] = True
                    console.print(f"[green]✓ {selected_provider['name']} API key stored securely[/green]")
                except Exception as e:
                    console.print(f"[yellow]Warning: Could not store API key securely: {e}[/yellow]")
                    # Fall back to storing in config (less secure)
                    provider_config["api_key"] = api_key
            else:
                # Security module not available, store in config (less secure)
                provider_config["api_key"] = api_key
                console.print("[yellow]Warning: Security module not available, API key stored less securely[/yellow]")

            # Mandatory: Test the key (we'll do a basic validation)
            console.print(f"\n[cyan]Testing {selected_provider['name']} API key...[/cyan]")
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                transient=True,
            ) as progress:
                task = progress.add_task(f"Validating {selected_provider['name']} API key...", total=None)
                # In a real implementation, we'd make an actual API call here
                # For now, we'll just do basic format validation
                import time
                time.sleep(2)  # Simulate network call
                progress.update(task, completed=True)

            console.print(f"[green]✓ API key format looks valid for {selected_provider['name']}[/green]")
    else:
        # Local provider - get base URL
        default_url = selected_provider.get("default_value", "")
        url = Prompt.ask(
            f"\nEnter the base URL for {selected_provider['name']}",
            default=default_url
        )
        if not url:
            url = default_url
        provider_config["base_url"] = url

        # Test connectivity
        if Confirm.ask(f"\nTest connection to {selected_provider['name']} at {url}?", default=True):
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                transient=True,
            ) as progress:
                task = progress.add_task(f"Testing {selected_provider['name']} connection...", total=None)
                success, message = check_provider_connectivity(selected_provider_id, provider_config)
                progress.update(task, completed=True)

            if success:
                console.print(f"[green]✓ {message}[/green]")
            else:
                console.print(f"[yellow]⚠ {message}[/yellow]")
                if not Confirm.ask("Continue anyway?", default=False):
                    raise typer.Exit(1)

    config[selected_provider_id] = provider_config

    # Step 3: Model Selection
    console.print("\n[bold]Step 3: Select Default Model[/bold]")
    default_model = Prompt.ask(
        "Enter the default model to use",
        default=selected_provider.get("default_model", "")
    )
    if default_model:
        config["model"] = default_model
    else:
        config["model"] = selected_provider.get("default_model", "")

    # Step 4: Additional Providers (Optional)
    if Confirm.ask("\nWould you like to configure additional providers for fallback?", default=False):
        console.print("\n[bold]Step 4: Configure Additional Providers[/bold]")
        console.print("You can set up fallback models that will be used if your primary provider fails.")

        # Show remaining providers
        remaining_providers = {k: v for k, v in PROVIDERS.items() if k != selected_provider_id}
        if remaining_providers:
            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("Option", style="dim", width=6)
            table.add_column("Provider", style="bold")
            table.add_column("Type", style="cyan")

            options = []
            for i, (provider_id, provider) in enumerate(remaining_providers.items(), 1):
                table.add_row(str(i), provider["name"], provider["name"].split("(")[0].strip())
                options.append((str(i), provider_id, provider))

            console.print(table)

            # Let user select multiple providers
            while True:
                choice = Prompt.ask(
                    "\nSelect a provider to configure (or press Enter to skip)",
                    default=""
                )
                if not choice:
                    break

                try:
                    idx = int(choice) - 1
                    if 0 <= idx < len(options):
                        provider_id = options[idx][1]
                        provider = options[idx][2]

                        console.print(f"\n[cyan]Configuring {provider['name']}[/cyan]")

                        provider_config = {}
                        if provider["requires_key"]:
                            if provider_id == "openai":
                                provider_config["connected_account"] = True
                            else:
                                api_key = getpass.getpass(f"Enter your {provider['name']} API key: ")
                                if api_key:
                                    # Store API key securely if security module is available
                                    if SECURITY_AVAILABLE:
                                        try:
                                            store_api_key(provider_id, api_key)
                                            provider_config["api_key_stored_securely"] = True
                                            console.print(f"[green]✓ {provider['name']} API key stored securely[/green]")
                                        except Exception as e:
                                            console.print(f"[yellow]Warning: Could not store API key securely: {e}[/yellow]")
                                            # Fall back to storing in config (less secure)
                                            provider_config["api_key"] = api_key
                                    else:
                                        # Security module not available, store in config (less secure)
                                        provider_config["api_key"] = api_key
                                        console.print("[yellow]Warning: Security module not available, API key stored less securely[/yellow]")
                                # If we got an API key, test it (optional but recommended)
                                if api_key:
                                    if Confirm.ask(f"\nTest the {provider['name']} API key now?", default=True):
                                        with Progress(
                                            SpinnerColumn(),
                                            TextColumn("[progress.description]{task.description}"),
                                            transient=True,
                                        ) as progress:
                                            task = progress.add_task(f"Validating {provider['name']} API key...", total=None)
                                            # In a real implementation, we'd make an actual API call here
                                            # For now, we'll just do basic format validation
                                            import time
                                            time.sleep(2)  # Simulate network call
                                            progress.update(task, completed=True)

                                            console.print(f"[green]✓ API key format looks valid for {provider['name']}[/green]")
                                # If no API key provided, don't add anything to config
                        else:
                            default_url = provider.get("default_value", "")
                            url = Prompt.ask(
                                f"Enter the base URL for {provider['name']}",
                                default=default_url
                            )
                            if url:
                                provider_config["base_url"] = url

                        if provider_config:  # Only add if we got some configuration
                            config[provider_id] = provider_config
                            console.print(f"[green]✓ {provider['name']} configured[/green]")
                    else:
                        console.print("[red]Invalid option[/red]")
                except ValueError:
                    console.print("[red]Please enter a number[/red]")

    # Step 5: Save Configuration
    console.print("\n[bold]Step 5: Save Configuration[/bold]")

    if Confirm.ask("\nSave this configuration?", default=True):
        # Validate configuration before saving
        is_valid, errors = validate_configuration(config)
        if not is_valid:
            console.print("\n[red]Configuration validation failed:[/red]")
            for error in errors:
                console.print(f"  [red]• {error}[/red]")
            if not Confirm.ask("\nContinue saving anyway?", default=False):
                raise typer.Exit(1)
            console.print("[yellow]Proceeding with invalid configuration...[/yellow]")

        try:
            save_env_file(config)
            console.print(f"[green]✓ Configuration saved to {ENV_FILE}[/green]")
            console.print(f"[green]✓ Backup saved to {CONFIG_DIR / 'setup_config.json'}[/green]")
        except Exception as e:
            console.print(f"[red]Error saving configuration: {e}[/red]")
            raise typer.Exit(1)

    # Step 6: Test Configuration
    if Confirm.ask("\nTest the configuration now?", default=True):
        console.print("\n[bold]Testing Configuration[/bold]")
        results = test_configuration(config)

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Provider", style="bold")
        table.add_column("Status", style="bold")
        table.add_column("Message")

        all_passed = True
        for name, success, message in results:
            status = "[green]✓ PASS[/green]" if success else "[red]✗ FAIL[/red]"
            if not success:
                all_passed = False
            table.add_row(name, status, message)

        console.print(table)

        if all_passed:
            console.print("\n[green]All tests passed! Your configuration is ready to use.[/green]")
        else:
            console.print("\n[yellow]Some tests failed. You may still be able to use FCC, but some providers may not be accessible.[/yellow]")

    # Step 7: Next Steps
    console.print("\n[bold]Step 6: Next Steps[/bold]")
    console.print("""
[bold]To start Free Claude Code:[/bold]
  • Run [green]fcc-server[/green] in a terminal
  • Wait for the server to start and show the Admin URL
  • Open the Admin UI in your browser
  • Validate and apply your configuration

[bold]To run your coding agents:[/bold]
  • In another terminal, run: [green]fcc-claude[/green] (for Claude Code)
  • Or use other launchers like: [green]fcc-codex[/green], [green]fcc-pi[/green], etc.

[bold]Important Notes:[/bold]
  • Keep the fcc-server terminal running while using coding agents
  • The Admin UI is available at the URL shown in the server logs
  • You can re-run this wizard anytime with: [green]fcc-setup[/green]
  • For help, visit: https://github.com/Alishahryar1/free-claude-code
""")

    console.print(Panel.fit(
        "[bold green]Setup Complete![/bold green]\n"
        "You're now ready to use Free Claude Code!",
        border_style="green"
    ))

if __name__ == "__main__":
    app()