# Free Claude Code Master Enhancement Plan

## Vision
Transform Free Claude Code from a capable model proxy into a production-ready, safe, and intelligent AI orchestration platform with advanced memory systems, agent collaboration capabilities, and developer-centric tooling.

## Guiding Principles
1. **Safety First**: Built-in guardrails, PII detection, and content filtering
2. **Privacy by Design**: Local processing options for sensitive data
3. **Extensibility**: Pluggable architectures for prompts, safety, fact-checking, and toolkits
4. **Performance**: Optional Rust/Python optimizations for bottlenecks
5. **Developer Experience**: IDE integration, automation, and clear documentation
6. **Incremental Adoption**: Features can be enabled/disabled independently

## Phase 0: Foundation & Research (Week 0)
*Goals: Establish baseline, profile performance, research integrations*

### 0.1 Performance Profiling
- Run cProfile/pyinstrument on core pathways (streaming, token estimation, routing)
- Identify top 5 bottlenecks for potential Rust optimization
- Document findings in `PERFORMANCE_BASELINE.md`

### 0.2 Dependency Audit
- Review current dependencies for conflicts with planned additions
- Check compatibility of PyO3 0.21+ with Python 3.14
- Research mature libraries for each proposed feature area

### 0.3 Architecture Review
- Map current data flow: request → routing → provider → streaming ledger → response
- Identify extension points for new systems (memory, safety, fact-checking)
- Document in `ARCHITECTURE_EXTENSION_POINTS.md`

**Deliverables**: Performance baseline, dependency report, extension point documentation

## Phase 1: Safety, UX & Core Stability (Weeks 1-2)
*Goals: Eliminate friction points, establish trust foundations*

### 1.1 Onboarding Wizard (High Impact)
- **Files**: `scripts/setup_wizard.py` (using typer), CLI command integration
- **Features**:
  - Interactive provider selection with validation
  - Secure API key storage (encrypted `.fcc/keys/` using cryptography library)
  - Local provider auto-detection (LM Studio, Ollama endpoints)
  - Configuration testing before saving
  - Clear next-steps guidance
- **Innovation**: Voice-guided setup option for accessibility

### 1.2 System Prompts Framework (High Impact)
- **Files**: `src/free_claude_code/config/prompts.py`, settings integration
- **Features**:
  - YAML-based prompt templates with Jinja2 variable substitution
  - Global and role-specific prompts (planner/coder/reviewer)
  - Admin UI for live prompt testing and versioning
  - Template variables: `{project_name}`, `{user_id}`, `{timestamp}`, `{allowed_dir}`
  - Hot-reload capability without server restart
- **Innovation**: Prompt effectiveness scoring based on user feedback loops

### 1.3 Safety & Guardrails Framework (Critical)
- **Files**: New `src/free_claude_code/core/safety/` package
- **Components**:
  - **Content Filters**: Profanity, hate speech, violence (using detoxify or custom models)
  - **PII Detector**: Regex + spaCy NER for emails, phones, API keys, addresses, SSNs
  - **Custom Rules Engine**: User-definable regex patterns for org-specific data
  - **Provider Native Safety**: Integration layer for providers offering safety features
  - **Audit Logging**: Structured logging of filtered/blocked events (with redaction)
  - **Configurable Sensitivity**: Per-filter type adjustment (low/medium/high)
- **Integration**: Middleware in request/response pipeline in `runtime/application.py`
- **Innovation**: Real-time safety dashboard in Admin UI showing filter statistics

### 1.4 Enhanced Error Handling & Observability (Medium Impact)
- **Files**: Runtime error handling, telemetry setup
- **Features**:
  - Specific troubleshooting guidance for common failure modes
  - Provider Request ID propagation through all layers
  - Sentry integration with Request ID context for rapid triage
  - Structured error responses with actionable remediation steps
  - Links to relevant documentation sections in error messages
- **Innovation**: Self-healing suggestions (e.g., "Detected Ollama not running - suggest 'ollama serve'")

**Deliverables**: Production-ready onboarding, safety framework, improved error handling

## Phase 2: Memory Systems & Fact-Checking (Weeks 3-4)
*Goals: Enable context persistence, reduce hallucinations, improve agent continuity*

