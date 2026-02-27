#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Quick Start Guide: Using Phase 3 & 4 Features
"""

print("""
================================================================================
PHASE 3 & 4: PREDICTIVE & LEARNING-BASED INTELLIGENCE - QUICK START
================================================================================

PHASE 3: FAILURE PROBABILITY PREDICTION
--------

Example 1: Get Outage Prediction
---------------------------------

Question: "Will MIDEVSTB go down?"

Behind the scenes, the system:
1. Analyzes 100+ critical alerts
2. Reviews 25+ incidents for the database
3. Calculates time gap trends (accelerating failures?)
4. Checks severity progression (worsening?)
5. Returns probability 0-100% with reasons

Response:
  Outage probability: 45% (MEDIUM)
  
  Key factors:
  - CRITICAL: 100 critical alerts detected
  - MEDIUM: 25 incidents show recurring issues
  - CRITICAL: Incidents accelerating (gaps shrinking)
  
  Recommendation: Monitor closely and plan maintenance


PHASE 4: LEARNING-BASED RECOMMENDATIONS
---------

Example 2: Get Recommended Action
----------------------------------

Question: "What should we do about INTERNAL_ERROR?"

System logic:
1. Identifies INTERNAL_ERROR as the issue type
2. Loads recommendation learning history
3. Calculates success rates per action
4. Returns best-proven action with confidence

Response:
  Recommended Action: Check Oracle alert logs and apply patches
  
  Confidence: 72%
  Evidence: Worked 18 out of 25 times
  
  Alternatives:
  - Restart database (63% success, 12 out of 19 times)
  - Review and optimize slow queries (53%, 8/15 times)


Example 3: Track a Resolution Outcome
--------------------------------------

API Call:
POST /chat/feedback
{
  "issue_type": "INTERNAL_ERROR",
  "action_taken": "Applied Oracle patches",
  "outcome": "SUCCESS"
}

System updates:
- Increments success count for "Check Oracle alert logs..." action
- Recalculates confidence: now 73% (19/26)
- Persists to recommendation_history.json
- Next time, chatbot shows updated confidence


CHATBOT EXAMPLES
-----------------

Query 1: Stability Check
User: "Is midevstb stable now?"
Bot: Shows risk trend + outage probability + validation status

Query 2: Predictive
User: "Will DB1 crash?"
Bot: "Outage probability: 35% (LOW). Currently stable pattern detected."

Query 3: Action Request
User: "What can we do about midevstb performance?"
Bot: "For PERFORMANCE issues: Analyze and rebuild indexes (45% confidence)"

Query 4: Explainability
User: "Why is MIDEVSTB at risk?"
Bot: [Lists specific factors with scoring breakdown]


VIEW LEARNING STATISTICS
--------------------------

API Call:
GET /chat/stats

Response:
{
  "learning_statistics": {
    "total_issue_types": 6,
    "total_actions_tracked": 14,
    "most_reliable_action": "Check Oracle alert logs and apply patches",
    "most_reliable_success_rate": 72,
    "issue_stats": [
      {
        "issue": "INTERNAL_ERROR",
        "actions_tracked": 3,
        "best_action": "Check Oracle alert logs",
        "success_rate": 72
      },
      ...
    ]
  }
}


KEY FEATURES OVERVIEW
----------------------

Failure Probability Scoring:
  ✓ Weights 4 factors equally (25 pts each)
  ✓ Critical alert frequency
  ✓ Incident frequency
  ✓ Time gap trends (detects acceleration)
  ✓ Severity progression

Recommendation Learning:
  ✓ Tracks issue -> action -> outcome
  ✓ Calculates success rates
  ✓ Persists to JSON
  ✓ Improves with each outcome
  ✓ Provides alternatives

Explainability:
  ✓ Every prediction includes reasons
  ✓ Score breakdown shows factor contributions
  ✓ Evidence shows success rate (X out of Y times)
  ✓ Risk levels: LOW, MEDIUM, HIGH, CRITICAL


PRODUCTION WORKFLOW
---------------------

1. Initial Deployment
   - System loads with pre-built learning history
   - Chatbot immediately answers questions
   - No training period required

2. Daily Operations
   - Monitor dashboard & risk trends
   - Ask chatbot about potential issues
   - Track resolution outcomes via /chat/feedback

3. Continuous Improvement
   - Confidence in recommendations increases
   - Best actions surface automatically
   - Historical patterns become visible

4. Monthly Review
   - Check /chat/stats for insights
   - Identify most common issues
   - Verify recommended actions are working


PYTHON 3.6.8 COMPATIBLE
------------------------

All code follows these constraints:
  ✓ No f-strings (uses .format())
  ✓ No type hints
  ✓ No dataclasses
  ✓ No walrus operators
  ✓ Standard library only
  ✓ Works on PuTTY/Linux with Python 3.6.8


TESTING
--------

Run all tests:
  python test_phases_3_4.py

Expected output:
  [PASS] Outage Probability
  [PASS] Recommendation Engine  
  [PASS] Full Integration
  
  Total: 3/3 - ALL TESTS PASSED!


TROUBLESHOOTING
-----------------

Q: Chatbot says "Please specify database" for predictive questions?
A: Make sure target name is in question. Example: "Will MIDEVSTB go down?" ✓

Q: Recommendations show default (low confidence)?
A: No learning history yet. Track outcomes via /chat/feedback to improve.

Q: Learning data not persisting?
A: Check that recommendation_history.json is writable in app directory.

Q: Outage probability seems low?
A: Ensure sufficient alerts and incidents exist. Pattern requires 20+ incidents.


API REFERENCE
--------------

POST /chat/
  Request: {"message": "Will MIDEVSTB go down?"}
  Response: Includes prediction + recommendation if relevant

POST /chat/feedback
  Request: {
    "issue_type": "INTERNAL_ERROR",
    "action_taken": "Applied patches",
    "outcome": "SUCCESS"
  }
  Response: Updated confidence + new recommendations

GET /chat/stats
  Response: Learning statistics and analytics

POST /chat/warmup
  Initializes chatbot (call on app startup)


FILES
-------

New:
  incident_engine/recommendation_engine.py
  recommendation_history.json
  test_phases_3_4.py
  PHASE_3_4_DOCUMENTATION.md

Modified:
  incident_engine/correlation_engine.py (enhanced outage_probability)
  controllers/chat_controller.py (integrated predictions & recommendations)

================================================================================
Ready to deploy! All tests pass. System is production-ready. 🚀
================================================================================
""")
