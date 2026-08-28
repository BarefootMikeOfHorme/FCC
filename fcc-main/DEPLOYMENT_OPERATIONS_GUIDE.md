# Deployment and Operations Guide for Free Claude Code

## Overview
This guide provides comprehensive instructions for deploying, configuring, operating, and maintaining Free Claude Code in various environments ranging from development setups to production enterprise deployments.

## 1. System Requirements and Prerequisites

### 1.1 Minimum Requirements
- **Operating System**: Windows 10/11, macOS 12+, or Linux (Ubuntu 20.04+, RHEL 8+, Debian 11+)
- **Processor**: Modern x86_64 or ARM64 CPU with 2+ cores
- **Memory**: 4 GB RAM minimum (8 GB recommended)
- **Storage**: 2 GB available disk space
- **Network**: Internet access for model providers (optional for local-only mode)

### 1.2 Recommended Production Requirements
- **Operating System**: Linux (Ubuntu 22.04 LTS, RHEL 9, or Debian 12)
- **Processor**: 4+ core CPU
- **Memory**: 8 GB RAM minimum (16 GB recommended for heavy usage)
- **Storage**: SSD with 10+ GB available space
- **Network**: Reliable internet connection with bandwidth >= 10 Mbps
- **Optional Hardware**: TPM 2.0 for enhanced security, GPU for local model acceleration

### 1.3 Software Dependencies
- **Python**: 3.9+ (3.11 recommended)
- **Package Manager**: pip (latest) or uv (recommended for faster installs)
- **Git**: For version control and updates
- **Optional**: Docker (for containerized deployment), Node.js (for some development tools)

## 2. Installation Methods

### 2.1 Standard Installation (Recommended)
```bash
# Clone the repository
git clone https://github.com/your-org/free-claude-code.git
cd free-claude-code

# Install using uv (recommended) or pip
uv pip install -e .  # Development installation with editable mode
# OR
pip install -e .     # Standard pip installation

# Verify installation
fcc --help
```

### 2.2 Production Installation with Dependency Locking
```bash
# For reproducible builds
uv pip compile pyproject.toml -o requirements.txt
uv pip install --system -r requirements.txt

# Or with pip
pip install -r requirements.txt
```

### 2.3 Containerized Deployment
```bash
# Build the Docker image
docker build -t free-claude-code:latest .

# Run the container
docker run -d \
  --name free-claude-code \
  -p 8082:8082 \
  -v ./data:/app/data \
  -v ./config:/app/config \
  -e FCC_SETTINGS_MODULE=config.settings \
  free-claude-code:latest
```

### 2.4 Kubernetes Deployment
```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: free-claude-code
spec:
  replicas: 3
  selector:
    matchLabels:
      app: free-claude-code
  template:
    metadata:
      labels:
        app: free-claude-code
    spec:
      containers:
      - name: free-claude-code
        image: free-claude-code:latest
        ports:
        - containerPort: 8082
        volumeMounts:
        - name: config
          mountPath: /app/config
        - name: data
          mountPath: /app/data
        env:
        - name: FCC_SETTINGS_MODULE
          value: "config.settings"
      volumes:
      - name: config
        configMap:
          name: free-claude-code-config
      - name: data
        persistentVolumeClaim:
          claimName: free-claude-code-data
---
apiVersion: v1
kind: Service
metadata:
  name: free-claude-code-service
spec:
  selector:
    app: free-claude-code
  ports:
    - protocol: TCP
      port: 80
      targetPort: 8082
  type: LoadBalancer
```

## 3. Configuration Management

### 3.1 Configuration Sources (in order of precedence)
1. Environment variables (highest priority)
2. `.env` file in current directory
3. `$HOME/.fcc/settings.toml` (user-specific)
4. `/etc/fcc/settings.toml` (system-wide)
5. `pyproject.toml` defaults (lowest priority)

### 3.2 Environment Variables
All settings can be overridden via environment variables using the format:
```
FCC_<SETTING_NAME_IN_UPPERCASE>
```

