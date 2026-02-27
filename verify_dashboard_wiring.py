#!/usr/bin/env python
"""
DASHBOARD WIRING - FULL VERIFICATION
Checks all phases are properly connected to the intelligence service.
"""

from services.intelligence_service import (
    INTELLIGENCE_SERVICE, 
    INCIDENT_COMMANDER_AVAILABLE,
    ANSWER_CONTRACTS_AVAILABLE,
    DATA_AWARENESS_AVAILABLE,
    PHASE7_TRUST_AVAILABLE
)
from data_engine.global_cache import GLOBAL_DATA, SYSTEM_READY

print('='*60)
print('DASHBOARD WIRING - FULL VERIFICATION')
print('='*60)

# Check all phases
print('\n[PHASE AVAILABILITY]')
print(f'  Phase 7 (Enterprise Trust):   {PHASE7_TRUST_AVAILABLE}')
print(f'  Phase 8 (Data Awareness):     {DATA_AWARENESS_AVAILABLE}')
print(f'  Phase 9 (Incident Commander): {INCIDENT_COMMANDER_AVAILABLE}')
print(f'  Phase 10 (Answer Contracts):  {ANSWER_CONTRACTS_AVAILABLE}')

SYSTEM_READY['ready'] = True

# Test data - distinct counts for MIDEVSTB vs MIDEVSTBN
GLOBAL_DATA['alerts'] = [
    {'target': 'MIDEVSTBN:cpu', 'severity': 'CRITICAL', 'message_text': 'ORA-00600'} for _ in range(1000)
] + [
    {'target': 'MIDEVSTB:listener', 'severity': 'CRITICAL', 'message_text': 'Listener'} for _ in range(500)
] + [
    {'target': 'MIDEVSTB:memory', 'severity': 'WARNING', 'message_text': 'SGA'} for _ in range(200)
]

print(f'\n[TEST DATA LOADED]')
print(f'  Total alerts: {len(GLOBAL_DATA["alerts"])}')
print(f'  MIDEVSTBN CRITICAL: 1000')
print(f'  MIDEVSTB CRITICAL:  500')
print(f'  MIDEVSTB WARNING:   200')

# Run tests
tests = [
    # Phase 9 - Incident Commander
    ('Phase 9: Incident Status', 'What is the incident status?', 'INCIDENT_COMMAND', None),
    ('Phase 9: Priority', 'What is the top priority?', 'INCIDENT_COMMAND', None),
    ('Phase 9: Next Action', 'What should I do now?', 'INCIDENT_COMMAND', None),
    ('Phase 9: Escalation', 'Should I escalate?', 'INCIDENT_COMMAND', None),
    ('Phase 9: Prediction', 'What might fail next?', 'INCIDENT_COMMAND', None),
    ('Phase 9: Blast Radius', 'What is the blast radius?', 'INCIDENT_COMMAND', None),
    
    # Phase 10 - Answer Contracts (numeric only)
    ('Phase 10: Numeric Only', 'How many critical alerts for MIDEVSTB? Give only the number', None, '500'),
    
    # Bug Fixes - Strict DB matching
    ('Bug Fix: MIDEVSTB count', 'How many critical alerts for MIDEVSTB?', 'FACT', None),
    
    # Core queries
    ('Core: Total Count', 'How many alerts total?', 'FACT', None),
    ('Core: DB Query', 'Which database has most alerts?', 'FACT', None),
]

print('\n[QUERY ROUTING TESTS]')
print('-'*60)

passed_count = 0
total_count = len(tests)

for name, query, expected_type, expected_answer in tests:
    result = INTELLIGENCE_SERVICE.analyze(query)
    qt = result.get('question_type')
    answer = result.get('answer', '').strip()
    
    # Determine pass/fail
    passed = True
    notes = []
    
    # Check question type if expected
    if expected_type and qt != expected_type:
        passed = False
        notes.append(f'type={qt}')
    
    # Check answer if expected
    if expected_answer:
        if answer != expected_answer:
            passed = False
            notes.append(f'answer="{answer}"')
    
    # For numeric only, verify digits
    if 'Give only the number' in query:
        if not answer.isdigit():
            passed = False
            notes.append('not_numeric')
    
    status = '✅' if passed else '❌'
    if passed:
        passed_count += 1
    
    note_str = f' ({", ".join(notes)})' if notes else ''
    print(f'{status} {name}{note_str}')

print('\n' + '-'*60)
print(f'PASSED: {passed_count}/{total_count}')

# Additional checks
print('\n[ANSWER CONTRACT INTEGRATION]')
result = INTELLIGENCE_SERVICE.analyze('How many critical alerts?')
has_contract = 'answer_contract' in result
print(f'  Contract metadata in response: {"✅" if has_contract else "❌"}')

# Check scope bleeding protection
print('\n[SCOPE BLEEDING PROTECTION]')
result = INTELLIGENCE_SERVICE.analyze('How many critical alerts for MIDEVSTB?')
answer = result.get('answer', '')
has_midevstbn = 'MIDEVSTBN' in answer.upper()
print(f'  MIDEVSTB query excludes MIDEVSTBN: {"✅" if not has_midevstbn else "❌"}')

# Check 500 in answer (not 1000 or 1500)
has_500 = '500' in answer
has_1000 = '1000' in answer or '1,000' in answer
print(f'  Correct count (500 not 1000): {"✅" if has_500 and not has_1000 else "❌"}')

print('\n' + '='*60)
if passed_count == total_count:
    print('ALL DASHBOARD WIRING VERIFIED ✅')
else:
    print(f'ISSUES FOUND: {total_count - passed_count} failed ⚠️')
print('='*60)
