"""
Monitoring Provider Registry

Allows registration of provider-specific monitoring sources, e.g.:
- GPU metrics
- Model load metrics
- Provider latency/error stats
- Local LLM engine metrics

Providers are simple objects with:
- optional initialize()
- required collect() -> Dict[str, Any]
"""

from typing import Dict, Any


class MonitoringProviderRegistry:
    def __init__(self) -> None:
        self.providers: Dict[str, Any] = {}

    def register(self, name: str, provider: Any) -> None:
        """Register a monitoring provider."""
        self.providers[name] = provider

    def initialize(self) -> None:
        """Initialize all providers (if they expose initialize())."""
        for provider in self.providers.values():
            init = getattr(provider, "initialize", None)
            if callable(init):
                try:
                    init()
                except Exception:
                    # Provider init failure should not break monitoring
                    continue

    def collect(self) -> Dict[str, Any]:
        """Collect metrics from all providers."""
        output: Dict[str, Any] = {}
        for name, provider in self.providers.items():
            collect = getattr(provider, "collect", None)
            if callable(collect):
                try:
                    output[name] = collect()
                except Exception:
                    # Provider failure should not break global metrics
                    output[name] = {"error": "collection_failed"}
        return output
