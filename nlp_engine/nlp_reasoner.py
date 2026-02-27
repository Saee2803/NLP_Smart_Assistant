"""
NLP Reasoner for OEM Intelligence Chatbot

CRITICAL FIX: This is a complete rewrite to use the proper reasoning pipeline.

The old implementation had these problems:
1. Same answer for different questions
2. INTERNAL_ERROR treated as root cause (it's a SYMPTOM)
3. No proper intent classification
4. No ORA code drilling
5. Generic template responses

The new implementation:
1. Uses OEMIntentEngine for proper intent classification
2. Uses OEMDataAnalyzer to drill into ORA codes and context
3. Uses OEMReasoningPipeline for structured reasoning
4. Each intent has UNIQUE handling logic
5. Evidence-based answers with specific root causes

CONVERSATIONAL INTELLIGENCE UPGRADE:
6. Detects follow-up queries (limit, reference, filter)
7. Uses session context for intelligent responses
8. Provides clarification when context is missing
9. Applies filters/limits on cached result sets

Python 3.6 compatible.
"""

from data_engine.global_cache import GLOBAL_DATA
from nlp_engine.context_memory import ContextMemory


class NLPReasoner:
    """
    NLP Reasoner for OEM Incident Intelligence.
    
    CRITICAL: Uses the new reasoning pipeline for proper analysis.
    Each question type MUST produce a UNIQUE, contextual answer.
    
    CONVERSATIONAL UPGRADE: Handles follow-up queries intelligently.
    """
    
    def __init__(self):
        """Initialize the reasoner with the new pipeline."""
        self.memory = ContextMemory()
        self._pipeline = None
        self._last_target = None
        self._router = None
    
    @property
    def pipeline(self):
        """Lazy-load the reasoning pipeline."""
        if self._pipeline is None:
            from nlp_engine.oem_reasoning_pipeline import OEMReasoningPipeline
            self._pipeline = OEMReasoningPipeline()
        return self._pipeline
    
    @property
    def router(self):
        """Lazy-load the intent response router."""
        if self._router is None:
            from nlp_engine.intent_response_router import IntentResponseRouter
            self._router = IntentResponseRouter()
        return self._router
    
    def answer(self, question, return_target=False):
        """
        Process a user question and return an answer.
        
        CRITICAL: This is the main entry point. It MUST:
        1. Classify intent correctly
        2. Detect follow-up queries
        3. Route to the appropriate handler
        4. Return a UNIQUE answer for each question type
        
        CONVERSATIONAL UPGRADE:
        - Detects follow-up queries
        - Uses session context when available
        - Provides clarification when context is missing
        
        Args:
            question: User's natural language question
            return_target: If True, return (answer, target) tuple
        
        Returns:
            Answer string, or (answer, target) tuple if return_target=True
        """
        q = question.strip()
        
        # Check if OEM data is available
        alerts = GLOBAL_DATA.get("alerts", [])
        if not alerts:
            result = "OEM alert data is not available."
            return (result, None) if return_target else result
        
        # =====================================================
        # CONVERSATIONAL INTELLIGENCE: Detect follow-up queries
        # =====================================================
        is_followup, followup_type = self.router.is_followup_question(q)
        
        if is_followup:
            # Try to handle as follow-up query
            followup_result = self._handle_followup(q, followup_type)
            if followup_result:
                answer = followup_result.get("answer")
                target = followup_result.get("target")
                
                # Update memory with the result
                if target:
                    self._last_target = target
                    self.memory.update(
                        target=target,
                        question=q
                    )
                
                return (answer, target) if return_target else answer
            
            # If follow-up handling failed, provide clarification
            clarification = self._get_clarification_message(followup_type)
            return (clarification, None) if return_target else clarification
        
        # =====================================================
        # STANDARD PROCESSING: Process through reasoning pipeline
        # =====================================================
        try:
            result = self.pipeline.process(q)
            
            answer = result.get("answer", "Unable to process question.")
            target = result.get("target")
            
            # Update memory with the target and result context
            if target:
                self._last_target = target
            
            # Store result context for follow-up queries
            self.memory.update(
                target=target,
                intent=result.get("intent"),
                question=q,
                answer_type=result.get("question_type", "FACT")
            )
            
            # Try to extract and store result set for follow-up filtering
            result_set = self._extract_result_set(answer, result)
            if result_set:
                self.memory.update(result_set=result_set, result_count=len(result_set))
            
            return (answer, target) if return_target else answer
            
        except Exception as e:
            # Fallback to basic handling on error
            error_msg = "Error processing question: {0}".format(str(e))
            return (error_msg, None) if return_target else error_msg
    
    def _handle_followup(self, question, followup_type):
        """
        Handle follow-up queries using session context.
        
        Args:
            question: User's follow-up question
            followup_type: Type of follow-up (LIMIT, REFERENCE, FILTER)
        
        Returns:
            dict with answer and target, or None if context is missing
        """
        context = self.memory.get_context_summary()
        
        if not context.get("has_context"):
            return None  # No context available
        
        # Get alerts from global data
        alerts = GLOBAL_DATA.get("alerts", [])
        if not alerts:
            return None
        
        # Handle different followup types
        if followup_type == "LIMIT":
            return self._handle_limit_followup(question, context, alerts)
        
        elif followup_type == "REFERENCE":
            return self._handle_reference_followup(question, context, alerts)
        
        elif followup_type == "FILTER":
            return self._handle_filter_followup(question, context, alerts)
        
        return None
    
    def _handle_limit_followup(self, question, context, alerts):
        """Handle LIMIT follow-ups: "show me 20", "top 10"."""
        limit = self.router.extract_limit_number(question)
        if not limit:
            return None
        
        # Use cached result set if available
        if context.get("can_filter") and self.memory.last_result_set:
            result_set = self.memory.last_result_set[:limit]
            count = len(result_set)
            
            answer = "Showing top {0} items from previous result:\n\n".format(count)
            for i, item in enumerate(result_set, 1):
                if isinstance(item, dict):
                    answer += "{0}. {1}\n".format(i, item.get("target", "Unknown"))
                else:
                    answer += "{0}. {1}\n".format(i, str(item))
            
            return {
                "answer": answer.strip(),
                "target": context.get("database")
            }
        
        # Filter alerts based on last context
        filtered_alerts = self._filter_by_context(alerts, context)
        if not filtered_alerts:
            return None
        
        # Get top N alerts
        top_alerts = filtered_alerts[:limit]
        
        # Build answer
        answer = self._format_alert_list(top_alerts, limit, context)
        
        return {
            "answer": answer,
            "target": context.get("database")
        }
    
    def _handle_reference_followup(self, question, context, alerts):
        """Handle REFERENCE follow-ups: "this database", "same one"."""
        database = context.get("database")
        if not database:
            return None
        
        # Filter alerts for this database
        db_alerts = [a for a in alerts if 
                    (a.get("target_name") or a.get("target") or "").upper() == database.upper()]
        
        if not db_alerts:
            return {
                "answer": "No alerts found for {0}.".format(database),
                "target": database
            }
        
        # Build summary answer
        answer = "For {0}:\n\n".format(database)
        answer += "Total alerts: {0}\n".format(len(db_alerts))
        
        # Count by severity
        severity_counts = {}
        for a in db_alerts:
            sev = a.get("severity", "UNKNOWN")
            severity_counts[sev] = severity_counts.get(sev, 0) + 1
        
        if severity_counts:
            answer += "\nBy severity:\n"
            for sev, count in sorted(severity_counts.items(), key=lambda x: x[1], reverse=True):
                answer += "- {0}: {1}\n".format(sev, count)
        
        return {
            "answer": answer.strip(),
            "target": database
        }
    
    def _handle_filter_followup(self, question, context, alerts):
        """Handle FILTER follow-ups: "only critical", "just errors"."""
        severity = self.router.extract_filter_severity(question)
        if not severity:
            return None
        
        # Use cached result set if available, otherwise filter alerts
        if context.get("can_filter") and self.memory.last_result_set:
            # Filter cached result set
            filtered = [item for item in self.memory.last_result_set 
                       if isinstance(item, dict) and item.get("severity") == severity]
            
            if not filtered:
                return {
                    "answer": "No {0} severity items in previous result.".format(severity),
                    "target": context.get("database")
                }
            
            answer = "Filtered to {0} severity ({1} items):\n\n".format(severity, len(filtered))
            for i, item in enumerate(filtered[:20], 1):
                answer += "{0}. {1}\n".format(i, item.get("target", "Unknown"))
            
            return {
                "answer": answer.strip(),
                "target": context.get("database")
            }
        
        # Filter alerts based on context + severity
        filtered_alerts = self._filter_by_context(alerts, context)
        filtered_alerts = [a for a in filtered_alerts if a.get("severity") == severity]
        
        if not filtered_alerts:
            return {
                "answer": "No {0} severity alerts found.".format(severity),
                "target": context.get("database")
            }
        
        # Build answer
        answer = self._format_alert_list(filtered_alerts, 20, context, severity_filter=severity)
        
        return {
            "answer": answer,
            "target": context.get("database")
        }
    
    def _filter_by_context(self, alerts, context):
        """Filter alerts based on session context."""
        filtered = alerts
        
        # Filter by database if available
        if context.get("database"):
            db = context["database"].upper()
            filtered = [a for a in filtered if 
                       (a.get("target_name") or a.get("target") or "").upper() == db]
        
        # Filter by severity if available
        if context.get("severity"):
            sev = context["severity"]
            filtered = [a for a in filtered if a.get("severity") == sev]
        
        return filtered
    
    def _format_alert_list(self, alerts, limit, context, severity_filter=None):
        """Format a list of alerts into a readable answer."""
        count = len(alerts)
        display_count = min(count, limit)
        
        answer = ""
        if context.get("database"):
            answer += "For {0}".format(context["database"])
        else:
            answer += "Showing"
        
        if severity_filter:
            answer += " - {0} severity".format(severity_filter)
        
        answer += " ({0} total, showing {1}):\n\n".format(count, display_count)
        
        for i, alert in enumerate(alerts[:display_count], 1):
            target = alert.get("target_name") or alert.get("target") or "Unknown"
            msg = alert.get("message") or alert.get("msg_text") or ""
            severity = alert.get("severity", "")
            
            # Truncate message
            if len(msg) > 80:
                msg = msg[:77] + "..."
            
            answer += "{0}. [{1}] {2}: {3}\n".format(i, severity, target, msg)
        
        return answer.strip()
    
    def _extract_result_set(self, answer, result):
        """
        Extract result set from answer for follow-up filtering.
        
        This is a simple heuristic - if the answer contains a list of items,
        extract them for potential follow-up operations.
        """
        # For now, return empty - this would need more sophisticated parsing
        # In production, you'd extract structured data from the result
        return []
    
    def _get_clarification_message(self, followup_type):
        """
        Generate clarification message when context is missing for follow-up.
        
        This makes the assistant feel human-like and helpful.
        """
        if followup_type == "LIMIT":
            return ("I'd like to show you a limited set, but I need more context. "
                   "What would you like to see? (e.g., 'standby alerts', 'critical alerts', "
                   "'alerts for MIDEVSTBN')")
        
        elif followup_type == "REFERENCE":
            return ("I'm not sure which database or item you're referring to. "
                   "Could you specify? (e.g., 'MIDEVSTBN', 'standby alerts')")
        
        elif followup_type == "FILTER":
            return ("I can filter the results, but I need to know what data to filter. "
                   "What would you like to see? (e.g., 'show standby alerts', "
                   "'show critical alerts for MIDEVSTBN')")
        
        return ("I need more context to answer that question. "
               "Could you be more specific?")
    
    def get_last_target(self):
        """Get the last mentioned target database."""
        return self._last_target
    
    def reset(self):
        """Reset conversation context."""
        self._last_target = None
        self.memory.clear()


# =====================================================
# BACKWARD COMPATIBILITY - Keep old methods working
# =====================================================

class OEMReasonerLegacy:
    """
    Legacy wrapper for backward compatibility.
    Delegates to the new pipeline but maintains old interface.
    """
    
    def __init__(self):
        self.reasoner = NLPReasoner()
    
    def reason(self, question):
        """Legacy reason method."""
        return self.reasoner.answer(question, return_target=False)
    
    def analyze(self, question):
        """Legacy analyze method."""
        return self.reasoner.answer(question, return_target=True)



