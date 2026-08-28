# Memory System Policies and Strategies for Free Claude Code

This document defines the comprehensive memory system policies, use scenarios, compaction rules, and context scaling strategies for the Free Claude Code memory architecture.

## 🧠 Memory Tiers and Use Scenarios

### 1. Working Memory (Immediate Context)
- **Purpose**: Current turn processing, active tool use, immediate reasoning
- **Capacity**: Unlimited (bounded by LLM context window)
- **Use Cases**:
  - Processing the current user message
  - Active tool execution and result handling
  - Immediate reasoning steps
  - Current conversation turn state
- **Lifecycle**: Reset after each turn completion
- **Implementation**: Native Python variables in workflow processing

### 2. Ephemeral Short-Term Memory (Conversation Buffer)
- **Purpose**: Recent conversation history for contextual awareness
- **Capacity**: Configurable token limit (default: 4,000 tokens)
- **Use Cases**:
  - Maintaining conversation coherence
  - Referencing recent exchanges (last 5-10 turns)
  - Context for immediate follow-up questions
  - Short-term task continuity
- **Configuration**: `memory_short_term_max_tokens` setting
- **Implementation**: LangChain ConversationBufferMemory
- **Reset Conditions**:
  - Conversation timeout (configurable)
  - Explicit user reset command
  - Memory limit exceeded (truncates oldest entries)

### 3. Persistent Long-Term Memory (Vector Store)
- **Purpose**: Permanent knowledge retention, cross-conversation learning
- **Capacity**: Configurable item limit (default: 10,000 items)
- **Use Cases**:
  - User preferences and settings retention
  - Important decisions and rationales
  - Learned patterns and heuristics
  - Factual knowledge accumulation
  - Cross-project knowledge sharing
  - Long-term skill acquisition
- **Configuration**:
  - `memory_persistent_max_items`
  - `memory_persistent_similarity_threshold` (default: 0.7)
  - `memory_persistent_importance_decay` (default: 0.95)
  - `memory_persistent_auto_store_threshold` (default: 0.6)
- **Implementation**: ChromaDB + SentenceTransformers
- **Persistence**: Survives application restarts, stored in `~/.fcc/memory/chroma/`

## 📏 Context Scaling Policies

Different tasks require different context sizes. The system should dynamically scale context usage based on task complexity:

### Context Scale Levels
| Scale | Token Range | Use Case Examples | Model Preset Configuration |
|-------|-------------|-------------------|----------------------------|
| **XS** | 1K-4K tokens | Simple Q&A, quick commands, basic coding help | `memory_short_term_max_tokens: 2000` |
| **S** | 4K-8K tokens | Standard conversations, moderate code editing | `memory_short_term_max_tokens: 6000` |
| **M** | 8K-16K tokens | Complex debugging, multi-file edits, detailed explanations | `memory_short_term_max_tokens: 12000` |
| **L** | 16K-32K tokens | Architectural design, system planning, complex algorithms | `memory_short_term_max_tokens: 24000` |
| **XL** | 32K-64K tokens | Large codebase analysis, comprehensive documentation | `memory_short_term_max_tokens: 48000` |
| **XXL** | 64K-128K tokens | Enterprise system evaluation, major refactoring planning | `memory_short_term_max_tokens: 96000` |
| **MAX** | 128K-500K tokens | Whole large program evaluation, complex system design | Requires model with 500k+ context |
| **ULTRA** | 500K-1M tokens | Scientific computation, CAD generation, massive data analysis | Requires model with 1M+ context |

### Dynamic Context Allocation Rules

1. **Task Complexity Detection**:
   - Simple queries (<50 chars): XS scale
   - Moderate queries (50-200 chars): S-M scale
   - Complex requests (>200 chars or containing code): L-XL scale
   - Explicit "analyze", "evaluate", "design" keywords: XL-XXL scale
   - File/project analysis requests: XXL-MAX scale

2. **Context Usage Policy**:
   - **Always start minimal**: Begin with XS or S scale context
   - **Scale up on demand**: Increase context size when:
     - User references earlier conversation beyond short-term memory
     - Task requires accessing persistent knowledge
     - Complex reasoning chains detected
   - **Scale down after completion**: After intensive processing, revert to appropriate baseline
   - **Never exceed necessary**: Use smallest context size that adequately handles the task

