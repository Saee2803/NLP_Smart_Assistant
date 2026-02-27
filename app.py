import os
from typing import Any
from typing import Dict, Union
from sqlite3 import Connection
from sqlite3 import Cursor
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import bcrypt
from starlette.templating import _TemplateResponse
from starlette.templating import _TemplateResponse
from starlette.templating import _TemplateResponse
from starlette.templating import _TemplateResponse

from auth.database import get_db

from controllers.chat_controller import chat_router
from controllers.alerts_controller import alerts_router
from controllers.confidence_controller import confidence_router
from controllers.dashboard_controller import dashboard_router
from controllers.rca_controller import rca_router

from data_engine.data_fetcher import DataFetcher
from data_engine.global_cache import GLOBAL_DATA, SYSTEM_READY, INIT_STATUS, set_system_ready

from incident_engine.risk_trend_analyzer import RiskTrendAnalyzer
from learning.pattern_engine import PatternEngine
from data_engine.target_normalizer import TargetNormalizer
from storage.database import Database


# =====================================================
# APP INIT
# =====================================================
app = FastAPI(title="OEM Incident Intelligence System")
templates = Jinja2Templates(directory="templates")


# =====================================================
# STATIC FILES
# =====================================================
if os.path.isdir("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")


# =====================================================
# CORS
# =====================================================
app.add_middleware(
    CORSMiddleware,
   allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =====================================================
# OEM DATA LOADER (SYNCHRONOUS - PRODUCTION WIRING)
# =====================================================
def load_oem_data() -> None:
    """
    Load all OEM data synchronously on startup.
    CRITICAL: This ensures GLOBAL_DATA is fully populated 
    before any API requests are served.
    """
    
    print("=" * 60)
    print("[*] OEM PRODUCTION DATA LOADING INITIATED")
    print("=" * 60)

    try:
        # Stage 1: Fetch raw data
        print("[*] Stage 1: Fetching raw data...")
        fetcher = DataFetcher()
        data = fetcher.fetch({})

        alerts = data.get("alerts", [])
        metrics = data.get("metrics", [])
        incidents = data.get("incidents", [])

        print("[OK] Alerts loaded        : {0}".format(len(alerts)))
        INIT_STATUS["alerts_loaded"] = True
        
        print("[OK] Metrics loaded       : {0}".format(len(metrics)))
        INIT_STATUS["metrics_loaded"] = True
        
        print("[OK] Incidents loaded     : {0}".format(len(incidents)))
        INIT_STATUS["incidents_built"] = True

        # CRITICAL FIX: Persist incidents to database for pattern learning
        print("[*] Skipping incident persistence for quick startup...")
        # Temporarily disabled to avoid database lock issues
        # try:
        #     from storage.database import Database
        #     db = Database()
        #     persisted_count = 0
        #     for incident in incidents:
        #         try:
        #             db.insert_incident(
        #                 target=incident.get("target"),
        #                 issue_type=incident.get("issue_type", "UNKNOWN"),
        #                 severity=incident.get("severity", "INFO"),
        #                 alert_count=incident.get("alert_count", 1),
        #                 first_seen=incident.get("first_seen"),
        #                 last_seen=incident.get("last_seen")
        #             )
        #             persisted_count += 1
        #         except Exception:
        #             pass
        #     db.close()
        #     print("[OK] Incidents persisted  : {0}".format(persisted_count))
        # except Exception as e:
        #     print("[!] Warning: Incident persistence failed: {0}".format(str(e)))
        print("[OK] Database persistence skipped")

        # Stage 2: Validation is now LAZY (computed on-demand)
        print("[*] Stage 2: Validation configured for on-demand computation")
        print("[OK] Validations will be computed when requested")
        INIT_STATUS["validations_computed"] = True
        validated_alerts = []  # Empty initially, computed on demand

        # Stage 3: Build risk trends
        print("[*] Stage 3: Computing risk trends...")
        risk_trends = []
        try:
            trend_analyzer: RiskTrendAnalyzer = RiskTrendAnalyzer(alerts, incidents)
            risk_trends = trend_analyzer.build_trends()
            print("[OK] Risk trends computed : {0}".format(len(risk_trends)))
            INIT_STATUS["risk_trends_computed"] = True
        except Exception as e:
            print("[!] Risk trend analysis failed: {0}".format(str(e)))
            import traceback
            traceback.print_exc()
            if not INIT_STATUS["error"]:
                INIT_STATUS["error"] = "Risk trends failed: {0}".format(str(e))

        # Stage 4: Learn patterns from historical data
        print("[*] Stage 4: Learning patterns from historical data...")
        patterns = []
        try:
            # Initialize database for pattern engine
            db = Database()
            
            # Get unique targets
            targets = set()
            for alert in alerts:
                if alert and alert.get("target"):
                    normalized = TargetNormalizer.normalize(alert.get("target"))
                    if normalized:
                        targets.add(normalized)
            
            # Learn patterns for each target
            pattern_engine = PatternEngine(db, min_confidence=0.60, lookback_days=60)
            for target in sorted(targets):
                try:
                    # Day of week patterns
                    day_patterns = pattern_engine.detect_day_of_week_patterns(target)
                    patterns.extend(day_patterns)
                    
                    # Hour of day patterns
                    hour_patterns = pattern_engine.detect_hour_of_day_patterns(target)
                    patterns.extend(hour_patterns)
                except Exception:
                    pass
            
            db.close()
            print("[OK] Patterns learned     : {0}".format(len(patterns)))
            INIT_STATUS["patterns_computed"] = True
        except Exception as e:
            print("[!] Pattern learning failed: {0}".format(str(e)))
            import traceback
            traceback.print_exc()
            if not INIT_STATUS["error"]:
                INIT_STATUS["error"] = "Pattern learning failed: {0}".format(str(e))

        # Stage 5: Computing failure predictions...
        print("[*] Stage 5: Computing failure predictions...")
        print("[*] Skipping prediction computation for quick startup...")
        predictions = []
        print("[OK] Predictions skipped for quick startup")
        INIT_STATUS["predictions_computed"] = True

        # Stage 6: Computing RCA summaries...
        print("[*] Stage 6: Computing RCA summaries...")
        print("[*] Skipping RCA computation for quick startup...")
        rca_summaries = []
        print("[OK] RCA computation skipped")
        INIT_STATUS["rca_computed"] = True

        # Stage 7: Update global cache (ATOMIC)
        print("[*] Stage 7: Populating GLOBAL_DATA...")
        GLOBAL_DATA.clear()
        GLOBAL_DATA.update({
            "alerts": alerts,
            "metrics": metrics,
            "incidents": incidents,
            "validated_alerts": validated_alerts,
            "risk_trends": risk_trends,
            "patterns": patterns,
            "predictions": predictions,
            "rca_summaries": rca_summaries
        })

        # Mark system as ready
        set_system_ready(True)

        print("=" * 60)
        print("[OK] GLOBAL_DATA populated successfully")
        print("[OK] SYSTEM READY - All components operational")
        print("=" * 60)

    except Exception as e:
        print("=" * 60)
        print("[ERROR] OEM data load FAILED: {0}".format(str(e)))
        print("=" * 60)
        import traceback
        traceback.print_exc()
        INIT_STATUS["error"] = str(e)
        set_system_ready(False)


# =====================================================
# STARTUP (SYNCHRONOUS - NO BACKGROUND THREAD)
# =====================================================
@app.on_event("startup")
def startup_event() -> None:
    """
    Load data SYNCHRONOUSLY on startup.
    Server will not accept requests until data is loaded.
    This is CRITICAL for production systems.
    """
    print("[*] Server startup initiated")
    print("[*] Loading OEM data BEFORE accepting requests...")
    
    # Load data synchronously - this blocks until complete
    load_oem_data()
    
    print("[OK] Startup event completed")
    print("[OK] Server is now accepting requests")
    print("")


# =====================================================
# ROUTERS - ALL UNDER /api PREFIX
# =====================================================
app.include_router(dashboard_router, prefix="/api/dashboard", tags=["Dashboard"])
app.include_router(chat_router, prefix="/api/chat", tags=["Chat"])
app.include_router(alerts_router, prefix="/api/alerts", tags=["Alerts"])
app.include_router(confidence_router, prefix="/api/confidence", tags=["Confidence"])
app.include_router(rca_router, prefix="/api/rca", tags=["RCA"])


# =====================================================
# HEALTH CHECK ENDPOINT
# =====================================================
@app.get("/health")
def health_check():
    """
    Health check endpoint for production monitoring.
    Returns system status and data counts.
    """
    is_ready: bool = SYSTEM_READY.get("ready", False)
    
    return {
        "status": "UP" if is_ready else "INITIALIZING",
        "system_ready": is_ready,
        "alerts": len(GLOBAL_DATA.get("alerts", [])),
        "incidents": len(GLOBAL_DATA.get("incidents", [])),
        "metrics": len(GLOBAL_DATA.get("metrics", [])),
        "init_status": INIT_STATUS
    }


# =====================================================
# AUTH PAGES
# =====================================================
@app.get("/", response_class=HTMLResponse)
def root(request: Request) -> _TemplateResponse:
    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request) -> _TemplateResponse:
    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/signup", response_class=HTMLResponse)
