# -*- coding: utf-8 -*-
"""
Query Executor - Executes query plans against the alert data
Works at the raw data level (CSV rows) to get accurate results
"""

import os
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
import re


class QueryResult:
    """Structured query result"""
    
    def __init__(self):
        self.success = True
        self.error_message = None
        self.query_type = None
        self.total_count = 0
        self.filtered_count = 0
        self.data = []  # List of alert dicts
        self.aggregations = {}  # severity counts, database counts, etc.
        self.metadata = {}  # offset, limit, has_more, etc.
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'success': self.success,
            'error_message': self.error_message,
            'query_type': self.query_type,
            'total_count': self.total_count,
            'filtered_count': self.filtered_count,
            'data': self.data,
            'aggregations': self.aggregations,
            'metadata': self.metadata
        }


class QueryExecutor:
    """Executes query plans against the CSV alert data"""
    
    def __init__(self, data_path: str = None):
        self.data_path = data_path or os.path.join(
            os.path.dirname(os.path.dirname(__file__)), 
            'data', 'alerts', 'oem_alerts_raw.csv'
        )
        self._df = None
        self._last_load_time = None
        self._cache_duration = 300  # 5 minutes cache
    
    def _load_data(self) -> pd.DataFrame:
        """Load alert data from CSV with caching"""
        now = datetime.now()
        
        if self._df is not None and self._last_load_time:
            if (now - self._last_load_time).total_seconds() < self._cache_duration:
                return self._df
        
        if not os.path.exists(self.data_path):
            raise FileNotFoundError(f"Alert data file not found: {self.data_path}")
        
        self._df = pd.read_csv(self.data_path, encoding='utf-8', low_memory=False)
        self._last_load_time = now
        
        # Normalize column names
        self._df.columns = [c.strip().lower() for c in self._df.columns]
        
        # Parse alert_time if exists
        if 'alert_time' in self._df.columns:
            self._df['alert_time'] = pd.to_datetime(
                self._df['alert_time'], 
                errors='coerce',
                format='%Y-%m-%d %H:%M:%S'
            )
        
        return self._df
    
    def execute(self, query_plan) -> QueryResult:
        """Execute a query plan and return results"""
        result = QueryResult()
        result.query_type = query_plan.query_type
        
        try:
            df = self._load_data()
            result.total_count = len(df)
            
            # Apply filters
            filtered_df = self._apply_filters(df, query_plan.filters)
            result.filtered_count = len(filtered_df)
            
            # Execute based on query type
            if query_plan.query_type == 'COUNT':
                result = self._execute_count(filtered_df, query_plan, result)
            elif query_plan.query_type == 'SUMMARY':
                result = self._execute_summary(filtered_df, query_plan, result)
            elif query_plan.query_type == 'LIST':
                result = self._execute_list(filtered_df, query_plan, result)
            elif query_plan.query_type == 'AGGREGATE':
                result = self._execute_aggregate(filtered_df, query_plan, result)
            elif query_plan.query_type == 'DETAIL':
                result = self._execute_detail(filtered_df, query_plan, result)
            elif query_plan.query_type == 'COMPARE':
                result = self._execute_compare(df, query_plan, result)
            else:
                # Default to summary
                result = self._execute_summary(filtered_df, query_plan, result)
            
        except Exception as e:
            result.success = False
            result.error_message = str(e)
        
        return result
    
    def _apply_filters(self, df: pd.DataFrame, filters: Dict[str, Any]) -> pd.DataFrame:
        """Apply all filters to the dataframe"""
        if not filters:
            return df
        
        filtered = df.copy()
        
        # Database filter (target_name) - STRICT EXACT MATCHING (BUG FIX)
        # MIDEVSTB should NOT match MIDEVSTBN
        if filters.get('database'):
            db_pattern = filters['database'].upper()
            if 'target_name' in filtered.columns:
                # STRICT match - exact database name only
                mask = filtered['target_name'].fillna('').str.upper() == db_pattern
                filtered = filtered[mask]
        
        # Multiple databases filter - STRICT EXACT MATCHING
        if filters.get('databases'):
            if 'target_name' in filtered.columns:
                db_list = [d.upper() for d in filters['databases']]
                mask = filtered['target_name'].fillna('').str.upper().isin(db_list)
                filtered = filtered[mask]
        
        # Severity filter - case insensitive
        if filters.get('severity'):
            sev = filters['severity'].upper()
            if 'alert_state' in filtered.columns:
                mask = filtered['alert_state'].fillna('').str.upper() == sev
                filtered = filtered[mask]
        
        # Multiple severities filter
        if filters.get('severities'):
            if 'alert_state' in filtered.columns:
                sev_list = [s.upper() for s in filters['severities']]
                mask = filtered['alert_state'].fillna('').str.upper().isin(sev_list)
                filtered = filtered[mask]
        
        # Alert type filter (message content)
        if filters.get('alert_type'):
            alert_type = filters['alert_type'].lower()
            if 'message' in filtered.columns:
                mask = filtered['message'].fillna('').str.lower().str.contains(
                    alert_type, regex=False, na=False
                )
                filtered = filtered[mask]
        
        # Issue type filter (maps to keywords in message)
        if filters.get('issue_type'):
            issue_type = filters['issue_type'].upper()
            if 'message' in filtered.columns:
                issue_keywords = self._get_issue_keywords(issue_type)
                if issue_keywords:
                    pattern = '|'.join(issue_keywords)
                    mask = filtered['message'].fillna('').str.lower().str.contains(
                        pattern, regex=True, case=False, na=False
                    )
                    filtered = filtered[mask]
        
        # ORA code filter
        if filters.get('ora_codes'):
            if 'message' in filtered.columns:
                ora_patterns = [f"ORA-{code}" for code in filters['ora_codes']]
                pattern = '|'.join(ora_patterns)
                mask = filtered['message'].fillna('').str.contains(
                    pattern, regex=True, case=False, na=False
                )
                filtered = filtered[mask]
        
        # Time range filter
        if filters.get('time_range') and 'alert_time' in filtered.columns:
            time_range = filters['time_range']
            now = datetime.now()
            
            if time_range == 'today':
                start_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
                mask = filtered['alert_time'] >= start_time
                filtered = filtered[mask]
            elif time_range == 'last_24h':
                start_time = now - timedelta(hours=24)
                mask = filtered['alert_time'] >= start_time
                filtered = filtered[mask]
            elif time_range == 'last_hour':
                start_time = now - timedelta(hours=1)
                mask = filtered['alert_time'] >= start_time
                filtered = filtered[mask]
            elif time_range == 'this_week':
                start_time = now - timedelta(days=now.weekday())
                start_time = start_time.replace(hour=0, minute=0, second=0, microsecond=0)
                mask = filtered['alert_time'] >= start_time
                filtered = filtered[mask]
            elif time_range == 'last_7_days':
                start_time = now - timedelta(days=7)
                mask = filtered['alert_time'] >= start_time
                filtered = filtered[mask]
            elif time_range == 'this_month':
                start_time = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                mask = filtered['alert_time'] >= start_time
                filtered = filtered[mask]
        
        return filtered
    
    def _get_issue_keywords(self, issue_type: str) -> List[str]:
        """Get keywords for issue types"""
        issue_map = {
            'DATAGUARD': ['dataguard', 'data guard', 'standby', 'sync', 'lag'],
            'TABLESPACE': ['tablespace', 'space', 'storage', 'disk'],
            'MEMORY': ['memory', 'sga', 'pga', 'buffer', 'cache'],
            'PERFORMANCE': ['performance', 'slow', 'wait', 'cpu', 'latency'],
            'CONNECTION': ['connection', 'listener', 'tns', 'network'],
            'BACKUP': ['backup', 'rman', 'archive', 'recovery'],
            'REPLICATION': ['replication', 'sync', 'goldengate', 'streams'],
            'LOCK': ['lock', 'deadlock', 'blocking', 'contention'],
            'INDEX': ['index', 'rebuild', 'fragmented'],
            'ARCHIVE': ['archive', 'archivelog', 'redo'],
        }
        return issue_map.get(issue_type, [])
    
    def _execute_count(self, df: pd.DataFrame, query_plan, result: QueryResult) -> QueryResult:
        """Execute a COUNT query"""
        result.data = []
        result.aggregations = {
            'total': len(df)
        }
        
        # Add severity breakdown if requested
        if 'alert_state' in df.columns:
            severity_counts = df['alert_state'].fillna('Unknown').value_counts().to_dict()
            result.aggregations['by_severity'] = severity_counts
        
        return result
    
    def _execute_summary(self, df: pd.DataFrame, query_plan, result: QueryResult) -> QueryResult:
        """Execute a SUMMARY query - counts + breakdowns without listing alerts"""
        result.data = []
        result.aggregations = {
            'total': len(df)
        }
        
        # Severity breakdown
        if 'alert_state' in df.columns:
            severity_counts = df['alert_state'].fillna('Unknown').value_counts().to_dict()
            result.aggregations['by_severity'] = severity_counts
        
        # Database breakdown
        if 'target_name' in df.columns:
            db_counts = df['target_name'].fillna('Unknown').value_counts().head(10).to_dict()
            result.aggregations['by_database'] = db_counts
        
        # Top alert messages
        if 'message' in df.columns:
            top_messages = df['message'].fillna('Unknown').value_counts().head(5).to_dict()
            result.aggregations['top_messages'] = top_messages
        
        return result
    
    def _execute_list(self, df: pd.DataFrame, query_plan, result: QueryResult) -> QueryResult:
        """Execute a LIST query - return paginated alert records"""
        # Sorting
        if query_plan.sort_by and query_plan.sort_by in df.columns:
            ascending = query_plan.sort_order != 'desc'
            df = df.sort_values(by=query_plan.sort_by, ascending=ascending)
        elif 'alert_time' in df.columns:
            # Default sort by alert_time descending (newest first)
            df = df.sort_values(by='alert_time', ascending=False)
        
        # Pagination
        offset = query_plan.offset or 0
        limit = query_plan.limit or 10
        
        paginated_df = df.iloc[offset:offset + limit]
        
        # Convert to list of dicts
        result.data = []
        for _, row in paginated_df.iterrows():
            alert = {}
            for col in df.columns:
                val = row[col]
                if pd.isna(val):
                    alert[col] = None
                elif isinstance(val, pd.Timestamp):
                    alert[col] = val.strftime('%Y-%m-%d %H:%M:%S')
                else:
                    alert[col] = str(val)
            result.data.append(alert)
        
        # Metadata
        result.metadata = {
            'offset': offset,
            'limit': limit,
            'has_more': (offset + limit) < len(df),
            'showing': len(result.data)
        }
        
        # Also add severity breakdown
        if 'alert_state' in df.columns:
            severity_counts = df['alert_state'].fillna('Unknown').value_counts().to_dict()
            result.aggregations['by_severity'] = severity_counts
        
        return result
    
    def _execute_aggregate(self, df: pd.DataFrame, query_plan, result: QueryResult) -> QueryResult:
        """Execute an AGGREGATE query - group by and count"""
        group_by = query_plan.aggregation.get('group_by', 'alert_state') if query_plan.aggregation else 'alert_state'
        
        if group_by in df.columns:
            agg_result = df[group_by].fillna('Unknown').value_counts().to_dict()
            result.aggregations = {
                'group_by': group_by,
                'counts': agg_result,
                'total': len(df)
            }
        else:
            result.aggregations = {'total': len(df)}
        
        return result
    
    def _execute_detail(self, df: pd.DataFrame, query_plan, result: QueryResult) -> QueryResult:
        """Execute a DETAIL query - get full details of specific alerts"""
        # For detail queries, return more fields and fewer records
        limit = min(query_plan.limit or 5, 20)
        
        if 'alert_time' in df.columns:
            df = df.sort_values(by='alert_time', ascending=False)
        
        detailed_df = df.head(limit)
        
        result.data = []
        for _, row in detailed_df.iterrows():
            alert = {}
            for col in df.columns:
                val = row[col]
                if pd.isna(val):
                    alert[col] = None
                elif isinstance(val, pd.Timestamp):
                    alert[col] = val.strftime('%Y-%m-%d %H:%M:%S')
                else:
                    alert[col] = str(val)
            result.data.append(alert)
        
        return result
    
    def _execute_compare(self, df: pd.DataFrame, query_plan, result: QueryResult) -> QueryResult:
        """Execute a COMPARE query - compare two entities"""
        compare = query_plan.aggregation.get('compare', {}) if query_plan.aggregation else {}
        entity1 = compare.get('entity1')
        entity2 = compare.get('entity2')
        
        if not entity1 or not entity2:
            result.error_message = "Comparison requires two entities"
            return result
        
        if 'target_name' in df.columns:
            # Compare two databases
            df1 = df[df['target_name'].fillna('').str.upper().str.contains(entity1.upper())]
            df2 = df[df['target_name'].fillna('').str.upper().str.contains(entity2.upper())]
            
            result.aggregations = {
                entity1: {
                    'total': len(df1),
                    'by_severity': df1['alert_state'].fillna('Unknown').value_counts().to_dict() if 'alert_state' in df1.columns else {}
                },
                entity2: {
                    'total': len(df2),
                    'by_severity': df2['alert_state'].fillna('Unknown').value_counts().to_dict() if 'alert_state' in df2.columns else {}
                }
            }
        
        return result


# Singleton instance
_executor = None

def get_executor() -> QueryExecutor:
    """Get singleton query executor instance"""
    global _executor
    if _executor is None:
        _executor = QueryExecutor()
    return _executor


# Test
if __name__ == '__main__':
    from query_planner import QueryPlan
    
    executor = QueryExecutor()
    
    # Test COUNT query
    plan = QueryPlan()
    plan.query_type = 'COUNT'
    plan.filters = {'database': 'MIDEVSTB'}
    
    result = executor.execute(plan)
    print(f"COUNT result: {result.filtered_count} alerts")
    print(f"Aggregations: {result.aggregations}")
    
    # Test LIST query with severity filter
    plan2 = QueryPlan()
    plan2.query_type = 'LIST'
    plan2.filters = {'database': 'MIDEVSTB', 'severity': 'CRITICAL'}
    plan2.limit = 5
    
    result2 = executor.execute(plan2)
    print(f"\nLIST result: {len(result2.data)} alerts shown")
    for alert in result2.data:
        print(f"  - {alert.get('target_name')}: {alert.get('alert_state')} - {alert.get('message', '')[:50]}...")
