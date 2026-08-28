# Ecosystem Discovery and Extension Mechanisms for Free Claude Code

## Overview
Free Claude Code is designed to be an open, extensible platform that can integrate with various AI agents, IDEs, and external services. This document outlines the mechanisms for ecosystem discovery and extension.

## Discovery Mechanisms

### 1. Service Discovery via Standard APIs
FCC exposes industry-standard APIs that enable discovery by external systems:

- **Anthropic Messages API** (`/v1/messages`)
- **OpenAI Responses API** (`/v1/responses`)
- **Model Catalog Endpoint** (`/v1/models` with various views)
- **Health Endpoint** (`/health`)

External agents can discover FCC services by:
1. Listening for FCC announcements on the network
2. Checking known endpoints (localhost:8082)
3. Querying the model catalog to verify FCC identity
4. Using health checks to verify service availability

### 2. Agent-to-Agent Discovery
FCC agents can discover each other through:

- **Shared Configuration**: Agents read from common configuration sources
- **Central Registry**: Optional service registry for agent discovery
- **Broadcast Announcements**: Agents announce their presence on startup
- **Hierarchical Discovery**: Child agents discover parent agents through configuration

### 3. IDE and Editor Discovery
IDEs discover FCC through:

- **Standard API Compatibility**: FCC appears as an Anthropic/OpenAI compatible endpoint
- **Configuration Guides**: Documented setup procedures in README
- **Extension Examples**: Pi extension demonstrates registration patterns
- **Protocol Compliance**: VS Code protocol tests ensure compatibility

## Extension Mechanisms

### 1. API-Level Extensions
Since FCC implements standard APIs, extensions can:

- Add new endpoints alongside existing ones
- Modify behavior through middleware or proxy layers
- Enhance the model catalog with additional metadata
- Provide alternative authentication mechanisms

### 2. Agent System Extensions
The agent hierarchy (Main/Project/Assistant) can be extended by:

- Creating new agent types that inherit from BaseAgent
- Adding capabilities to existing agent types
- Extending the message passing system with new message types
- Adding new memory storage or retrieval methods

### 3. CLI and Interface Extensions
Extensions to the command-line interface:

- New commands added to entrypoints.py
- Additional CLI modules in the cli/ directory
- Extended setup wizard with new configuration options
- Additional health monitoring and diagnostic tools

### 4. Memory System Extensions
Extensions to the Phase 2 memory systems:

- New memory storage backends (beyond ChromaDB)
- Additional memory item types or metadata fields
- Enhanced search and retrieval algorithms
- New specialized storage methods (beyond conversation summaries, preferences, decisions)

## Implementation Patterns

### 1. Pi Extension Pattern
The existing `pi_extension.ts` demonstrates how external agents can:
- Discover FCC's model catalog via `/v1/models?view=messages`
- Register "Free Claude Code" as a provider in the host agent
- Handle authentication via environment variables
- This pattern can be adapted for any external system

### 2. Middleware Pattern
Extensions can insert middleware to:
- Log or monitor requests/responses
- Transform requests or responses
- Add authentication or authorization
- Implement rate limiting or quotas

### 3. Plugin Pattern
Future extension system could support:
- Discoverable plugin directories
- Standard plugin interfaces
- Versioned plugin APIs
- Dependency management between plugins

## Configuration for Discovery

### Service Advertisement
FCC can advertise its presence through:
- mDNS/Bonjour service discovery
- UDP broadcast announcements
- Central service registration (consul, etcd, etc.)
- Simple HTTP-based discovery endpoints

### Discovery Configuration
Agents and services can configure discovery through:
- Environment variables (FCC_DISCOVERY_ENDPOINTS)
- Configuration files (discovery.yaml or similar)
- Command-line flags (--discovery-mode)
- Default localhost discovery for development

## Security Considerations

### Trust and Authentication
Discovery mechanisms should:
- Validate service identity before establishing trust
- Use secure channels for sensitive information
- Support authentication for discovery endpoints
- Implement authorization for sensitive operations

### Rate Limiting and Abuse Prevention
- Limit discovery request frequency
- Validate discovery responses to prevent spoofing
- Implement circuit breakers for unreliable discovery sources

## Examples

### Discovering FCC from an External Agent
```python
# Pseudocode for external agent discovering FCC
import httpx

def discover_fcc():
    # Try common endpoints
    endpoints = ["http://localhost:8082", "http://127.0.0.1:8082"]

    for endpoint in endpoints:
        try:
            # Check health endpoint
            health_resp = httpx.get(f"{endpoint}/health", timeout=2.0)
            if health_resp.status_code == 200:
                # Verify it's FCC by checking model catalog
                models_resp = httpx.get(f"{endpoint}/v1/models", timeout=2.0)
                if models_resp.status_code == 200:
                    return endpoint
        except Exception:
            continue
    return None
```

### Advertising FCC Services
```python
# Pseudocode for FCC advertising its services
def advertise_services():
    # Announce via mDNS
    # Broadcast on local network
    # Update central registry if configured
    pass
```

## Future Considerations

### Standardized Discovery Protocols
- Consider implementing or supporting:
  - DNS-SD (DNS Service Discovery)
  - SSDP (Simple Service Discovery Protocol)
  - mDNS/Bonjour
  - Consul/Etcd service registration

### Extension Marketplace
- Eventually support a marketplace for FCC extensions
- Version compatibility checking
- User ratings and reviews
- Secure extension installation

### Interoperability Standards
- Align with emerging AI agent interoperability standards
- Support common agent communication protocols
- Participate in standardization efforts