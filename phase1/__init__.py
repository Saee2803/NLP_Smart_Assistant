# PHASE 1: NLP Foundation for DBA Assistant
# ==========================================
# This module provides:
# 1. Intent extraction from natural language
# 2. CSV-based query engine
# 3. Deterministic answer generation
#
# RULES:
# - Data source is ONLY CSV (static dataset)
# - No hallucination - only factual answers
# - If data missing, say so explicitly
# ==========================================

__version__ = "1.0.0"
__phase__ = 1
