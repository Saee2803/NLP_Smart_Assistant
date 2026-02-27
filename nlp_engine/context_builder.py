from data_engine.data_fetcher import DataFetcher

def build_context(intent: str, question: str):
    fetcher = DataFetcher()
    context = {}

    if intent == "TIME_EVENT":
        context["start_time"] = "2025-06-23 10:05"
        context["end_time"]   = "2025-06-23 10:07"

    if "midevstbn" in question.lower():
        context["host"] = "MIDEVSTBN"

    return fetcher.fetch(context)

