import re

class IntentDetector:
    def detect(self, question: str) -> dict:
        q = question.lower()

        intent = "general"
        entities = {}

        if any(w in q for w in ["why", "reason", "root cause"]):
            intent = "root_cause"

        elif any(w in q for w in ["what happened", "timeline", "when"]):
            intent = "timeline"

        elif any(w in q for w in ["stable", "status", "health"]):
            intent = "status"

        elif any(w in q for w in ["risk", "risky"]):
            intent = "risk"

        # -------- Time entities --------
        if "yesterday" in q:
            entities["day"] = "yesterday"

        if "last night" in q or "night" in q:
            entities["time_range"] = "night"

        # -------- Target extraction --------
        tokens = re.findall(r"[A-Z0-9_.-]{4,}", question.upper())
        if tokens:
            entities["target"] = tokens[0]

        return {
            "intent": intent,
            "entities": entities
        }

