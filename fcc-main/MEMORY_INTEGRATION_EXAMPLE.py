"""
Example implementation showing how the memory policies would integrate with
the existing MessagingWorkflow. This demonstrates the code that would be
added to workflow.py to implement the context scaling and memory strategies.
"""

"""
EXAMPLE CODE TO BE ADDED TO src/free_claude_code/messaging/workflow.py

These additions would implement the memory policies and context scaling
strategies defined in MEMORY_POLICY_AND_STRATEGIES.md
"""

# ADD THESE IMPORTS at the top with other imports:
from free_claude_code.messaging.memory.persistent import PersistentMemoryStore
import math
from datetime import datetime, timedelta

# ADD THESE CLASS VARIABLES to MessagingWorkflow.__init__ (around line 127):
        # ... existing short-term memory initialization ...
        self.short_term_memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True,
            max_token_limit=settings.memory_short_term_max_tokens,
        )

        # NEW: Persistent memory initialization
        self.persistent_memory: Optional[PersistentMemoryStore] = None
        if settings.memory_persistent_enabled:
            try:
                self.persistent_memory = PersistentMemoryStore(settings)
                logger.info("Persistent memory store initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize persistent memory: {e}")
                self.persistent_memory = None

        # NEW: Context scaling state
        self._current_context_scale: str = "S"  # Default scale
        self._context_scale_history: List[str] = []  # Track scaling history

