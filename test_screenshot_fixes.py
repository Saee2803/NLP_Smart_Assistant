#!/usr/bin/env python
"""
Test the specific queries from the dashboard screenshots to verify fixes.
"""

from services.intelligence_service import INTELLIGENCE_SERVICE
from data_engine.global_cache import GLOBAL_DATA, SYSTEM_READY

SYSTEM_READY['ready'] = True

# Simulate real data
GLOBAL_DATA['alerts'] = [
    {'target': 'MIDEVSTBN:cpu', 'severity': 'CRITICAL', 'message_text': 'ORA-600 internal error', 'issue_type': 'INTERNAL_ERROR'} 
    for _ in range(331097)
] + [
    {'target': 'MIDEVSTBN:memory', 'severity': 'CRITICAL', 'message_text': 'Database issue', 'issue_type': 'OTHER'} 
    for _ in range(152838)
] + [
    {'target': 'MIDEVSTB:listener', 'severity': 'CRITICAL', 'message_text': 'ORA-12537 TNS connection', 'issue_type': 'ORA-12537'} 
    for _ in range(16176)
] + [
    {'target': 'MIDEVSTB:storage', 'severity': 'CRITICAL', 'message_text': 'Tablespace full', 'issue_type': 'STORAGE'} 
    for _ in range(1119)
] + [
    {'target': 'MIDEVSTB:other', 'severity': 'CRITICAL', 'message_text': 'General issue', 'issue_type': 'OTHER'} 
    for _ in range(148557)
]

total = len(GLOBAL_DATA['alerts'])
print(f"Loaded {total:,} alerts")
print("="*70)

# Test 1: Numeric only mode
print("\n[TEST 1] How many CRITICAL alerts exist for MIDEVSTB? Give only the number")
print("-"*70)
result = INTELLIGENCE_SERVICE.analyze("How many CRITICAL alerts exist for MIDEVSTB? Give only the number")
print(f"Answer: {result.get('answer')}")
is_numeric = result.get('answer', '').strip().isdigit()
print(f"✅ PASS (numeric only)" if is_numeric else "❌ FAIL (should be digits only)")

# Test 2: One big issue or many
print("\n[TEST 2] 649,769 critical alerts — one big issue or many?")
print("-"*70)
result = INTELLIGENCE_SERVICE.analyze("649,769 critical alerts — one big issue or many?")
answer = result.get('answer', '')
print(f"Answer:\n{answer[:500]}")
has_assessment = 'issue' in answer.lower() and ('one' in answer.lower() or 'many' in answer.lower())
print(f"\n✅ PASS (explains one vs many)" if has_assessment else "\n❌ FAIL (should explain issue count)")

# Test 3: Which error is causing most
print("\n[TEST 3] Which error is causing most of the alerts?")
print("-"*70)
result = INTELLIGENCE_SERVICE.analyze("Which error is causing most of the alerts?")
answer = result.get('answer', '')
print(f"Answer:\n{answer[:500]}")
has_double_dash = 'ORA--' in answer
print(f"\n❌ FAIL (has ORA-- double dash)" if has_double_dash else "\n✅ PASS (no double dash)")

# Test 4: Explain like senior DBA
print("\n[TEST 4] Explain this like you're talking to another senior DBA")
print("-"*70)
result = INTELLIGENCE_SERVICE.analyze("Explain this like you're talking to another senior DBA")
answer = result.get('answer', '')
print(f"Answer:\n{answer[:700]}")
is_conversational = "here's what" in answer.lower() or "what i'd do" in answer.lower() or "alright" in answer.lower()
print(f"\n✅ PASS (conversational DBA style)" if is_conversational else "\n❌ FAIL (should be conversational)")

# Test 5: Show alerts for MIDEVSTB only, exclude standby
print("\n[TEST 5] show alerts for MIDEVSTB only. Do not include standby")
print("-"*70)
result = INTELLIGENCE_SERVICE.analyze("show alerts for MIDEVSTB only. Do not include standby")
answer = result.get('answer', '')
print(f"Answer:\n{answer[:300]}")
excludes_standby = 'MIDEVSTBN' not in answer.upper()
print(f"\n✅ PASS (excludes standby)" if excludes_standby else "\n❌ FAIL (should not mention MIDEVSTBN)")

print("\n" + "="*70)
print("SCREENSHOT ISSUE VERIFICATION COMPLETE")
print("="*70)
