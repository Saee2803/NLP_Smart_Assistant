# services/query_planner.py
"""
==============================================================
QUERY PLANNER - Convert intent + entities to data operations
==============================================================

Converts natural language understanding into structured query plans
that can be executed against the CSV data.

Query Types:
- COUNT: Return count with breakdown
- SUMMARY: Return summary without list
- LIST: Return list of items
- AGGREGATE: Return aggregated data
- DETAIL: Return detailed info about single item

Python 3.6.8 compatible.
"""

from typing import Dict, Any, List, Optional


class QueryPlan:
    """
    Represents a structured query plan for data execution.
    """
    
    # Query types
    TYPE_COUNT = "COUNT"
    TYPE_SUMMARY = "SUMMARY"
    TYPE_LIST = "LIST"
    TYPE_AGGREGATE = "AGGREGATE"
    TYPE_DETAIL = "DETAIL"
    TYPE_COMPARE = "COMPARE"
    
    def __init__(self):
        self.query_type = self.TYPE_LIST
        self.data_source = "alerts"  # alerts, incidents, metrics
        self.filters = {}
        self.sort_by = None
        self.sort_order = "desc"
        self.limit = None
        self.offset = 0
        self.group_by = None
        self.aggregations = []
        self.projections = []  # Fields to include in output
        self.include_breakdown = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert plan to dictionary."""
        return {
            "query_type": self.query_type,
            "data_source": self.data_source,
            "filters": self.filters,
            "sort_by": self.sort_by,
            "sort_order": self.sort_order,
            "limit": self.limit,
            "offset": self.offset,
            "group_by": self.group_by,
            "aggregations": self.aggregations,
            "include_breakdown": self.include_breakdown
        }


class QueryPlanner:
    """
    Plans data queries based on intent and entities.
    
    Takes NLU output and creates executable query plans.
    """
    
    # Intent to query type mapping
    INTENT_QUERY_MAP = {
        # Summary/Count intents
        "ALERT_SUMMARY": QueryPlan.TYPE_SUMMARY,
        "ALERT_COUNT": QueryPlan.TYPE_COUNT,
        
        # List intents
        "ALERT_LIST": QueryPlan.TYPE_LIST,
        "FOLLOWUP_LIMIT": QueryPlan.TYPE_LIST,
        "FOLLOWUP_SEVERITY": QueryPlan.TYPE_LIST,
        "ISSUE_TYPE_QUERY": QueryPlan.TYPE_LIST,
        
        # Aggregate intents
        "DATABASE_QUERY": QueryPlan.TYPE_AGGREGATE,
        "TIME_BASED": QueryPlan.TYPE_AGGREGATE,
        
        # Analysis intents
        "ROOT_CAUSE": QueryPlan.TYPE_DETAIL,
        "RECOMMENDATION": QueryPlan.TYPE_DETAIL,
        "HEALTH_CHECK": QueryPlan.TYPE_SUMMARY,
        "PREDICTION": QueryPlan.TYPE_DETAIL,
        
        # Comparison
        "COMPARISON": QueryPlan.TYPE_COMPARE
    }
    
    def plan(self, intent: Dict[str, Any], 
             merged_entities: Dict[str, Any],
             context: Dict[str, Any] = None) -> QueryPlan:
        """
        Create a query plan from intent and entities.
        
        Args:
            intent: Intent classification result (dict) or intent name (str)
            merged_entities: Merged entities with context
            context: Additional context information
            
        Returns:
            QueryPlan ready for execution
        """
        plan = QueryPlan()
        
        # Handle intent as string or dict
        if isinstance(intent, dict):
            intent_name = intent.get("intent", "UNKNOWN")
        else:
            intent_name = str(intent) if intent else "UNKNOWN"
        
        # Set query type based on intent
        plan.query_type = self.INTENT_QUERY_MAP.get(intent_name, QueryPlan.TYPE_LIST)
        
        # Build filters
        plan.filters = self._build_filters(merged_entities)
        
        # Set pagination
        plan.limit = merged_entities.get("limit")
        plan.offset = merged_entities.get("offset", 0)
        
        # Handle specific intents
        if intent_name == "ALERT_SUMMARY":
            plan = self._plan_alert_summary(plan, merged_entities)
        
        elif intent_name == "ALERT_COUNT":
            plan = self._plan_alert_count(plan, merged_entities)
        
        elif intent_name in ["ALERT_LIST", "FOLLOWUP_LIMIT", "FOLLOWUP_SEVERITY"]:
            plan = self._plan_alert_list(plan, merged_entities)
        
        elif intent_name == "ISSUE_TYPE_QUERY":
            plan = self._plan_issue_type(plan, merged_entities)
        
        elif intent_name == "DATABASE_QUERY":
            plan = self._plan_database_query(plan, merged_entities)
        
        elif intent_name == "ROOT_CAUSE":
            plan = self._plan_root_cause(plan, merged_entities)
        
        elif intent_name == "RECOMMENDATION":
            plan = self._plan_recommendation(plan, merged_entities)
        
        elif intent_name == "HEALTH_CHECK":
            plan = self._plan_health_check(plan, merged_entities)
        
        return plan
    
    def _build_filters(self, entities: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build filter dictionary from entities.
        Uses simple key-value pairs that QueryExecutor understands.
        """
        filters = {}
        
        # Database filter - simple value for executor
        if entities.get("database"):
            filters["database"] = entities["database"].upper()
        
        # Severity filter - simple value
        if entities.get("severity"):
            filters["severity"] = entities["severity"].upper()
        
        # Issue type filter - simple string
        if entities.get("issue_type"):
            filters["issue_type"] = entities["issue_type"].upper()
        
        # ORA code filter - list of codes
        if entities.get("ora_codes"):
            filters["ora_codes"] = entities["ora_codes"]
        
        # Time range filter - simple string
        if entities.get("time_range"):
            filters["time_range"] = entities["time_range"]
        
        # Alert type filter (if different from issue_type)
        if entities.get("alert_type"):
            filters["alert_type"] = entities["alert_type"]
        
        return filters
        
        return filters
    
    def _get_issue_keywords(self, issue_type: str) -> List[str]:
        """Get keywords for issue type filtering."""
        issue_keywords = {
            "standby": ["standby", "data guard", "dataguard", "apply", "transport", "mrp", "redo", "ora-16"],
            "tablespace": ["tablespace", "space", "full", "extent", "ora-1654", "ora-1653"],
            "connection": ["connection", "listener", "tns", "ora-12541", "ora-12537"],
            "memory": ["memory", "pga", "sga", "ora-4031"],
            "performance": ["slow", "wait", "lock", "blocking"],
            "backup": ["backup", "rman", "archive"],
            "internal": ["internal error", "ora-600", "ora-7445"]
        }
        return issue_keywords.get(issue_type, [issue_type])
    
    def _plan_alert_summary(self, plan: QueryPlan, entities: Dict) -> QueryPlan:
        """Plan for alert summary (count + breakdown, no list)."""
        plan.query_type = QueryPlan.TYPE_SUMMARY
        plan.include_breakdown = True
        plan.aggregations = [
            {"field": "severity", "function": "count", "alias": "severity_breakdown"}
        ]
        plan.limit = None  # No list needed
        return plan
    
    def _plan_alert_count(self, plan: QueryPlan, entities: Dict) -> QueryPlan:
        """Plan for alert count."""
        plan.query_type = QueryPlan.TYPE_COUNT
        plan.include_breakdown = True
        plan.aggregations = [
            {"field": "severity", "function": "count", "alias": "severity_count"}
        ]
        return plan
    
    def _plan_alert_list(self, plan: QueryPlan, entities: Dict) -> QueryPlan:
        """Plan for alert listing."""
        plan.query_type = QueryPlan.TYPE_LIST
        plan.sort_by = "alert_time"
        plan.sort_order = "desc"
        plan.limit = entities.get("limit", 20)
        plan.projections = ["target_name", "severity", "message", "alert_time"]
        return plan
    
    def _plan_issue_type(self, plan: QueryPlan, entities: Dict) -> QueryPlan:
        """Plan for issue type query (standby, tablespace, etc.)."""
        plan.query_type = QueryPlan.TYPE_LIST
        plan.sort_by = "alert_time"
        plan.limit = entities.get("limit", 20)
        return plan
    
    def _plan_database_query(self, plan: QueryPlan, entities: Dict) -> QueryPlan:
        """Plan for database-level queries (which has most alerts, etc.)."""
        plan.query_type = QueryPlan.TYPE_AGGREGATE
        plan.group_by = "target_name"
        plan.aggregations = [
            {"field": "target_name", "function": "count", "alias": "alert_count"}
        ]
        plan.sort_by = "alert_count"
        plan.sort_order = "desc"
        plan.limit = 10
        return plan
    
    def _plan_root_cause(self, plan: QueryPlan, entities: Dict) -> QueryPlan:
        """Plan for root cause analysis."""
        plan.query_type = QueryPlan.TYPE_DETAIL
        plan.data_source = "incidents"  # Use incidents for RCA
        plan.projections = ["target_name", "issue_type", "root_cause", "message", "occurrence_count"]
        return plan
    
    def _plan_recommendation(self, plan: QueryPlan, entities: Dict) -> QueryPlan:
        """Plan for recommendation query."""
        plan.query_type = QueryPlan.TYPE_DETAIL
        plan.data_source = "incidents"
        plan.include_breakdown = False
        return plan
    
    def _plan_health_check(self, plan: QueryPlan, entities: Dict) -> QueryPlan:
        """Plan for health check query."""
        plan.query_type = QueryPlan.TYPE_SUMMARY
        plan.aggregations = [
            {"field": "severity", "function": "count"},
            {"field": "issue_type", "function": "count"}
        ]
        plan.include_breakdown = True
        return plan


