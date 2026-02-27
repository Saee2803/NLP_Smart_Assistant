"""
Test Intent Routing Gate

Verifies that ENTITY_COUNT and ENTITY_LIST intents:
1. Are detected correctly
2. Bypass alert analysis pipeline
3. Return direct factual answers
"""

import sys
sys.path.insert(0, '.')

from nlp_engine.oem_intent_engine import OEMIntentEngine


def test_intent_routing():
    """Test the intent routing gate."""
    engine = OEMIntentEngine()
    
    # Test cases: (question, expected_intent, should_bypass)
    test_cases = [
        # ENTITY_COUNT cases - MUST bypass alert analysis
        ("How many servers in OEM?", "ENTITY_COUNT", True),
        ("How many databases are monitored?", "ENTITY_COUNT", True),
        ("Count of databases", "ENTITY_COUNT", True),
        ("Total number of servers", "ENTITY_COUNT", True),
        ("How many dbs do we have?", "ENTITY_COUNT", True),
        ("How many targets are monitored?", "ENTITY_COUNT", True),
        
        # ENTITY_LIST cases - MUST bypass alert analysis
        ("List all databases", "ENTITY_LIST", True),
        ("Show all servers", "ENTITY_LIST", True),
        ("What are the databases?", "ENTITY_LIST", True),
        ("Which databases are monitored?", "ENTITY_LIST", True),
        ("Give me a list of all targets", "ENTITY_LIST", True),
        
        # Non-entity intents - should NOT bypass (use full pipeline)
        ("Why is FINDB failing?", "ROOT_CAUSE", False),
        ("What errors occurred after midnight?", "TIME_BASED", False),
        ("Will HRDB fail next?", "PREDICTIVE", False),
        ("What is the health status of PRODDB?", "HEALTH_STATUS", False),
    ]
    
    print("=" * 70)
    print("INTENT ROUTING GATE TEST")
    print("=" * 70)
    
    passed = 0
    failed = 0
    
    for question, expected_intent, should_bypass in test_cases:
        result = engine.classify(question)
        actual_intent = result["intent"]
        actual_bypass = result.get("bypass_alert_analysis", False)
        
        intent_match = actual_intent == expected_intent
        bypass_match = actual_bypass == should_bypass
        
        status = "✅ PASS" if (intent_match and bypass_match) else "❌ FAIL"
        
        if intent_match and bypass_match:
            passed += 1
        else:
            failed += 1
        
        print("\n{} Question: '{}'".format(status, question))
        print("   Expected: intent={}, bypass={}".format(expected_intent, should_bypass))
        print("   Actual:   intent={}, bypass={}".format(actual_intent, actual_bypass))
        
        if not intent_match:
            print("   ⚠️  Intent mismatch!")
        if not bypass_match:
            print("   ⚠️  Bypass flag mismatch!")
    
    print("\n" + "=" * 70)
    print("RESULTS: {} passed, {} failed".format(passed, failed))
    print("=" * 70)
    
    return failed == 0


if __name__ == "__main__":
    success = test_intent_routing()
    sys.exit(0 if success else 1)
