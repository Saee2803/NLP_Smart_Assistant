from data_engine.data_fetcher import DataFetcher
from incident_engine.correlation_engine import CorrelationEngine

class ReasoningService:

    def analyze_environment(self):
        fetcher = DataFetcher()
        data = fetcher.fetch({})   # no question, full context

        alerts = data["alerts"]
        metrics = data["metrics"]

        results = []

        engine = CorrelationEngine(alerts, metrics)

        for alert in alerts[:20]:   # top alerts only
            rca = engine.analyze(alert)
            results.append({
                "alert": alert,
                "rca": rca
            })

        return results

