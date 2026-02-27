class ActionPlanner:
    """
    Converts failure prediction + incident signals
    into an actionable, prioritized plan.

    Fully rule-based & explainable.
    """

    # =====================================================
    # MAIN ENTRY
    # =====================================================
    def build_plan(self, prediction):
        probability = prediction.get("failure_probability", 0)
        reasons = prediction.get("reasons", [])
        target = prediction.get("target")

        actions = []

        # -------------------------------------------------
        # HIGH RISK ACTIONS
        # -------------------------------------------------
        if probability >= 70:
            actions.extend([
                {
                    "priority": "P1",
                    "action": "Immediate investigation required",
                    "details": "Review OEM alerts, database alert logs, and OS logs immediately"
                },
                {
                    "priority": "P1",
                    "action": "Enable enhanced monitoring",
                    "details": "Increase alert sensitivity and reduce polling intervals"
                }
            ])

        # -------------------------------------------------
        # MEDIUM RISK ACTIONS
        # -------------------------------------------------
        elif probability >= 40:
            actions.extend([
                {
                    "priority": "P2",
                    "action": "Proactive health check",
                    "details": "Validate DB health, sessions, background processes"
                },
                {
                    "priority": "P2",
                    "action": "Capacity review",
                    "details": "Check CPU, memory, storage headroom"
                }
            ])

        # -------------------------------------------------
        # LOW RISK ACTIONS
        # -------------------------------------------------
        else:
            actions.append({
                "priority": "P3",
                "action": "Routine monitoring",
                "details": "No immediate action required, continue observation"
            })

        # -------------------------------------------------
        # ROOT CAUSE BASED ACTIONS
        # -------------------------------------------------
        for r in reasons:
            r_lower = r.lower()

            if "cpu" in r_lower:
                actions.append({
                    "priority": "P1",
                    "action": "CPU optimization",
                    "details": "Identify CPU-heavy queries, batch jobs, and rebalance workloads"
                })

            if "memory" in r_lower:
                actions.append({
                    "priority": "P1",
                    "action": "Memory tuning",
                    "details": "Analyze PGA/SGA usage, JVM heap, and memory leaks"
                })

            if "storage" in r_lower:
                actions.append({
                    "priority": "P1",
                    "action": "Storage cleanup",
                    "details": "Check tablespace usage, archive logs, and filesystem capacity"
                })

            if "no recovery" in r_lower:
                actions.append({
                    "priority": "P1",
                    "action": "Recovery verification",
                    "details": "Confirm whether alerts cleared and services restarted successfully"
                })

            if "repeated" in r_lower:
                actions.append({
                    "priority": "P2",
                    "action": "Pattern analysis",
                    "details": "Compare with historical incidents and recurring failure windows"
                })

        # -------------------------------------------------
        # FINAL CLEANUP (deduplicate)
        # -------------------------------------------------
        actions = self._deduplicate(actions)

        return {
            "target": target,
            "risk_level": prediction.get("confidence"),
            "recommended_actions": actions
        }

    # =====================================================
    # HELPERS
    # =====================================================
    def _deduplicate(self, actions):
        seen = set()
        unique = []

        for a in actions:
            key = (a["priority"], a["action"])
            if key not in seen:
                seen.add(key)
                unique.append(a)

        return unique

