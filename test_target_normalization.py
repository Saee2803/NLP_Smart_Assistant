#!/usr/bin/env python
"""
TEST_TARGET_NORMALIZATION.PY

Validates the canonical target normalization fix.
Python 3.6.8 compatible.

Run: python test_target_normalization.py
"""

from data_engine.target_normalizer import TargetNormalizer


def test_normalize_basic():
    """Test basic normalization rules"""
    print("\n[TEST] Basic Normalization")
    
    # Rule 1: None/empty
    assert TargetNormalizer.normalize(None) is None
    assert TargetNormalizer.normalize("") is None
    assert TargetNormalizer.normalize("   ") is None
    print("  ✓ None/empty handling")
    
    # Rule 2: Case normalization
    assert TargetNormalizer.normalize("middevstb") == "MIDDEVSTB"
    assert TargetNormalizer.normalize("MIDDEVSTB") == "MIDDEVSTB"
    assert TargetNormalizer.normalize("MidDevStb") == "MIDDEVSTB"
    print("  ✓ Case normalization")
    
    # Rule 3: Whitespace stripping
    assert TargetNormalizer.normalize("  middevstb  ") == "MIDDEVSTB"
    assert TargetNormalizer.normalize("\tmiddevstb\n") == "MIDDEVSTB"
    print("  ✓ Whitespace stripping")
    
    # Rule 4: Listener filtering
    assert TargetNormalizer.normalize("19CLISTENER_MIDDEVSTB") is None
    assert TargetNormalizer.normalize("19clistener_something") is None
    print("  ✓ Listener filtering")


def test_equals_comparison():
    """Test target equality checking"""
    print("\n[TEST] Target Equality")
    
    # Same canonical form
    assert TargetNormalizer.equals("MIDDEVSTB", "middevstb") == True
    assert TargetNormalizer.equals("MIDDEVSTB", "MidDevStb") == True
    print("  ✓ Different formats → same result")
    
    # Different targets
    assert TargetNormalizer.equals("MIDDEVSTB", "OTHERDB") == False
    print("  ✓ Different targets → False")
    
    # Listener noise
    assert TargetNormalizer.equals("19CLISTENER_MIDDEVSTB", "MIDDEVSTB") == False
    print("  ✓ Listener entries → False")
    
    # None cases
    assert TargetNormalizer.equals(None, "MIDDEVSTB") == False
    assert TargetNormalizer.equals("MIDDEVSTB", None) == False
    assert TargetNormalizer.equals(None, None) == False
    print("  ✓ None handling")


def test_idempotence():
    """Test idempotence property"""
    print("\n[TEST] Idempotence")
    
    test_values = [
        "MIDDEVSTB",
        "middevstb",
        "MidDevStb",
        "  MIDDEVSTB  ",
        "OTHERDB",
        None,
        ""
    ]
    
    for val in test_values:
        first = TargetNormalizer.normalize(val)
        second = TargetNormalizer.normalize(first)
        assert first == second, "Failed idempotence for: {0}".format(val)
    
    print("  ✓ Normalize(Normalize(x)) == Normalize(x)")


def test_determinism():
    """Test deterministic behavior"""
    print("\n[TEST] Determinism")
    
    test_values = [
        "MIDDEVSTB",
        "middevstb",
        "  MIDDEVSTB  ",
        "OTHERDB",
    ]
    
    for val in test_values:
        r1 = TargetNormalizer.normalize(val)
        r2 = TargetNormalizer.normalize(val)
        r3 = TargetNormalizer.normalize(val)
        assert r1 == r2 == r3, "Not deterministic for: {0}".format(val)
    
    print("  ✓ f(x) always returns same result")


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("TARGET NORMALIZATION VALIDATION TESTS")
    print("="*60)
    
    try:
        test_normalize_basic()
        test_equals_comparison()
        test_idempotence()
        test_determinism()
        
        print("\n" + "="*60)
        print("ALL TESTS PASSED ✓")
        print("="*60 + "\n")
        return True
        
    except AssertionError as e:
        print("\n" + "="*60)
        print("TEST FAILED ✗")
        print("Error: {0}".format(str(e)))
        print("="*60 + "\n")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
