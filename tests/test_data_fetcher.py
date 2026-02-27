from nlp_engine.question_parser import QuestionParser
from data_engine.data_fetcher import DataFetcher

q = "Why did mitestdb reboot last night?"

context = QuestionParser.parse(q)
fetcher = DataFetcher()

data = fetcher.fetch(context)

print("\nALERTS:", len(data["alerts"]))
print("METRICS:", len(data["metrics"]))

print("\nSample Alert:", data["alerts"][:1])
print("Sample Metric:", data["metrics"][:1])

