from nlp_engine.question_parser import QuestionParser

questions = [
    "Why did FINDB reboot yesterday?",
    "Is CPU issue still ongoing?",
    "What happened last night at 2 AM?",
    "Which server is risky now?",
    "What should we do for memory issue?"
]

for q in questions:
    print("\nQ:", q)
    print(QuestionParser.parse(q))