Examples:
- `FCC_MODEL="nvidia_nim/nvidia/nemotron-3-super-120b-a12b"`
- `FCC_HOST="0.0.0.0"`
- `FCC_PORT="8082"`
- `FCC_LOG_LEVEL="DEBUG"`
- `FCC_MEMORY_PERSISTENT_ENABLED="false"`

### 3.3 TOML Configuration File
Create `.fcc/settings.toml` in your home directory:
```toml
# ~/.fcc/settings.toml
[openrouter]
api_key = "sk-or-v1-..."

[anthropic]
api_key = "sk-ant-..."

[model]
default = "anthropic/claude-3-5-sonnet-20241022"
fallbacks = ["anthropic/claude-3-opus-20240229", "anthropic/claude-3-haiku-20240307"]

[memory]
short_term_max_tokens = 6000
persistent_enabled = true
persistent_max_items = 15000

[security]
audit_log_enabled = true
evidence_retention_days = 365

[logging]
level = "INFO"
raw_api_payloads = false
```

### 3.4 Provider-Specific Configuration
API keys and provider settings can be managed through the secure storage system:
```bash
# Store API keys securely
fcc-setup --provider openai --api-key sk-...
fcc-setup --provider anthropic --api-key sk-ant-...

# Or through the setup wizard
fcc-setup
```

## 4. Deployment Patterns

### 4.1 Single-Instance Deployment (Small Teams)
- **Use Case**: Teams of 1-10 users, development or testing environments
- **Components**: Single Free Claude Code instance handling all requests
- **Resources**: 2-4 CPU cores, 4-8 GB RAM
- **High Availability**: None (manual restart for updates)
- **Setup**:
  ```bash
  # Install and configure
  uv pip install -e .
  fcc-setup  # Run setup wizard for API keys

  # Start the service
  fcc-server  # or: python -m free_claude_code.server
  ```

### 4.2 Load-Balanced Deployment (Medium Teams)
- **Use Case**: Teams of 10-100 users, production environments
- **Components**: Multiple Free Claude Code instances behind a load balancer
- **Resources**: 2+ instances, each with 2-4 CPU cores, 4-8 GB RAM
- **High Availability**: Active-passive or active-active with session affinity
- **Setup**:
  ```bash
  # Deploy multiple instances (example with Docker)
  docker-compose up -d --scale free-claude-code=3

  # Or with Kubernetes
  kubectl apply -f deployment.yaml
  ```

### 4.3 Microservices Deployment (Large Enterprises)
- **Use Case**: Organizations with 100+ users, complex integrations
- **Components**: Separated services for different functions:
  - API Gateway (authentication, rate limiting)
  - Core Service (main Free Claude Code logic)
  - Memory Service (dedicated persistent memory storage)
  - Agent Service (specialized agent handling)
  - Monitoring Service (metrics, logging, alerting)
- **Resources**: Scalable based on service-specific demands
- **High Availability**: Full redundancy with automated failover
- **Setup**: Use service mesh (Istio, Linkerd) or cloud-native patterns

### 4.4 Edge Deployment (Distributed Environments)
- **Use Case**: Remote offices, field operations, disconnected environments
- **Components**: Local Free Claude Code instance with optional sync to central
- **Resources**: Minimal hardware (can run on Raspberry Pi class devices)
- **Connectivity**: Intermittent internet with store-and-forward capability
- **Setup**:
  ```bash
  # Lightweight configuration for edge devices
  export FCC_ENABLE_WEB_SERVER_TOOLS=false
  export FCC_MEMORY_PERSISTENT_MAX_ITEMS=1000
  export FCC_LOG_LEVEL=WARN

  fcc-server
  ```

## 5. Configuration for Different Use Cases

### 5.1 Development Environment
```toml
# ~/.fcc/settings.dev.toml
[logging]
level = "DEBUG"
raw_api_payloads = true
raw_sse_events = true
cli_diagnostics = true

[security]
audit_log_enabled = true
evidence_retention_days = 30  # Shorter for dev

[memory]
short_term_max_tokens = 2000  # Smaller for faster testing
persistent_enabled = false    # Often disabled in dev

[optimizations]
enable_network_probe_mock = true
enable_title_generation_skip = true
```

