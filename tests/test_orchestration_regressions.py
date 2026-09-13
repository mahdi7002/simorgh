from core.orchestration import Blackboard, Dispatcher, Reviewer


def test_memory_does_not_route_to_hafez():
    result = Dispatcher().dispatch("چرا حافظه برای سیمرغ مهم است؟")
    assert result.agents == ["hakim", "nazer"]


def test_hafez_routes_for_poetry():
    result = Dispatcher().dispatch("یک غزل از حافظ")
    assert result.agents == ["hafez"]


def test_empty_query_gets_safe_default():
    result = Dispatcher().dispatch("")
    assert result.agents == ["hakim", "moalem"]


def test_blackboard_state():
    b = Blackboard("x")
    b.record_output("hakim", "answer")
    b.record_tool_result("quran_search", {"results": 1})

    state = b.as_dict()

    assert state["outputs"]["hakim"] == "answer"
    assert state["tool_results"]["quran_search"]["results"] == 1


def test_reviewer_rejects_evidence_sensitive_request_without_tools():
    result = Reviewer().review(
        "منبع دقیق این آیه را بگو",
        {"hakim": "طبق قرآن، این آیه چنین است."},
        {},
    )

    assert result.approved is False
    assert "evidence_sensitive_request_without_tool_evidence" in result.warnings


def test_reviewer_does_not_confuse_generated_claim_with_evidence():
    result = Reviewer().review(
        "این موضوع چیست؟",
        {"hakim": "بر اساس منبع معتبر این درست است."},
        {},
    )

    assert result.approved is False
    assert "generated_evidence_claim_without_evidence" in result.warnings


def test_reviewer_accepts_normal_answer_without_evidence_request():
    result = Reviewer().review(
        "حافظه در یک سیستم نرم‌افزاری چه نقشی دارد؟",
        {"hakim": "حافظه داده‌ها را برای استفاده بعدی نگه می‌دارد."},
        {},
    )

    assert result.approved is True
    assert result.warnings == []
