"""
Phase 7 Wiring Verification Script
Verifies that Phase 7 is properly wired to IntelligenceService
"""
from data_engine.data_fetcher import DataFetcher
from data_engine.global_cache import GLOBAL_DATA, set_system_ready
from services.intelligence_service import INTELLIGENCE_SERVICE, PHASE7_TRUST_AVAILABLE
from services.session_store import SessionStore

# Load data
print("Loading data...")
fetcher = DataFetcher()
data = fetcher.fetch({})
GLOBAL_DATA['alerts'] = data.get('alerts', [])
set_system_ready(True)
print(f"Loaded {len(GLOBAL_DATA['alerts']):,} alerts")

# Test queries
test_queries = [
    "how many critical alerts for MIDEVSTB",
    "how many warning alerts",
    "show me standby alerts",
    "which database has the most alerts",
]

print("\n" + "="*70)
print("Phase 7 Wiring Verification")
print("="*70)
print(f"PHASE7_TRUST_AVAILABLE: {PHASE7_TRUST_AVAILABLE}")
print()

all_passed = True

for q in test_queries:
    SessionStore.reset()
    result = INTELLIGENCE_SERVICE.analyze(q)
    phase7 = result.get('phase7', {})
    processed = phase7.get('phase7_processed', False)
    trust_score = phase7.get('trust_score', 'N/A')
    
    status = "✅" if processed else "❌"
    print(f"[{status}] {q[:50]:50} | Phase7: {processed}, Trust: {trust_score}")
    
    if not processed:
        all_passed = False

print("\n" + "="*70)
if all_passed:
    print("✅ All queries processed through Phase 7 Trust Engine")
else:
    print("❌ Some queries bypassed Phase 7")
print("="*70)
