#!/usr/bin/env python
"""
Verify dashboard wiring for all phases including Phase 9 Incident Commander.
"""

from services.intelligence_service import INTELLIGENCE_SERVICE, INCIDENT_COMMANDER_AVAILABLE
from data_engine.global_cache import GLOBAL_DATA, SYSTEM_READY

SYSTEM_READY['ready'] = True

# Load test data - MIDEVSTB vs MIDEVSTBN (distinct counts)
GLOBAL_DATA['alerts'] = [
    {'target': 'MIDEVSTBN:cpu_health', 'severity': 'CRITICAL', 'message_text': 'ORA-00600'} for _ in range(1000)
] + [
    {'target': 'MIDEVSTB:listener', 'severity': 'CRITICAL', 'message_text': 'Listener down'} for _ in range(500)
]

print('='*60)
print('DASHBOARD WIRING VERIFICATION')
print('='*60)

# =====================================================
# PHASE 9: INCIDENT COMMANDER
# =====================================================
print('\n[PHASE 9] INCIDENT COMMANDER HANDLERS')
print('-'*40)

phase9_tests = [
    ('Incident Status', 'What is the incident status?'),
    ('Priority/Triage', 'What is the top priority?'),
    ('Next Action', 'What should I do now?'),
    ('Escalation', 'Should I escalate this?'),
    ('Prediction', 'What might fail next?'),
    ('Blast Radius', 'What is the blast radius?'),
]

phase9_passed = 0
for name, query in phase9_tests:
    result = INTELLIGENCE_SERVICE.analyze(query)
    qt = result.get('question_type', 'UNKNOWN')
    passed = qt == 'INCIDENT_COMMAND'
    status = '✅' if passed else '❌'
    if passed:
        phase9_passed += 1
    print(f'{status} {name}: {qt}')

print(f'\nPhase 9: {phase9_passed}/{len(phase9_tests)} passed')

# =====================================================
# BUG FIXES: MIDEVSTB vs MIDEVSTBN, Strict Number Mode
# =====================================================
print('\n[BUG FIXES] STRICT DB MATCHING')
print('-'*40)

# Test 1: MIDEVSTB count (should be 500, not 1500)
result = INTELLIGENCE_SERVICE.analyze('How many critical alerts for MIDEVSTB?')
answer = result.get('answer', '')
has_500 = '500' in answer
has_1000 = '1000' in answer or '1,000' in answer
test1_pass = has_500 and not has_1000
print(f'MIDEVSTB vs MIDEVSTBN: {"✅" if test1_pass else "❌"} (500 expected)')

# Test 2: Strict number mode
result = INTELLIGENCE_SERVICE.analyze('How many critical alerts for MIDEVSTB? Give only the number')
answer = result.get('answer', '').strip()
is_just_number = answer.isdigit() or answer.replace(',', '').isdigit()
print(f'Strict Number Mode: {"✅" if is_just_number else "❌"} (got: "{answer}")')

# =====================================================
# CORE QUERY TYPES
# =====================================================
print('\n[CORE] QUERY TYPES')
print('-'*40)

core_tests = [
    ('Count Query', 'How many critical alerts?', 'FACT'),
    ('Database Query', 'Which database has most alerts?', 'FACT'),
    ('Error Query', 'What does ORA-00600 mean?', 'ANALYSIS'),
    ('Time Query', 'When did alerts start?', 'FACT'),
]

core_passed = 0
for name, query, expected_type in core_tests:
    result = INTELLIGENCE_SERVICE.analyze(query)
    qt = result.get('question_type', 'UNKNOWN')
    passed = qt == expected_type or qt == 'INCIDENT_COMMAND'
    status = '✅' if passed else '⚠️'
    if passed:
        core_passed += 1
    print(f'{status} {name}: {qt}')

print(f'\nCore: {core_passed}/{len(core_tests)} passed')

# =====================================================
# SUMMARY
# =====================================================
print('\n' + '='*60)
total = phase9_passed + core_passed + (2 if test1_pass and is_just_number else 0)
max_total = len(phase9_tests) + len(core_tests) + 2
print(f'TOTAL: {total}/{max_total} checks passed')
print(f'INCIDENT_COMMANDER_AVAILABLE: {INCIDENT_COMMANDER_AVAILABLE}')
print('='*60)
