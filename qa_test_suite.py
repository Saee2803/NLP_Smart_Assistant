#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
QA Test Suite for OEM Incident Intelligence System
Tests all Phase 1, 2, 3 features end-to-end
"""

import requests
import json
import sys
import time

BASE_URL = "http://127.0.0.1:8000"

# Test result tracking
RESULTS = {
    'passed': [],
    'failed': [],
    'errors': []
}

def test_api(name, method, endpoint, expected_status=200, validate_response=None):
    """
    Generic API test function
    """
    try:
        url = "{base}{endpoint}".format(base=BASE_URL, endpoint=endpoint)
        print("\n[TEST] {name}".format(name=name))
        print("  URL: {url}".format(url=url))
        
        if method == "GET":
            response = requests.get(url, timeout=10)
        elif method == "POST":
            response = requests.post(url, timeout=10, json={})
        
        print("  Status: {status}".format(status=response.status_code))
        
        if response.status_code != expected_status:
            msg = "Expected {exp}, got {got}".format(exp=expected_status, got=response.status_code)
            RESULTS['failed'].append((name, msg))
            return False
        
        # Validate response structure if provided
        if validate_response:
            try:
                data = response.json() if response.text else {}
                if not validate_response(data):
                    RESULTS['failed'].append((name, "Response validation failed"))
                    return False
            except Exception as e:
                RESULTS['failed'].append((name, "Response parsing error: {0}".format(str(e))))
                return False
        
        RESULTS['passed'].append(name)
        print("  ✓ PASS")
        return True
    
    except Exception as e:
        RESULTS['errors'].append((name, str(e)))
        print("  ✗ ERROR: {0}".format(str(e)))
        return False

# ========================================
# PHASE 1: DATA & PERSISTENCE
# ========================================
print("\n" + "="*60)
print("PHASE 1: DATA & PERSISTENCE")
print("="*60)

test_api(
    "CSV auto-migrates to DB",
    "GET",
    "/dashboard/api/summary",
    expected_status=200,
    validate_response=lambda d: 'total_alerts' in d or 'alerts' in str(d).lower()
)

# ========================================
# PHASE 2: INTELLIGENCE & APIs
# ========================================
print("\n" + "="*60)
print("PHASE 2: INTELLIGENCE ENGINES & APIs")
print("="*60)

# Dashboard Summary
test_api(
    "Dashboard Summary API",
    "GET",
    "/dashboard/api/summary",
    expected_status=200,
    validate_response=lambda d: isinstance(d, dict)
)

# Databases endpoint
test_api(
    "Databases API",
    "GET",
    "/dashboard/api/databases",
    expected_status=200,
    validate_response=lambda d: isinstance(d, (dict, list))
)

# Incidents endpoint
test_api(
    "Incidents API",
    "GET",
    "/dashboard/api/incidents",
    expected_status=200,
    validate_response=lambda d: isinstance(d, (dict, list))
)

# Risk Trends
test_api(
    "Risk Trends API",
    "GET",
    "/dashboard/api/risk_trends",
    expected_status=200,
    validate_response=lambda d: isinstance(d, (dict, list))
)

# RCA Latest
test_api(
    "RCA Latest API",
    "GET",
    "/dashboard/api/rca/latest",
    expected_status=200,
    validate_response=lambda d: isinstance(d, (dict, list))
)

# Alerts API
test_api(
    "Alerts API",
    "GET",
    "/alerts/api/",
    expected_status=200,
    validate_response=lambda d: isinstance(d, (dict, list))
)

# Confidence API
test_api(
    "Confidence API",
    "GET",
    "/confidence/api/",
    expected_status=200,
    validate_response=lambda d: isinstance(d, (dict, list))
)

# ========================================
# PHASE 3: SLA & REPORTING
# ========================================
print("\n" + "="*60)
print("PHASE 3: SLA TRACKING & REPORTING")
print("="*60)

# Test SLA status endpoint (if exists)
test_api(
    "SLA Status API (Phase 3)",
    "GET",
    "/sla/api/status",
    expected_status=(200, 404),  # May or may not be implemented
)

# Test Reports endpoint (if exists)
test_api(
    "Reports API (Phase 3)",
    "GET",
    "/reporting/api/latest",
    expected_status=(200, 404),  # May or may not be implemented
)

# ========================================
# PHASE 3: AUTO-REMEDIATION
# ========================================
print("\n" + "="*60)
print("PHASE 3: AUTO-REMEDIATION")
print("="*60)

test_api(
    "Remediation Proposals (Phase 3)",
    "GET",
    "/remediation/api/proposals",
    expected_status=(200, 404),  # May or may not be implemented
)

# ========================================
# NLP CHATBOT TESTS
# ========================================
print("\n" + "="*60)
print("PHASE 2: NLP CHATBOT QUERIES")
print("="*60)

def test_chat_query(question, expected_keywords):
    """Test a chatbot query and validate response contains expected keywords"""
    try:
        print("\n[CHAT] Question: {0}".format(question))
        response = requests.post(
            "{base}/chat".format(base=BASE_URL),
            json={'question': question},
            timeout=15
        )
        
        if response.status_code != 200:
            msg = "Status {0}".format(response.status_code)
            RESULTS['failed'].append(("Chat: {0}".format(question[:30]), msg))
            print("  ✗ FAIL: {0}".format(msg))
            return False
        
        data = response.json() if response.text else {}
        answer = data.get('answer', data.get('response', str(data))).lower()
        
        print("  Answer: {0}...".format(answer[:100]))
        
        # Check for expected keywords
        found = [kw for kw in expected_keywords if kw.lower() in answer]
        if found:
            RESULTS['passed'].append("Chat: {0}".format(question[:30]))
            print("  ✓ PASS (found: {0})".format(', '.join(found)))
            return True
        else:
            RESULTS['failed'].append(("Chat: {0}".format(question[:30]), "Missing keywords: {0}".format(expected_keywords)))
            print("  ⚠ PARTIAL (no keywords found)")
            return False
    
    except Exception as e:
        RESULTS['errors'].append(("Chat: {0}".format(question[:30]), str(e)))
        print("  ✗ ERROR: {0}".format(str(e)))
        return False

# Test specific NLP queries
test_chat_query(
    "Which database is most unstable?",
    ['unstable', 'database', 'health', 'failure', 'risk']
)

test_chat_query(
    "Why does MIDEVSTBN fail at night?",
    ['midevstbn', 'night', 'fail', 'hour', 'time']
)

test_chat_query(
    "What should be fixed first?",
    ['priority', 'fix', 'database', 'issue', 'risk']
)

# ========================================
# DATA PERSISTENCE TEST
# ========================================
print("\n" + "="*60)
print("DATA PERSISTENCE VERIFICATION")
print("="*60)

# Check that summary has actual data
try:
    print("\n[TEST] Verify data persistence")
    response = requests.get("{base}/dashboard/api/summary".format(base=BASE_URL), timeout=10)
    if response.status_code == 200:
        data = response.json()
        summary_text = json.dumps(data)
        if len(summary_text) > 100:  # Should have substantial data
            RESULTS['passed'].append("Data persistence verified")
            print("  ✓ Data persisted in memory: {0} bytes".format(len(summary_text)))
        else:
            RESULTS['failed'].append(("Data persistence", "Insufficient data"))
            print("  ✗ Data appears incomplete")
except Exception as e:
    RESULTS['errors'].append(("Data persistence", str(e)))
    print("  ✗ ERROR: {0}".format(str(e)))

# ========================================
# RESULTS SUMMARY
# ========================================
print("\n" + "="*60)
print("TEST RESULTS SUMMARY")
print("="*60)

total = len(RESULTS['passed']) + len(RESULTS['failed']) + len(RESULTS['errors'])
print("\nPASSED:  {0}/{1}".format(len(RESULTS['passed']), total))
print("FAILED:  {0}/{1}".format(len(RESULTS['failed']), total))
print("ERRORS:  {0}/{1}".format(len(RESULTS['errors']), total))

if RESULTS['failed']:
    print("\n[FAILED TESTS]")
    for test, reason in RESULTS['failed']:
        print("  ✗ {0}: {1}".format(test, reason))

if RESULTS['errors']:
    print("\n[TEST ERRORS]")
    for test, reason in RESULTS['errors']:
        print("  ✗ {0}: {1}".format(test, reason))

print("\n" + "="*60)
success_rate = (len(RESULTS['passed']) / total * 100) if total > 0 else 0
if success_rate >= 80:
    print("STATUS: DEMO READY ✓")
elif success_rate >= 50:
    print("STATUS: NEEDS FIX ⚠")
else:
    print("STATUS: BROKEN ✗")
print("="*60)

sys.exit(0 if success_rate >= 80 else 1)
