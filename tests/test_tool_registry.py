from core.tools import ToolRegistry, build_default_registry


def test_registry_handles_successful_local_tool():
    r = ToolRegistry()

    r.register(
        "demo",
        lambda query: {"query": query, "ok": True},
        source="unit-test",
    )

    result = r.execute("demo", "hello")

    assert result.status == "OK"
    assert result.tool == "demo"
    assert result.data["ok"] is True
    assert result.provenance["execution"] == "local"


def test_registry_handles_missing_tool():
    r = ToolRegistry()

    result = r.execute("missing", "hello")

    assert result.status == "NOT_AVAILABLE"
    assert result.data is None


def test_registry_handles_tool_failure():
    r = ToolRegistry()

    def broken(_query):
        raise RuntimeError("boom")

    r.register(
        "broken",
        broken,
        source="unit-test",
    )

    result = r.execute("broken", "hello")

    assert result.status == "NOT_AVAILABLE"
    assert result.provenance["error_type"] == "RuntimeError"


def test_default_registry_has_supported_local_tools():
    r = build_default_registry()

    assert r.available("poetry_search")
    assert r.available("quran_search")
    assert r.available("book_search")
    assert r.available("yazd_lore")


def test_orchestrator_records_tool_results(monkeypatch):
    from core.orchestration.orchestrator import Orchestrator

    def fake_ask(
        question,
        agent="hakim",
        *,
        tool_context="",
        use_builtin_tools=True,
    ):
        assert use_builtin_tools is False
        return f"{agent}: {bool(tool_context)}"

    monkeypatch.setattr(
        "core.orchestration.orchestrator.ask",
        fake_ask,
    )

    o = Orchestrator()
    result = o.run("یک غزل از حافظ", max_agents=2)

    assert result["tool_results"]
    assert "poetry_search" in result["tool_results"]
    assert result["tool_results"]["poetry_search"]["status"] == "OK"
    assert result["tool_results"]["poetry_search"]["status"] == "OK"


def test_tool_planner_routes_sources_independently():
    from core.tools import ToolPlanner

    p = ToolPlanner()

    assert p.plan("یک غزل از حافظ").tools == ["poetry_search"]
    assert p.plan("برای قرآن درباره عدالت توضیح بده").tools == ["quran_search"]
    assert p.plan("درباره بادگیر دولت‌آباد بگو").tools == ["yazd_lore"]
    assert p.plan("یک کتاب درباره فلسفه معرفی کن").tools == ["book_search"]


def test_tool_planner_can_select_multiple_sources():
    from core.tools import ToolPlanner

    plan = ToolPlanner().plan("شعر حافظ و قرآن درباره عشق")

    assert "poetry_search" in plan.tools
    assert "quran_search" in plan.tools