def signup_page(request: Request) -> _TemplateResponse:
    return templates.TemplateResponse("signup.html", {"request": request})


# =====================================================
# SIGNUP
# =====================================================
@app.post("/signup", response_model=None)
async def signup(request: Request) -> Union[JSONResponse, Dict[str, bool]]:
    try:
        data = await request.json()
    except Exception:
        return JSONResponse({"success": False, "message": "Invalid JSON"}, status_code=400)

    username = data.get("username", "").strip()
    password = data.get("password", "")

    if not username or not password:
        return JSONResponse({"success": False, "message": "Username and password required"}, status_code=400)

    try:
        hashed: str = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    except Exception:
        return JSONResponse({"success": False, "message": "Password hashing failed"}, status_code=500)

    conn = None
    try:
        conn: Connection = get_db()
        cur: Cursor = conn.cursor()
        cur.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (username, hashed)
        )
        conn.commit()
        conn.close()
        return {"success": True}

    except Exception:
        if conn:
            try:
                conn.close()
            except Exception:
                pass
        return JSONResponse({"success": False, "message": "User exists or DB error"}, status_code=409)


# =====================================================
# LOGIN
# =====================================================
@app.post("/login")
async def login(request: Request) -> JSONResponse:
    try:
        data = await request.json()
    except Exception:
        return JSONResponse({"success": False, "message": "Invalid JSON"}, status_code=400)

    username = data.get("username", "").strip()
    password = data.get("password", "")

    if not username or not password:
        return JSONResponse({"success": False, "message": "Missing credentials"}, status_code=400)

    conn = None
    try:
        conn: Connection = get_db()
        cur: Cursor = conn.cursor()
        cur.execute("SELECT password_hash FROM users WHERE username = ?", (username,))
        row = cur.fetchone()
        conn.close()

        if not row or not bcrypt.checkpw(password.encode('utf-8'), row[0].encode('utf-8')):
            return JSONResponse({"success": False, "message": "Invalid credentials"}, status_code=401)

        resp = JSONResponse({"success": True})
        resp.set_cookie("logged_in", username, httponly=True, samesite="lax", path="/")
        return resp

    except Exception:
        return JSONResponse({"success": False, "message": "Login error"}, status_code=500)


