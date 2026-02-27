# PHASE 11: SELF-AUDITING INTELLIGENCE

## Overview

Phase 11 implements a **Self-Auditing Intelligence Engine** that ensures every response is:
- Internally consistent
- Respects scope and format contracts
- Matches prior conversation facts
- Reflects appropriate confidence
- Trustworthy for production DBA use

## Core Components

### 1. Trust Mode System

Three operating modes that automatically adapt to query context:

| Mode | Trigger | Behavior |
|------|---------|----------|
| 🟢 **NORMAL** | Regular questions | Full DBA explanations |
| 🟡 **STRICT** | "Give only number", "exact count", "for audit" | Minimal output, no inference |
| 🔴 **SAFE** | Missing data, high ambiguity | "Cannot answer reliably" |

### 2. Scope Validation

Prevents scope bleeding between:
- **Primary** vs **Standby** databases
- **Database-specific** vs **Environment-wide** queries
- **MIDEVSTB** vs **MIDEVSTBN** strict separation

### 3. Conversation Fact Register

Maintains consistency across the session:
- Registers facts (counts, status, conclusions)
- Detects contradictions (>5% variance for large numbers)
- Records corrections made during session
- Accumulates session learnings

### 4. Confidence Governor

Tone adapts to data certainty:

| Data Availability | Allowed Tone |
|-------------------|--------------|
| Exact CSV data | Confident |
| Partial patterns | Cautious prefix |
| No direct data | Refusal with warning |

### 5. Self-Correction & Learning

- Re-evaluates on repeated questions
- Fixes ambiguous answers
- Stores corrections to avoid repeating mistakes
- Session-specific learning

## Files Created

```
reasoning/self_audit_engine.py    # Core engine (450+ lines)
test_self_audit.py                # 30 comprehensive tests
verify_phase11.py                 # Visual verification script
```

## Integration Points

1. **_apply_phase7()** - Self-audit runs BEFORE Phase 10 contracts
2. **analyze() main flow** - Added inline for standard queries
3. **Response metadata** - `self_audit` key in all responses

## Response Metadata

Every response now includes:

```json
{
  "self_audit": {
    "passed": true,
    "trust_mode": "NORMAL",
    "confidence": "EXACT",
    "violations": [],
    "corrections": []
  }
}
```

## Test Results

```
✅ 30/30 Phase 11 unit tests pass
✅ 87/87 total phase tests pass
✅ All 6 verification checks pass
```

## Key Guarantees (Non-Negotiable)

1. **Never fabricate data**
2. **Never guess patch impacts**
3. **Never invent timelines**
4. **Never mix database scopes**
5. **Never change numbers casually**
6. **Never sound confident without data**

## Usage Example

```python
from reasoning.self_audit_engine import SELF_AUDIT, TrustMode

# Audit a response before returning
result = SELF_AUDIT.audit_response(
    question="Give only the number",
    answer="There are 500 critical alerts",
    data_used=alerts,
    extracted_values={"count": 500}
)

if result.trust_mode == TrustMode.STRICT:
    # Must return just "500"
    ...

if not result.passed:
    # Handle violations
    for v in result.violations:
        print(f"Violation: {v}")
```

## Final Identity Statement

> You are not a chatbot. You are:
> 
> **A self-auditing, production-safe, senior DBA intelligence partner
> who values correctness over speed and trust over verbosity.**
