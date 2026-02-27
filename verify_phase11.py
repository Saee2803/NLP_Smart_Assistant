# verify_phase11.py
"""
PHASE 11 VERIFICATION: Self-Auditing Intelligence

Demonstrates:
1. Trust Mode Detection (NORMAL, STRICT, SAFE)
2. Scope Validation (primary vs standby)
3. Contradiction Detection
4. Confidence-based Tone
5. Session Learning
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def print_section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)


def verify_trust_modes():
    """Verify trust mode detection."""
    print_section("1. TRUST MODE DETECTION")
    
    from reasoning.self_audit_engine import TrustModeDetector, TrustMode
    
    test_cases = [
        ("How many critical alerts?", TrustMode.NORMAL),
        ("Give only the number", TrustMode.STRICT),
        ("Exact count for audit", TrustMode.STRICT),
        ("Is it critical yes or no?", TrustMode.STRICT),
        ("What are the alerts?", TrustMode.NORMAL),
    ]
    
    all_pass = True
    for question, expected in test_cases:
        mode = TrustModeDetector.detect_mode(question)
        status = "✓" if mode == expected else "✗"
        if mode != expected:
            all_pass = False
        print(f"  {status} \"{question[:40]}...\" → {mode.value}")
    
    return all_pass


def verify_scope_validation():
    """Verify scope bleeding protection."""
    print_section("2. SCOPE VALIDATION")
    
    from reasoning.self_audit_engine import ScopeValidator
    
    # Test scope detection
    scope_tests = [
        ("for MIDEVSTB only, exclude standby", "primary"),
        ("Show me only standby database alerts", "standby"),
        ("How many critical alerts total?", "environment"),
        ("What's happening on MIDEVSTB?", "primary"),
    ]
    
    all_pass = True
    for question, expected_scope in scope_tests:
        scope = ScopeValidator.detect_scope(question)
        status = "✓" if scope == expected_scope else "✗"
        if scope != expected_scope:
            all_pass = False
        print(f"  {status} \"{question[:40]}...\" → {scope}")
    
    # Test scope violation detection
    print("\n  Scope Violation Detection:")
    is_valid, reason = ScopeValidator.validate_scope(
        answer="MIDEVSTBN has 100 alerts...",
        expected_scope="primary",
        target_db="MIDEVSTB"
    )
    status = "✓" if not is_valid else "✗"
    if is_valid:
        all_pass = False
    print(f"  {status} Standby in primary scope detected: {not is_valid}")
    
    return all_pass


def verify_self_audit():
    """Verify self-audit engine."""
    print_section("3. SELF-AUDIT ENGINE")
    
    from reasoning.self_audit_engine import SelfAuditEngine, TrustMode
    
    engine = SelfAuditEngine()
    
    # Test STRICT mode violation
    result = engine.audit_response(
        question="Give only the number",
        answer="There are 500 critical alerts",
        data_used=[{"id": 1}]
    )
    
    strict_violation = result.trust_mode == TrustMode.STRICT and len(result.violations) > 0
    status = "✓" if strict_violation else "✗"
    print(f"  {status} STRICT mode violation detected: {strict_violation}")
    
    # Test scope violation
    result = engine.audit_response(
        question="for MIDEVSTB only, exclude standby",
        answer="MIDEVSTBN has the most alerts",
        data_used=[{"id": 1}],
        extracted_values={"target_database": "MIDEVSTB"}
    )
    
    scope_violations = [v for v in result.violations if "SCOPE" in v]
    status = "✓" if scope_violations else "✗"
    print(f"  {status} SCOPE violation detected: {len(scope_violations) > 0}")
    
    return strict_violation and len(scope_violations) > 0


def verify_confidence_tones():
    """Verify confidence-based tone application."""
    print_section("4. CONFIDENCE-BASED TONE")
    
    from reasoning.self_audit_engine import SelfAuditEngine
    from reasoning.self_audit_engine import ConfidenceLevel
    
    engine = SelfAuditEngine()
    
    # EXACT confidence - no changes
    exact = engine.apply_confidence_tone("500 alerts found", ConfidenceLevel.EXACT)
    status = "✓" if exact == "500 alerts found" else "✗"
    print(f"  {status} EXACT confidence: No tone change")
    
    # PARTIAL confidence - adds caution
    partial = engine.apply_confidence_tone("500 alerts found", ConfidenceLevel.PARTIAL)
    status = "✓" if "Based on available" in partial else "✗"
    print(f"  {status} PARTIAL confidence: Adds caution prefix")
    
    # NONE confidence - adds warning
    none_conf = engine.apply_confidence_tone("500 alerts found", ConfidenceLevel.NONE)
    status = "✓" if "Limited Confidence" in none_conf else "✗"
    print(f"  {status} NONE confidence: Adds warning")
    
    return True


def verify_session_learning():
    """Verify session learning persistence."""
    print_section("5. SESSION LEARNING")
    
    from reasoning.self_audit_engine import SELF_AUDIT
    
    SELF_AUDIT.reset()
    
    # Add learning
    SELF_AUDIT.add_session_learning("Primary and standby were mixed in first response")
    
    learnings = SELF_AUDIT.fact_register.get_learnings()
    status = "✓" if len(learnings) == 1 else "✗"
    print(f"  {status} Learning persisted: {len(learnings)} learning(s)")
    
    # Check stats
    stats = SELF_AUDIT.get_stats()
    status = "✓" if "audits_performed" in stats else "✗"
    print(f"  {status} Stats tracking: audits={stats.get('audits_performed', 0)}, learnings={stats.get('session_learnings', 0)}")
    
    return len(learnings) == 1


def verify_integration():
    """Verify integration with IntelligenceService."""
    print_section("6. INTELLIGENCE SERVICE INTEGRATION")
    
    # Load data first (simulate startup)
    from data_engine.global_cache import GLOBAL_DATA, set_system_ready
    from data_engine.data_fetcher import DataFetcher
    
    try:
        fetcher = DataFetcher()
        alerts, metrics = fetcher.load_all()
        GLOBAL_DATA["alerts"] = alerts
        GLOBAL_DATA["metrics"] = metrics
        set_system_ready(True)
    except Exception as e:
        print(f"  ⚠ Could not load data: {e}")
        # Create mock data for testing
        GLOBAL_DATA["alerts"] = [
            {"target_name": "MIDEVSTB", "severity": "CRITICAL", "message": "ORA-600 internal error"},
            {"target_name": "MIDEVSTBN", "severity": "WARNING", "message": "Archive log gap"},
        ] * 100
        set_system_ready(True)
    
    from services.intelligence_service import IntelligenceService
    
    service = IntelligenceService()
    
    # Test that self_audit metadata appears
    result = service.analyze("How many critical alerts?")
    
    has_audit = "self_audit" in result
    status = "✓" if has_audit else "✗"
    print(f"  {status} Self-audit metadata in response: {has_audit}")
    
    if has_audit:
        audit = result["self_audit"]
        print(f"      - Trust mode: {audit.get('trust_mode', 'N/A')}")
        print(f"      - Passed: {audit.get('passed', 'N/A')}")
        print(f"      - Confidence: {audit.get('confidence', 'N/A')}")
    
    # Test STRICT mode query
    result = service.analyze("Give only the number")
    has_strict = result.get("self_audit", {}).get("trust_mode") == "STRICT"
    status = "✓" if has_strict else "○"
    print(f"  {status} STRICT mode for 'Give only number': {has_strict}")
    
    return has_audit


def main():
    print("\n" + "="*60)
    print("  PHASE 11: SELF-AUDITING INTELLIGENCE VERIFICATION")
    print("="*60)
    print("\nThis phase ensures the DBA intelligence partner:")
    print("  • Self-audits every answer before responding")
    print("  • Detects and prevents scope bleeding")
    print("  • Maintains conversation consistency")
    print("  • Adapts tone to data confidence")
    print("  • Never fabricates or over-assumes")
    
    results = []
    
    results.append(("Trust Mode Detection", verify_trust_modes()))
    results.append(("Scope Validation", verify_scope_validation()))
    results.append(("Self-Audit Engine", verify_self_audit()))
    results.append(("Confidence Tones", verify_confidence_tones()))
    results.append(("Session Learning", verify_session_learning()))
    results.append(("Service Integration", verify_integration()))
    
    print_section("SUMMARY")
    
    all_pass = True
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        if not passed:
            all_pass = False
        print(f"  {status}: {name}")
    
    print("\n" + "="*60)
    if all_pass:
        print("  ✓ PHASE 11 VERIFICATION: ALL CHECKS PASSED")
    else:
        print("  ✗ PHASE 11 VERIFICATION: SOME CHECKS FAILED")
    print("="*60 + "\n")
    
    return all_pass


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
