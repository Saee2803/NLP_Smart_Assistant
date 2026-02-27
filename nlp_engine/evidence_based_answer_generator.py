# nlp_engine/evidence_based_answer_generator.py
"""
Evidence-Based Answer Generator

Synthesizes answers from:
- Phase 2 Intelligence (TimeAwarePredictor, DatabaseHealthScorer, MultiCauseRCA)
- Phase 1 Learning (PatternEngine, AnomalyDetector)
- Historical data and trends

Generates natural language explanations with evidence.

Python 3.6 compatible.
"""


class EvidenceBasedAnswerGenerator(object):
    """
    Generate conversational answers with evidence from intelligence engines.
    """
    
    def __init__(self, db, time_aware_predictor=None, health_scorer=None, 
                 multi_cause_rca=None, pattern_engine=None, anomaly_detector=None):
        """
        Initialize generator.
        
        Args:
            db: Database instance
            time_aware_predictor: TimeAwarePredictor instance
            health_scorer: DatabaseHealthScorer instance
            multi_cause_rca: MultiCauseRCA instance
            pattern_engine: PatternEngine instance
            anomaly_detector: AnomalyDetector instance
        """
        self.db = db
        self.time_aware_predictor = time_aware_predictor
        self.health_scorer = health_scorer
        self.multi_cause_rca = multi_cause_rca
        self.pattern_engine = pattern_engine
        self.anomaly_detector = anomaly_detector
    
    # =====================================================
    # PRIMARY API
    # =====================================================
    
    def generate_answer(self, intent, target, context):
        """
        Generate answer based on intent and context.
        
        Args:
            intent: Intent from classifier (WHY, WHEN, HEALTH, RISK, etc.)
            target: Target database name
            context: Entity extraction context
        
        Returns:
            Answer string with evidence
        """
        if not intent or not target:
            return self._generate_clarification_prompt(target, context)
        
        # Route to specific answer generator
        generator_method = getattr(self, '_answer_{0}'.format(intent.lower()), None)
        
        if generator_method:
            return generator_method(target, context)
        else:
            return self._answer_general(target, context)
    
    # =====================================================
    # INTENT-SPECIFIC ANSWER GENERATORS
    # =====================================================
    
    def _answer_why(self, target, context):
        """
        Answer 'Why' questions - root cause analysis.
        
        Integrates with MultiCauseRCA for ranked causes.
        """
        # Get recent incidents for target
        recent_incidents = self.db.get_incidents(target, days=7)
        
        if not recent_incidents:
            return "No recent incidents found for {0}.".format(target)
        
        # Get latest incident
        latest = recent_incidents[0] if recent_incidents else None
        if not latest:
            return "Could not analyze incident for {0}.".format(target)
        
        # Use MultiCauseRCA if available
        if self.multi_cause_rca:
            rca = self.multi_cause_rca.analyze_incident(latest)
            
            if rca and 'causes' in rca and rca['causes']:
                causes = rca['causes']
                
                # Build answer with top causes
                answer_parts = []
                answer_parts.append(
                    "The latest incident for {0} was caused by:".format(target)
                )
                
                for i, cause in enumerate(causes[:3], 1):
                    confidence_pct = int(cause.get('display_confidence', '0').rstrip('%'))
                    cause_name = cause.get('cause_name', 'unknown cause')
                    evidence = cause.get('evidence', 'root cause identified')
                    
                    # Truncate evidence for readability
                    if len(evidence) > 120:
                        evidence = evidence[:117] + '...'
                    
                    answer_parts.append(
                        "{0}. {1} ({2}%) - {3}".format(i, cause_name, confidence_pct, evidence)
                    )
                
                return "\n".join(answer_parts)
        
        # Fallback: return simple cause if available
        if latest.get('description'):
            return "The incident was related to: {0}".format(latest.get('description', 'unknown'))
        
        return "Root cause analysis in progress for {0}.".format(target)
    
    def _answer_when(self, target, context):
        """
        Answer 'When' questions - timing of incidents/predictions.
        
        Integrates with TimeAwarePredictor for risk windows.
        """
        # Get last incident
        recent = self.db.get_incidents(target, days=7)
        if recent:
            latest = recent[0]
            timestamp = latest.get('timestamp', 'unknown time')
            return "The last incident for {0} occurred at {1}.".format(target, timestamp)
        
        # If no recent incidents, predict next high-risk window
        if self.time_aware_predictor:
            prediction = self.time_aware_predictor.predict_high_risk_window(target)
            
            if prediction:
                hour_window = prediction.get('hour_window', 'unknown')
                day_window = prediction.get('day_window', 'any day')
                confidence = prediction.get('combined_confidence', 0)
                
                return (
                    "No recent incidents. High-risk window for {0}: {1} on {2} "
                    "(confidence: {3:.0%})"
                ).format(target, hour_window, day_window, confidence)
        
        return "No recent incidents found for {0}.".format(target)
    
    def _answer_frequent(self, target, context):
        """
        Answer 'How frequently' questions.
        
        Shows incident frequency and patterns.
        """
        # Get all incidents
        all_incidents = self.db.get_incidents(target, days=90)
        
        if not all_incidents:
            return "No incidents found for {0} in the last 90 days.".format(target)
        
        frequency = len(all_incidents)
        avg_per_week = frequency / (90 / 7.0)
        
        answer_parts = []
        answer_parts.append(
            "Incident frequency for {0}: {1} incidents in 90 days ({2:.1f} per week).".format(
                target, frequency, avg_per_week
            )
        )
        
        # Use PatternEngine if available
        if self.pattern_engine:
            patterns = self.pattern_engine.get_patterns(target)
            if patterns:
                answer_parts.append("Recurring patterns:")
                for pattern in patterns[:3]:
                    hour = pattern.get('hour_of_day')
                    day = pattern.get('day_of_week')
                    count = pattern.get('incident_count', 0)
                    
                    if hour and day:
                        answer_parts.append(
                            "  - {0}:00 on {1}s ({2} incidents)".format(hour, day, count)
                        )
        
        return "\n".join(answer_parts)
    
    def _answer_health(self, target, context):
        """
        Answer 'What is health' questions.
        
        Uses DatabaseHealthScorer for comprehensive health assessment.
        """
        if not self.health_scorer:
            return "Health scoring not available."
        
        health = self.health_scorer.score_database(target, days=7)
        
        score = health.get('health_score', 50)
        state = health.get('health_state', 'UNKNOWN')
        
        # PRODUCTION CALIBRATION: Check alert volume
        recent_critical_alerts = self._count_recent_critical_alerts(target, days=7)
        
        answer_parts = []
        
        # Adjust wording if alert volume is very high
        if recent_critical_alerts >= 10:
            answer_parts.append(
                "Health Status for {0}: {1}/100 ({2}) - OPERATIONALLY UNSTABLE due to sustained critical alert volume (metric telemetry limited)".format(
                    target, score, state
                )
            )
        else:
            answer_parts.append(
                "Health Status for {0}: {1}/100 ({2})".format(target, score, state)
            )
        
        # Add top issues
        top_issues = health.get('top_issues', [])
        if top_issues:
            answer_parts.append("Top Issues:")
            for issue in top_issues[:3]:
                component = issue.get('component', 'unknown')
                explanation = issue.get('explanation', 'issue')
                answer_parts.append("  - {0}: {1}".format(component, explanation))
        
        # Add recommendations
        recommendations = health.get('recommendations', [])
        if recommendations:
            answer_parts.append("Recommendations:")
            for i, rec in enumerate(recommendations[:2], 1):
                answer_parts.append("  {0}. {1}".format(i, rec))
        
        return "\n".join(answer_parts)
    
    def _answer_risk(self, target, context):
        """
        Answer 'What is risk' questions.
        
        Combines health scorer and predictor for risk assessment.
        """
        answer_parts = []
        
        # PRODUCTION CALIBRATION: Check alert volume first
        recent_critical_alerts = self._count_recent_critical_alerts(target, days=7)
        
        # Current risk from health scorer
        if self.health_scorer:
            health = self.health_scorer.score_database(target, days=7)
            score = health.get('health_score', 50)
            
            if score >= 80:
                risk_level = 'LOW'
            elif score >= 60:
                risk_level = 'MEDIUM'
            elif score >= 40:
                risk_level = 'HIGH'
            else:
                risk_level = 'CRITICAL'
            
            # Override risk level if alert volume is very high
            if recent_critical_alerts >= 10 and risk_level in ['LOW', 'MEDIUM']:
                risk_level = 'HIGH'
                answer_parts.append(
                    "Current Risk Level for {0}: {1} (health score {2}/100, elevated by sustained critical alert volume despite limited metric telemetry)".format(
                        target, risk_level, score
                    )
                )
            else:
                answer_parts.append(
                    "Current Risk Level for {0}: {1} (health score {2}/100)".format(
                        target, risk_level, score
                    )
                )
        
        # Future risk from predictor
        if self.time_aware_predictor:
            prediction = self.time_aware_predictor.predict_high_risk_window(target)
            
            if prediction:
                hour = prediction.get('hour_window', 'unknown')
                day = prediction.get('day_window', 'any day')
                conf = prediction.get('combined_confidence', 0)
                
                answer_parts.append(
                    "Highest risk: {0} on {1} (confidence {2:.0%})".format(hour, day, conf)
                )
        
        if not answer_parts:
            answer_parts.append("Risk assessment unavailable for {0}.".format(target))
        
        return "\n".join(answer_parts)
    
    def _answer_recommendation(self, target, context):
        """
        Answer 'What should we do' questions.
        
        Pulls recommendations from health scorer and recent RCA.
        """
        answer_parts = []
        answer_parts.append("Recommended actions for {0}:".format(target))
        
        # From health scorer
        if self.health_scorer:
            health = self.health_scorer.score_database(target, days=7)
            recommendations = health.get('recommendations', [])
            
            if recommendations:
                for i, rec in enumerate(recommendations, 1):
                    answer_parts.append("  {0}. {1}".format(i, rec))
        else:
            answer_parts.append("  1. Review recent incidents and patterns")
            answer_parts.append("  2. Check for anomalies in metrics")
            answer_parts.append("  3. Analyze root cause drivers")
        
        # From RCA if available
        if self.multi_cause_rca:
            recent = self.db.get_incidents(target, days=7)
            if recent:
                rca = self.multi_cause_rca.analyze_incident(recent[0])
                if rca and 'causes' in rca:
                    answer_parts.append("\n  Prevention strategies:")
                    for cause in rca['causes'][:2]:
                        cause_name = cause.get('cause_name', 'unknown')
                        answer_parts.append(
                            "    - Monitor {0} closely".format(cause_name)
                        )
        
        return "\n".join(answer_parts)
    
    def _answer_prediction(self, target, context):
        """
        Answer 'What will happen next' questions.
        
        Uses TimeAwarePredictor for future predictions.
        """
        if not self.time_aware_predictor:
            return "Prediction engine not available."
        
        prediction = self.time_aware_predictor.predict_next_failure_window(target)
        
        if not prediction:
            return "No predictable pattern found for {0}.".format(target)
        
        hours_from_now = prediction.get('hours_from_now', 'unknown')
        estimated_time = prediction.get('estimated_time', 'soon')
        
        answer_parts = []
        answer_parts.append(
            "Predicted next high-risk window for {0}: in {1} hours ({2})".format(
                target, hours_from_now, estimated_time
            )
        )
        
        recommendations = prediction.get('recommendations', [])
        if recommendations:
            answer_parts.append("Mitigation steps:")
            for i, rec in enumerate(recommendations[:3], 1):
                answer_parts.append("  {0}. {1}".format(i, rec))
        
        return "\n".join(answer_parts)
    
    def _answer_comparison(self, target, context):
        """Answer comparison questions."""
        return (
            "Detailed comparison analysis for {0} would require "
            "specifying what to compare against (another database, time period, etc.)."
        ).format(target)
    
    def _answer_general(self, target, context):
        """Answer general questions."""
        health = None
        if self.health_scorer:
            health = self.health_scorer.score_database(target, days=7)
        
        # PRODUCTION CALIBRATION: Check alert volume
        recent_critical_alerts = self._count_recent_critical_alerts(target, days=7)
        
        if health:
            score = health.get('health_score', 50)
            state = health.get('health_state', 'UNKNOWN')
            
            # Add operational context if high alert volume
            if recent_critical_alerts >= 10:
                return "For {0}: Current health is {1}/100 ({2}), but operationally unstable due to high critical alert volume. Ask about health, risk, frequency, or causes.".format(
                    target, score, state
                )
            
            return "For {0}: Current health is {1}/100 ({2}). Ask about health, risk, frequency, or causes.".format(
                target, score, state
            )
        
        return "I can help with questions about {0}'s incidents, health, risk, and causes. What would you like to know?".format(target)
    
    # =====================================================
    # HELPERS
    # =====================================================
    
    def _count_recent_critical_alerts(self, target, days=7):
        """
        Count recent CRITICAL alerts for target.
        Used for production calibration when metrics are sparse.
        """
        if not self.db:
            return 0
        
        try:
            from datetime import datetime, timedelta
            from data_engine.target_normalizer import TargetNormalizer
            
            # Get alerts from database
            alerts = self.db.get_alerts(target=target, days=days)
            
            if not alerts:
                return 0
            
            count = 0
            for alert in alerts:
                if alert.get('severity') == 'CRITICAL':
                    count += 1
            
            return count
        except Exception:
            return 0
    
    def _generate_clarification_prompt(self, target, context):
        """Generate prompt to clarify question."""
        if not target:
            return "Please specify which database you want to ask about (e.g., FINDB, HRDB)."
        
        return "I need more information to answer your question about {0}. What specifically would you like to know?".format(target)
