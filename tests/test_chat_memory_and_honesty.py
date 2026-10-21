import core.chat as chat


def _capture(monkeypatch):
    seen = {}

    def fake(system_prompt, user_message, max_tokens=350, needs_quality=False):
        seen["message"] = user_message
        return "پاسخ مدل"

    monkeypatch.setattr(chat, "generate", fake)
    return seen


def test_history_reaches_the_model_when_given(monkeypatch):
    seen = _capture(monkeypatch)
    chat.ask("نام من چیست؟", history=[("نام من آزمونگر است", "سلام آزمونگر")])
    assert "آزمونگر" in seen["message"]
    assert "نام من چیست؟" in seen["message"]


def test_no_history_block_without_history(monkeypatch):
    seen = _capture(monkeypatch)
    chat.ask("نام من چیست؟")
    assert "گفتگوی پیشین" not in seen["message"]


def test_only_the_last_four_turns_are_sent(monkeypatch):
    seen = _capture(monkeypatch)
    turns = [("u%d" % i, "s%d" % i) for i in range(6)]
    chat.ask("ادامه بده", history=turns)
    assert "u5" in seen["message"] and "u2" in seen["message"]
    assert "u1" not in seen["message"] and "u0" not in seen["message"]


def test_unverified_work_is_labelled_not_blocked(monkeypatch):
    monkeypatch.setattr(chat, "generate", lambda *a, **k: "پاسخ مدل")
    monkeypatch.setattr(chat, "_title_in_catalog", lambda t: False)
    text, ai = chat.ask("درباره کتاب «کلیات ارزان» از مولانا چه می‌دانی؟", return_metadata=True)
    assert ai is True
    assert text.startswith("پاسخ مدل")
    assert "کلیات ارزان" in text and "⚠️" in text


def test_known_work_is_not_labelled(monkeypatch):
    monkeypatch.setattr(chat, "generate", lambda *a, **k: "پاسخ مدل")
    monkeypatch.setattr(chat, "_title_in_catalog", lambda t: True)
    text, _ = chat.ask("درباره کتاب «مثنوی» چه می‌دانی؟", return_metadata=True)
    assert "⚠️" not in text


def test_unreadable_catalog_still_labels(monkeypatch):
    monkeypatch.setattr(chat, "generate", lambda *a, **k: "پاسخ مدل")

    def boom(_t):
        raise RuntimeError("catalog missing")

    monkeypatch.setattr(chat, "_title_in_catalog", boom)
    text, _ = chat.ask("درباره دیوان «نمونه» چه می‌دانی؟", return_metadata=True)
    assert "⚠️" in text


def test_label_needs_a_work_word_before_the_quoted_title(monkeypatch):
    monkeypatch.setattr(chat, "generate", lambda *a, **k: "پاسخ مدل")
    monkeypatch.setattr(chat, "_title_in_catalog", lambda t: False)
    text, _ = chat.ask("درباره «گلستان» چه می‌دانی؟", return_metadata=True)
    assert "⚠️" not in text