### 2.1 Ephemeral Short-Term Memory (High Impact)
- **Technology**: LangChain's `ConversationBufferMemory`
- **Files**: `src/free_claude_code/messaging/workflow.py`, transcript context enhancements
- **Features**:
  - Session-scoped memory with automatic token-based pruning
  - Configurable `MEMORY_SHORT_TERM_MAX_TOKENS` (default: 4000)
  - Integration with turn intake for context-aware processing
  - Memory isolation between concurrent sessions
  - Visualization in Admin UI (memory usage, content preview)
- **Innovation**: Adaptive pruning that preserves recent tool outputs and key decisions

### 2.2 Persistent Memory Store (High Impact)
- **Technology**: Chroma (vector DB) + SentenceTransformers (local embeddings)
- **Files**: New `src/free_claude_code/messaging/memory/persistent.py`
- **Features**:
  - Chroma vector store in `~/.fcc/memory/chroma/`
  - SentenceTransformers for local embedding generation (privacy-preserving)
  - Namespace isolation: `project_id`, `user_id`, `agent_role`
  - CRUD operations with metadata tagging (importance, timestamp, source)
  - Similarity search for memory recall
  - Automatic storage of key facts, decisions, and learned preferences
  - GDPR-compliant deletion capabilities
- **Innovation**: Hierarchical memory (short-term → working memory → long-term archive)

### 2.3 Fact-Checking System (High Impact)
- **Technology**: Pluggable fact-checker providers with confidence scoring
- **Files**: New `src/free_claude_code/core/factcheck/` package
- **Providers**:
  - Wikipedia API (for general knowledge verification)
  - Google Fact Check Tools API (for claim verification)
  - Custom database (for organizational knowledge base)
  - arXiv API (for technical/scientific claims)
- **Integration Points**:
  - Optional post-processing for factual queries (configurable triggers)
  - Confidence scoring (0-1.0) with source attribution
  - User-configurable fact-checking thresholds
  - Background processing option to avoid latency
  - Integration with memory system to store verified facts
  - Prompt augmentation with verified facts when confidence > threshold
- **Innovation**: Fact-check confidence influences agent decision-making (e.g., low confidence triggers more conservative responses)

### 2.4 Memory Scoping & Access Control (Medium Impact)
- **Files**: Memory system enhancements, workflow integration
- **Features**:
  - Role-based access (planner vs coder vs reviewer memory visibility)
  - Project-scoped memory isolation (using `allowed_dir` or explicit project ID)
  - Memory sharing controls between agent roles (configurable matrix)
  - Audit logging for all memory access operations
  - Memory quotas per project/user to prevent abuse
  - Automatic memory archiving based on age and access patterns
- **Innovation**: Memory lineage tracking (how facts were derived and verified)

**Deliverables**: Robust memory systems, reduced hallucinations, context-aware agents

## Phase 3: Agent Orchestration & Automation (Weeks 5-6)
*Goals: Enable sophisticated multi-agent workflows, improve developer productivity*

### 3.1 Agent Role Routing with LangChain Patterns (High Impact - Directly Addresses User Suggestion)
- **Technology**: LangChain agent patterns, routing chains, fallback mechanisms
- **Files**:
  - Extended `src/free_claude_code/application/routing.py`
  - New `src/free_claude_code/config/agent_routing.py`
  - Workflow task classification enhancements
- **Features**:
  - Configuration: `AGENT_PLANNER_MODEL`, `AGENT_CODER_MODEL`, `AGENT_REVIEWER_MODEL`
  - LangChain-based task classification (keywords, patterns, LLM-based classifier)
  - Intelligent fallback chains: if coder model fails → try other code-specialized models → general models
  - Role-specific prompt injection from system prompts framework
  - Memory access controls per agent role
  - Workflow state tracking for complex agent handoffs
  - LangChain agent executor for complex multi-step reasoning
- **Innovation**: Adaptive role assignment based on task complexity and historical success rates

### 3.2 Memory Summarization & Compression (Medium Impact)
- **Technology**: LangChain's `ConversationSummaryMemory`, summarization chains
- **Files**: New `src/free_claude_code/messaging/memory/summarizer.py`
- **Features**:
  - Background summarization when context exceeds threshold (configurable)
  - Tunable compression ratio (default: 3:1 reduction)
  - Preservation of key facts, decisions, and tool execution summaries
  - Option to use local models (LM Studio/Ollama) for privacy-sensitive summarization
  - Integration with Chroma for storing summarized memories
  - Configurable summarization triggers (token count, time-based, event-based)
  - Summary quality metrics and user feedback loop
