# NLP Smart Assistant - Architecture Documentation

## Overview

The NLP Smart Assistant provides a conversational interface for querying alert data. It understands natural language queries, maintains conversation context, and returns accurate results from the CSV data.

## Architecture

```
USER QUERY
    │
    ▼
┌──────────────────┐
│ Intent Classifier │ ← Classifies query intent (ALERT_COUNT, ALERT_SUMMARY, etc.)
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Entity Extractor │ ← Extracts databases, severity, limit, time ranges, etc.
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Context Manager  │ ← Merges with previous conversation context
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Query Planner    │ ← Converts intent + entities to query plan
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Query Executor   │ ← Executes plan against CSV data
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Response Gen     │ ← Formats results as natural language
└────────┬─────────┘
         │
         ▼
    ANSWER
```

## Components

### 1. Intent Classifier (`nlp_engine/smart_intent.py`)

Classifies user queries into intents:
- `ALERT_COUNT` - "How many alerts?"
- `ALERT_SUMMARY` - "Show me alert summary"
- `ALERT_LIST` - "List alerts"
- `FOLLOWUP_SEVERITY` - "Show me critical ones"
- `FOLLOWUP_LIMIT` - "List top 5"
- `ROOT_CAUSE` - "What is the root cause?"
- `RECOMMENDATION` - "What should I do?"
- And more...

### 2. Entity Extractor (`nlp_engine/entity_extractor.py`)

Extracts structured entities from queries:
- **databases**: ["MIDEVSTB", "MIDEVSTBN"]
- **severity**: "CRITICAL" | "WARNING"
- **limit**: 5, 10, 20...
- **time_range**: "today", "last_24h", "this_week"
- **issue_type**: "DATAGUARD", "TABLESPACE", etc.
- **ora_codes**: ["ORA-600", "ORA-1654"]

### 3. Context Manager (`services/context_manager.py`)

Maintains conversation context per session:
- **Entity Inheritance**: Follow-up queries inherit database/filters from previous
- **Database Switch**: New database resets severity filters
- **Pagination**: Tracks offset for "show more" queries

Example:
```
User: "How many alerts for MIDEVSTB?"    → database=MIDEVSTB
User: "Show me critical ones"            → database=MIDEVSTB, severity=CRITICAL (inherited)
User: "What about MIDEVSTBN?"            → database=MIDEVSTBN (switched)
```

### 4. Query Planner (`services/query_planner.py`)

Converts intent + entities into executable query plans:
- **COUNT**: Just count alerts
- **SUMMARY**: Count + severity breakdown
- **LIST**: Paginated alert list
- **AGGREGATE**: Group by field
- **COMPARE**: Compare two entities

### 5. Query Executor (`data_engine/query_executor.py`)

Executes query plans against CSV data:
- Loads `data/alerts/oem_alerts_raw.csv`
- Applies filters (database, severity, issue type)
- Returns structured results with aggregations

### 6. Response Generator (`services/response_generator.py`)

Formats results as natural language:
- Count responses with severity breakdown
- Summary with top alert types
- Paginated list with emojis
- Follow-up suggestions

### 7. NLP Orchestrator (`services/nlp_orchestrator.py`)

Ties everything together:
- Entry point: `process_query(query, session_id)`
- Handles special commands (help, reset)
- Error handling and fallbacks

## API Endpoints

### V2 Chat API (New)

```
POST /chat/v2
{
    "message": "How many critical alerts for MIDEVSTB?",
    "session_id": "user123",
    "new_conversation": false
}

Response:
{
    "question": "...",
    "answer": "There are **649769** critical alerts for MIDEVSTB...",
    "intent": "ALERT_SUMMARY",
    "confidence": 0.92,
    "question_type": "FACT",
    "entities": {"database": "MIDEVSTB", "severity": "CRITICAL"},
    "result_count": 649769,
    "suggestions": ["Show me the warning alerts", "What is the root cause?"]
}
```

### V2 Context Debug

```
GET /chat/v2/context?session_id=user123

Response:
{
    "session_id": "user123",
    "context": {
        "database": "MIDEVSTB",
        "severity": "CRITICAL",
        "last_intent": "ALERT_SUMMARY",
        ...
    }
}
```

### V2 Reset

```
POST /chat/v2/reset?session_id=user123
```

## Example Conversation

```
User: How many alerts are there?
Bot:  There are 650,782 alerts.
      - Critical: 650,764
      - Warning: 18

User: Show me alerts for MIDEVSTB
Bot:  Alert Summary for MIDEVSTB:
      Total: 649,787 alerts
      - Critical: 649,769
      - Warning: 18

User: Show me the critical ones
Bot:  Showing 20 of 649,769 critical alerts for MIDEVSTB:
      1. 🔴 midevstb - Critical
         The database status is UNKNOWN.
      ...

User: List top 5
Bot:  Showing 5 of 649,769 alerts...

User: What about MIDEVSTBN?
Bot:  Showing 20 of 483,932 alerts for MIDEVSTBN...
```

## Files Created

| File | Purpose |
|------|---------|
| `nlp_engine/entity_extractor.py` | Extract entities from queries |
| `nlp_engine/smart_intent.py` | Classify query intents |
| `services/context_manager.py` | Manage conversation context |
| `services/query_planner.py` | Generate query plans |
| `data_engine/query_executor.py` | Execute plans against CSV |
| `services/response_generator.py` | Format responses |
| `services/nlp_orchestrator.py` | Main orchestrator |

## Running Tests

```bash
python test_nlp_orchestrator.py
```

## Integration

The V2 API is integrated into the existing chat controller at `/chat/v2`. The original `/chat` endpoint remains unchanged for backward compatibility.

To switch the dashboard to use V2:
1. Change API endpoint from `/chat/` to `/chat/v2`
2. Handle the new response fields (`intent`, `entities`, `suggestions`)
