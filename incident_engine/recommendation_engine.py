#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Learning-Based Recommendation Engine for OEM Incident Intelligence System

Tracks issue -> action -> outcome relationships
Persists learning in JSON for recommendations based on historical success rates
"""

import json
import os
from collections import defaultdict


class RecommendationEngine:
    """
    Learns from historical issue resolution outcomes.
    
    Tracks:
    - Issue type (INTERNAL_ERROR, TIMEOUT, etc.)
    - Recommended action (Restart, Tune Memory, etc.)
    - Outcome (SUCCESS, PARTIAL, FAILED)
    
    Recommends actions based on highest success rate.
    """
    
    LEARNING_FILE = "recommendation_history.json"
    
    def __init__(self):
        """Initialize recommendation engine and load learning history"""
        self.history = self._load_history()
    
    # =====================================================
    # MAIN API: RECOMMEND FIX
    # =====================================================
    def recommend_fix(self, issue_type):
        """
        Recommend the best action for an issue type based on success history.
        
        Args:
            issue_type: Issue type (e.g., "INTERNAL_ERROR", "TIMEOUT", "OTHER")
        
        Returns:
            {
                "issue_type": "...",
                "recommended_action": "...",
                "confidence": 0-100,
                "evidence": "Worked X out of Y times",
                "alternatives": [
                    {"action": "...", "success_rate": 0-100},
                    ...
                ]
            }
        """
        if issue_type not in self.history:
            # No learning yet - return default recommendations
            return self._default_recommendation(issue_type)
        
        actions_data = self.history[issue_type]
        
        if not actions_data:
            return self._default_recommendation(issue_type)
        
        # Calculate success rates
        scores = {}
        for action, outcomes in actions_data.items():
            success_count = outcomes.get("success", 0)
            total = outcomes.get("total", 0)
            success_rate = (success_count * 100.0 / total) if total > 0 else 0
            scores[action] = {
                "success_rate": success_rate,
                "success": success_count,
                "total": total
            }
        
        # Find best action
        best_action = max(scores, key=lambda a: scores[a]["success_rate"])
        best_data = scores[best_action]
        
        # Get alternatives
        alternatives = sorted([
            {
                "action": action,
                "success_rate": int(data["success_rate"]),
                "evidence": "{} out of {} times".format(data["success"], data["total"])
            }
            for action, data in scores.items()
            if action != best_action
        ], key=lambda x: x["success_rate"], reverse=True)
        
        confidence = int(best_data["success_rate"])
        evidence = "{} out of {} times".format(best_data["success"], best_data["total"])
        
        return {
            "issue_type": issue_type,
            "recommended_action": best_action,
            "confidence": confidence,
            "evidence": evidence,
            "alternatives": alternatives[:3]  # Top 3 alternatives
        }
    
    # =====================================================
    # LEARNING API: TRACK OUTCOME
    # =====================================================
    def track_outcome(self, issue_type, action, outcome):
        """
        Record the outcome of a recommended action.
        
        Args:
            issue_type: Issue type (e.g., "INTERNAL_ERROR")
            action: Action taken (e.g., "Restart database")
            outcome: Result ("SUCCESS", "PARTIAL", or "FAILED")
        
        Returns:
            True if tracked successfully
        """
        if outcome not in ("SUCCESS", "PARTIAL", "FAILED"):
            return False
        
        if issue_type not in self.history:
            self.history[issue_type] = {}
        
        if action not in self.history[issue_type]:
            self.history[issue_type][action] = {
                "success": 0,
                "partial": 0,
                "failed": 0,
                "total": 0
            }
        
        action_data = self.history[issue_type][action]
        
        if outcome == "SUCCESS":
            action_data["success"] += 1
        elif outcome == "PARTIAL":
            action_data["partial"] += 1
        else:
            action_data["failed"] += 1
        
        action_data["total"] += 1
        
        # Persist to disk
        self._save_history()
        return True
    
    # =====================================================
    # DEFAULT RECOMMENDATIONS (NO LEARNING YET)
    # =====================================================
    def _default_recommendation(self, issue_type):
        """
        Provide default recommendation when no learning data exists.
        Based on common OEM issue patterns.
        """
        defaults = {
            "INTERNAL_ERROR": {
                "action": "Check Oracle alert logs and apply patches",
                "confidence": 40
            },
            "TIMEOUT": {
                "action": "Increase session timeout and check lock contention",
                "confidence": 45
            },
            "MEMORY_ERROR": {
                "action": "Tune SGA and PGA memory parameters",
                "confidence": 50
            },
            "STORAGE_FULL": {
                "action": "Add tablespace storage and clean up old data",
                "confidence": 55
            },
            "PERFORMANCE": {
                "action": "Analyze and rebuild indexes, update statistics",
                "confidence": 45
            },
            "OTHER": {
                "action": "Review OEM alert details and contact DBA team",
                "confidence": 30
            }
        }
        
        default = defaults.get(issue_type, defaults["OTHER"])
        
        return {
            "issue_type": issue_type,
            "recommended_action": default["action"],
            "confidence": default["confidence"],
            "evidence": "No historical data - using default recommendation",
            "alternatives": []
        }
    
    # =====================================================
    # PERSISTENCE
    # =====================================================
    def _load_history(self):
        """Load learning history from JSON file"""
        if os.path.exists(self.LEARNING_FILE):
            try:
                with open(self.LEARNING_FILE, 'r') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}
    
    def _save_history(self):
        """Save learning history to JSON file"""
        try:
            with open(self.LEARNING_FILE, 'w') as f:
                json.dump(self.history, f, indent=2)
        except Exception as e:
            print("Warning: Could not persist learning history: {}".format(str(e)))
    
    # =====================================================
    # ANALYTICS
    # =====================================================
    def get_learning_stats(self):
        """
        Return statistics about learned patterns.
        
        Returns:
            {
                "total_issue_types": int,
                "total_actions_tracked": int,
                "most_reliable_action": "...",
                "issue_stats": [
                    {
                        "issue": "INTERNAL_ERROR",
                        "actions": 5,
                        "best_action": "Check logs",
                        "success_rate": 80
                    },
                    ...
                ]
            }
        """
        total_actions = 0
        issue_stats = []
        best_action_overall = None
        best_success_overall = 0
        
        for issue_type, actions_data in self.history.items():
            if not actions_data:
                continue
            
            total_actions += len(actions_data)
            
            # Find best action for this issue
            best_action_for_issue = None
            best_success_for_issue = 0
            
            for action, outcomes in actions_data.items():
                success_count = outcomes.get("success", 0)
                total = outcomes.get("total", 0)
                success_rate = (success_count * 100.0 / total) if total > 0 else 0
                
                if success_rate > best_success_for_issue:
                    best_success_for_issue = success_rate
                    best_action_for_issue = action
                
                if success_rate > best_success_overall:
                    best_success_overall = success_rate
                    best_action_overall = action
            
            issue_stats.append({
                "issue": issue_type,
                "actions_tracked": len(actions_data),
                "best_action": best_action_for_issue,
                "success_rate": int(best_success_for_issue)
            })
        
        issue_stats.sort(key=lambda x: x["success_rate"], reverse=True)
        
        return {
            "total_issue_types": len(self.history),
            "total_actions_tracked": total_actions,
            "most_reliable_action": best_action_overall,
            "most_reliable_success_rate": int(best_success_overall),
            "issue_stats": issue_stats
        }
