from evaluation.knowledge_eval import evaluate, normalize


def test_normalize_structured_lookup_result():
    result = normalize(
        {
            "status": "answer",
            "poet": "فردوسی",
            "candidates": [],
            "verse": "نمونه",
        }
    )

    assert result["status"] == "answer"
    assert result["poet"] == "فردوسی"


def test_evaluate_tracks_accuracy_and_false_positive():
    cases = [
        {"id": 1, "q": "a", "poet": "فردوسی", "status": "answer"},
        {"id": 2, "q": "b", "status": "not_found"},
    ]

    def fake_lookup(query):
        if query == "a":
            return {"status": "answer", "poet": "فردوسی"}
        return {"status": "answer", "poet": "حافظ"}

    report = evaluate(cases, fake_lookup)

    assert report["known_cases"] == 1
    assert report["answered_known_cases"] == 1
    assert report["correct_known_answers"] == 1
    assert report["false_positive_count"] == 1
    assert report["false_positive_rate"] == 0.5