### 5.2 Testing/CI Environment
```toml
# ~/.fcc/settings.ci.toml
[logging]
level = "WARN"  # Reduce noise in logs
raw_api_payloads = false

[model]
default = "lmstudio/local"  # Use local models to avoid API costs

[memory]
persistent_enabled = false    # Clean state for each test
short_term_max_tokens = 1000

[security]
audit_log_enabled = false     # Often disabled in CI

[rate_limiting]
provider_rate_limit = 1       # Minimal for testing
```

### 5.3 High-Security Environment
```toml
# ~/.fcc/settings.secure.toml
[logging]
level = "INFO"
raw_api_payloads = false      # Never log raw payloads
raw_sse_events = false
cli_diagnostics = false

[security]
audit_log_enabled = true
evidence_retention_days = 2555  # 7 years for compliance
encrypt_api_keys = true
master_key_rotation_days = 90

[memory]
persistent_enabled = true
persistent_max_items = 5000   # Limit to reduce attack surface
auto_store_threshold = 0.8    # Only store highly important items

[network]
web_server_tools = false      # Disable web fetching if not needed
allow_private_networks = false

[container]
run_as_non_root = true
drop_all_capabilities = true
```

### 5.4 High-Performance Environment
```toml
# ~/.fcc/settings.performance.toml
[logging]
level = "WARN"  # Reduce I/O overhead

[memory]
short_term_max_tokens = 8000
persistent_enabled = true
persistent_max_items = 50000
persistent_similarity_threshold = 0.8
importance_decay = 0.99     # Slower decay for frequently accessed items

[optimizations]
enable_network_probe_mock = false
enable_title_generation_skip = false
enable_suggestion_mode_skip = false
enable_filepath_extraction_mock = false

[concurrency]
provider_max_concurrency = 10
provider_progress_timeout = 120.0

[caching]
enable_response_caching = true
cache_ttl_seconds = 300
```

## 6. Operational Procedures

### 6.1 Starting and Stopping the Service
#### Manual Start
```bash
# Direct execution
fcc-server

# With specific config
FCC_SETTINGS_MODULE=config.production fcc-server

# Background execution (Unix-like)
nohup fcc-server > logs/fcc.log 2>&1 &
echo $! > logs/fcc.pid

# Background execution (Windows)
start /b fcc-server > logs\fcc.log 2>&1
```

#### Using System Services
##### Linux (systemd)
```ini
# /etc/systemd/system/free-claude-code.service
[Unit]
Description=Free Claude Code Service
After=network.target

[Service]
Type=simple
User=fcc-user
Group=fcc-group
WorkingDirectory=/opt/free-claude-code
ExecStart=/opt/free-claude-code/venv/bin/fcc-server
Restart=on-failure
RestartSec=10
EnvironmentFile=/opt/free-claude-code/config/production.env

[Install]
WantedBy=multi-user.target
```

##### Windows Service
```powershell
# Create using NSSM (Non-Sucking Service Manager)
nssm install FreeClaudeCode "C:\path\to\fcc-server.exe"
nssm set FreeClaudeCode AppDirectory "C:\path\to"
nssm set FreeClaudeCode AppParameters "--config production"
nssm set FreeClaudeCode AppStdout "C:\logs\fcc.out"
nssm set FreeClaudeCode AppStderr "C:\logs\fcc.err"
nssm start FreeClaudeCode
```

### 6.2 Health Checks and Monitoring
#### Basic Health Endpoint
```bash
curl http://localhost:8082/health
# Returns: {"status": "ok", "timestamp": "2026-08-24T19:11:00Z", "version": "x.y.z"}
```

#### Detailed Health Check
```bash
curl http://localhost:8082/health?detailed=true
# Returns comprehensive system information
```

#### CLI Health Command
```bash
fcc-health           # Basic health
fcc-health --detailed # Detailed health with metrics
```

#### Custom Health Checks
Create custom health check scripts that verify:
- API responsiveness
- Memory system functionality
- Agent system status
- External provider connectivity
- Disk space availability
- Resource utilization thresholds

### 6.3 Backup and Recovery
#### Configuration Backup
```bash
# Backup user-specific configuration
cp -r ~/.fcc ~/backup/fcc_$(date +%Y%m%d_%H%M%S)

# Backup system-wide configuration
cp -r /etc/fcc ~/backup/fcc_system_$(date +%Y%m%d_%H%M%S)
```

