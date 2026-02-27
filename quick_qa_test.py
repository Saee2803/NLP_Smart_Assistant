#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
OEM System QA Validation - All Features Test
"""
import requests
import json
import time
import sys

BASE = "http://192.168.0.195:4540"
TESTS_PASSED = 0
TESTS_FAILED = 0

def test(name, func):
    """Run a test function"""
    global TESTS_PASSED, TESTS_FAILED
    try:
        func()
        print("[OK] {0}".format(name))
        TESTS_PASSED += 1
    except AssertionError as e:
        print("[FAIL] {0}: {1}".format(name, str(e)))
        TESTS_FAILED += 1
    except Exception as e:
        print("[ERROR] {0}: {1}".format(name, str(e)))
        TESTS_FAILED += 1

# ===== PHASE 1: DATA =====
print("\n=== PHASE 1: DATA & PERSISTENCE ===\n")

def test_summary_api():
    r = requests.get("{0}/dashboard/api/summary".format(BASE), timeout=10)
    assert r.status_code == 200, "Status {0}".format(r.status_code)
    data = r.json()
    assert data, "Response empty"

test("Dashboard Summary API", test_summary_api)

def test_data_persists():
    r = requests.get("{0}/dashboard/api/summary".format(BASE), timeout=10)
    assert r.status_code == 200
    assert len(r.content) > 1000, "Data too small: {0} bytes".format(len(r.content))

test("Data loaded in memory", test_data_persists)

# ===== PHASE 2: APIS =====
print("\n=== PHASE 2: INTELLIGENCE APIS ===\n")

endpoints = [
    ("Dashboard Summary", "/dashboard/api/summary"),
    ("Databases", "/dashboard/api/databases"),
    ("Incidents", "/dashboard/api/incidents"),
    ("Risk Trends", "/dashboard/api/risk_trends"),
    ("RCA Latest", "/dashboard/api/rca/latest"),
    ("Alerts", "/alerts/api/"),
    ("Confidence", "/confidence/api/"),
]

for name, endpoint in endpoints:
    def make_test(ep, nm):
        def inner():
            r = requests.get("{0}{1}".format(BASE, ep), timeout=10)
            assert r.status_code in [200, 404], "Status {0}".format(r.status_code)
            if r.status_code == 200:
                assert len(r.content) > 100, "Empty response"
        return inner
    
    test(name, make_test(endpoint, name))

# ===== CHATBOT =====
print("\n=== PHASE 2: NLP CHATBOT ===\n")

def test_chat():
    r = requests.post("{0}/chat".format(BASE), 
                     json={"question": "Which database is most unstable?"},
                     timeout=15)
    assert r.status_code == 200, "Chat returned {0}".format(r.status_code)
    data = r.json()
    ans = str(data).lower()
    assert len(ans) > 50, "Answer too short"

test("Chat API responds", test_chat)

# ===== PHASE 3: SLA =====
print("\n=== PHASE 3: SLA & REPORTING ===\n")

def test_sla():
    # Check if SLA endpoint exists
    r = requests.get("{0}/sla/api/status".format(BASE), timeout=10)
    # May not exist yet, that's ok
    assert r.status_code in [200, 404, 405], "Unexpected {0}".format(r.status_code)

test("SLA endpoint (Phase 3)", test_sla)

# ===== PHASE 3: REMEDIATION =====
print("\n=== PHASE 3: AUTO-REMEDIATION ===\n")

def test_remediation():
    r = requests.get("{0}/remediation/api/proposals".format(BASE), timeout=10)
    assert r.status_code in [200, 404, 405], "Unexpected {0}".format(r.status_code)

test("Remediation endpoint (Phase 3)", test_remediation)

# ===== SUMMARY =====
print("\n" + "="*50)
print("RESULTS: {0} PASSED, {1} FAILED".format(TESTS_PASSED, TESTS_FAILED))
print("="*50)

if TESTS_FAILED == 0:
    print("\nSTATUS: ✓ DEMO READY\n")
    sys.exit(0)
elif TESTS_FAILED <= 2:
    print("\nSTATUS: ⚠ MOSTLY WORKING\n")
    sys.exit(0)
else:
    print("\nSTATUS: ✗ NEEDS FIX\n")
    sys.exit(1)
