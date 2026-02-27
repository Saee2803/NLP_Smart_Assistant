#!/usr/bin/env python
"""Quick test for senior DBA explanation query."""

from services.intelligence_service import INTELLIGENCE_SERVICE
from data_engine.global_cache import GLOBAL_DATA, SYSTEM_READY

SYSTEM_READY['ready'] = True
GLOBAL_DATA['alerts'] = [
    {'target': 'MIDEVSTBN:cpu', 'severity': 'CRITICAL', 'message_text': 'ORA-600 internal error'} 
    for _ in range(100)
]

print("Testing: explain this like you're talking to another senior DBA")
print("="*70)
result = INTELLIGENCE_SERVICE.analyze("explain this like you're talking to another senior DBA")
answer = result.get('answer', '')
print(answer)
print("="*70)
print("Contains 'Alright' or 'What I'd do':", 'alright' in answer.lower() or "what i'd do" in answer.lower())
