from collections import defaultdict
from datetime import datetime, timedelta
from data_engine.target_normalizer import TargetNormalizer


class RiskTrendAnalyzer:
    """
    Analyzes risk trend over time for databases / targets
    Uses:
    - incidents (first_seen / last_seen)
    - critical alerts (time / alert_time)
    """

    def __init__(self, alerts, incidents):
        self.alerts = alerts if isinstance(alerts, list) else []
        self.incidents = incidents if isinstance(incidents, list) else []

    # =================================================
    # PUBLIC API
    # =================================================
    def analyze_target(self, target, days=7):
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        daily_risk = self._daily_risk(target, start_date, end_date)
        trend = self._calculate_trend(daily_risk)

        return {
            "target": target,
            "days_analyzed": days,
            "daily_risk": daily_risk,
            "trend": trend["trend"],
            "risk_score": trend["risk_score"],
            "reason": trend["reason"]
        }

    def build_trends(self, days=7):
        targets = []
        seen_targets = set()

        for a in self.alerts:
            if not a:
                continue
            t = a.get("target")
            if t and t not in seen_targets:
                seen_targets.add(t)
                targets.append(t)

        targets.sort()

        trend_list = []
        for t in targets:
            try:
                trend_list.append(self.analyze_target(t, days))
            except Exception:
                pass

        return trend_list

    # =================================================
    # DAILY RISK CALCULATION
    # =================================================
    def _daily_risk(self, target, start, end):
        day_map = defaultdict(int)

        if not target:
            return []

        # Normalize target once for comparison
        normalized_target = TargetNormalizer.normalize(target)
        if not normalized_target:
            return []

        # ---------- INCIDENT CONTRIBUTION ----------
        for inc in self.incidents:
            if not inc:
                continue

            if not TargetNormalizer.equals(inc.get("target"), normalized_target):
                continue

            first_seen = inc.get("first_seen")
            last_seen = inc.get("last_seen")

            if not isinstance(first_seen, datetime) or not isinstance(last_seen, datetime):
                continue

            # Skip if no overlap
            if first_seen > end or last_seen < start:
                continue

            # Clamp window (FIX)
            current = first_seen if first_seen > start else start
            last = last_seen if last_seen < end else end

            while current <= last:
                day_map[current.date()] += 3
                current = current + timedelta(days=1)

        # ---------- CRITICAL ALERT CONTRIBUTION ----------
        for a in self.alerts:
            if not a:
                continue

            if not TargetNormalizer.equals(a.get("target"), normalized_target):
                continue

            if a.get("severity") != "CRITICAL":
                continue

            # FIX: support both time & alert_time
            t = a.get("time") or a.get("alert_time")
            if not isinstance(t, datetime):
                continue

            if t < start or t > end:
                continue

            day_map[t.date()] += 1

        # ---------- FINAL FORMAT ----------
        result = []
        for day in sorted(day_map.keys()):
            result.append({
                "date": str(day),
                "risk": day_map[day]
            })

        return result

    # =================================================
    # TREND DECISION
    # =================================================
    def _calculate_trend(self, daily_risk):
        if not daily_risk:
            # PRODUCTION FALLBACK: Check alert frequency even without daily_risk
            alert_trend = self._calculate_alert_frequency_trend()
            if alert_trend:
                return alert_trend

            return {
                "trend": "INSUFFICIENT_DATA",
                "risk_score": 0,
                "reason": "No risk data available"
            }

        risks = []
        for d in daily_risk:
            try:
                risks.append(int(d.get("risk", 0)))
            except Exception:
                pass

        if len(risks) < 2:
            # PRODUCTION FALLBACK: Check alert frequency
            alert_trend = self._calculate_alert_frequency_trend()
            if alert_trend:
                return alert_trend

            return {
                "trend": "INSUFFICIENT_DATA",
                "risk_score": sum(risks),
                "reason": "Not enough historical data"
            }

        mid = len(risks) // 2

        first_half = sum(risks[:mid])
        second_half = sum(risks[mid:])

        if first_half == 0:
            if second_half > 0:
                return {
                    "trend": "INCREASING",
                    "risk_score": second_half,
                    "reason": "Risk events starting to increase"
                }
            return {
                "trend": "STABLE",
                "risk_score": second_half,
                "reason": "No significant risk detected"
            }

        ratio = float(second_half) / float(first_half)

        if ratio > 1.2:
            return {
                "trend": "INCREASING",
                "risk_score": second_half,
                "reason": "Risk events increasing over time"
            }

        if ratio < 0.8:
            return {
                "trend": "DECREASING",
                "risk_score": second_half,
                "reason": "Risk events reducing over time"
            }

        return {
            "trend": "STABLE",
            "risk_score": second_half,
            "reason": "No significant risk change detected"
        }

    # =================================================
    # PRODUCTION FALLBACK: ALERT FREQUENCY TREND
    # =================================================
    def _calculate_alert_frequency_trend(self):
        """
        Fallback: When metric-based trend shows INSUFFICIENT_DATA,
        compute trend using alert frequency over time.
        
        Returns None if insufficient alerts, otherwise returns trend dict.
        """
        if not self.alerts:
            return None

        # Count CRITICAL alerts per day (last 7 days)
        day_counts = defaultdict(int)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)

        for alert in self.alerts:
            if not alert:
                continue
            if alert.get("severity") != "CRITICAL":
                continue
            
            alert_time = alert.get("time") or alert.get("alert_time")
            if not isinstance(alert_time, datetime):
                continue
            
            if start_date <= alert_time <= end_date:
                day_counts[alert_time.date()] += 1

        if not day_counts:
            return None

        # Need at least 2 days of data
        if len(day_counts) < 2:
            return None

        # Calculate trend from alert counts
        sorted_days = sorted(day_counts.keys())
        counts = [day_counts[day] for day in sorted_days]
        
        mid = len(counts) // 2
        first_half = sum(counts[:mid])
        second_half = sum(counts[mid:])

        # High alert volume = assign meaningful risk score
        total_alerts = sum(counts)
        risk_score = min(total_alerts * 5, 100)

        if first_half == 0:
            if second_half > 0:
                return {
                    "trend": "INCREASING",
                    "risk_score": risk_score,
                    "reason": "Alert frequency increasing (metric data sparse)"
                }
            return None

        ratio = float(second_half) / float(first_half)

        if ratio > 1.2:
            return {
                "trend": "INCREASING",
                "risk_score": risk_score,
                "reason": "Alert frequency increasing over time (metric data sparse)"
            }
        
        if ratio < 0.8:
            return {
                "trend": "DECREASING",
                "risk_score": risk_score,
                "reason": "Alert frequency decreasing (metric data sparse)"
            }

        # High alert volume but stable trend
        if total_alerts >= 10:
            return {
                "trend": "STABLE_HIGH_VOLUME",
                "risk_score": risk_score,
                "reason": "Sustained high alert volume detected (metric data sparse)"
            }

        return None