#### Data Backup
```bash
# Backup persistent memory store
cp -r ~/.fcc/memory ~/backup/fcc_memory_$(date +%Y%m%d_%H%M%S)

# Backup logs (if stored locally)
cp -r ~/.fcc/logs ~/backup/fcc_logs_$(date +%Y%m%d_%H%M%S)
```

#### Automated Backup Script
```bash
#!/bin/bash
# backup_fcc.sh
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/mnt/backups/fcc_${TIMESTAMP}"

mkdir -p "${BACKUP_DIR}"

# Backup configuration
cp -r ~/.fcc "${BACKUP_DIR}/config"

# Backup persistent data
if [ -d ~/.fcc/memory ]; then
    cp -r ~/.fcc/memory "${BACKUP_DIR}/memory"
fi

# Backup logs
if [ -d ~/.fcc/logs ]; then
    cp -r ~/.fcc/logs "${BACKUP_DIR}/logs"
fi

# Create manifest
echo "Backup created at $(date)" > "${BACKUP_DIR}/MANIFEST"
echo "Free Claude Code version: $(fcc --version)" >> "${BACKUP_DIR}/MANIFEST"

# Optional: compress and encrypt
# tar -czf "${BACKUP_DIR}.tar.gz" -C "${BACKUP_DIR}" .
# openssl enc -aes-256-cbc -salt -in "${BACKUP_DIR}.tar.gz" -out "${BACKUP_DIR}.tar.gz.enc"
```

#### Recovery Procedure
1. Stop the Free Claude Code service
2. Restore configuration from backup
3. Restore persistent data from backup
4. Verify file permissions and ownership
5. Start the service and validate functionality
6. Monitor logs for any issues

### 6.4 Log Management
#### Log Locations
- **Default**: `~/.fcc/logs/` (rotating files)
- **Custom**: Set via `FCC_LOG_FILE_PATH` environment variable
- **Structured**: JSON format for machine parsing
- **Human-readable**: Text format for manual inspection

#### Log Rotation
Configure using system log rotation tools:
```bash
# /etc/logrotate.d/free-claude-code
~/.fcc/logs/*.log {
    daily
    rotate 14
    compress
    delaycompress
    missingok
    notifempty
    create 640 fcc-user fcc-group
    sharedscripts
    postrotate
        # Signal service to reopen log files if needed
        systemctl kill -s SIGUSR1 free-claude-code.service >/dev/null 2>&1 || true
    endscript
}
```

#### Log Monitoring and Alerting
Set up alerts for:
- Repeated authentication failures
- Memory allocation errors
- Provider API timeouts or errors
- Disk space warnings (<10% free)
- High CPU usage (>90% for 5+ minutes)
- Service restart events
- Security audit events

### 6.5 Updates and Upgrades
#### Checking for Updates
```bash
# Check current version
fcc --version

# Check for latest version (if using git)
git fetch origin
git log HEAD..origin/main --oneline

# Check PyPI for latest package
pip index versions free-claude-code
```

#### Upgrade Procedure
```bash
# 1. Stop the service
systemctl stop free-claude-code.service  # Linux
# or: net stop FreeClaudeCode            # Windows

# 2. Backup current installation
cp -r /opt/free-claude-code /opt/free-claude-code.backup.$(date +%Y%m%d_%H%M%S)

# 3. Pull latest code
git pull origin main  # If installed from git
# or: pip install --upgrade free-claude-code  # If installed from PyPI

# 4. Update dependencies
uv pip sync -r requirements.txt  # If using uv
# or: pip install -r requirements.txt  # If using pip

# 5. Run database migrations if any
fcc-db upgrade  # Hypothetical command

# 6. Start the service
systemctl start free-claude-code.service  # Linux
# or: net start FreeClaudeCode            # Windows

# 7. Verify operation
fcc-health --detailed
```

