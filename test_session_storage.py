#!/usr/bin/env python
"""
Test session storage to verify it's working correctly.

This simulates the exact flow from the dashboard:
1. set_session_id -> reset_session -> process -> set_context
2. set_session_id -> get_context (should have context from step 1)
"""

import sys
sys.path.insert(0, 'c:\\NLP_Smart_Assistant')

from services.session_store import SessionStore, _SESSION_STORAGE, _ACTIVE_SESSION_ID

def main():
    session_id = "test_session_123"
    
    print("="*60)
    print("TEST 1: Initial state")
    print("="*60)
    print("_SESSION_STORAGE:", list(_SESSION_STORAGE.keys()))
    print("_ACTIVE_SESSION_ID:", _ACTIVE_SESSION_ID)
    print()
    
    # Simulate Message 1: new_conversation=True
    print("="*60)
    print("SIMULATING MESSAGE 1: new_conversation=True")
    print("="*60)
    
    # Step 1: set_session_id
    print("\n1. Calling set_session_id('%s')..." % session_id)
    SessionStore.set_session_id(session_id)
    print("   _ACTIVE_SESSION_ID:", SessionStore.get_session_id())
    print("   _SESSION_STORAGE keys:", list(_SESSION_STORAGE.keys()))
    print("   cls._state is _SESSION_STORAGE[session_id]:", SessionStore._state is _SESSION_STORAGE[session_id])
    
    # Step 2: reset_session (because new_conversation=True)
    print("\n2. Calling reset_session('%s')..." % session_id)
    SessionStore.reset_session(session_id)
    print("   cls._state is _SESSION_STORAGE[session_id]:", SessionStore._state is _SESSION_STORAGE[session_id])
    
    # Step 3: Simulate IntelligenceService storing context
    print("\n3. Setting conversation context (simulating query processing)...")
    SessionStore.set_conversation_context(
        topic="ALERTS_BY_DB",
        last_target="MIDEVSTB",
        databases=["MIDEVSTB"],
        result_count=165855,
        has_context=True
    )
    
    # Step 4: Verify context was stored
    print("\n4. Reading context back...")
    ctx = SessionStore.get_conversation_context()
    print("   Context:", ctx)
    print("   has_context:", ctx.get("has_context"))
    print("   topic:", ctx.get("topic"))
    print("   last_target:", ctx.get("last_target"))
    
    # Verify it's in session storage
    print("\n5. Checking _SESSION_STORAGE directly...")
    stored_ctx = _SESSION_STORAGE[session_id].get("conversation_context", {})
    print("   _SESSION_STORAGE[%s]['conversation_context']:" % session_id, stored_ctx)
    print()
    
    # Now simulate Message 2: new_conversation=False
    print("="*60)
    print("SIMULATING MESSAGE 2: new_conversation=False")
    print("="*60)
    
    # Step 1: set_session_id (same session)
    print("\n1. Calling set_session_id('%s') again..." % session_id)
    SessionStore.set_session_id(session_id)
    print("   cls._state is _SESSION_STORAGE[session_id]:", SessionStore._state is _SESSION_STORAGE[session_id])
    
    # Step 2: Read context (should still have it!)
    print("\n2. Reading context (should be preserved)...")
    ctx = SessionStore.get_conversation_context()
    print("   Context:", ctx)
    print("   has_context:", ctx.get("has_context"))
    print("   topic:", ctx.get("topic"))
    print("   last_target:", ctx.get("last_target"))
    
    if ctx.get("has_context"):
        print("\n" + "="*60)
        print("SUCCESS! Context is preserved across messages!")
        print("="*60)
    else:
        print("\n" + "="*60)
        print("FAILURE! Context was lost!")
        print("="*60)


if __name__ == "__main__":
    main()
