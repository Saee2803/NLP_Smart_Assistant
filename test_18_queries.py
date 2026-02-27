"""
Test for the 18 problematic queries from screenshots
Verifies Data Awareness Layer and improved response quality
"""
import sys
sys.path.insert(0, '.')

from data_engine.data_fetcher import DataFetcher
from data_engine.global_cache import GLOBAL_DATA, set_system_ready
from services.intelligence_service import INTELLIGENCE_SERVICE, DATA_AWARENESS_AVAILABLE
from services.session_store import SessionStore


def load_test_data():
    """Load alert data for testing."""
    print("Loading test data...")
    fetcher = DataFetcher()
    data = fetcher.fetch({})
    GLOBAL_DATA['alerts'] = data.get('alerts', [])
    set_system_ready(True)
    print(f"Loaded {len(GLOBAL_DATA['alerts']):,} alerts")
    return len(GLOBAL_DATA['alerts']) > 0


def test_query(query, expected_keywords, should_not_contain=None):
    """Test a query and check for expected keywords in response."""
    SessionStore.reset()
    result = INTELLIGENCE_SERVICE.analyze(query)
    answer = result.get("answer", "")
    
    # Check expected keywords
    found = [kw for kw in expected_keywords if kw.lower() in answer.lower()]
    missing = [kw for kw in expected_keywords if kw.lower() not in answer.lower()]
    
    # Check should_not_contain
    unwanted = []
    if should_not_contain:
        unwanted = [kw for kw in should_not_contain if kw.lower() in answer.lower()]
    
    passed = len(found) >= len(expected_keywords) * 0.5 and len(unwanted) == 0
    
    return {
        "query": query,
        "passed": passed,
        "answer_preview": answer[:200] + "..." if len(answer) > 200 else answer,
        "found_keywords": found,
        "missing_keywords": missing,
        "unwanted_found": unwanted,
        "confidence": result.get("confidence", 0)
    }


def run_all_tests():
    """Run all 18 problematic queries."""
    if not load_test_data():
        print("Failed to load data")
        return False
    
    print(f"\nDATA_AWARENESS_AVAILABLE: {DATA_AWARENESS_AVAILABLE}")
    
    # Define test cases
    test_cases = [
        # Issue 1: Relationship query
        {
            "query": "Are these related to MIDEVSTB?",
            "expected": ["related", "standby", "MIDEVSTB"],
            "should_not": None
        },
        # Issue 2: Normality query
        {
            "query": "Is this alert volume normal for MIDEVSTB?",
            "expected": ["normal", "baseline", "threshold"],
            "should_not": None
        },
        # Issue 3: Patch query (should say data not available)
        {
            "query": "Did alerts increase after last patch?",
            "expected": ["not available", "patch"],
            "should_not": ["increased significantly", "yes"]  # Should NOT claim to know
        },
        # Issue 4: Apply lag query (should say metric not available)
        {
            "query": "What is the current apply lag in minutes?",
            "expected": ["not available", "lag"],
            "should_not": ["0 minutes", "normal lag"]  # Should NOT fabricate numbers
        },
        # Issue 5: Yesterday query
        {
            "query": "show alerts from yesterday only",
            "expected": ["yesterday", "alert"],
            "should_not": None
        },
        # Issue 6: Repeated warnings query
        {
            "query": "Why are MIDEVSTB warnings repeated?",
            "expected": ["repeat"],
            "should_not": None
        },
        # Issue 7: Count only - STRICT NUMBER MODE returns only the number
        {
            "query": "How many CRITICAL alerts exist for MIDEVSTB? Give only the number",
            "expected": ["165837"],
            "should_not": ["alert", "for"]  # Should NOT have extra text
        },
        # Issue 9: One issue or many
        {
            "query": "We have 649,769 critical alerts — is this one big issue or many issues?",
            "expected": ["issue", "pattern"],
            "should_not": None
        },
        # Issue 10: Which error most
        {
            "query": "Which error is causing most of the alerts?",
            "expected": ["ORA", "error"],
            "should_not": None
        },
        # Issue 12: Worried query
        {
            "query": "Should I be worried right now?",
            "expected": ["worried", "recommendation"],
            "should_not": None
        },
        # Issue 13: Failure prediction
        {
            "query": "Which database is most likely to fail next?",
            "expected": ["database", "risk", "critical"],
            "should_not": None
        },
        # Issue 14: Ignore consequences
        {
            "query": "What happens if we ignore these alerts?",
            "expected": ["ignore", "consequence"],
            "should_not": None
        },
        # Issue 16: Evidence query
        {
            "query": "What evidence supports this being a CRITICAL risk?",
            "expected": ["evidence", "critical"],
            "should_not": None
        },
        # Issue 17: Manager explanation
        {
            "query": "Explain this to a manager",
            "expected": ["summary", "impact", "recommendation"],
            "should_not": ["ORA-600", "trace"]  # Should be non-technical
        },
        # Issue 18: Senior DBA explanation
        {
            "query": "Explain this like you're talking to another senior DBA",
            "expected": ["ORA", "trace", "check"],
            "should_not": None
        },
    ]
    
    print("\n" + "="*70)
    print("TESTING 18 PROBLEMATIC QUERIES")
    print("="*70)
    
    passed = 0
    failed = 0
    
    for i, tc in enumerate(test_cases, 1):
        result = test_query(
            tc["query"],
            tc["expected"],
            tc.get("should_not")
        )
        
        status = "✅" if result["passed"] else "❌"
        print(f"\n{status} Query {i}: {tc['query'][:50]}...")
        print(f"   Confidence: {result['confidence']}")
        print(f"   Found: {result['found_keywords']}")
        if result["missing_keywords"]:
            print(f"   Missing: {result['missing_keywords']}")
        if result["unwanted_found"]:
            print(f"   ⚠️ Unwanted: {result['unwanted_found']}")
        print(f"   Preview: {result['answer_preview'][:100]}...")
        
        if result["passed"]:
            passed += 1
        else:
            failed += 1
    
    print("\n" + "="*70)
    print(f"RESULTS: {passed} PASSED, {failed} FAILED")
    print("="*70)
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