- **Innovation**: Hierarchical summarization (sentence → paragraph → section → document level)

### 3.3 Tool Use Ledger & Replay (Medium Impact)
- **Technology**: Append-only SQLite + LangChain callback handlers
- **Files**:
  - Enhanced `src/free_claude_code/core/anthropic/streaming/ledger.py` (tracking)
  - New `src/free_claude_code/messaging/memory/tool_ledger.py` (SQLite append-only)
  - Workflow execution logging enhancements
- **Features**:
  - Immutable tool execution log (inputs, outputs, timing, model used)
  - LangChain callback handlers for automatic tracing
  - Replay capability for debugging agent runs (step-by-step execution)
  - Audit trail for compliance and reproducibility
  - Optional encryption for sensitive tool data
  - Performance analytics (tool success rates, average execution time)
  - Export capabilities (JSON, CSV) for external analysis
- **Innovation**: "What-if" replay scenarios (modify inputs and see potential outcomes)

### 3.4 Automation & Code Quality Features (Medium Impact)
- **Technology**: Pre-commit hooks, automated testing suggestions, linting integration
- **Files**: New `src/free_claude_code/automation/` package
- **Features**:
  - Dry-run mode for tool execution (simulate without side effects)
  - Automatic linting of generated code (ruff, pylint, mypy, bandit)
  - Pre-commit hook generation for agent workflows
  - Automated test suggestion based on generated code patterns (pytest, unittest)
  - Security scanning of generated code (bandit, safety)
  - Configurable automation triggers (code generation, pre-tool execution, etc.)
  - Integration with IDE language servers for real-time feedback
  - Code quality dashboard in Admin UI
- **Innovation**: Learned code quality preferences (adjust suggestions based on user acceptance/rejection)

### 3.5 Observability & Telemetry (Medium Impact)
- **Technology**: OpenTelemetry (Python) + Sentry
- **Files**: New `src/free_claude_code/config/telemetry.py`, health endpoints
- **Features**:
  - Request tracing with OpenTelemetry spans (provider calls, model invocations, tool use)
  - Model latency and failure rate metrics
  - Resource usage monitoring (memory tokens, CPU, GPU if available)
  - Export capabilities (Prometheus, JSON, CSV via OpenTelemetry)
  - Provider health check endpoints (`/health/providers` with last error + Request ID)
  - Custom metrics for business logic (agent handoffs, memory cache hits, fact-check rates)
  - Distributed tracing across agent collaborations
  - Alerting on SLA violations (response time, error rate thresholds)
- **Innovation**: Predictive scaling suggestions based on usage patterns

**Deliverables**: Production-ready agent orchestration, developer productivity tools, observability

## Phase 4: Ecosystem, Discovery & IDE Integration (Weeks 7-8)
*Goals: Enable project-specific workflows, community collaboration, seamless IDE experience*

### 4.1 Project Profiles (Medium Impact)
- **Files**: New `src/free_claude_code/config/project.py`, loader enhancements
- **Features**:
  - Per-project `.fcc/project.yaml` overriding global settings
  - Project-specific model selections, token budgets, memory configurations
  - Automatic detection when launching from project directory
  - Support for shared team profiles via git (`~/.fcc/team-profiles/`) or shared directory
  - Profile inheritance (base → team → project → local overrides)
  - Profile validation and conflict resolution
  - Profile templates for common use cases (web dev, data science, embedded systems)
  - Profile versioning and change tracking
- **Innovation**: Profile recommendation engine based on project structure analysis

### 4.2 Git/MCP Toolkit Discovery (High Impact)
- **Technology**: GitHub API + MCP registry integration
- **Files**: New `src/free_claude_code/discovery/` package
- **Components**:
  - **Git Scanner**: Searches GitHub for repositories with MCP/toolkit markers
    - Specific file patterns: `mcp.json`, `toolkit.yaml`, `agents/`, `tools/`
    - Topic-based search: `mcp`, `agent-toolkit`, `claude-code-extension`
    - Trending and starred repository prioritization
  - **MCP Registry**: Interacts with official MCP registries (when available)
  - **Community Index**: Curated list of verified toolkits (community-maintained)
  - **CLI Commands**: `fcc-discover`, `fcc-install <toolkit>`, `fcc-update`, `fcc-list`
  - **Sandboxing**: Restricted permissions for untrusted toolkits (filesystem, network limits)
  - **Version Tracking**: Automatic update notifications for installed toolkits
  - **Dependency Resolution**: Handles toolkit dependencies and conflicts
  - **Metadata Extraction**: Description, author, license, dependencies, compatibility matrix
