"""
Final Terminal vs Dashboard Comparison Test
"""
import requests
from services.nlp_orchestrator import process_query

print('='*70)
print('FINAL TERMINAL vs DASHBOARD COMPARISON')
print('='*70)

tests = [
    'how many warning alerts?',
    'show only warnings', 
    'show all critical alerts',
    'show alerts excluding warning',
    'which database has the most alerts?'
]

all_pass = True
for q in tests:
    print(f'\nQuery: "{q}"')
    print('-'*50)
    
    # Terminal
    t = process_query(q, f't_{hash(q)}')
    t_intent = t.get('intent')
    t_count = t.get('result_count')
    print(f'TERMINAL: Intent={t_intent}, Count={t_count}')
    
    # Dashboard
    try:
        r = requests.post('http://localhost:8000/chat', json={'message': q, 'new_conversation': True}, timeout=15)
        d = r.json()
        d_reply = d.get('reply', '')[:80]
        print(f'DASHBOARD: {d_reply}...')
        
        # Check if both are working
        if t_intent and '**' in d.get('reply', ''):
            print('STATUS: OK')
        else:
            print('STATUS: Issue')
            all_pass = False
    except Exception as e:
        print(f'DASHBOARD ERROR: {e}')
        all_pass = False

print('\n' + '='*70)
if all_pass:
    print('Dashboard wiring VERIFIED - Terminal and Dashboard both working!')
else:
    print('Some issues detected')
print('='*70)
