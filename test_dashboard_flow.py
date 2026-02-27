#!/usr/bin/env python
"""
Test the exact dashboard flow to verify context is preserved.

This simulates:
1. "show me alerts for MIDEVSTB" (first message, new_conversation=True)
2. "ok show me 18 warning" (follow-up, new_conversation=False)

Expected: Second query should return 18 WARNING alerts for MIDEVSTB
"""

import sys
sys.path.insert(0, 'c:\\NLP_Smart_Assistant')

# Load data first before importing IntelligenceService
from data_engine.data_fetcher import DataFetcher
fetcher = DataFetcher()
data = fetcher.fetch()

from services.session_store import SessionStore, _SESSION_STORAGE
from services.intelligence_service import IntelligenceService, GLOBAL_DATA
from data_engine.global_cache import set_system_ready

def simulate_dashboard_flow():
    """Simulate exact dashboard flow"""
    
    session_id = "dashboard_test_" + str(int(__import__('time').time()))
    
    print("="*70)
    print("SIMULATING DASHBOARD FLOW")
    print("Session ID:", session_id)
    print("="*70)
    
    # Use pre-loaded data
    print("\n[SETUP] Using pre-loaded alert data...")
    GLOBAL_DATA.update(data)
    print("[SETUP] Loaded {} alerts".format(len(GLOBAL_DATA.get("alerts", []))))
    
    # Set system as ready (normally done by app startup)
    set_system_ready(True)
    print("[SETUP] System marked as READY")
    
    # Initialize intelligence service
    service = IntelligenceService()
    
    # ========================================
    # MESSAGE 1: "show me alerts for MIDEVSTB"
    # ========================================
    print("\n" + "="*70)
    print("MESSAGE 1: 'show me alerts for MIDEVSTB' (new_conversation=True)")
    print("="*70)
    
    # Set session (like controller does)
    SessionStore.set_session_id(session_id)
    print("[STEP 1] Called set_session_id")
    print("         _state is _SESSION_STORAGE[session_id]:", SessionStore._state is _SESSION_STORAGE[session_id])
    
    # Reset session (like controller does for new_conversation=True)
    SessionStore.reset_session(session_id)
    print("[STEP 2] Called reset_session (new_conversation=True)")
    print("         _state is _SESSION_STORAGE[session_id]:", SessionStore._state is _SESSION_STORAGE[session_id])
    
    # Process the message
    result1 = service.analyze("show me alerts for MIDEVSTB")
    print("[STEP 3] IntelligenceService.analyze() completed")
    print("\n         ANSWER (first 200 chars):")
    answer1 = result1.get("answer", "")[:200]
    print("         " + answer1.replace("\n", "\n         "))
    
    # Check context after message 1
    ctx1 = SessionStore.get_conversation_context()
    print("\n[CONTEXT AFTER MSG 1]")
    print("         topic:", ctx1.get("topic"))
    print("         last_target:", ctx1.get("last_target"))
    print("         databases:", ctx1.get("databases"))
    print("         has_context:", ctx1.get("has_context"))
    print("         result_count:", ctx1.get("result_count"))
    
    # ========================================
    # MESSAGE 2: "ok show me 18 warning"
    # ========================================
    print("\n" + "="*70)
    print("MESSAGE 2: 'ok show me 18 warning' (new_conversation=False)")
    print("="*70)
    
    # Set session again (like controller does)
    SessionStore.set_session_id(session_id)
    print("[STEP 1] Called set_session_id")
    print("         _state is _SESSION_STORAGE[session_id]:", SessionStore._state is _SESSION_STORAGE[session_id])
    
    # NO reset because new_conversation=False
    print("[STEP 2] NO reset_session (new_conversation=False)")
    
    # Check context before message 2
    ctx_before = SessionStore.get_conversation_context()
    print("\n[CONTEXT BEFORE MSG 2]")
    print("         topic:", ctx_before.get("topic"))
    print("         last_target:", ctx_before.get("last_target"))
    print("         databases:", ctx_before.get("databases"))
    print("         has_context:", ctx_before.get("has_context"))
    
    if not ctx_before.get("has_context"):
        print("\n!!! CRITICAL BUG: Context was lost between messages !!!")
        return False
    
    # Process the follow-up message
    result2 = service.analyze("ok show me 18 warning")
    print("\n[STEP 3] IntelligenceService.analyze() completed")
    
    answer2 = result2.get("answer", "")
    print("\n         FULL ANSWER:")
    print("         " + answer2.replace("\n", "\n         "))
    
    # ========================================
    # VALIDATION
    # ========================================
    print("\n" + "="*70)
    print("VALIDATION")
    print("="*70)
    
    # Check if we got WARNING alerts
    if "WARNING" in answer2 and "18" in answer2 and "MIDEVSTB" in answer2.upper():
        print("\n[SUCCESS] Got 18 WARNING alerts for MIDEVSTB!")
        return True
    elif "No" in answer2 and "WARNING" in answer2:
        print("\n[FAILURE] Got 'No WARNING alerts found' - context or filter issue!")
        return False
    else:
        print("\n[UNCERTAIN] Check answer above manually")
        return None


if __name__ == "__main__":
    success = simulate_dashboard_flow()
    print("\n" + "="*70)
    if success:
        print("DASHBOARD FLOW: PASSED")
    else:
        print("DASHBOARD FLOW: FAILED")
    print("="*70)
