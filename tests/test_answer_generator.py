from data_engine.data_fetcher import DataFetcher
from incident_engine.correlation_engine import CorrelationEngine
from nlp_engine.answer_generator import AnswerGenerator

fetcher = DataFetcher()
data = fetcher.fetch({"severity": "CRITICAL"})

engine = CorrelationEngine(data["alerts"], data["metrics"])
analysis = engine.analyze(data["alerts"][0])

gen = AnswerGenerator()
answer = gen.generate(analysis)

print("\n===== CHATBOT ANSWER =====")
print(answer)