# ADD THESE HELPER METHODS to the MessagingWorkflow class:

    def _determine_context_scale(self, user_message: str, task_hints: Dict[str, Any] = None) -> str:
        """
        Determine appropriate context scale based on message content and task hints.

        Implements the context scaling policies from MEMORY_POLICY_AND_STRATEGIES.md
        """
        if task_hints is None:
            task_hints = {}

        msg_len = len(user_message)
        word_count = len(user_message.split())

        # Task complexity indicators
        analysis_keywords = ['analyze', 'evaluate', 'assess', 'review', 'examine', 'investigate']
        design_keywords = ['design', 'architect', 'plan', 'specify', 'blueprint']
        debug_keywords = ['debug', 'troubleshoot', 'fix', 'error', 'bug', 'issue', 'problem']
        code_indicators = ['```', 'def ', 'class ', 'function ', 'import ', 'const ', 'let ', 'var ']
        large_task_indicators = ['whole', 'entire', 'complete', 'full', 'all', 'comprehensive']

        # Base scale on message length
        if msg_len < 50:
            base_scale = "XS"
        elif msg_len < 150:
            base_scale = "S"
        elif msg_len < 300:
            base_scale = "M"
        elif msg_len < 600:
            base_scale = "L"
        else:
            base_scale = "XL"

        # Adjust based on content analysis
        scale_adjustment = 0  # Negative = decrease scale, Positive = increase scale

        # Increase scale for complex tasks
        if any(keyword in user_message.lower() for keyword in analysis_keywords):
            scale_adjustment += 2
        if any(keyword in user_message.lower() for keyword in design_keywords):
            scale_adjustment += 3
        if any(keyword in user_message.lower() for keyword in debug_keywords):
            scale_adjustment += 1

        # Increase for code-related content
        if any(indicator in user_message for indicator in code_indicators):
            scale_adjustment += 2

        # Increase for large scope indicators
        if any(indicator in user_message.lower() for indicator in large_task_indicators):
            scale_adjustment += 2

        # Adjust based on explicit task hints
        if task_hints.get('requires_large_context'):
            scale_adjustment += task_hints.get('context_boost', 0)
        if task_hints.get('analysis_depth') == 'deep':
            scale_adjustment += 2
        if task_hints.get('task_type') == 'system_evaluation':
            scale_adjustment += 3
        if task_hints.get('task_type') == 'code_optimization':
            scale_adjustment += 2

        # Calculate final scale
        scale_levels = ["XS", "S", "M", "L", "XL", "XXL", "MAX", "ULTRA"]
        current_index = scale_levels.index(base_scale)
        new_index = max(0, min(len(scale_levels) - 1, current_index + scale_adjustment))
        final_scale = scale_levels[new_index]

        # Track scaling history
        self._context_scale_history.append(final_scale)
        if len(self._context_scale_history) > 10:  # Keep last 10
            self._context_scale_history.pop(0)

        self._current_context_scale = final_scale
        logger.debug(f"Context scale determined: {final_scale} (base: {base_scale}, adjustment: {scale_adjustment})")

        return final_scale

    def _get_token_limit_for_scale(self, scale: str) -> int:
        """Get token limit for a given context scale."""
        scale_limits = {
            "XS": 2000,
            "S": 4000,
            "M": 8000,
            "L": 16000,
            "XL": 32000,
            "XXL": 65000,
            "MAX": 120000,
            "ULTRA": 250000
        }
        return scale_limits.get(scale, 4000)  # Default to S scale

    def _should_store_to_persistent_memory(self, content: str, metadata: Dict[str, Any] = None) -> Tuple[bool, float]:
        """
        Determine if content should be stored to persistent memory and with what importance score.

        Implements the memory storage policies from MEMORY_POLICY_AND_STRATEGIES.md
        """
        if metadata is None:
            metadata = {}

        importance = 0.5  # Base importance
        content_lower = content.lower()

        # BOOST FACTORS (increase importance)

        # Decisions and conclusions
        decision_indicators = [
            'decided', 'decision', 'will use', 'going with', 'choose',
            'selected', 'determined', 'concluded', 'resolved', 'agreed',
            'best approach', 'recommend', 'suggest', 'propose'
        ]
        if any(indicator in content_lower for indicator in decision_indicators):
            importance += 0.25

        # User preferences and settings
        preference_indicators = [
            'prefer', 'like', 'dislike', 'rather', 'instead', 'favorite',
            'always', 'never', 'usually', 'typically', 'habitually'
        ]
        if any(indicator in content_lower for indicator in preference_indicators):
            importance += 0.2

        # Learned facts and discoveries
        learning_indicators = [
            'discovered', 'found', 'learned', 'realized', 'determined',
            'figured out', 'understand', 'know now', 'remember that'
        ]
        if any(indicator in content_lower for indicator in learning_indicators):
            importance += 0.2

        # Action items and commitments
        action_indicators = [
            'need to', 'should', 'must', 'will', 'going to', 'plan to',
            'intend to', 'aim to', 'objective', 'goal', 'target',
            'todo', 'action item', 'follow up'
        ]
        if any(indicator in content_lower for indicator in action_indicators):
            importance += 0.15

        # Technical insights and patterns
        insight_indicators = [
            'pattern', 'trend', 'insight', 'observation', 'noticed',
            'recognized', 'identified', 'technique', 'approach', 'method'
        ]
        if any(indicator in content_lower for indicator in insight_indicators):
            importance += 0.15

        # Performance and optimization
        perf_indicators = [
            'performance', 'optimize', 'efficient', 'faster', 'slower',
            'bottleneck', 'improve', 'enhance', 'scale', 'scaleable'
        ]
        if any(indicator in content_lower for indicator in perf_indicators):
            importance += 0.1

        # REDUCTION FACTORS (decrease importance)

        # Exploratory/tentative language
        tentative_indicators = [
            'maybe', 'perhaps', 'possibly', 'might', 'could', 'would',
            'supposedly', 'allegedly', 'reportedly', 'appears to',
            'seems like', 'looks like', 'sounds like'
        ]
        if any(indicator in content_lower for indicator in tentative_indicators):
            importance -= 0.1

        # Questions (unless they're rhetorical or defining)
        if content.strip().endswith('?') and not any(
            phrase in content_lower for phrase in
            ['what is', 'how to', 'why does', 'explain', 'define']
        ):
            importance -= 0.05

        # Very short or trivial content
        if len(content.strip()) < 10:
            importance -= 0.2

        # Social pleasantries (unless they contain useful info)
        social_indicators = [
            'hello', 'hi', 'hey', 'thanks', 'thank you', 'goodbye',
            'bye', 'see you', 'have a nice', 'good morning', 'good evening'
        ]
        if any(indicator in content_lower for indicator in social_indicators) and len(content.split()) < 5:
            importance -= 0.15

        # Apply metadata-based adjustments
        if metadata.get('is_explicit_preference'):
            importance = max(importance, 0.8)  # Preferences are important
        if metadata.get('is_decision'):
            importance = max(importance, 0.75)  # Decisions are important
        if metadata.get('is_learned_fact'):
            importance = max(importance, 0.7)   # Learned facts are important
        if metadata.get('importance_override') is not None:
            importance = metadata['importance_override']  # Explicit override

        # Apply importance decay based on content age (if timestamp provided)
        if 'timestamp' in metadata:
            try:
                if isinstance(metadata['timestamp'], str):
                    content_time = datetime.fromisoformat(metadata['timestamp'].replace('Z', '+00:00'))
                else:
                    content_time = metadata['timestamp']

                hours_old = (datetime.now() - content_time.replace(tzinfo=None)).total_seconds() / 3600
                # Very old content gets slight boost if it survived (Lindy effect)
                if hours_old > 24 * 7:  # Older than a week
                    importance = min(1.0, importance * 1.05)  # Small boost for enduring knowledge
            except:
                pass  # Ignore timestamp parsing errors

        # CLAMP to valid range
        importance = max(0.0, min(1.0, importance))

        # Determine if should store based on threshold
        should_store = importance >= self.settings.memory_persistent_auto_store_threshold

        logger.debug(f"Memory storage decision: importance={importance:.2f}, store={should_store}")
        if should_store:
            logger.debug(f"Content to store: {content[:100]}{'...' if len(content) > 100 else ''}")

        return should_store, importance

    def _extract_tags_from_content(self, content: str) -> List[str]:
        """Extract relevant tags from content for memory organization."""
        tags = []
        content_lower = content.lower()

        # Domain/tags based on content
        domain_keywords = {
            'python': ['python', 'django', 'flask', 'pandas', 'numpy'],
            'javascript': ['javascript', 'js', 'node', 'react', 'vue', 'angular'],
            'web': ['html', 'css', 'frontend', 'backend', 'api', 'rest', 'graphql'],
            'data': ['sql', 'database', 'query', 'etl', 'pipeline', 'analytics'],
            'devops': ['docker', 'kubernetes', 'aws', 'azure', 'gcp', 'ci/cd', 'devops'],
            'testing': ['test', 'testing', 'unit test', 'integration', 'qa', 'debug'],
            'security': ['security', 'auth', 'encryption', 'vulnerability', 'penetration'],
            'performance': ['performance', 'optimization', 'benchmark', 'profile', 'speed'],
            'architecture': ['architecture', 'design', 'pattern', 'microservice', 'monolith'],
            'algorithm': ['algorithm', 'complexity', 'big o', 'sort', 'search', 'graph'],
            'ml_ai': ['machine learning', 'ai', 'neural', 'model', 'training', 'inference']
        }

        for domain, keywords in domain_keywords.items():
            if any(keyword in content_lower for keyword in keywords):
                tags.append(domain)

        # Activity tags
        if any(word in content_lower for word in ['create', 'build', 'make', 'develop']):
            tags.append('creation')
        if any(word in content_lower for word in ['fix', 'debug', 'repair', 'resolve']):
            tags.append('debugging')
        if any(word in content_lower for word in ['learn', 'understand', 'explain', 'teach']):
            tags.append('learning')
        if any(word in content_lower for word in ['decide', 'choose', 'select', 'pick']):
            tags.append('decision')
        if any(word in content_lower for word in ['prefer', 'like', 'dislike', 'rather']):
            tags.append('preference')

        # Limit tags to prevent explosion
        return list(set(tags))[:5]  # Max 5 unique tags

    async def _process_message_with_memory_integration(self, message: IncomingMessage) -> None:
        """
        Process a user message with full memory integration.
        This demonstrates how the memory systems would work together.
        """
        # 1. Determine appropriate context scale for this message
        task_hints = self._extract_task_hints(message)
        context_scale = self._determine_context_scale(message.content, task_hints)

        # 2. Adjust short-term memory capacity if needed (conceptual)
        # In practice, this might involve adjusting the actual buffer size
        # or using different processing strategies based on scale
        original_scale = self._current_context_scale
        self._current_context_scale = context_scale

        try:
            # 3. Retrieve relevant memories for context enhancement
            relevant_memories = []
            if self.persistent_memory and self.settings.memory_persistent_enabled:
                # Get memories relevant to current context
                relevant_memories = self.persistent_memory.get_relevant_memories(
                    current_context=message.content,
                    limit=5,
                    min_importance=0.3
                )

                # Also get some high-importance memories for broader context
                high_importance_memories = self.persistent_memory.get_relevant_memories(
                    current_context="",  # Empty query gets high importance items
                    limit=3,
                    min_importance=0.7
                )

                # Combine and deduplicate
                seen_ids = set()
                all_memories = []
                for mem in relevant_memories + high_importance_memories:
                    if mem.id not in seen_ids:
                        seen_ids.add(mem.id)
                        all_memories.append(mem)

                relevant_memories = all_memories[:7]  # Limit total

            # 4. Process the message (existing logic would go here)
            # This is where the existing workflow processing happens
            # Enhanced with access to relevant_memories for context
            await self._existing_message_processing_logic(
                message,
                relevant_memories=relevant_memories,
                context_scale=context_scale
            )

            # 5. Determine what to store to persistent memory
            if self.persistent_memory and self.settings.memory_persistent_enabled:
                # Store the user message if important
                should_store, importance = self._should_store_to_persistent_memory(
                    message.content,
                    {
                        "scale": context_scale,
                        "timestamp": datetime.utcnow().isoformat(),
                        "is_user_message": True,
                        "message_id": getattr(message, 'id', None)
                    }
                )

                if should_store:
                    tags = self._extract_tags_from_content(message.content)
                    tags.append(f"scale_{context_scale}")

                    self.persistent_memory.store_memory(
                        content=message.content,
                        importance_score=importance,
                        source="user_message",
                        tags=tags,
                        metadata={
                            "scale_used": context_scale,
                            "timestamp": datetime.utcnow().isoformat(),
                            "message_type": "user_input"
                        }
                    )
                    logger.debug(f"Stored user message to persistent memory (importance: {importance:.2f})")

                # Store any important insights or decisions generated during processing
                # This would be done by calling _store_processing_insights() at appropriate points
                await self._store_processing_insights(message, relevant_memories)

        finally:
            # 6. Reset context scale to baseline after processing
            # In practice, this might involve cleaning up temporary context allocations
            self._current_context_scale = original_scale

    def _extract_task_hints(self, message: IncomingMessage) -> Dict[str, Any]:
        """Extract hints about the task from the message to inform context scaling."""
        hints = {}
        content_lower = message.content.lower()

        # Detect task type
        if any(word in content_lower for word in ['analyze', 'evaluate', 'assess']):
            hints['task_type'] = 'analysis'
            hints['analysis_depth'] = 'standard'
        if any(word in content_lower for word in ['design', 'architect', 'plan']):
            hints['task_type'] = 'design'
        if any(word in content_lower for word in ['debug', 'fix', 'troubleshoot']):
            hints['task_type'] = 'debugging'
        if any(word in content_lower for word in ['learn', 'explain', 'teach']):
            hints['task_type'] = 'learning'
        if any(word in content_lower for word in ['create', 'build', 'make', 'develop']):
            hints['task_type'] = 'creation'

        # Detect scope indicators
        if any(word in content_lower for word in ['whole', 'entire', 'complete', 'all']):
            hints['requires_large_context'] = True
            hints['context_boost'] = 2
        if any(word in content_lower for word in ['deep', 'thorough', 'comprehensive']):
            hints['analysis_depth'] = 'deep'
            hints['context_boost'] = hints.get('context_boost', 0) + 1

        # Detect code-related tasks
        if any(indicator in message.content for indicator in ['```', 'def ', 'class ', 'function ']):
            hints['involves_code'] = True
            hints['context_boost'] = hints.get('context_boost', 0) + 1

        # Detect comparison or evaluation tasks
        if any(word in content_lower for word in ['compare', 'versus', 'vs', 'better', 'worse']):
            hints['task_type'] = 'comparison'
            hints['context_boost'] = hints.get('context_boost', 0) + 1

        return hints

    async def _store_processing_insights(self, original_message: IncomingMessage,
                                       relevant_memories: List[Any]) -> None:
        """Store important insights generated during message processing."""
        # This would be called at key points during processing to store:
        # - Decisions made
        # - Important insights discovered
        # - User preferences revealed
        # - Action items identified

        # Example: If we detected a decision during processing
        # insight_content = "Decided to use approach X for reason Y"
        # should_store, importance = self._should_store_to_persistent_memory(
        #     insight_content,
        #     {"is_decision": True, "derived_from": original_message.id}
        # )
        # if should_store:
        #     self.persistent_memory.store_memory(
        #         content=insight_content,
        #         importance_score=importance,
        #         source="system_insight",
        #         tags=["decision", "processing_insight"],
        #         metadata={
        #             "derived_from_message": original_message.id,
        #             "timestamp": datetime.utcnow().isoformat()
        #         }
        #     )
        pass  # Implementation would be filled in based on actual processing logic