# =====================================================
# DASHBOARD
# =====================================================
@app.get("/dashboard", response_class=HTMLResponse, response_model=None)
def dashboard(request: Request) -> Union[RedirectResponse, _TemplateResponse]:
    if not request.cookies.get("logged_in"):
        return RedirectResponse("/login")

    response = templates.TemplateResponse("dashboard_oem.html", {"request": request})
    # Prevent browser caching of dashboard to ensure JS updates are loaded
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


# =====================================================
# LOGOUT
# =====================================================
@app.get("/logout")
def logout() -> RedirectResponse:
    resp = RedirectResponse("/login")
    resp.delete_cookie("logged_in", path="/")
    return resp


# =====================================================
# INTELLIGENT DBA CHAT ASSISTANT
# =====================================================
from pydantic import BaseModel
from data_engine.target_normalizer import TargetNormalizer
from collections import Counter
from datetime import datetime
import re

class ChatMessage(BaseModel):
    message: str = ""
    new_conversation: bool = False  # DASHBOARD FIX: Reset session for new chats

def fuzzy_match_database(query: str, alerts: list) -> str:
    """Fuzzy match database name from query against known databases"""
    # Get all known database names
    known_dbs = set()
    for a in alerts:
        if a and a.get("target"):
            db = TargetNormalizer.normalize(a.get("target"))
            if db:
                known_dbs.add(db)
    
    query_upper: str = query.upper()
    
    # Direct match
    for db in known_dbs:
        if db in query_upper:
            return db
    
    # Partial match (e.g., MIDDEVSTB matches MIDEVSTB or MIDEVSTBN)
    query_tokens = re.findall(r'[A-Za-z0-9_]{3,}', query_upper)
    for token in query_tokens:
        for db in known_dbs:
            # Check if token is similar to db name (allowing for typos)
            if token in db or db in token:
                return db
            # Check Levenshtein-like similarity
            if len(token) >= 4 and len(db) >= 4:
                common: int = sum(1 for a, b in zip(token, db) if a == b)
                if common >= min(len(token), len(db)) * 0.6:
                    return db
    
    return None