- **Innovation**: Trust scoring system for discovered toolkits (based on downloads, stars, issues, maintenance)

### 4.3 IDE Integration Enhancements (Medium Impact)
- **Technology**: Language Server Protocol (LSP) + IDE-specific enhancements
- **Files**: New `src/free_claude_code/ide/` package
- **Features**:
  - **LSP Server**: Provides IDE features via Language Server Protocol
    - Real-time syntax checking for FCC-specific syntax
    - Autocompletion for FCC commands, configurations, agent roles
    - Inline documentation for all FCC concepts
    - Refactoring tools (renaming agents, tools, memory namespaces)
    - Go-to-definition for memory references, tool definitions
  - **VS Code Extension**: Enhanced version with:
    - Debugger integration for agent workflows (set breakpoints in message flows)
    - Visual workflow designer for complex agent orchestrations (drag-and-drop)
    - Direct connection to FCC admin UI from IDE sidebar
    - Template generation for common agent patterns (planner/coder/reviewer)
    - Real-time memory usage and content visualization
    - One-click toolkit installation from discovery system
  - **JetBrains Plugin**: Similar feature set for IntelliJ IDEA, PyCharm, etc.
  - **Command Palette Integration**: FCC-specific actions in IDE command palettes
  - **Live Preview**: See agent workflow outputs directly in IDE
- **Innovation**: Context-aware IDE assistance (suggests relevant tools/memories based on current code)

### 4.4 Memory System Project Integration (Enhancement of Phase 2)
- **Files**: Memory system updates
- **Features**:
  - Project-scoped memory namespaces (automatic from `.fcc/project.yaml`)
  - Cross-project memory sharing controls (explicit opt-in required)
  - Project-specific summarization rules (different compression ratios per project type)
  - Memory quotas enforced per project
  - IDE visualization of project memory usage and top memories
  - Automatic memory archiving based on project activity
  - Project memory templates for common knowledge bases
- **Innovation**: Memory inheritance (projects can inherit memories from template projects)

**Deliverables**: Seamless ecosystem integration, professional IDE experience, project isolation

## Phase 5: Performance Optimization & Rust Integration (Weeks 9-10)
*Goals: Address performance bottlenecks, leverage Rust where beneficial*

### 5.1 Targeted Rust/PyO3 Optimizations (Based on Phase 0 Profiling)
- **Approach**: Optimize only proven bottlenecks with Rust extensions
- **Fallback Strategy**: Pure Python implementations always available
- **Integration Method**:
  - Use `maturin` or `setuptools-rust` in `pyproject.toml`
  - Conditional import: try Rust extension, fall back to Python
  - Feature flags in settings to enable/disable Rust components
- **Likely Candidates** (to be confirmed by profiling):
  - **Token Estimation**: `src/free_claude_code/core/token_estimation.py`
    - Rust implementation for rapid token counting
    - Particularly valuable for vision models processing image tokens
  - **Streaming Ledger Processing**: `src/free_claude_code/core/anthropic/streaming/ledger.py`
    - Per-token/event processing optimizations
    - State management for high-frequency updates
  - **Model Routing Logic**: `src/free_claude_code/application/routing.py`
    - Fast path for common model resolution patterns
    - Prefix tree/trie optimizations for model lookups
  - **Safety/PII Filtering**: `src/free_claude_code/core/safety/` package
    - High-performance regex matching for content filtering
    - Parallel processing for batch content scanning
  - **Embedding Generation** (if using local models):
    - Accelerated vector operations for similarity search
- **Files to Modify**:
  - Create `src/free_claude_code/rust/` directory with `Cargo.toml`
  - Rust source files for each optimized component
  - Python wrapper modules with fallback logic
  - `pyproject.toml` build system configuration
  - Settings for enabling/disabling Rust extensions
- **Innovation**: Adaptive performance mode (automatically enable Rust extensions when detect Rust toolchain)

