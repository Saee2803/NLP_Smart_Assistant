#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test script to validate all fixes for OEM Incident Intelligence System
"""

import sys
import os
from datetime import datetime, timedelta

# Add project to path
sys.path.insert(0, os.path.dirname(__file__))

def test_incident_aggregator():
    """Test 1: Verify time-window based incident aggregation works"""
    print("\n[TEST 1] Incident Aggregator - Time Window Logic")
    print("=" * 60)
    
    from incident_engine.incident_aggregator import IncidentAggregator
    
    # TEST A: Time window behavior
    print("\nTest A: Time window aggregation (should be 2 incidents)")
    alerts = [
        {"target": "DB1", "issue_type": "ERROR", "severity": "CRITICAL", "time": datetime(2025, 1, 1, 10, 0, 0)},
        {"target": "DB1", "issue_type": "ERROR", "severity": "CRITICAL", "time": datetime(2025, 1, 1, 10, 5, 0)},  # 5 min gap
        {"target": "DB1", "issue_type": "ERROR", "severity": "CRITICAL", "time": datetime(2025, 1, 1, 10, 20, 0)},  # 15 min gap
    ]
    
    agg = IncidentAggregator(alerts)
    incidents = agg.build_incidents()
    
    print("  Input: 3 alerts, same target+issue+severity")
    print("  Gaps: 5 min (same incident), 15 min (new incident)")
    print("  Output: {} incidents".format(len(incidents)))
    
    assert len(incidents) == 2, "Expected 2 incidents, got {}".format(len(incidents))
    assert incidents[0]['count'] == 2, "First incident should have count=2"
    assert incidents[1]['count'] == 1, "Second incident should have count=1"
    
    print("  PASS: Correctly separated by time window")
    
    # TEST B: Different targets
    print("\nTest B: Different targets (should be separate incidents)")
    alerts2 = [
        {"target": "DB1", "issue_type": "ERROR", "severity": "CRITICAL", "time": datetime(2025, 1, 1, 10, 0, 0)},
        {"target": "DB2", "issue_type": "ERROR", "severity": "CRITICAL", "time": datetime(2025, 1, 1, 10, 0, 0)},
    ]
    
    agg2 = IncidentAggregator(alerts2)
    incidents2 = agg2.build_incidents()
    
    print("  Input: 2 alerts, different targets")
    print("  Output: {} incidents".format(len(incidents2)))
    
    assert len(incidents2) == 2, "Expected 2 incidents, got {}".format(len(incidents2))
    print("  PASS: Different targets create separate incidents")
    
    print("\nPASS: All time-window tests passed")
    return True


def test_startup_flow():
    """Test 2: Verify full startup flow with real data"""
    print("\n[TEST 2] Full Startup Flow")
    print("=" * 60)
    
    from data_engine.data_fetcher import DataFetcher
    from incident_engine.metric_alert_validator import MetricAlertValidator
    from incident_engine.risk_trend_analyzer import RiskTrendAnalyzer
    
    print("Loading OEM data...")
    
    try:
        fetcher = DataFetcher()
        data = fetcher.fetch({})
        
        alerts = data.get("alerts", [])
        metrics = data.get("metrics", [])
        incidents = data.get("incidents", [])
        
        print("[OK] Alerts loaded: {}".format(len(alerts)))
        print("[OK] Metrics loaded: {}".format(len(metrics)))
        print("[OK] Incidents built: {}".format(len(incidents)))
        
        # Verify incident count is reasonable
        assert len(incidents) > 100, "Expected 100+ incidents, got {}. Time-window fix may not be working.".format(len(incidents))
        print("[OK] Incident count is reasonable ({}+ incidents)".format(len(incidents)))
        
        # Validate alerts
        validator = MetricAlertValidator(alerts, metrics)
        validated_alerts = validator.validate()
        print("[OK] Validations computed: {}".format(len(validated_alerts)))
        
        # Risk trends - MUST pass both alerts and incidents
        trend_analyzer = RiskTrendAnalyzer(alerts, incidents)
        risk_trends = trend_analyzer.build_trends()
        print("[OK] Risk trends computed: {}".format(len(risk_trends)))
        
        assert len(risk_trends) > 0, "Risk trends should not be empty"
        
        # Verify incidents have expected structure
        sample = incidents[0]
        required_keys = ['target', 'issue_type', 'severity', 'count', 'first_seen', 'last_seen']
        for key in required_keys:
            assert key in sample, "Incident missing key: {}".format(key)
        
        print("\nSample incidents:")
        for i in incidents[:3]:
            print("  - Target: {}, Issue: {}, Count: {}, Severity: {}".format(
                i.get('target'), i.get('issue_type'), i.get('count'), i.get('severity')))
        
        print("\nPASS: Full startup flow works correctly")
        return True
        
    except Exception as e:
        print("FAIL: {}".format(str(e)))
        import traceback
        traceback.print_exc()
        return False


def test_risk_trend_analyzer():
    """Test 3: Verify RiskTrendAnalyzer works with both alerts and incidents"""
    print("\n[TEST 3] Risk Trend Analyzer")
    print("=" * 60)
    
    from incident_engine.risk_trend_analyzer import RiskTrendAnalyzer
    
    # Create test data
    alerts = [
        {"target": "DB1", "severity": "CRITICAL", "time": datetime.now() - timedelta(days=1)},
        {"target": "DB1", "severity": "WARNING", "time": datetime.now()},
    ]
    
    incidents = [
        {"target": "DB1", "issue_type": "ERROR", "first_seen": datetime.now() - timedelta(days=1), "last_seen": datetime.now()},
    ]
    
    analyzer = RiskTrendAnalyzer(alerts, incidents)
    trends = analyzer.build_trends()
    
    print("Generated trends: {}".format(len(trends)))
    assert len(trends) > 0, "Should have at least 1 trend"
    
    trend = trends[0]
    print("Sample trend:")
    print("  - Target: {}".format(trend.get('target')))
    print("  - Trend: {}".format(trend.get('trend')))
    print("  - Risk Score: {}".format(trend.get('risk_score')))
    
    print("\nPASS: RiskTrendAnalyzer works correctly")
    return True


def main():
    print("\n" + "=" * 60)
    print("OEM INCIDENT INTELLIGENCE SYSTEM - FIX VALIDATION")
    print("=" * 60)
    
    tests = [
        ("Incident Aggregator", test_incident_aggregator),
        ("Risk Trend Analyzer", test_risk_trend_analyzer),
        ("Full Startup Flow", test_startup_flow),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print("\nFAIL: {} - {}".format(name, str(e)))
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    for name, result in results:
        status = "PASS" if result else "FAIL"
        print("[{}] {}".format(status, name))
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    print("\nTotal: {}/{}".format(passed, total))
    
    if passed == total:
        print("\nALL TESTS PASSED!")
        return 0
    else:
        print("\nSOME TESTS FAILED!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