# Singleton instance
_planner = None

def get_query_planner() -> QueryPlanner:
    """Get the singleton query planner instance."""
    global _planner
    if _planner is None:
        _planner = QueryPlanner()
    return _planner


# Convenience function
def create_query_plan(intent: Dict, entities: Dict, context: Dict = None) -> QueryPlan:
    """Create a query plan from intent and entities."""
    return get_query_planner().plan(intent, entities, context)


# Test
if __name__ == "__main__":
    planner = QueryPlanner()
    
    # Test: show alerts for MIDEVSTB
    intent1 = {"intent": "ALERT_SUMMARY"}
    entities1 = {"database": "MIDEVSTB", "severity": None, "limit": None}
    plan1 = planner.plan(intent1, entities1)
    print("Query 1: show alerts for MIDEVSTB")
    print("Plan:", plan1.to_dict())
    
    # Test: ok show me 18 warning
    intent2 = {"intent": "FOLLOWUP_LIMIT", "is_followup": True}
    entities2 = {"database": "MIDEVSTB", "severity": "WARNING", "limit": 18}
    plan2 = planner.plan(intent2, entities2)
    print("\nQuery 2: ok show me 18 warning")
    print("Plan:", plan2.to_dict())
    
    # Test: which database has most alerts
    intent3 = {"intent": "DATABASE_QUERY"}
    entities3 = {"database": None}
    plan3 = planner.plan(intent3, entities3)
    print("\nQuery 3: which database has most alerts")
    print("Plan:", plan3.to_dict())