3. **Model Preset Mapping**:
   - Define presets in configuration that map to context scales:
     ```
     # Example preset configurations
     preset_quick:  # For simple queries
       context_scale: XS
       max_tokens: 2048
       temperature: 0.7

     preset_standard:  # For regular conversations
       context_scale: S
       max_tokens: 4096
       temperature: 0.8

     preset_thinking:  # For complex reasoning
       context_scale: L
       max_tokens: 16384
       temperature: 0.6

     preset_evaluation:  # For system/code evaluation
       context_scale: XXL
       max_tokens: 65536
       temperature: 0.5

     preset_ultra:  # For massive computations
       context_scale: ULTRA
       max_tokens: 1048576
       temperature: 0.3
     ```

## 📉 Compaction and Summarization Strategies

### 1. Short-Term Memory Compaction
When `memory_short_term_max_tokens` is approached:

**Trigger**: When memory usage reaches 80% of limit

**Strategy**: Hierarchical summarization
1. Identify oldest 30% of conversation turns
2. Apply extractive summarization to preserve:
   - Key decisions made
   - Important user preferences expressed
   - Critical context for ongoing tasks
   - Unanswered questions or pending actions
3. Replace compacted turns with summary + metadata
4. Maintain pointer to full history in persistent store for deep recall if needed

**Compaction Ratio**: Target 3:1 reduction (3 turns → 1 summary turn)

### 2. Persistent Memory Pruning and Decay
To prevent unbounded growth while preserving valuable knowledge:

**Trigger**: When item count exceeds `memory_persistent_max_items` OR daily maintenance

**Strategy**: Multi-factor importance scoring
```
Current Importance = Base Importance × (Decay Factor ^ Days Since Access) × Access Frequency Boost
```

Where:
- **Base Importance**: Assigned at storage time (0.0-1.0)
- **Decay Factor**: `memory_persistent_importance_decay` (e.g., 0.95 = 5% daily decay)
- **Days Since Access**: Time since last retrieval or use
- **Access Frequency Boost**: 1.0 + log(access_count) × 0.1 (caps at 2.0x boost)

**Pruning Process**:
1. Calculate current importance for all items
2. Sort by importance (ascending)
3. Remove lowest importance items until under limit
4. Preserve minimum threshold of 0.3 importance regardless of age (prevents loss of foundational knowledge)

### 3. Summarization Quality Guidelines

For all summarization operations, follow these principles:

**Preserve**:
- Explicit decisions and conclusions
- Action items and their owners
- Critical context for understanding
- User-expressed preferences and constraints
- Important factual information

**Can Condense/Summarize**:
- Exploratory discussions that didn't lead to conclusions
- Redundant or repetitive points
- Intermediate reasoning steps (keep only key insights)
- Social pleasantries and filler conversation
- Technical details that are available elsewhere

**Summarization Prompt Template**:
```
Create a concise summary that preserves:
1. Any decisions made or conclusions reached
2. Action items, responsible parties, and deadlines
3. Important context necessary for future understanding
4. User preferences, constraints, or requirements expressed
5. Key factual information learned

Do NOT include:
- Exploratory paths that were abandoned
- Redundant repetitions
- Social pleasantries
- Intermediate steps that don't affect the outcome

Be concise but comprehensive. Target length: ~1/3 of original.
```

## 🔄 Context Scaling Workflow

Here's how the system should dynamically scale context during a typical interaction:

### Scenario: User asks to "analyze this large codebase for performance bottlenecks"

1. **Initial Assessment** (XS-S scale):
   - User request classified as complex analysis task
   - System allocates M-L scale context (8K-24K tokens)
   - Loads relevant files and recent conversation into context

2. **Processing Phase** (L-XL scale):
   - As analysis progresses, detects need for more context
   - Scales up to XL-XXL scale (32K-96K tokens)
   - Loads additional relevant files, documentation, historical decisions
   - Uses persistent memory to recall similar past analyses

3. **Intensive Computation** (MAX scale if needed):
   - For particularly large/complex codebases
   - Temporarily scales to MAX scale (128K-500K tokens)
   - Performs deep analysis using full context window
   - Relies on persistent memory for cross-reference knowledge

4. **Synthesis Phase** (L scale):
   - After analysis complete, scales back to L scale
   - Begins formulating response and recommendations
   - Uses short-term memory for immediate reasoning
   - Pulls key insights from persistent memory as needed