### 5.2 Vision/Model Generation Performance (Per User Request)
- **Focus**: Optimize pathways for vision models and generation tasks
- **Specific Enhancements**:
  - **Image Token Estimation**: Specialized Rust implementation for vision models
    - Efficient calculation of tokens from image dimensions
    - Support for common vision model tokenization strategies
  - **Multimodal Streaming Ledger**: Enhanced ledger for vision+text interleaving
    - Optimized handling of image blocks interleaved with text
    - Efficient token accounting for mixed modality streams
  - **Generation-Specific Optimizations**:
    - Rust-accelerated stop-sequence detection
    - Efficient handling of repetitive patterns in generations
    - Optimized tool call parsing for vision-assisted coding
- **Innovation**: Dynamic token estimation models that adapt to observed model behavior

### 5.3 Performance Monitoring & Tuning
- **Files**: Enhanced telemetry, performance profiling tools
- **Features**:
  - Rust extension performance metrics in telemetry
  - Comparison dashboard (Rust vs Python performance)
  - Automatic fallback triggers on Rust extension errors
  - Build-time optimization flags (release vs debug profiles)
  - Cross-platform compatibility testing (Linux, Windows, macOS)
  - Performance regression detection in CI
- **Innovation**: Machine learning-based performance prediction (suggest optimizations based on usage patterns)

**Deliverables**: Measurable performance improvements where beneficial, maintained accessibility

## Phase 6: Production Hardening & Documentation (Weeks 11-12)
*Goals: Ensure production readiness, comprehensive documentation, community readiness*

### 6.1 Security Audit & Hardening
- **Files**: Security review of all new components
- **Features**:
  - Dependency vulnerability scanning
  - Penetration testing of new interfaces (discovery, admin API)
  - Input validation and sanitization across all new features
  - Secure defaults for all security-relevant configurations
  - Audit logging for security-sensitive operations
  - Regular security update procedures
  - Security configuration hardening guide
- **Innovation**: Automated security compliance checking (CIS benchmarks, etc.)

### 6.2 Comprehensive Documentation
- **Files**: Updated docs, tutorials, API references
- **Features**:
  - **Getting Started Guide**: Revised for onboarding wizard experience
  - **Security Guide**: Detailed safety framework usage
  - **Memory Systems Guide**: How to leverage short/long term memory
  - **Agent Orchestration Guide**: Building multi-agent workflows
  - **Developer Guide**: IDE integration, automation features, contributing
  - **Ecosystem Guide**: Discovering and installing toolkits
  - **Performance Guide**: Rust extensions, profiling, tuning
  - **API Reference**: Complete reference for all public interfaces
  - **Troubleshooting Guide**: Common issues and solutions
  - **Video Tutorials**: Key feature demonstrations
- **Innovation**: Interactive documentation with live examples

### 6.3 Testing & Quality Assurance
- **Files**: Enhanced test suite, CI/CD improvements
- **Features**:
  - Unit tests for all new components (>90% coverage target)
  - Integration tests for key workflows (onboarding, agent orchestration, memory)
  - End-to-end tests for common use cases (coding agent workflows)
  - Performance regression testing
  - Security testing in CI pipeline
  - Cross-platform testing matrix (Linux, Windows, macOS)
  - Accessibility testing (for onboarding wizard and UI components)
  - Chaos engineering tests for resilience
- **Innovation**: Property-based testing for complex systems (memory, routing)

### 6.4 Release Preparation
- **Files**: Release scripts, changelog, contribution guide updates
- **Features**:
  - Semantic versioning strategy
  - Changelog generation from commit history
  - Release candidate testing procedure
  - Rollback procedures for problematic releases
  - Backward compatibility guarantees documentation
  - Deprecation policy for removing old features
  - Community release announcement templates
- **Innovation**: Canary release framework for gradual rollout

**Deliverables**: Production-ready release, comprehensive documentation, tested quality

## Success Metrics & Evaluation Criteria

### Adoption Metrics
- [ ] 50% reduction in first-time setup completion time
- [ ] 70% of new users complete onboarding wizard successfully
- [ ] 40% increase in active monthly users after safety features launch
- [ ] 30% reduction in support tickets related to configuration errors

### Safety & Trust Metrics
- [ ] 95%+ accuracy in PII detection (measured against test dataset)
- [ ] 80%+ user trust score in safety mechanisms (survey-based)
- [ ] <0.1% false positive rate in content filtering (configurable)
- [ ] 100% of security findings addressed within SLA

