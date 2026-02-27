"""Test INTELLIGENCE_SERVICE directly without HTTP server"""
from services.intelligence_service import INTELLIGENCE_SERVICE, SYSTEM_READY, GLOBAL_DATA
from data_engine.data_fetcher import DataFetcher
from services.session_store import SessionStore

print('='*70)
print('DIRECT INTELLIGENCE_SERVICE TEST')
print('='*70)

# Load data manually
print('\nLoading data...')
fetcher = DataFetcher()
result = fetcher.fetch()

# Check what fetch returns
print(f'Fetch returned type: {type(result)}')
if isinstance(result, tuple):
    alerts, incidents, metrics = result
    print(f'Alerts: {len(alerts)}, Incidents: {len(incidents)}, Metrics: {len(metrics)}')
    GLOBAL_DATA['alerts'] = alerts
else:
    print(f'Unexpected return: {result}')
    alerts = []

SYSTEM_READY['ready'] = True
print(f'GLOBAL_DATA alerts: {len(GLOBAL_DATA.get("alerts", []))}')

# Test queries
queries = [
    'how many warning alerts',
    'show only warnings',
    'show alerts excluding warning',
    'show all critical alerts',
    'which database has the most alerts?'
]

print('\n' + '='*70)
print('QUERY TESTS')
print('='*70)

for q in queries:
    SessionStore.reset()
    result = INTELLIGENCE_SERVICE.analyze(q)
    answer = result.get('answer', 'N/A')
    print(f'\nQuery: {q}')
    print(f'Answer: {answer[:100]}...' if len(answer) > 100 else f'Answer: {answer}')

print('\n' + '='*70)