5. **Response Delivery** (S scale):
   - Final response formatted and delivered
   - Context scales back to S scale for efficient delivery
   - Important insights stored to persistent memory:
     - Performance bottlenecks discovered (as decisions)
     - Optimization strategies recommended (as user preferences for future)
     - Analysis methodology notes (as contextual knowledge)

6. **Post-Interaction** (S→XS scale):
   - After response delivered, scales to baseline
   - Short-term memory retains recent exchange
   - Persistent memory updated with:
     - Conversation summary with key findings
     - User preferences revealed during interaction
     - Any decisions made about next steps

## 🎯 Model Preset Configuration Examples

### Configuration Structure
```yaml
# Memory and context scaling presets
context_presets:
  # For simple, quick interactions
  quick_response:
    description: "For simple queries and commands"
    short_term_tokens: 2000  # XS scale
    persistent_auto_store_threshold: 0.8  # Only store very important items
    enable_aggressive_compaction: true
    default_temperature: 0.7

  # For standard conversations
  standard_chat:
    description: "For regular conversational interactions"
    short_term_tokens: 4000  # S scale
    persistent_auto_store_threshold: 0.6  # Standard storage
    enable_aggressive_compaction: false
    default_temperature: 0.8

  # For deep thinking and reasoning
  deep_thinking:
    description: "For complex problem solving and reasoning"
    short_term_tokens: 12000  # M scale
    persistent_auto_store_threshold: 0.4  # Store more items for learning
    enable_aggressive_compaction: false
    default_temperature: 0.6  # Lower temp for focused reasoning

  # For system evaluation and design
  system_evaluation:
    description: "For analyzing systems, architectures, or large codebases"
    short_term_tokens: 24000  # L scale
    persistent_auto_store_threshold: 0.3  # Store almost everything significant
    enable_aggressive_compaction: false
    default_temperature: 0.5

  # For massive computations (requires compatible model)
  massive_computation:
    description: "For scientific computing, CAD, large data analysis"
    short_term_tokens: 96000  # XL scale (would need model config for larger)
    persistent_auto_store_threshold: 0.2  # Store generously for learning
    enable_aggressive_compaction: false
    default_temperature: 0.3  # Very focused, deterministic

  # Specialized presets for specific providers/models that support huge contexts
  ultra_context:
    description: "For models supporting 500k+ token contexts"
    short_term_tokens: 300000  # Would be handled by model context, not short-term memory
    persistent_auto_store_threshold: 0.1  # Store liberally for knowledge building
    enable_aggressive_compaction: false
    default_temperature: 0.2
```

### Memory Usage Rules by Preset
| Preset | Short-Term Use | Persistent Storage Threshold | Compaction Strategy | Typical Use Case |
|--------|----------------|------------------------------|---------------------|------------------|
| **quick_response** | Minimal (2K) | High (0.8) - only critical items | Aggressive | Simple questions, commands |
| **standard_chat** | Moderate (4K) | Medium (0.6) | Standard | Regular conversations |
| **deep_thinking** | Generous (12K) | Low (0.4) - store more for learning | None | Complex reasoning, debugging |
| **system_evaluation** | Very Generous (24K) | Very Low (0.3) - store most significant | None | Architecture, design, large code analysis |
| **massive_computation** | Extensive (96K) | Minimal (0.2) - store generously | None | Scientific computing, data analysis |
| **ultra_context** | Handled by model | Minimal (0.1) - knowledge building focus | None | 500k+ token tasks requiring huge context |

## 📈 Implementation Guidelines

### For Developers Adding Memory Features

1. **When to Use Which Memory Tier**:
   ```
   IF processing current turn:
       USE Working Memory
   ELSE IF needing recent conversation context (last few turns):
       USE Ephemeral Short-Term Memory
   ELSE IF needing historical knowledge, preferences, decisions:
       USE Persistent Long-Term Memory
   ```

2. **When to Store to Persistent Memory**:
   Store when ANY of these conditions are met:
   - Importance score ≥ `memory_persistent_auto_store_threshold`
   - Item is a user preference or explicit setting
   - Item represents a decision with rationale
   - Item contains learned factual knowledge
   - Item is a conversation summary with actionable insights

3. **Summarization Triggers**:
   Automatically summarize when:
   - Short-term memory reaches 80% of limit
   - Conversation exceeds 20 turns without natural breakpoints
   - User indicates topic shift or completion
   - System prepares for context scaling up

