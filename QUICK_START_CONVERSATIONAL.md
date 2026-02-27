# Quick Start: Using the Conversational NLP Assistant

## For End Users

### What's New?

Your NLP Assistant is now **conversational**! You can ask follow-up questions naturally:

#### Before (Old Behavior)
```
❌ User: "how many standby alerts?"
   Bot:  "Peak hour is 3:00 AM"  (WRONG - routed to TIME)

❌ User: "show me 20"
   Bot:  "Unable to process question"
```

#### After (New Behavior)
```
✅ User: "how many standby alerts?"
   Bot:  "123 Data Guard standby alerts found."  (CORRECT - COUNT)

✅ User: "show me 20"
   Bot:  "Showing top 20 standby alerts:
          1. [CRITICAL] MIDEVSTBN: ORA-16191..."
```

### Examples You Can Try

**1. Count + Follow-up Limit:**
```
"how many standby alerts?"
"show me 20"
"only critical ones"
```

**2. Database Reference:**
```
"which database has most alerts?"
"show alerts for this database"
"only critical"
```

**3. Complex Filtering:**
```
"show alerts for MIDEVSTBN"
"only critical ones"
"top 10"
```

**4. Smart Clarification:**
```
"show me 10"  (no context)
→ Bot asks: "What would you like to see?"
"standby alerts"
"show me 10"  (now works!)
```

---

## For Developers

### Quick Integration Guide

#### 1. Using Follow-up Detection

```python
from nlp_engine.intent_response_router import IntentResponseRouter

question = "show me 20"
is_followup, followup_type = IntentResponseRouter.is_followup_question(question)

if is_followup:
    if followup_type == "LIMIT":
        limit = IntentResponseRouter.extract_limit_number(question)
        print(f"User wants {limit} items")
    elif followup_type == "REFERENCE":
        print("User is referencing prior context")
    elif followup_type == "FILTER":
        severity = IntentResponseRouter.extract_filter_severity(question)
        print(f"User wants {severity} items")
```

#### 2. Using Context Memory

```python
from nlp_engine.context_memory import ContextMemory

memory = ContextMemory()

# Store context after answering
memory.update(
    target="MIDEVSTBN",
    intent="STANDBY_DATAGUARD",
    topic="STANDBY_ALERTS",
    result_count=123,
    severity="CRITICAL"
)

# Check context for follow-ups
context = memory.get_context_summary()
if context["has_context"]:
    print(f"Last database: {context['database']}")
    print(f"Last topic: {context['topic']}")
    print(f"Can filter: {context['can_filter']}")
```

#### 3. Using COUNT Guard Rule

```python
from nlp_engine.intent_response_router import IntentResponseRouter

question = "how many standby alerts?"

# CRITICAL: Always check this BEFORE routing
if IntentResponseRouter.is_count_question(question):
    # MUST return COUNT (number)
    # NEVER return TIME aggregation
    return format_as_count(result)
else:
    # Can return other formats
    return format_as_needed(result)
```

#### 4. Full Example: Handling Follow-ups

```python
from nlp_engine.nlp_reasoner import NLPReasoner

reasoner = NLPReasoner()

# Initial question
answer1 = reasoner.answer("how many standby alerts?")
# → "123 Data Guard standby alerts found."
# Context stored automatically

# Follow-up question
answer2 = reasoner.answer("show me 20")
# → "Showing top 20 standby alerts: ..."
# Uses stored context

# Another follow-up
answer3 = reasoner.answer("only critical ones")
# → "Filtered to CRITICAL severity (45 items): ..."
# Applies filter on cached results

# Reset for new conversation
reasoner.reset()
```

---

## Testing Your Changes

### Unit Test Example

```python
def test_followup_limit():
    from nlp_engine.intent_response_router import IntentResponseRouter
    
    # Test detection
    is_followup, ftype = IntentResponseRouter.is_followup_question("show me 20")
    assert is_followup == True
    assert ftype == "LIMIT"
    
    # Test extraction
    limit = IntentResponseRouter.extract_limit_number("show me 20")
    assert limit == 20
    
    # Test edge cases
    limit = IntentResponseRouter.extract_limit_number("top ten")
    assert limit == 10

def test_followup_reference():
    from nlp_engine.intent_response_router import IntentResponseRouter
    
    is_followup, ftype = IntentResponseRouter.is_followup_question("this database")
    assert is_followup == True
    assert ftype == "REFERENCE"

def test_count_guard():
    from nlp_engine.intent_response_router import IntentResponseRouter
    
    # COUNT keywords must be detected
    assert IntentResponseRouter.is_count_question("how many alerts?") == True
    assert IntentResponseRouter.is_count_question("total alerts") == True
    
    # TIME keywords should NOT trigger COUNT
    assert IntentResponseRouter.is_count_question("which hour?") == False
```

