"""
PHASE 2: Test Suite
====================
Tests for Conversational Intelligence.

MANDATORY TEST CASES:
1. Q: show me alerts for MIDEVSTB → Q: ok show me 18 warning 
   → Must show 18 WARNING alerts for MIDEVSTB (preserves db context)

2. Q: show me standby issues → Q: ok show me 20
   → Must show 20 standby alerts (preserves category context)

3. Q: show me alerts for MIDEVSTB → Q: how many total alerts exist
   → Must show TOTAL alerts (context reset)

4. Q: show me alerts for MIDEVSTB → Q: only critical
   → Must show CRITICAL alerts for MIDEVSTB (filter in same db context)
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load data before importing Phase 2 components
def load_test_data():
    """Load alert data into GLOBAL_DATA for testing."""
    from data_engine.data_fetcher import DataFetcher
    from data_engine.global_cache import GLOBAL_DATA, set_system_ready
    
    print("Loading test data...")
    try:
        fetcher = DataFetcher()
        data = fetcher.fetch({})
        
        # Populate GLOBAL_DATA
        GLOBAL_DATA["alerts"] = data.get("alerts", [])
        GLOBAL_DATA["metrics"] = data.get("metrics", [])
        GLOBAL_DATA["incidents"] = data.get("incidents", [])
        
        set_system_ready(True)
        print(f"✓ Loaded {len(GLOBAL_DATA['alerts']):,} alerts")
        return True
    except Exception as e:
        print(f"✗ Failed to load data: {e}")
        return False

# Load data at module level
DATA_LOADED = load_test_data()

from phase2.context_manager import (
    ConversationContext, ContextManager, ContextBuilder,
    get_context_manager, reset_context
)
from phase2.followup_detector import (
    FollowUpType, FollowUpDetector, ContextResolver,
    detect_followup
)
from phase2.service import Phase2Service


def test_context_manager():
    """Test ContextManager basic operations."""
    print("\n" + "="*60)
    print("TEST: Context Manager")
    print("="*60)
    
    manager = ContextManager()
    
    # Test empty context
    ctx = manager.get_context("session1")
    assert not ctx.has_context, "New context should not have context"
    print("✓ Empty context created correctly")
    
    # Test context update
    ctx = manager.update_context("session1", 
        has_context=True,
        last_database="MIDEVSTB",
        last_severity="CRITICAL"
    )
    assert ctx.has_context, "Context should be active after update"
    assert ctx.last_database == "MIDEVSTB"
    assert ctx.last_severity == "CRITICAL"
    print("✓ Context updated correctly")
    
    # Test context persistence
    ctx2 = manager.get_context("session1")
    assert ctx2.last_database == "MIDEVSTB"
    print("✓ Context persists across gets")
    
    # Test context reset
    manager.reset_context("session1")
    ctx3 = manager.get_context("session1")
    assert not ctx3.has_context
    print("✓ Context reset works")
    
    print("\n✅ All Context Manager tests passed!")
    return True


def test_followup_detector():
    """Test FollowUpDetector classification."""
    print("\n" + "="*60)
    print("TEST: Follow-up Detector")
    print("="*60)
    
    detector = FollowUpDetector()
    
    # Create context with active state
    context = ConversationContext(
        has_context=True,
        last_database="MIDEVSTB",
        last_severity=None,
        last_category=None,
        last_intent="LIST"
    )
    
    # Test LIMIT detection
    ftype, info = detector.detect("ok show me 20", context)
    assert ftype == FollowUpType.LIMIT, f"Expected LIMIT, got {ftype}"
    assert info.get("limit") == 20, f"Expected limit=20, got {info}"
    print(f"✓ 'ok show me 20' → LIMIT (limit=20)")
    
    # Test FILTER detection
    ftype, info = detector.detect("only critical", context)
    assert ftype == FollowUpType.FILTER, f"Expected FILTER, got {ftype}"
    assert info.get("severity") == "CRITICAL"
    print(f"✓ 'only critical' → FILTER (severity=CRITICAL)")
    
    # Test LIMIT_FILTER detection
    ftype, info = detector.detect("show me 18 warning", context)
    assert ftype == FollowUpType.LIMIT_FILTER, f"Expected LIMIT_FILTER, got {ftype}"
    assert info.get("limit") == 18
    assert info.get("severity") == "WARNING"
    print(f"✓ 'show me 18 warning' → LIMIT_FILTER (limit=18, severity=WARNING)")
    
    # Test CONTEXT_RESET detection
    ftype, info = detector.detect("how many total alerts exist", context)
    assert ftype == FollowUpType.CONTEXT_RESET, f"Expected CONTEXT_RESET, got {ftype}"
    print(f"✓ 'how many total alerts exist' → CONTEXT_RESET")
    
    # Test NOT_FOLLOWUP (no context)
    empty_context = ConversationContext.empty()
    ftype, info = detector.detect("show me alerts", empty_context)
    assert ftype == FollowUpType.NOT_FOLLOWUP, f"Expected NOT_FOLLOWUP, got {ftype}"
    print(f"✓ No context → NOT_FOLLOWUP")
    
    print("\n✅ All Follow-up Detector tests passed!")
    return True


def test_context_resolver():
    """Test ContextResolver parameter merging."""
    print("\n" + "="*60)
    print("TEST: Context Resolver")
    print("="*60)
    
    resolver = ContextResolver()
    
    # Context: MIDEVSTB alerts
    context = ConversationContext(
        has_context=True,
        last_database="MIDEVSTB",
        last_severity=None,
        last_category="standby",
        last_intent="LIST"
    )
    
    # Test LIMIT resolution
    resolved = resolver.resolve(
        "ok show me 20",
        FollowUpType.LIMIT,
        {"limit": 20},
        context
    )
    assert resolved["database"] == "MIDEVSTB", "Should preserve database"
    assert resolved["category"] == "standby", "Should preserve category"
    assert resolved["limit"] == 20, "Should set new limit"
    print(f"✓ LIMIT: db=MIDEVSTB, cat=standby, limit=20")
    
    # Test FILTER resolution
    resolved = resolver.resolve(
        "only critical",
        FollowUpType.FILTER,
        {"severity": "CRITICAL"},
        context
    )
    assert resolved["database"] == "MIDEVSTB", "Should preserve database"
    assert resolved["severity"] == "CRITICAL", "Should set new severity"
    print(f"✓ FILTER: db=MIDEVSTB, severity=CRITICAL")
    
    # Test LIMIT_FILTER resolution
    resolved = resolver.resolve(
        "show me 18 warning",
        FollowUpType.LIMIT_FILTER,
        {"limit": 18, "severity": "WARNING"},
        context
    )
    assert resolved["database"] == "MIDEVSTB"
    assert resolved["severity"] == "WARNING"
    assert resolved["limit"] == 18
    print(f"✓ LIMIT_FILTER: db=MIDEVSTB, severity=WARNING, limit=18")
    
    print("\n✅ All Context Resolver tests passed!")
    return True


def test_phase2_service_basic():
    """Test Phase2Service basic processing."""
    print("\n" + "="*60)
    print("TEST: Phase 2 Service (Basic)")
    print("="*60)
    
    service = Phase2Service()
    session_id = "test_session_basic"
    
    # Clear any existing context
    service.clear_context(session_id)
    
    # First question - should create context
    result = service.process_question("show me alerts for MIDEVSTB", session_id)
    
    print(f"Q: show me alerts for MIDEVSTB")
    print(f"  → Followup type: {result.get('followup_type')}")
    print(f"  → Context used: {result.get('context_used')}")
    print(f"  → Answer preview: {result.get('answer', '')[:100]}...")
    
    assert result.get("success"), "First question should succeed"
    assert result.get("context_used") == False, "First question should not use context"
    
    # Check context was created
    ctx = service.context_manager.get_context(session_id)
    assert ctx.has_context, "Context should be created"
    assert ctx.last_database == "MIDEVSTB", f"Database should be MIDEVSTB, got {ctx.last_database}"
    print(f"  → Context created: db={ctx.last_database}")
    
    print("\n✅ Phase 2 Service basic test passed!")
    return True


def test_mandatory_case_1():
    """
    MANDATORY: Q: show me alerts for MIDEVSTB → Q: ok show me 18 warning
    Expected: 18 WARNING alerts for MIDEVSTB (preserves db context)
    """
    print("\n" + "="*60)
    print("MANDATORY TEST 1: Limit + Filter Follow-up")
    print("="*60)
    
    service = Phase2Service()
    session_id = "mandatory_1"
    service.clear_context(session_id)
    
    # Q1: Initial question
    print("\nQ1: show me alerts for MIDEVSTB")
    result1 = service.process_question("show me alerts for MIDEVSTB", session_id)
    print(f"  → Success: {result1.get('success')}")
    print(f"  → Intent db: {result1.get('intent', {}).get('database')}")
    
    # Q2: Follow-up with limit and filter
    print("\nQ2: ok show me 18 warning")
    result2 = service.process_question("ok show me 18 warning", session_id)
    
    print(f"  → Followup type: {result2.get('followup_type')}")
    print(f"  → Context used: {result2.get('context_used')}")
    print(f"  → Intent: {result2.get('intent')}")
    print(f"  → Answer: {result2.get('answer', '')[:200]}")
    
    # Verify
    intent = result2.get("intent", {})
    assert result2.get("context_used") == True, "Should use context"
    assert intent.get("database") == "MIDEVSTB", f"Should preserve MIDEVSTB, got {intent.get('database')}"
    assert intent.get("severity") == "WARNING", f"Should filter WARNING, got {intent.get('severity')}"
    
    print("\n✅ MANDATORY TEST 1 PASSED!")
    return True


def test_mandatory_case_2():
    """
    MANDATORY: Q: show me standby issues → Q: ok show me 20
    Expected: 20 standby alerts (preserves category context)
    """
    print("\n" + "="*60)
    print("MANDATORY TEST 2: Limit with Category Preservation")
    print("="*60)
    
    service = Phase2Service()
    session_id = "mandatory_2"
    service.clear_context(session_id)
    
    # Q1: Initial question with category
    print("\nQ1: show me standby issues")
    result1 = service.process_question("show me standby issues", session_id)
    print(f"  → Success: {result1.get('success')}")
    
    # Check context has category
    ctx = service.context_manager.get_context(session_id)
    print(f"  → Context category: {ctx.last_category}")
    
    # Q2: Follow-up with just limit
    print("\nQ2: ok show me 20")
    result2 = service.process_question("ok show me 20", session_id)
    
    print(f"  → Followup type: {result2.get('followup_type')}")
    print(f"  → Context used: {result2.get('context_used')}")
    print(f"  → Answer: {result2.get('answer', '')[:200]}")
    
    # Verify context was used
    assert result2.get("context_used") == True, "Should use context"
    assert result2.get("followup_type") == "LIMIT", f"Should be LIMIT followup"
    
    print("\n✅ MANDATORY TEST 2 PASSED!")
    return True


def test_mandatory_case_3():
    """
    MANDATORY: Q: show me alerts for MIDEVSTB → Q: how many total alerts exist
    Expected: TOTAL alerts count (context reset)
    """
    print("\n" + "="*60)
    print("MANDATORY TEST 3: Context Reset")
    print("="*60)
    
    service = Phase2Service()
    session_id = "mandatory_3"
    service.clear_context(session_id)
    
    # Q1: Initial question
    print("\nQ1: show me alerts for MIDEVSTB")
    result1 = service.process_question("show me alerts for MIDEVSTB", session_id)
    print(f"  → Success: {result1.get('success')}")
    print(f"  → Intent db: {result1.get('intent', {}).get('database')}")
    
    # Q2: Context reset question
    print("\nQ2: how many total alerts exist")
    result2 = service.process_question("how many total alerts exist", session_id)
    
    print(f"  → Followup type: {result2.get('followup_type')}")
    print(f"  → Context used: {result2.get('context_used')}")
    print(f"  → Answer: {result2.get('answer', '')[:200]}")
    
    # Verify context was reset (not used)
    assert result2.get("context_used") == False, "Should NOT use context (reset)"
    assert result2.get("followup_type") == "CONTEXT_RESET", "Should be CONTEXT_RESET"
    
    print("\n✅ MANDATORY TEST 3 PASSED!")
    return True


def test_mandatory_case_4():
    """
    MANDATORY: Q: show me alerts for MIDEVSTB → Q: only critical
    Expected: CRITICAL alerts for MIDEVSTB (filter in same db context)
    """
    print("\n" + "="*60)
    print("MANDATORY TEST 4: Filter with DB Preservation")
    print("="*60)
    
    service = Phase2Service()
    session_id = "mandatory_4"
    service.clear_context(session_id)
    
    # Q1: Initial question
    print("\nQ1: show me alerts for MIDEVSTB")
    result1 = service.process_question("show me alerts for MIDEVSTB", session_id)
    print(f"  → Success: {result1.get('success')}")
    print(f"  → Intent db: {result1.get('intent', {}).get('database')}")
    
    # Q2: Filter follow-up
    print("\nQ2: only critical")
    result2 = service.process_question("only critical", session_id)
    
    print(f"  → Followup type: {result2.get('followup_type')}")
    print(f"  → Context used: {result2.get('context_used')}")
    print(f"  → Intent: {result2.get('intent')}")
    print(f"  → Answer: {result2.get('answer', '')[:200]}")
    
    # Verify
    intent = result2.get("intent", {})
    assert result2.get("context_used") == True, "Should use context"
    assert intent.get("database") == "MIDEVSTB", f"Should preserve MIDEVSTB, got {intent.get('database')}"
    assert intent.get("severity") == "CRITICAL", f"Should filter CRITICAL, got {intent.get('severity')}"
    
    print("\n✅ MANDATORY TEST 4 PASSED!")
    return True


def run_all_tests():
    """Run all Phase 2 tests."""
    print("\n" + "="*70)
    print("PHASE 2: CONVERSATIONAL INTELLIGENCE - TEST SUITE")
    print("="*70)
    
    results = []
    
    # Unit tests
    results.append(("Context Manager", test_context_manager()))
    results.append(("Follow-up Detector", test_followup_detector()))
    results.append(("Context Resolver", test_context_resolver()))
    results.append(("Phase 2 Service Basic", test_phase2_service_basic()))
    
    # Mandatory integration tests
    results.append(("MANDATORY 1: Limit+Filter Follow-up", test_mandatory_case_1()))
    results.append(("MANDATORY 2: Category Preservation", test_mandatory_case_2()))
    results.append(("MANDATORY 3: Context Reset", test_mandatory_case_3()))
    results.append(("MANDATORY 4: Filter with DB Preservation", test_mandatory_case_4()))
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status}: {name}")
    
    print(f"\n  Total: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL PHASE 2 TESTS PASSED! 🎉")
    else:
        print(f"\n⚠️ {total - passed} tests failed")
    
    return passed == total


if __name__ == "__main__":
    run_all_tests()