#### Rollback Procedure
```bash
# 1. Stop the service
systemctl stop free-claude-code.service

# 2. Restore from backup
rm -rf /opt/free-claude-code
cp -r /opt/free-claude-code.backup.$(DATE) /opt/free-claude-code

# 3. Restore dependencies
uv pip sync -r requirements.txt.backup.$(DATE)
# or: pip install -r requirements.txt.backup.$(DATE)

# 4. Start the service
systemctl start free-claude-code.service

# 5. Verify operation
fcc-health
```

## 7. Scaling and Performance Optimization

### 7.1 Vertical Scaling (Single Instance)
- **Increase CPU Cores**: Benefit from parallel request processing
- **Increase Memory**: Larger memory caches and better performance under load
- **Faster Storage**: SSD/NVMe for reduced latency in memory operations
- **Network Upgrade**: 1GbE → 10GbE for high-throughput scenarios

### 7.2 Horizontal Scaling (Multiple Instances)
- **Load Balancing**: Distribute requests across multiple instances
- **Session Affinity**: Optional, depending on whether state is shared
- **Shared Memory**: Use external memory store (Redis, PostgreSQL) for shared state
- **Database Sharding**: For very large deployments, shard by user or project

### 7.3 Performance Tuning Parameters
#### Memory System
```toml
# Increase for better cache hit rates (more RAM required)
memory_persistent_max_items = 100000

# Decrease for faster retrieval (may reduce relevance)
memory_persistent_similarity_threshold = 0.75

# Increase for longer-term retention of important memories
memory_persistent_importance_decay = 0.98
```

#### Concurrency
```toml
# Increase for handling more simultaneous requests
provider_max_concurrency = 20

# Decrease to reduce pressure on external APIs
provider_rate_limit = 2

# Increase for longer-running requests
provider_progress_timeout = 1800.0  # 30 minutes
```

#### Caching
```toml
# Enable response caching for repeated queries
enable_response_caching = true

# Cache duration in seconds
cache_ttl_seconds = 600

# Cache size limit (number of entries)
cache_max_size = 1000
```

### 7.4 Monitoring Key Metrics
Track these metrics for performance optimization:
- **Request Latency**: p50, p95, p99 response times
- **Throughput**: Requests per second
- **Error Rate**: Percentage of failed requests
- **Memory Usage**: RSS and cache hit rates
- **CPU Utilization**: Overall and per-core usage
- **External API Calls**: Count and latency to model providers
- **Memory Store Operations**: Insertions, retrievals, and deletions
- **Agent Spawn Rate**: Frequency of agent creation

## 8. Security Operations

### 8.1 Regular Security Tasks
#### Daily
- Review security audit logs for anomalies
- Check for failed authentication attempts
- Verify backup completion and integrity

#### Weekly
- Review security findings and vulnerability alerts
- Check for available security updates to dependencies
- Validate encryption key rotation (if enabled)
- Review quarantine items and false positive/negative rates

#### Monthly
- Conduct access control review (who has what permissions)
- Test incident response procedures
- Review log retention and archival compliance
- Conduct vulnerability assessment of deployment environment

#### Quarterly
- Perform penetration testing (internal or third-party)
- Review and update security policies and procedures
- Test backup and disaster recovery procedures
- Evaluate security tool effectiveness and tuning

### 8.2 Key Management
#### API Key Rotation
```bash
# Rotate a specific provider's API key
fcc-setup --provider openai --rotate-key

# Or manually:
# 1. Generate new key from provider portal
# 2. Store new key securely
# 3. Update applications to use new key
# 4. Monitor for issues during transition
# 5. Revoke old key after grace period
```

#### Master Key Rotation (for encryption)
```bash
# Rotate the master encryption key
fcc-security rotate-master-key

# Or manually:
# 1. Generate new master key
# 2. Re-encrypt all stored keys with new master key
# 3. Replace old master key file
# 4. Securely delete old master key
```

### 8.3 Audit and Compliance
#### Audit Log Review
Focus on:
- Privileged operations (configuration changes, key management)
- Failed access attempts
- Data export events
- Administrative actions
- Security policy modifications

#### Compliance Reporting
Generate reports for:
- GDPR/CCPA data subject requests
- HIPAA access controls (if applicable)
- SOC 2 Type II requirements
- ISO 27001 audit requirements
- Internal policy compliance