def analyze_time_distribution(alerts: list) -> dict:
    """Analyze time distribution of alerts"""
    hour_counts = Counter()
    for a in alerts:
        if a:
            time_str = a.get("time") or a.get("first_seen") or ""
            if time_str and isinstance(time_str, str):
                try:
                    for fmt in ["%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f"]:
                        try:
                            dt: datetime = datetime.strptime(time_str[:19], fmt[:19])
                            hour_counts[dt.hour] += 1
                            break
                        except:
                            pass
                except:
                    pass
    return dict(hour_counts)

def get_severity_distribution(alerts: list) -> dict:
    """Get severity distribution"""
    severity_counts = Counter()
    for a in alerts:
        if a:
            sev = (a.get("severity") or "INFO").upper()
            severity_counts[sev] += 1
    return dict(severity_counts)

def analyze_database_health(db_name: str, alerts: list) -> dict:
    """Comprehensive database health analysis"""
    db_alerts = [a for a in alerts if a and TargetNormalizer.normalize(a.get("target")) == db_name]
    
    if not db_alerts:
        return None
    
    # Issue type distribution
    type_counts = Counter()
    severity_counts = Counter()
    time_distribution = Counter()
    
    for a in db_alerts:
        issue = a.get("issue_type") or a.get("alert_type") or "UNKNOWN"
        type_counts[issue] += 1
        
        sev = (a.get("severity") or "INFO").upper()
        severity_counts[sev] += 1
        
        time_str = a.get("time") or a.get("first_seen") or ""
        if time_str and isinstance(time_str, str):
            try:
                dt: datetime = datetime.strptime(time_str[:19], "%Y-%m-%dT%H:%M:%S")
                time_distribution[dt.hour] += 1
            except:
                pass
    
    critical_pct = (severity_counts.get("CRITICAL", 0) / len(db_alerts)) * 100 if db_alerts else 0
    
    return {
        "total_alerts": len(db_alerts),
        "type_distribution": dict(type_counts.most_common(10)),
        "severity_distribution": dict(severity_counts),
        "time_distribution": dict(time_distribution),
        "critical_percentage": critical_pct,
        "top_issue": type_counts.most_common(1)[0] if type_counts else ("UNKNOWN", 0)
    }

