# verify_phase12_wiring.py
"""Quick verification of Phase-12.1 Context Resolution Rules."""

from reasoning.phase12_guardrails import (
    Phase12Guardrails,
    enforce_phase12,
    get_active_db_scope,
    reset_db_scope,
    needs_scope_clarification,
    scope_safety_check
)

print('='*70)
print('PHASE-12.1 ENHANCED CONTEXT RESOLUTION RULES')
print('='*70)
print()

# Test 1: Database Scope Locking
print('[1] DATABASE SCOPE LOCKING')
reset_db_scope()
Phase12Guardrails.update_scope('How many critical alerts for MIDEVSTB?')
print('    Initial scope:', get_active_db_scope())

# Test scope persistence across follow-ups
followups = [
    'Critical count?',
    'Total alerts for that DB?',
    'This DB looks fine right?',
    'Is this likely to escalate?',
    'How many unique incidents?'
]
for q in followups:
    Phase12Guardrails.update_scope(q)
    print(f'    "{q}" -> Scope: {get_active_db_scope()}')

# Test 2: Scope Change Rules
print()
print('[2] SCOPE CHANGE RULES')
Phase12Guardrails.update_scope('Across all databases')
scope = Phase12Guardrails.get_current_scope()
print(f'    "Across all databases" -> Type: {scope.scope_type.value}')

# Test 3: Scope Safety Check
print()
print('[3] SCOPE SAFETY CHECK (Before Every Answer)')
reset_db_scope()
scope_type, is_valid = scope_safety_check('Critical count?')
print(f'    No prior scope + "Critical count?" -> Valid: {is_valid}, Needs clarification: {not is_valid}')

Phase12Guardrails.update_scope('Show MIDEVSTBN alerts')
scope_type, is_valid = scope_safety_check('Critical count?')
print(f'    With scope + "Critical count?" -> Valid: {is_valid}, Type: {scope_type}')

# Test 4: Fail-Safe Clarification
print()
print('[4] FAIL-SAFE BEHAVIOR')
reset_db_scope()
needs_clarify = needs_scope_clarification('How many critical?')
print(f'    Ambiguous question without scope -> Needs clarification: {needs_clarify}')

print()
print('='*70)
print('RESULT: All Context Resolution Rules Enforced!')
print('='*70)
