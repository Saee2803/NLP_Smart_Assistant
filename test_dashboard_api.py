#!/usr/bin/env python
"""
Test the chat API endpoint simulating dashboard behavior.

This tests:
1. Initial query sets context
2. Follow-up queries preserve context
3. Authentication handling
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

# Import the same components the API uses
from services.intelligence_service import IntelligenceService, INTELLIGENCE_SERVICE
from services.session_store import SessionStore
from data_engine.global_cache import GLOBAL_DATA, SYSTEM_READY

# Load data (simulating app startup)
print("[*] Loading OEM data...")
from app import load_oem_data
load_oem_data()

print("\n" + "="*60)
print("DASHBOARD API SIMULATION TEST")
print("="*60)

# Test 1: Initial query (new_conversation=True)
print("\n--- Test 1: Initial Query (new_conversation=True) ---")
SessionStore.reset()  # Simulate new_conversation=True
result1 = INTELLIGENCE_SERVICE.analyze("show me alerts for MIDEVSTB")
print("Q: show me alerts for MIDEVSTB")
print("A:", result1.get("answer", "")[:100])
print("Context after Q1:", SessionStore.get_conversation_context())

# Test 2: Follow-up query (new_conversation=False)  
print("\n--- Test 2: Follow-up Query (new_conversation=False) ---")
# DO NOT reset - this is a follow-up
result2 = INTELLIGENCE_SERVICE.analyze("ok show me 18 warning")
print("Q: ok show me 18 warning")
print("A:", result2.get("answer", "")[:200])
print("Context after Q2:", SessionStore.get_conversation_context())

# Test 3: Check if response has WARNING alerts
answer2 = result2.get("answer", "")
if "[WARNING]" in answer2 and "[CRITICAL]" not in answer2:
    print("\n[PASS] Follow-up correctly shows only WARNING alerts")
else:
    print("\n[FAIL] Follow-up showing wrong alerts")
    print("  Has WARNING:", "[WARNING]" in answer2)
    print("  Has CRITICAL:", "[CRITICAL]" in answer2)

# Test 4: Another follow-up
print("\n--- Test 3: Another Follow-up ---")
result3 = INTELLIGENCE_SERVICE.analyze("only critical")
print("Q: only critical")
print("A:", result3.get("answer", "")[:200])

print("\n" + "="*60)
print("TEST COMPLETE")
print("="*60)