### Performance Metrics
- [ ] 2-5x improvement in token estimation for vision models (if Rust-optimized)
- [ ] <100ms p95 response time for simple queries
- [ ] <5% error rate increase under load testing
- [ ] Efficient memory usage (<500MB baseline for typical usage)

### Feature Usage Metrics
- [ ] 60% adoption of agent role routing among power users
- [ ] 40% utilization of persistent memory for cross-session context
- [ ] 25% of users leverage fact-checking for factual queries
- [ ] 35% adoption of IDE integration features among developers

### Developer Experience Metrics
- [ ] 50% reduction in average debugging time for agent workflows
- [ ] 40% increase in community-contributed toolkits after discovery launch
- [ ] 70% satisfaction rate with IDE integration features (survey)
- [ ] 3x increase in first-time contributor success rate

## Risk Mitigation Strategies

### Technical Risks
- **Rust Integration Complexity**:
  - Mitigation: Feature flags, pure Python fallbacks, gradual rollout
  - Contingency: Delay Rust components if profiling shows insufficient benefit

- **Memory System Overhead**:
  - Mitigation: Configurable limits, efficient data structures, optional features
  - Contingency: Provide memory usage profiling tools and optimization guides

- **LangChain Dependency Risk**:
  - Mitigation: Abstract interfaces, ability to swap implementations
  - Contingency: Maintain lightweight alternatives for core memory functions

### Adoption Risks
- **Feature Overwhelm**:
  - Mitigation: Progressive disclosure, sensible defaults, onboarding guidance
  - Contingency: "Basic mode" vs "Advanced mode" configuration profiles

- **Performance Regression**:
  - Mitigation: Performance budgets in CI, regular profiling, opt-in enhancements
  - Contingency: Performance regression alerts and automatic rollback triggers

### Security Risks
- **New Attack Surfaces**:
  - Mitigation: Security review for all new components, least privilege principles
  - Contingency: Security scanning in CI, regular penetration testing, bug bounty program

## Implementation Roadmap Summary

| Phase | Duration | Primary Focus | Key Deliverables |
|-------|----------|---------------|------------------|
| 0 | Week 0 | Foundation & Research | Performance baseline, extension points |
| 1 | Weeks 1-2 | Safety, UX & Stability | Onboarding wizard, safety framework, error handling |
| 2 | Weeks 3-4 | Memory & Fact-Checking | Short/long term memory, fact-checking system |
| 3 | Weeks 5-6 | Orchestration & Automation | Agent role routing, tool ledger, automation features |
| 4 | Weeks 7-8 | Ecosystem & IDE | Project profiles, toolkit discovery, IDE integration |
| 5 | Weeks 9-10 | Performance | Targeted Rust/Python optimizations (based on profiling) |
| 6 | Weeks 11-12 | Production Hardening | Security audit, documentation, testing, release prep |

## Next Steps

1. **Review and Validate**: Confirm this plan aligns with your vision and priorities
2. **Prioritize Phases**: Determine if any phases should be accelerated or combined
3. **Resource Allocation**: Define team capacity and any external dependencies
4. **Kickoff Phase 0**: Begin performance profiling and dependency audit
5. **Establish Success Metrics**: Define baseline measurements for each metric category

## Open Questions for Your Input

1. **Phase Prioritization**: Which phase delivers the highest immediate value for your use case?
2. **Rust Integration**: Should we profile first (Phase 0) or identify likely candidates upfront?
3. **Safety Framework**: Any specific regulatory compliance requirements (HIPAA, GDPR, SOC2) to consider?
4. **Memory Preferences**: Preference for pure Python memory solutions vs LangChain integration?
5. **IDE Focus**: Which IDEs should we prioritize for initial integration (VS Code, JetBrains, both)?
6. **Community Features**: How important is the Git/MCP discovery vs focusing on core stability first?
7. **Release Strategy**: Prefer monthly incremental releases or larger quarterly releases?

Please provide feedback on:
- Any missing critical features or considerations
- Priority adjustments based on your immediate needs
- Technical constraints or preferences I should incorporate
- Preferred approach for handling open questions above

Once validated, I'll begin with Phase 0 (Foundation & Research) to establish our performance baseline and identify the most impactful optimization opportunities.