### 8.4 Incident Indicators
Watch for these signs of potential security issues:
- Sudden increase in failed login attempts
- Unusual geographic access patterns
- Unexpected data transfer volumes
- New or unexpected processes running
- Configuration changes outside normal windows
- Authentication token anomalies
- Memory access pattern changes
- Unexplained system or service restarts

## 9. Troubleshooting Guide

### 9.1 Common Issues and Solutions

#### Issue: Service Fails to Start
**Symptoms**:
- Process exits immediately after starting
- Error messages in logs about missing dependencies
- Port already in use error

**Solutions**:
1. Check logs for specific error messages
2. Verify all dependencies are installed: `uv pip sync`
3. Check if port 8082 is already in use: `netstat -an | grep 8082`
4. Verify configuration file syntax: `python -c "import free_claude_code.config.settings"`
5. Ensure sufficient permissions to bind to port and access data directories

#### Issue: High Memory Usage
**Symptoms**:
- Process using excessive RAM
- System swapping or becoming unresponsive
- Out of memory errors in logs

**Solutions**:
1. Check memory usage trends: `fcc-health --detailed`
2. Review memory configuration: `memory_persistent_max_items`
3. Check for memory leaks in custom extensions
4. Consider reducing cache sizes or increasing garbage collection frequency
5. Restart service to clear temporary accumulations (if acceptable)

#### Issue: Slow Response Times
**Symptoms**:
- Requests taking several seconds to complete
- Timeout errors from clients
- Poor user experience

**Solutions**:
1. Measure baseline performance with `fcc-health`
2. Check external API latency to model providers
3. Review memory store performance and consider tuning
4. Check CPU utilization - may need more cores or load balancing
5. Review concurrent request limits and consider increasing
6. Look for blocking operations in logs or traces

#### Issue: Unable to Connect to Model Providers
**Symptoms**:
- API connection errors in logs
- Fallback to local models failing
- Service degraded mode activation

**Solutions**:
1. Verify network connectivity and DNS resolution
2. Check API key validity and permissions
3. Verify provider status pages for outages
4. Check proxy configuration if applicable
5. Test API connectivity manually with curl or similar tool
6. Review rate limiting and backoff settings

#### Issue: Persistent Memory Corruption
**Symptoms**:
- Errors about invalid memory format
- Inconsistent search results
- Service failing to start due to memory load errors

**Solutions**:
1. Backup current memory store immediately
2. Attempt to recover from known good backup
3. If no backup available, reset memory store (loss of persisted memories)
4. Check disk health and file system integrity
5. Consider moving memory store to more reliable storage

### 9.2 Diagnostic Tools and Commands
#### Built-in Diagnostics
```bash
# Basic health check
fcc-health

# Detailed system information
fcc-health --detailed

# Version information
fcc --version

# Configuration validation
python -c "from free_claude_code.config.settings import Settings; Settings()"

# Memory statistics
fcc-memory stats  # Hypothetical command
```

#### System-Level Diagnostics
```bash
# Process information
ps aux | grep fcc
# or: Get-Process *fcc*  (PowerShell)

# Resource usage
top -p $(pgrep fcc)  # Linux
# or: Get-Process fcc | Select-Object CPU, WorkingSet  (PowerShell)

# Network connections
netstat -anp | grep fcc  # Linux
# or: Get-NetTCPConnection -OwningProcess (Get-Process fcc).Id  (PowerShell)

# File descriptor usage
lsof -p $(pgrep fcc)  # Linux
```

#### Log Analysis
```bash
# Real-time log viewing
tail -f ~/.fcc/logs/fcc.log

# Error extraction
grep -i error ~/.fcc/logs/fcc.log

# Security event extraction
grep -i "security\|auth\|fail" ~/.fcc/logs/fcc.log

# Performance analysis
grep -i "timeout\|slow\|latency" ~/.fcc/logs/fcc.log
```

### 9.3 When to Escalate
Contact support or engage expert assistance when:
- Service remains down after standard recovery procedures
- Data loss or corruption is suspected
- Security breach or unauthorized access is confirmed
- Performance issues persist after optimization attempts
- Custom extensions or integrations fail unexpectedly
- Root cause cannot be identified with available tools

## 10. Advanced Deployment Scenarios

