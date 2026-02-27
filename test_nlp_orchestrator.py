# -*- coding: utf-8 -*-
"""
Test script for the new NLP Smart Assistant
Tests the complete flow: Intent → Entity → Context → Plan → Execute → Response
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.nlp_orchestrator import NLPOrchestrator, process_query


def test_basic_queries():
    """Test basic query types"""
    print("\n" + "=" * 70)
    print("TEST: Basic Query Types")
    print("=" * 70)
    
    orchestrator = NLPOrchestrator()
    session_id = "test_basic"
    
    test_cases = [
        ("How many alerts are there?", "ALERT_COUNT"),
        ("Show me alert summary", "ALERT_SUMMARY"),
        ("List top 10 alerts", "ALERT_LIST"),
        ("What is the root cause?", "ROOT_CAUSE"),
    ]
    
    for query, expected_intent in test_cases:
        result = orchestrator.process(query, session_id)
        print(f"\n📝 Query: {query}")
        print(f"   Intent: {result['intent']} (expected: {expected_intent})")
        print(f"   Confidence: {result['confidence']:.2f}")
        print(f"   Result count: {result['result_count']}")
        
        # Check if intent matches (approximately)
        if expected_intent in result['intent'] or result['intent'] in expected_intent:
            print("   ✅ PASS")
        else:
            print(f"   ⚠️ Intent mismatch")


def test_entity_extraction():
    """Test entity extraction"""
    print("\n" + "=" * 70)
    print("TEST: Entity Extraction")
    print("=" * 70)
    
    orchestrator = NLPOrchestrator()
    session_id = "test_entity"
    
    test_cases = [
        ("Show me alerts for MIDEVSTB", {"databases": ["MIDEVSTB"]}),
        ("How many critical alerts?", {"severity": "CRITICAL"}),
        ("List top 5 warning alerts", {"limit": 5, "severity": "WARNING"}),
        ("Show me dataguard issues", {"issue_type": "DATAGUARD"}),
    ]
    
    for query, expected_entities in test_cases:
        result = orchestrator.process(query, session_id)
        print(f"\n📝 Query: {query}")
        print(f"   Entities: {result['entities']}")
        
        # Check expected entities
        all_match = True
        for key, expected in expected_entities.items():
            actual = result['entities'].get(key)
            if key == 'databases' and actual:
                actual_upper = [d.upper() for d in actual]
                expected_upper = [d.upper() for d in expected]
                if actual_upper != expected_upper:
                    print(f"   ⚠️ {key}: got {actual}, expected {expected}")
                    all_match = False
            elif key == 'severity' and actual:
                if actual.upper() != expected.upper():
                    print(f"   ⚠️ {key}: got {actual}, expected {expected}")
                    all_match = False
            elif actual != expected:
                print(f"   ⚠️ {key}: got {actual}, expected {expected}")
                all_match = False
        
        if all_match:
            print("   ✅ PASS")


def test_conversation_context():
    """Test conversation context and follow-ups"""
    print("\n" + "=" * 70)
    print("TEST: Conversation Context & Follow-ups")
    print("=" * 70)
    
    orchestrator = NLPOrchestrator()
    session_id = "test_context"
    orchestrator.clear_session(session_id)  # Start fresh
    
    # Conversation flow
    conversation = [
        ("How many alerts for MIDEVSTB?", "Should show MIDEVSTB count"),
        ("Show me the critical ones", "Should filter MIDEVSTB by CRITICAL"),
        ("List top 5", "Should show 5 critical alerts for MIDEVSTB"),
        ("What about MIDEVSTBN?", "Should switch to MIDEVSTBN, keep severity?"),
    ]
    
    for query, expectation in conversation:
        result = orchestrator.process(query, session_id)
        print(f"\n📝 Query: {query}")
        print(f"   Expectation: {expectation}")
        print(f"   Intent: {result['intent']}")
        print(f"   Merged Entities: {result['entities']}")
        print(f"   Result count: {result['result_count']}")
        print(f"   Answer preview: {result['answer'][:100]}...")


def test_response_generation():
    """Test response formatting"""
    print("\n" + "=" * 70)
    print("TEST: Response Generation")
    print("=" * 70)
    
    orchestrator = NLPOrchestrator()
    session_id = "test_response"
    
    test_cases = [
        "How many alerts are there for MIDEVSTB?",
        "Show me the summary",
        "List top 3 critical alerts",
    ]
    
    for query in test_cases:
        result = orchestrator.process(query, session_id)
        print(f"\n📝 Query: {query}")
        print(f"   Result count: {result['result_count']}")
        print(f"\n💬 Response:\n{result['answer']}")
        print(f"\n💡 Suggestions: {result.get('suggestions', [])}")
        print("-" * 70)


def test_special_commands():
    """Test special commands like reset, help"""
    print("\n" + "=" * 70)
    print("TEST: Special Commands")
    print("=" * 70)
    
    test_cases = ["help", "reset", "what can you do"]
    
    for query in test_cases:
        result = process_query(query, "test_special")
        print(f"\n📝 Query: {query}")
        print(f"   Intent: {result['intent']}")
        print(f"   Answer preview: {result['answer'][:150]}...")


def run_all_tests():
    """Run all tests"""
    print("\n" + "=" * 70)
    print("NLP SMART ASSISTANT - COMPREHENSIVE TEST SUITE")
    print("=" * 70)
    
    test_basic_queries()
    test_entity_extraction()
    test_conversation_context()
    test_response_generation()
    test_special_commands()
    
    print("\n" + "=" * 70)
    print("ALL TESTS COMPLETED")
    print("=" * 70)


if __name__ == '__main__':
    run_all_tests()
