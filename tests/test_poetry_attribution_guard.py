import sys
import types

import core.chat as chat


def _break_poetry_db(monkeypatch):
    fake = types.ModuleType("app.knowledge.poetry_lookup")

    def attribution(_question):
        raise FileNotFoundError("verse DB not found")

    fake.attribution = attribution
    monkeypatch.setitem(sys.modules, "app.knowledge.poetry_lookup", fake)

    def no_llm(*args, **kwargs):
        raise AssertionError("the language model must not be called")

    monkeypatch.setattr(chat, "generate", no_llm, raising=False)


def test_attribution_question_without_verse_db_refuses_to_guess(monkeypatch):
    _break_poetry_db(monkeypatch)
    assert chat.ask("این بیت از کیست: یک بیت نمونه") == chat.POETRY_DB_UNAVAILABLE_MESSAGE


def test_metadata_flag_is_false_for_the_deterministic_refusal(monkeypatch):
    _break_poetry_db(monkeypatch)
    assert chat.ask("شاعرش کیست؟ یک بیت نمونه", return_metadata=True) == (
        chat.POETRY_DB_UNAVAILABLE_MESSAGE,
        False,
    )


def test_guard_ignores_ordinary_questions():
    for q in ("سلام", "امروز هوا چطور است؟", "سراینده‌ی شاهنامه کیست؟"):
        assert not chat._looks_like_verse_attribution(q)