### 10.1 Air-Gapped Deployment
For environments with no internet connectivity:
```bash
# 1. Prepare on connected machine
uv pip install --no-deps free-claude-code
uv pip download -r requirements.txt -d ./packages

# 2. Transfer air-gapped medium
#    - Copy packages directory
#    - Copy free-claude-code source
#    - Copy documentation

# 3. Install on air-gapped system
uv pip install --no-index --find-links ./packages free-claude-code
uv pip install -e .

# 4. Configure for offline operation
export FCC_ENABLE_WEB_SERVER_TOOLS=false
export FCC_DEFAULT_PROVIDER="lmstudio/local"
```

### 10.2 Hybrid Cloud Deployment
Combining on-premises and cloud resources:
- **On-Premises**: Sensitive data processing, memory storage, internal tools
- **Cloud**: Elastic scaling for peak loads, global accessibility, specialized services
- **Communication**: Secure VPN or dedicated interconnect
- **Data Synchronization**: Encrypted replication with conflict resolution

### 10.3 Multi-Tenant Deployment
Serving multiple organizations or departments:
- **Isolation**: Separate memory stores, configuration, and API keys per tenant
- **Resource Limits**: Per-tenancy CPU, memory, and request limits
- **Branding**: Customizable interfaces per tenant
- **Billing**: Usage tracking per tenant for chargeback
- **Administration**: Centralized management with delegated tenant administration

### 10.4 Disaster Recovery Site
Warm standby for business continuity:
- **Active-Passive**: Primary site handles all traffic, standby ready to take over
- **Data Replication**: Real-time or near-real-time memory store synchronization
- **Configuration Sync**: Automated configuration deployment to standby
- **Testing**: Regular failover drills to validate readiness
- **Geographic Separation**: Sufficient distance to avoid correlated failures

## 11. Compliance and Regulatory Considerations

### 11.1 Data Protection Regulations
#### GDPR/CCPA Compliance
- **Data Minimization**: Only collect necessary information
- **Purpose Limitation**: Use data only for specified purposes
- **Storage Limitation**: Automatic deletion after retention period
- **Rights Support**: Access, rectification, erasure, portability
- **Privacy by Design**: Default settings favor privacy
- **Data Protection Impact Assessments**: Required for high-risk processing

#### HIPAA Compliance (if handling health information)
- **Access Controls**: Unique user identification, emergency access procedure
- **Audit Controls**: Hardware, software, and procedural mechanisms
- **Integrity Controls**: Mechanisms to authenticate ePHI
- **Transmission Security**: Encryption for data in motion
- **Physical Safeguards**: Facility access controls, workstation security

### 11.2 Industry Standards
#### ISO 27001 Information Security Management
- **ISMS Scope**: Definition of what is protected
- **Risk Assessment**: Formal process for identifying and evaluating risks
- **Risk Treatment**: Selected controls to address risks
- **Statement of Applicability**: Documentation of selected controls
- **Internal Audits**: Regular audits of ISMS effectiveness
- **Management Review**: Top-level review of ISMS performance

#### SOC 2 Type II
- **Security**: Protection against unauthorized access
- **Availability**: System availability for operation and use
- **Processing Integrity**: Complete, valid, accurate, timely, and authorized
- **Confidentiality**: Protection of information designated as confidential
- **Privacy**: Collection, use, retention, disclosure, and disposal of personal information

### 11.3 Audit Preparation
#### Documentation Readiness
- Maintain up-to-date network diagrams
- Keep configuration management records current
- Preserve change management logs
- Maintain incident response procedures
- Retain security policies and standards
- Keep training and awareness records

#### Evidence Collection
- Automated log collection and preservation
- Configuration snapshots before and after changes
- Access control lists and permissions documentation
- Vulnerability scan results and remediation tracking
- Penetration test reports and fix validation
- Third-party service attestations and certificates

#### Audit Procedures
- Prepare auditors with advance documentation
- Provide read-only access to production systems
- Facilitate interviews with responsible personnel
- Allow testing of controls with supervision
- Provide remediation plans for identified deficiencies
- Conduct exit meeting to discuss findings and recommendations

## 12. Glossary of Terms

