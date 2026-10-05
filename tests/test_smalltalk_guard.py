from core import database_answer
from core.database_answer import SMALLTALK_REPLY, build_database_answer, is_smalltalk


def test_greetings_are_smalltalk():
    for q in ["سلام", "درود", "سلام ممنون", "مرسی", "خداحافظ", "hi", "درود، خوبی؟", ""]:
        assert is_smalltalk(q), q


def test_topical_questions_are_not_smalltalk():
    for q in ["صبر چیست", "عدالت چیست", "سلام عدالت چیست", "سلام، صبر را توضیح بده"]:
        assert not is_smalltalk(q), q


def test_greeting_never_triggers_retrieval(monkeypatch):
    def boom(*args, **kwargs):
        raise AssertionError("retrieval must not run for smalltalk")

    for name in ("get_quran_wisdom", "get_poetic_wisdom", "get_book_wisdom"):
        monkeypatch.setattr(database_answer, name, boom)
    assert build_database_answer("سلام") == (SMALLTALK_REPLY, [])


def test_topic_still_reaches_retrieval(monkeypatch):
    called = []
    monkeypatch.setattr(database_answer, "get_quran_wisdom", lambda q, limit=2: called.append(q) or [])
    monkeypatch.setattr(database_answer, "get_poetic_wisdom", lambda q, limit=2: [])
    monkeypatch.setattr(database_answer, "get_book_wisdom", lambda q, limit=2: [])
    build_database_answer("صبر چیست")
    assert called == ["صبر چیست"]


def test_question_words_do_not_break_quran_retrieval():
    from core.quran_search import get_quran_wisdom

    plain = get_quran_wisdom("صبر", limit=3)
    asked = get_quran_wisdom("صبر چیست", limit=3)
    assert plain and asked
