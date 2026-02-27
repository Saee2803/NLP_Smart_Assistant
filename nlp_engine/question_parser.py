# nlp_engine/question_parser.py

import re
from datetime import datetime, timedelta


class QuestionParser:
    """
    Parses ANY user question and extracts intent + context.
    This is the brain of the chatbot.
    """

    INTENTS = {
        "WHY": ["why", "ka", "kasla", "reason"],
        "WHAT": ["what happened", "what was", "kya hua"],
        "STATUS": ["status", "stable", "resolved", "ongoing"],
        "RISK": ["risky", "risk", "danger", "safe"],
        "RECOMMEND": ["recommend", "solution", "what to do", "action"],
        "HISTORY": ["history", "yesterday", "last night", "earlier"]
    }

    METRIC_KEYWORDS = {
        "CPU": ["cpu", "processor"],
        "MEMORY": ["memory", "heap", "pga", "sga"],
        "STORAGE": ["disk", "storage", "tablespace", "archive"],
        "AVAILABILITY": ["down", "unavailable", "reboot", "restart"],
        "PERFORMANCE": ["slow", "latency", "performance"]
    }

    @classmethod
    def parse(cls, question: str) -> dict:
        q = question.lower()

        return {
            "intent": cls._detect_intent(q),
            "entity": cls._detect_entity(q),
            "database": cls._extract_database(q),
            "host": cls._extract_host(q),
            "time_window": cls._extract_time_window(q),
            "raw_question": question
        }

    # -------------------------
    # INTENT DETECTION
    # -------------------------
    @classmethod
    def _detect_intent(cls, q: str) -> str:
        for intent, keywords in cls.INTENTS.items():
            if any(k in q for k in keywords):
                return intent
        return "GENERAL"

    # -------------------------
    # METRIC / EVENT ENTITY
    # -------------------------
    @classmethod
    def _detect_entity(cls, q: str) -> str:
        for entity, keywords in cls.METRIC_KEYWORDS.items():
            if any(k in q for k in keywords):
                return entity
        return "ALERT"

    # -------------------------
    # DATABASE EXTRACTION
    # -------------------------
    @staticmethod
    def _extract_database(q: str):
        tokens = re.findall(r"[a-z0-9_]{3,}", q)
        for t in tokens:
            if t.endswith("db") or "db" in t:
                return t.upper()
        return None

    # -------------------------
    # HOST EXTRACTION
    # -------------------------
    @staticmethod
    def _extract_host(q: str):
        m = re.search(r"(server|host)\s+([a-z0-9\-]+)", q)
        if m:
            return m.group(2)
        return None

    # -------------------------
    # TIME WINDOW EXTRACTION
    # -------------------------
    @staticmethod
    def _extract_time_window(q: str):
        now = datetime.now()

        if "yesterday" in q:
            start = (now - timedelta(days=1)).replace(hour=0, minute=0)
            end = start + timedelta(days=1)
            return start, end

        if "last night" in q:
            start = (now - timedelta(days=1)).replace(hour=0, minute=0)
            end = start.replace(hour=6)
            return start, end

        if "2 am" in q:
            end = now.replace(hour=2, minute=0, second=0)
            start = end - timedelta(hours=1)
            return start, end

        return None

