"""Direct test to verify NLP pipeline output."""
import sys
sys.path.insert(0, '.')

# Initialize minimal data loading
from data_engine.global_cache import GLOBAL_DATA, set_system_ready

def setup_minimal():
    """Load data without full server startup."""
    from data_engine.data_fetcher import DataFetcher
    print("[*] Loading OEM data...")
    fetcher = DataFetcher()
    data = fetcher.fetch({})
    GLOBAL_DATA.clear()
    GLOBAL_DATA.update({
        "alerts": data.get("alerts", []),
        "metrics": data.get("metrics", []),
        "incidents": data.get("incidents", []),
    })
    set_system_ready(True)
    print("[OK] Loaded {} alerts".format(len(GLOBAL_DATA.get("alerts", []))))

def test_pipeline():
    """Test the NLP pipeline directly."""
    from services.intelligence_service import INTELLIGENCE_SERVICE
    from services.session_store import SessionStore
    
    questions = [
        ("show me alerts for MIDEVSTB", True),    # New conversation
        ("ok show me 18 warning", False),          # Follow-up: filter to 18 WARNING
        ("show me standby issues", True),          # New - should reset context
        ("ok show me 20", False),                  # Follow-up: limit
        ("only critical", False),                  # Follow-up: filter
        ("show me alerts for MIDEVSTB", True),    # New - explicit DB should reset
    ]
    
    for q_item in questions:
        q = q_item[0]
        is_new = q_item[1]
        print("\n" + "=" * 60)
        print("Q: {} (new_conversation={})".format(q, is_new))
        print("=" * 60)
        
        # Reset session for new conversations
        if is_new:
            SessionStore.reset()
        
        # Run through IntelligenceService
        result = INTELLIGENCE_SERVICE.analyze(q)
        
        # Show context after query
        ctx = SessionStore.get_conversation_context()
        print("Intent:", result.get("intent"))
        print("Question Type:", result.get("question_type"))
        print("Target:", result.get("target"))
        print("Confidence:", result.get("confidence_label"))
        print("Context:", "topic={}, alert_type={}, has_context={}".format(
            ctx.get("topic"), ctx.get("alert_type"), ctx.get("has_context")))
        print("\n--- ANSWER ---")
        print(result.get("answer", "N/A"))
        print("-" * 60)

if __name__ == "__main__":
    setup_minimal()
    test_pipeline()
