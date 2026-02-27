"""
Terminal vs Dashboard Output Comparison
Check if both are showing same results
"""
import requests
from services.nlp_orchestrator import process_query

print('='*70)
print('TERMINAL vs DASHBOARD OUTPUT COMPARISON')
print('='*70)

test_cases = [
    ('how many warning alerts?', 18, 'WARNING'),
    ('show only warnings', 18, 'WARNING'),
    ('show all critical alerts', 650764, 'CRITICAL'),
    ('show alerts excluding warning', 650764, 'CRITICAL'),
    ('which database has the most alerts?', None, None),
]

all_match = True

for query, expected_count, expected_sev in test_cases:
    print(f'\nQuery: "{query}"')
    print('-'*50)
    
    # TERMINAL (direct function call)
    t_result = process_query(query, f'terminal_{hash(query)}')
    t_count = t_result.get('result_count', 0)
    t_sev = t_result.get('entities', {}).get('severity')
    t_intent = t_result.get('intent')
    
    print(f'TERMINAL: Intent={t_intent}, Severity={t_sev}, Count={t_count}')
    
    # DASHBOARD (API call)
    try:
        resp = requests.post(
            'http://localhost:8000/chat',
            json={'message': query, 'new_conversation': True},
            timeout=15
        )
        d_result = resp.json()
        d_reply = d_result.get('reply', '')
        
        # Extract count from reply
        import re
        count_match = re.search(r'\*\*(\d+(?:,\d+)?)\*\*', d_reply)
        d_count = int(count_match.group(1).replace(',', '')) if count_match else 0
        
        print(f'DASHBOARD: Reply="{d_reply[:60]}..."')
        print(f'           Extracted count={d_count}')
        
        # Compare
        if expected_count:
            t_ok = t_count == expected_count
            d_ok = d_count == expected_count
            match = t_ok and d_ok
        else:
            # For MAX_DATABASE_QUERY, just check intent
            t_ok = t_intent == 'MAX_DATABASE_QUERY'
            d_ok = 'MIDEVSTBN' in d_reply or 'database' in d_reply.lower()
            match = t_ok and d_ok
        
        if match:
            print('STATUS: ✅ MATCH')
        else:
            print(f'STATUS: ❌ MISMATCH (Terminal OK: {t_ok}, Dashboard OK: {d_ok})')
            all_match = False
            
    except Exception as e:
        print(f'DASHBOARD ERROR: {e}')
        all_match = False

print('\n' + '='*70)
print('OVERALL:', '✅ ALL MATCH' if all_match else '❌ MISMATCH FOUND')
print('='*70)
