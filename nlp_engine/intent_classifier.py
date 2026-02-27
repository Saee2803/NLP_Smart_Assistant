# nlp_engine/intent_classifier.py
import re

# -----------------------------------------
# Intent constants
# -----------------------------------------
INTENT_WHY = "WHY"
INTENT_FREQUENT = "FREQUENT"
INTENT_SOLUTION = "SOLUTION"
INTENT_HEALTH = "HEALTH"
INTENT_UNKNOWN = "UNKNOWN"


class IntentClassifier:
    """
    Classifies user questions into intents
    and extracts database name if present.
    """

    def classify(self, question: str) -> dict:
        q = question.lower().strip()

        return {
            "intent": self._detect_intent(q),
            "database": self._extract_database(question)
        }

    # -------------------------------------
    # Intent detection
    # -------------------------------------
    def _detect_intent(self, q: str) -> str:

        if any(k in q for k in ["why", "ka", "kasla", "reason"]):
            return INTENT_WHY

        if any(k in q for k in ["frequent", "again", "many times", "kitni vela", "often"]):
            return INTENT_FREQUENT

        if any(k in q for k in ["solution", "fix", "kay karaycha", "what to do", "recommend"]):
            return INTENT_SOLUTION

        if any(k in q for k in ["health", "status", "stable", "overall"]):
            return INTENT_HEALTH

        return INTENT_UNKNOWN

    # -------------------------------------
    # Database name extraction
    # -------------------------------------
    def _extract_database(self, question: str):
        """
        Extracts DB name like FINDB, HRDB, MIDDEVSTB, etc.
        """
        tokens = re.findall(r"[A-Z0-9_]{4,}", question.upper())
        return tokens[0] if tokens else None


# ------------------------------------------------
# Legacy helper (KEEP BUT DO NOT USE)
# ------------------------------------------------
def convert_to_sql(question: str) -> str:
    """
    Legacy compatibility method.
    NOT used in OEM Incident Assistant.
    """

    classifier = IntentClassifier()
    result = classifier.classify(question)

    intent = result["intent"]
    db = result["database"] or "DATABASE"

    if intent == INTENT_WHY:
        return f"SELECT * FROM incidents WHERE database='{db}'"

    if intent == INTENT_FREQUENT:
        return f"SELECT category, COUNT(*) FROM incidents WHERE database='{db}' GROUP BY category"

    if intent == INTENT_SOLUTION:
        return f"SELECT recommendation FROM recommendations WHERE database='{db}'"

    if intent == INTENT_HEALTH:
        return f"SELECT availability FROM database_health WHERE database='{db}'"

    return "INVALID"


# ------------------------------------------------
# Standalone test
# ------------------------------------------------
if __name__ == "__main__":
    clf = IntentClassifier()
    while True:
        q = input("\nAsk: ")
        if q.lower() in ("exit", "quit"):
            break

        print(clf.classify(q))