- **API Key**: Secret token used to authenticate with external service providers
- **Agent**: Autonomous or semi-autonomous component that performs specific tasks
- **Memory Store**: System for storing and retrieving information over time
- **Sandbox**: Isolated execution environment for safe testing or untrusted code
- **Workload**: The amount of work being processed by the system at any given time
- **Throughput**: Number of requests or operations processed per unit time
- **Latency**: Time delay between request initiation and response completion
- **Retry**: Attempting a failed operation again after a delay
- **Backoff**: Increasing delay between retry attempts to avoid overwhelming systems
- **Circuit Breaker**: Pattern for temporarily stopping requests to a failing service
- **Health Check**: Automated test to verify service component functionality
- **Idempotent**: Operation that produces the same result regardless of how many times it's executed
- **Rate Limiting**: Restricting the frequency of operations to prevent overload
- **Timeout**: Maximum time to wait for an operation to complete before considering it failed
- **Bulkhead**: Isolation pattern to prevent failure in one component from cascading to others
- **Bulkhead**: Isolation pattern to prevent failure in one component from cascading to others
- **Canary Release**: Technique for reducing risk by rolling out changes to a small subset first
- **Blue/Green Deployment**: Deployment strategy that maintains two identical production environments
- **Rolling Update**: Deployment approach that updates instances incrementally
- **Feature Flag**: Mechanism for enabling or disabling functionality without deploying new code
- **Technical Debt**: Accumulated shortcuts or workarounds that need to be addressed later
- **Mean Time To Recovery (MTTR)**: Average time to restore service after a failure
- **Mean Time Between Failures (MTBF)**: Average time between system failures
- **Service Level Objective (SLO)**: Target level of service reliability
- **Service Level Indicator (SLI)**: Measure of service performance or reliability
- **Error Budget**: Allowable amount of unreliability within an SLO

## 13. Quick Reference Commands

### Installation and Setup
```bash
# Install from source
git clone https://github.com/your-org/free-claude-code.git
cd free-claude-code
uv pip install -e .

# Run setup wizard
fcc-setup

# Verify installation
fcc --version
fcc-health
```

### Service Management
```bash
# Start service
fcc-server
# or: python -m free_claude_code.server

# Start with specific configuration
FCC_SETTINGS_MODULE=config.production fcc-server

# Stop service (Ctrl+C or platform-specific service commands)
```

### Configuration Management
```bash
# Store API key securely
fcc-setup --provider openai --api-key sk-...

# List configured providers
fcc-setup --list

# Remove API key
fcc-setup --provider openai --remove
```

### Monitoring and Diagnostics
```bash
# Basic health check
fcc-health

# Detailed health with metrics
fcc-health --detailed

# Version information
fcc --version

# View logs (if file logging enabled)
tail -f ~/.fcc/logs/fcc.log
```

### Maintenance Operations
```bash
# Backup configuration
cp -r ~/.fcc ~/backup/fcc_config_$(date +%Y%m%d_%H%M%S)

# Backup persistent memory
cp -r ~/.fcc/memory ~/backup/fcc_memory_$(date +%Y%m%d_%H%M%S)

# Rotate encryption keys
fcc-security rotate-master-key

# Check for updates
pip index versions free-claude-code
```

### Troubleshooting
```bash
# Check service status
ps aux | grep fcc  # Linux
# or: Get-Process fcc  # PowerShell

# Check port usage
netstat -tulpn | grep 8082  # Linux
# or: Get-NetTCPConnection -LocalPort 8082  # PowerShell

# Verify configuration
python -c "import free_claude_code.config.settings; print('Config OK')"

# Test API connectivity
curl -s https://api.openai.com/v1/models -H "Authorization: Bearer sk-..."
```

## Conclusion
This deployment and operations guide provides comprehensive instructions for successfully deploying, configuring, operating, and maintaining Free Claude Code across a wide range of environments and use cases. From simple single-instance deployments to complex enterprise architectures, the procedures and best practices outlined here will help ensure reliable, secure, and efficient operation.

Regular review and updating of these procedures is recommended as the system evolves and as operational experience is gained. The guide should be treated as a living document that evolves alongside the Free Claude Code system itself.