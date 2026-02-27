from data_engine.data_fetcher import DataFetcher
from incident_engine.correlation_engine import CorrelationEngine

fetcher = DataFetcher()

context = {
    "severity": "CRITICAL"
}

data = fetcher.fetch(context)

engine = CorrelationEngine(
    alerts=data["alerts"],
    metrics=data["metrics"]
)

sample = data["alerts"][0]

result = engine.analyze(sample)

print("\n===== CORRELATION RESULT =====")
for k, v in result.items():
    print(k, ":", v)