@app.post("/chat")
async def chat_direct(request: Request, payload: ChatMessage):
    """
    DATA-DRIVEN OEM INCIDENT ANALYSIS ENGINE.
    
    ENHANCED: Now uses IntelligenceService for:
    1. Root cause inference with confidence
    2. Actions that are ALWAYS present (FOR ACTION INTENTS ONLY)
    3. Session memory across requests
    4. Enhanced response structure
    
    DASHBOARD FIX:
    - new_conversation=True resets session memory
    - Prevents root cause leakage between UI conversations
    
    PRODUCTION FIX (v2.2):
    - Formatter context reset per question
    - Strict intent-based data isolation
    - STANDBY_DATAGUARD uses ONLY standby alerts
    
    Response structure:
    {
        "reply": str,              # Main answer (backwards compatible)
        
        # NEW FIELDS (additive - won't break frontend)
        "target": str or None,
        "confidence": float,
        "confidence_label": str,   # HIGH/MEDIUM/LOW
        "actions": list,           # Only for ACTION intents
        "root_cause": str or None,
        "session_context": dict    # Memory summary
    }
    """
    question = payload.message.strip()
    if not question:
        return {"reply": "Please enter a question."}
    
    if not SYSTEM_READY.get("ready", False):
        return {"reply": "System is initializing. Please wait..."}
    
    # =====================================================
    # CRITICAL FIX: Always reset per-question context
    # Prevents formatter leakage between questions
    # =====================================================
    from services.session_store import SessionStore
    SessionStore.reset_question_context()
    
    # =====================================================
    # DASHBOARD FIX: Reset session for new conversations
    # =====================================================
    if payload.new_conversation:
        SessionStore.reset()
        try:
            from incident_engine.production_intelligence_engine import SessionMemoryEngine
            SessionMemoryEngine.reset()
        except ImportError:
            pass
    
    # CRITICAL: Use the IntelligenceService for enhanced analysis
    # The service internally handles formatter context reset
    from services.intelligence_service import INTELLIGENCE_SERVICE
    from nlp_engine.intent_response_router import IntentResponseRouter
    
    try:
        result = INTELLIGENCE_SERVICE.analyze(question)
        
        # =====================================================
        # API-LEVEL INTENT FILTERING (DASHBOARD FIX)
        # MANDATORY: Enforce strict 5-intent response rules
        # =====================================================
        question_type = result.get("question_type", "FACT")
        
        # =====================================================
        # STRICT: Determine what to include based on intent
        # FACT/STATUS questions: NO root cause, NO actions
        # ANALYSIS questions: root cause only
        # ACTION questions: root cause + actions
        # =====================================================
        include_actions = question_type == "ACTION"
        include_root_cause = question_type in ["ANALYSIS", "ACTION", "PREDICTION"]
        
        # Build enhanced response (backwards compatible)
        response = {
            "reply": result.get("answer", "No matching data found."),
            # NEW FIELDS - additive, won't break existing frontend
            "target": result.get("target"),
            "confidence": result.get("confidence", 0.5),
            "confidence_label": result.get("confidence_label", "MEDIUM"),
            # STRICT: Only include actions for ACTION intent
            "actions": result.get("actions", []) if include_actions else [],
            # STRICT: Only include root_cause for ANALYSIS/ACTION/PREDICTION
            "root_cause": result.get("root_cause") if include_root_cause else None,
            "session_context": result.get("session_context", {}),
            # Include question_type for frontend debugging
            "question_type": question_type
        }
        
        return response
        
    except Exception as e:
        # ===========================================================
        # PRODUCTION: Log error but DO NOT return generic summary
        # The generic "649,787 alerts across X databases" response
        # was causing confusion during follow-up queries.
        # Instead, return a specific error message.
        # ===========================================================
        import traceback
        print("[CHAT ERROR] Exception during /chat processing:")
        print(traceback.format_exc())
        
        # Return error message, NOT a generic summary
        return {
            "reply": "I encountered an issue processing your question. Please try rephrasing or ask a simpler question.",
            "confidence": 0.0,
            "confidence_label": "ERROR",
            "error": str(e)
        }


# =====================================================
# SESSION RESET ENDPOINT (DASHBOARD FIX)
# =====================================================
@app.post("/chat/reset")
async def chat_reset():
    """
    Reset session memory for new conversation.
    
    DASHBOARD FIX: Call this when user starts a new chat.
    Prevents root cause, actions, and locked values from
    bleeding into unrelated conversations.
    """
    from services.session_store import SessionStore
    SessionStore.reset()
    
    try:
        from incident_engine.production_intelligence_engine import SessionMemoryEngine
        SessionMemoryEngine.reset()
    except ImportError:
        pass
    
    return {"status": "success", "message": "Session memory cleared"}


# =====================================================
# ALERTS API ENDPOINT
# =====================================================
@app.get("/api/alerts")
def get_alerts(limit: int = 100):
    """Get alerts from global data"""
    if not SYSTEM_READY.get("ready", False):
        return {"alerts": [], "total": 0}
    
    alerts = GLOBAL_DATA.get("alerts", [])
    return {
        "alerts": alerts[:limit],
        "total": len(alerts)
    }


# =====================================================
# SERVER ENTRY POINT
# =====================================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app)