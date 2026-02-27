from datetime import datetime


class AnswerGenerator:
    """
    Converts RCA / correlation output into
    clear, human-readable explanations.
    """

    def generate(self, rca: dict) -> str:
        """
        Input: RCA dict from correlation engine
        Output: Natural language explanation
        """

        incident_time = rca.get("time")
        root_cause = rca.get("root_cause", "Unknown cause")
        risky = rca.get("risky", False)
        status = rca.get("current_status", "UNKNOWN")
        recommendation = rca.get("recommendation", "")

        time_str = (
            incident_time.strftime("%H:%M")
            if isinstance(incident_time, datetime)
            else "unknown time"
        )

        explanation = []

        # -------------------------
        # WHAT HAPPENED
        # -------------------------
        explanation.append(
            f"A critical alert occurred at {time_str}."
        )

        # -------------------------
        # WHY IT HAPPENED
        # -------------------------
        if "cpu" in root_cause.lower():
            explanation.append(
                "CPU utilization reached an abnormal level, "
                "which caused system instability."
            )

        elif "memory" in root_cause.lower():
            explanation.append(
                "High memory pressure was observed, "
                "which likely impacted system performance."
            )

        elif "storage" in root_cause.lower():
            explanation.append(
                "Storage-related metrics crossed safe thresholds, "
                "indicating possible space or I/O issues."
            )

        elif "repeated" in root_cause.lower():
            explanation.append(
                "No abnormal CPU, memory, or storage spikes were detected. "
                "However, this alert has occurred multiple times, "
                "indicating a recurring underlying issue."
            )

        else:
            explanation.append(
                "No clear metric anomaly was detected before this alert. "
                "The exact root cause could not be determined automatically."
            )

        # -------------------------
        # RISK ASSESSMENT
        # -------------------------
        if risky:
            explanation.append(
                "This incident indicates that the environment was at risk."
            )
        else:
            explanation.append(
                "This incident did not immediately make the environment risky."
            )

        # -------------------------
        # CURRENT STATUS
        # -------------------------
        if status == "STABLE":
            explanation.append(
                "The system is currently stable based on recent observations."
            )
        elif status == "UNSTABLE":
            explanation.append(
                "The system is currently unstable and requires attention."
            )
        else:
            explanation.append(
                "The current system status could not be confirmed."
            )

        # -------------------------
        # RECOMMENDATION
        # -------------------------
        if recommendation:
            explanation.append(
                f"Recommended action: {recommendation}"
            )

        return " ".join(explanation)

