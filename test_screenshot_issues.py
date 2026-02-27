"""Test the issues shown in the user's screenshots."""
import requests

queries = [
    ('give me ONLY the count of CRITICAL alerts for MIDEVSTB', 'Should show ONLY 649,769'),
    ('show CRITICAL alerts 11 to 20 for MIDEVSTBN', 'Should show alerts 11-20'),
    ('compare total vs critical alerts for both databases', 'Should show comparison table'),
    ('show standby alerts summary only', 'Should show standby count per DB'),
    ('group alerts by error code', 'Should group by ORA codes'),
    ('top 3 alert types per database', 'Should show top 3 types per DB'),
]

print('='*60)
print('TESTING SCREENSHOT ISSUES')
print('='*60)

for q, expected in queries:
    print(f'\nQuery: {q}')
    print(f'Expected: {expected}')
    print('-'*50)
    try:
        r = requests.post('http://localhost:8000/chat', json={'message': q})
        reply = r.json().get('reply', 'N/A')
        # Show first 400 chars
        print(f'Reply: {reply[:400]}')
        if len(reply) > 400:
            print('...(truncated)')
    except Exception as e:
        print(f'ERROR: {e}')
    print()

print('='*60)
print('TEST COMPLETE')
print('='*60)
