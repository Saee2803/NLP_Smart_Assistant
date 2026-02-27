"""
PHASE 1: Main Service
=====================
Orchestrates intent parsing, query execution, and answer generation.

USAGE:
    from phase1.service import process_question
    
    result = process_question("how many critical alerts for MIDEVSTB")
    print(result["answer"])

SUPPORTED QUESTIONS (PHASE 1):
1. "show me alerts for MIDEVSTB"
2. "how many alerts are there"
3. "how many critical alerts"
4. "show warning alerts"
5. "show standby issues"
6. "are there any critical alerts for this db?"

NOT SUPPORTED (future phases):
- Follow-ups like "ok show me 10"
- "why is this happening"
- "what should DBA do"
"""

from typing import Dict, Any, Optional

from phase1.intent_parser import Phase1IntentParser, parse_intent
from phase1.query_engine import Phase1QueryEngine, get_engine, execute_query
from phase1.answer_generator import Phase1AnswerGenerator, generate_answer


class Phase1Service:
    """
    Main orchestrator for Phase 1 NLP DBA Assistant.
    
    Connects:
    - Intent Parser: question → structured intent
    - Query Engine: intent → data results
    - Answer Generator: results → human answer
    """
    
    def __init__(self):
        """Initialize the service."""
        self.parser = Phase1IntentParser()
        self.engine = get_engine()
        self.generator = Phase1AnswerGenerator()
    
    def process(self, question: str) -> Dict[str, Any]:
        """
        Process a natural language question end-to-end.
        
        Args:
            question: User's question in natural language
            
        Returns:
            {
                "answer": str,           # Human-readable answer
                "intent": dict,          # Parsed intent object
                "query_result": dict,    # Raw query result
                "success": bool,         # Whether processing succeeded
                "confidence": float      # Confidence score
            }
        """
        # Step 1: Update parser with known databases
        known_dbs = self.engine.known_databases
        self.parser.set_known_databases(known_dbs)
        
        # Step 2: Parse intent
        intent = self.parser.parse(question)
        
        # Step 3: Check confidence threshold - ask for clarification if low
        if intent["confidence"] < 0.7 or intent["intent_type"] == "UNKNOWN":
            # Generate clarifying question based on what we did understand
            clarifying_msg = self._generate_clarification_request(intent, question)
            return {
                "answer": clarifying_msg,
                "intent": intent,
                "query_result": None,
                "success": False,
                "confidence": intent["confidence"]
            }
        
        # Step 4: Execute query
        query_result = self.engine.execute(intent)
        
        # Step 5: Generate answer with DBA intelligence
        answer = self.generator.generate(query_result, intent)
        
        return {
            "answer": answer,
            "intent": intent,
            "query_result": query_result,
            "success": query_result.get("success", False),
            "confidence": intent["confidence"]
        }
    
    def _generate_clarification_request(self, intent: Dict[str, Any], question: str) -> str:
        """
        Generate a clarifying question when confidence is low.
        
        DBA-friendly clarification without AI jargon.
        """
        database = intent.get("database")
        severity = intent.get("severity")
        
        if database and not severity:
            return (
                f"I understand you're asking about **{database}**. "
                "Could you clarify — do you want the total count, only critical alerts, "
                "or a specific type of information?"
            )
        elif severity and not database:
            return (
                f"You're asking about {severity.lower()} alerts. "
                "Would you like the count across all databases, or for a specific database?"
            )
        elif database and severity:
            return (
                f"I'm not entirely sure what information you need about "
                f"{severity.lower()} alerts for {database}. "
                "Would you like a count, a list, or a status summary?"
            )
        else:
            return (
                "I want to make sure I understand your question correctly. "
                "Could you please rephrase or provide more details? "
                "For example: 'show alerts for DBNAME' or 'how many critical alerts?'"
            )
    
    def parse_only(self, question: str) -> Dict[str, Any]:
        """
        Parse a question without executing the query.
        Useful for debugging intent extraction.
        """
        known_dbs = self.engine.known_databases
        self.parser.set_known_databases(known_dbs)
        return self.parser.parse(question)
    
    def is_phase1_question(self, question: str) -> bool:
        """
        Check if a question is within Phase 1 scope.
        
        Returns False for questions that require:
        - Context carryover
        - Action recommendations
        - Predictions
        - Root cause analysis
        """
        q_lower = question.lower().strip()
        
        # Questions NOT in Phase 1 scope
        out_of_scope_patterns = [
            r'\bwhy\s+is\b',           # "why is this happening"
            r'\bwhat\s+should\b',      # "what should DBA do"
            r'\brecommend\b',          # action recommendations
            r'\bpredict\b',            # predictions
            r'\bwill\s+fail\b',        # predictions
            r'\broot\s+cause\b',       # RCA
            r'\bfix\s+this\b',         # action recommendations
            r'\bsolve\b',              # action recommendations
            r'\bok\s+show\s+me\b',     # follow-up
            r'^more\b',                # follow-up
            r'^next\b',                # follow-up
            r'\bthis\s+database\b',    # requires context
            r'\bthat\s+one\b',         # requires context
            r'\bsame\s+db\b',          # requires context
        ]
        
        import re
        for pattern in out_of_scope_patterns:
            if re.search(pattern, q_lower):
                return False
        
        return True


# Singleton instance
_service_instance = None

def get_service() -> Phase1Service:
    """Get or create the service instance."""
    global _service_instance
    if _service_instance is None:
        _service_instance = Phase1Service()
    return _service_instance


def process_question(question: str) -> Dict[str, Any]:
    """
    Process a question using Phase 1 logic.
    
    This is the main entry point for Phase 1.
    
    Args:
        question: Natural language question
        
    Returns:
        Result dictionary with answer and metadata
    """
    service = get_service()
    return service.process(question)


def parse_question(question: str) -> Dict[str, Any]:
    """Parse a question without executing (for debugging)."""
    service = get_service()
    return service.parse_only(question)


def is_supported(question: str) -> bool:
    """Check if a question is supported in Phase 1."""
    service = get_service()
    return service.is_phase1_question(question)