### Integration Test Example

```python
def test_conversational_flow():
    from nlp_engine.nlp_reasoner import NLPReasoner
    
    reasoner = NLPReasoner()
    
    # Initial question
    answer = reasoner.answer("how many standby alerts?")
    assert "123" in answer or "Data Guard" in answer
    
    # Follow-up should work
    answer = reasoner.answer("show me 20")
    assert "Showing" in answer or "top 20" in answer
    
    # Filter should work
    answer = reasoner.answer("only critical")
    assert "CRITICAL" in answer
    
    # Reset and verify context is cleared
    reasoner.reset()
    answer = reasoner.answer("show me 10")
    assert "need more context" in answer.lower()
```

---

## Common Patterns

### Pattern 1: Count → Limit → Filter

```python
# User journey:
"how many standby alerts?"      → COUNT: 123
"show me 20"                    → LIMIT: Top 20
"only critical ones"            → FILTER: CRITICAL severity
```

### Pattern 2: Entity → Reference → Details

```python
# User journey:
"which database has most alerts?"  → ENTITY: MIDEVSTBN
"show alerts for this database"    → REFERENCE: MIDEVSTBN details
"what's causing it?"               → ANALYSIS: Root cause
```

### Pattern 3: Smart Clarification

```python
# User journey:
"show me 10"                       → CLARIFICATION: Need context
"standby alerts"                   → COUNT: 123
"show me 10"                       → LIMIT: Top 10 standby
```

---

## Troubleshooting

### Issue: Follow-up not working

**Symptom:** "show me 20" returns "need more context"  
**Cause:** No prior context stored  
**Fix:** Ensure initial question is processed first

```python
# WRONG
reasoner = NLPReasoner()
answer = reasoner.answer("show me 20")  # No context!

# RIGHT
reasoner = NLPReasoner()
reasoner.answer("how many standby alerts?")  # Store context
answer = reasoner.answer("show me 20")       # Use context
```

### Issue: COUNT routed to TIME

**Symptom:** "how many alerts" shows "peak hour" instead of count  
**Cause:** COUNT guard rule not applied  
**Fix:** Always check `is_count_question()` first

```python
# WRONG
if "hour" in question:
    return show_peak_hour()  # Breaks "how many alerts at 3am?"

# RIGHT
if IntentResponseRouter.is_count_question(question):
    return show_count()  # Always return count
elif IntentResponseRouter.is_time_question(question):
    return show_peak_hour()
```

### Issue: Context persists across conversations

**Symptom:** New conversation uses old context  
**Cause:** Forgot to reset  
**Fix:** Call `reset()` when starting new conversation

```python
# At conversation start
reasoner.reset()  # Clear old context
```

---

## Performance Tips

1. **Lazy Loading:** Router and pipeline are lazy-loaded (first use)
2. **Context Reuse:** Follow-ups reuse cached results (fast)
3. **Early Exit:** Follow-up detection happens before full processing

---

## API Changes

### Backward Compatible (No Breaking Changes)

All existing code continues to work:

```python
# OLD CODE (still works)
from nlp_engine.nlp_reasoner import NLPReasoner
reasoner = NLPReasoner()
answer = reasoner.answer("how many alerts?")

# NEW CODE (optional enhancements)
answer = reasoner.answer("show me 20")  # Now works!
```

### New Methods Added

```python
# IntentResponseRouter
is_followup_question(question) → (bool, str)
extract_limit_number(question) → int or None
extract_filter_severity(question) → str or None

# ContextMemory
get_context_summary() → dict
clear() → None

# NLPReasoner
reset() → None  # Clears context
```

---

## Best Practices

1. **Always check COUNT guard first:**
   ```python
   if IntentResponseRouter.is_count_question(q):
       return count_format(result)
   ```

2. **Store context after successful responses:**
   ```python
   memory.update(target=db, topic=topic, result_count=count)
   ```

3. **Reset context for new conversations:**
   ```python
   reasoner.reset()
   ```

4. **Provide clarification when context is missing:**
   ```python
   if not context["has_context"]:
       return clarification_message()
   ```

---

## Need Help?

- See `NLP_CONVERSATIONAL_UPGRADE.md` for full documentation
- Check code comments in modified files
- Test examples in this guide

**Happy Conversing! 🤖💬**