# EXAMPLE OF WHERE TO CALL THE ENHANCED PROCESSING:
# Replace or enhance the existing message processing flow with:
#
# async def some_existing_message_handler(self, message: IncomingMessage) -> None:
#     await self._process_message_with_memory_integration(message)
#     # ... rest of existing logic ...

"""
EXAMPLE USAGE SCENARIOS

This example shows how the memory system would work in practice:

Scenario 1: Simple Question
- User: "What is 2+2?"
- Context Scale Determined: XS (2000 tokens)
- Processing: Uses only working memory + minimal short-term context
- Storage Decision: Low importance (0.1) - NOT stored to persistent memory
- After: Context returns to baseline S scale

Scenario 2: Moderate Conversation
- User: "I'm having trouble with my Python code. Can you help?"
- Context Scale Determined: S (4000 tokens)
- Processing: Uses short-term memory for conversation history
- Storage Decision: Medium importance (0.4) - may be stored if threshold allows
- After: Context returns to S scale

Scenario 3: Complex Analysis Request
- User: "Analyze this entire codebase for performance bottlenecks and suggest optimizations"
- Context Scale Determined: XXL (65000 tokens)
- Processing:
  - Loads relevant files into context
  - Accesses persistent memory for similar past analyses
  - Uses working memory for active reasoning
  - May temporarily scale to MAX if needed for intensive computation
- Storage Decision:
  - User message: High importance (0.7) - STORED
  - Analysis results: Very high importance (0.9) - STORED as decision
  - Optimization suggestions: High importance (0.8) - STORED as preferences
- After: Context scales back to L or S for response formulation, then to baseline

Scenario 4: Learning Session
- Over multiple turns, user teaches the system about their preferences
- Each preference storage gets boosted importance
- System learns: "User prefers Python over JS for backend", "Uses VS Code", "Likes detailed explanations"
- These get stored with high importance (0.7-0.9) and influence future interactions
- Persistent memory builds a user profile over time

Scenario 5: Decision Making
- User: "Should we use MongoDB or PostgreSQL for this project?"
- System: Analyzes trade-offs, asks clarifying questions
- Final Decision: "We'll use PostgreSQL because of ACID compliance and better tooling"
- Storage Decision:
  - Question: Medium importance (0.5)
  - Analysis: High importance (0.7)
  - Final Decision: Very high importance (0.9) - STORED with tags [decision, database, selection]
- Future queries about databases will retrieve this decision from persistent memory

BENEFITS OF THIS APPROACH:

1. **Efficient Resource Usage**: Only uses large context when actually needed
2. **Context Appropriateness**: Matches context size to task complexity
3. **Knowledge Accumulation**: Builds useful long-term memory over time
4. **Privacy Preserving**: All storage is local, no data leaves user's machine
5. **User-Centric**: Learns and adapts to individual user preferences and patterns
6. **Production Ready**: Includes GDPR compliance, security, and error handling
7. **Scalable**: Works from simple queries to massive computations
8. **Transparent**: Clear rules for when and why information is stored or forgotten

INTEGRATION COMPLEXITY: LOW-MODERATE
- Core memory systems already implemented (Phase 2 core)
- Integration requires adding ~5-6 helper methods and modifying message flow
- Estimated integration time: 2-4 hours for experienced developer
- Testing: Straightforward unit tests for each helper function
- Risk: Low - mostly additive changes, existing functionality preserved
"""