4. **Context Scaling Triggers**:
   Scale up context when:
   - User references information likely not in short-term memory
   - Task involves analyzing large documents/codebases
   - Complex multi-step reasoning is detected
   - Explicit request for deep analysis or evaluation

   Scale down context when:
   - Current task phase completes
   - User shifts to simpler follow-up questions
   - Response generation begins
   - After delivering comprehensive analysis

## 🔧 Example Integration Points

These would be added to `MessagingWorkflow` to implement the policies:

### 1. Context Scaling Helper Method
```python
def _determine_context_scale(self, user_message: str, task_type: str = None) -> str:
    """Determine appropriate context scale based on message content and task type."""
    # Simple heuristic - in practice would use more sophisticated NLP
    msg_len = len(user_message)

    if any(keyword in user_message.lower() for keyword in
           ['analyze', 'evaluate', 'design', 'architecture', 'review', 'assess']):
        return 'XXL' if msg_len > 200 else 'XL'
    elif any(keyword in user_message.lower() for keyword in
             ['debug', 'troubleshoot', 'fix', 'error', 'bug']):
        return 'L' if msg_len > 100 else 'M'
    elif msg_len > 300 or ('"' in user_message and len(user_message.split('"')) > 3):
        return 'XL'  # Likely contains code or detailed specification
    elif msg_len > 100:
        return 'L'
    elif msg_len > 50:
        return 'M'
    else:
        return 'S'
```

### 2. Memory Storage Decision Helper
```python
def _should_store_to_persistent_memory(self,
                                     content: str,
                                     context: Dict[str, Any]) -> Tuple[bool, float]:
    """Determine if content should be stored to persistent memory and with what importance."""
    importance = 0.5  # Base importance

    # Boost importance for decision-related content
    if any(keyword in content.lower() for keyword in
           ['decided', 'decision', 'will use', 'going with', 'choose']):
        importance += 0.3

    # Boost for preferences
    if any(keyword in content.lower() for keyword in
           ['prefer', 'like', 'dislike', 'rather', 'instead']):
        importance += 0.2

    # Boost for learned facts
    if any(keyword in content.lower() for keyword in
           ['discovered', 'found', 'learned', 'realized', 'determined']):
        importance += 0.2

    # Boost for action items
    if any(keyword in content.lower() for keyword in
           ['todo', 'need to', 'should', 'must', 'will']):
        importance += 0.2

    # Reduce for exploratory content
    if any(keyword in content.lower() for keyword in
           ['maybe', 'perhaps', 'possibly', 'could', 'might']):
        importance -= 0.2

    # Clamp to valid range
    importance = max(0.0, min(1.0, importance))

    should_store = importance >= self.settings.memory_persistent_auto_store_threshold
    return should_store, importance
```

### 3. Context Scaling Integration Point
```python
async def process_user_message(self, message: IncomingMessage) -> None:
    # Determine appropriate context scale for this message
    context_scale = self._determine_context_scale(message.content)

    # Temporarily adjust short-term memory limit if needed
    original_limit = self.short_term_memory.memory_key  # Simplified
    # In practice, would adjust the actual token limit based on preset

    try:
        # Process message with appropriate context allocation
        await self._process_message_with_context_scale(message, context_scale)

        # After processing, determine what to store to persistent memory
        if self.persistent_memory:
            should_store, importance = self._should_store_to_persistent_memory(
                message.content,
                {"scale": context_scale, "timestamp": datetime.utcnow()}
            )

            if should_store:
                self.persistent_memory.store_memory(
                    content=message.content,
                    importance_score=importance,
                    context={"scale": context_scale, "type": "user_message"},
                    tags=self._extract_tags(message.content)
                )

    finally:
        # Reset context scale to baseline after processing
        # In practice, would restore original short-term memory limit
        pass
```

## 📋 Summary

This memory policy provides:

1. **Clear Tier Definition**: Working memory (immediate), Ephemeral short-term (recent conversation), Persistent long-term (permanent knowledge)
2. **Context Scaling Framework**: 7 defined scales from XS to ULTRA with specific use cases
3. **Compaction Rules**: Hierarchical summarization for short-term, importance-based decay for persistent
4. **Summarization Guidelines**: What to preserve vs. what can be condensed
5. **Model Preset System**: Configurable presets for different task types
6. **Integration Points**: Clear examples of how to implement in the codebase
7. **Workflow Example**: End-to-end context scaling during a complex task

The system intelligently allocates only the context necessary for each task, scales up when needed for intensive processing, and scales back down afterward—ensuring efficient resource usage while maintaining capability for the most demanding tasks when required.