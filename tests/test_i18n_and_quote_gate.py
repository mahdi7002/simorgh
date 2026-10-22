import core.chat as chat
import main
from core.i18n import detect_lang, t


def _capture(monkeypatch, reply="پاسخ مدل"):
    store = {}

    def fake(system_prompt, user_message, max_tokens=350, needs_quality=False):
        store["system"] = system_prompt
        store["message"] = user_message
        return reply

    monkeypatch.setattr(chat, "generate", fake)
    return store


def test_detect_lang():
    assert detect_lang("Who are you?") == "en"
    assert detect_lang("سلام") == "fa"
    assert detect_lang("سلام hello") == "fa"
    assert detect_lang("") == "fa"
    assert detect_lang("123 ?") == "fa"


def test_t_falls_back_to_persian_then_to_the_key():
    assert t("disc_ai", "xx") == t("disc_ai", "fa")
    assert t("no_such_key_zz", "en") == "no_such_key_zz"


def test_persian_disclosures_equal_the_original_constants():
    assert t("disc_ai", "fa") == main.AI_DISCLOSURE
    assert t("disc_kb", "fa") == main.KNOWLEDGE_DISCLOSURE


def test_english_question_gets_the_language_rule_and_loses_always_persian(monkeypatch):
    store = _capture(monkeypatch)
    chat.ask("Who are you?")
    assert "Language rule" in store["system"]
    assert "همیشه فارسی" not in store["system"]


def test_persian_question_prompt_is_unchanged(monkeypatch):
    store = _capture(monkeypatch)
    chat.ask("سلام، تو کیستی؟")
    assert "Language rule" not in store["system"]
    assert "همیشه فارسی" in store["system"]


def test_unverified_title_is_mentioned_to_the_model(monkeypatch):
    store = _capture(monkeypatch)
    monkeypatch.setattr(chat, "_title_in_catalog", lambda title: False)
    chat.ask("درباره کتاب «کلیات ارزان» چه می‌دانی؟")
    assert "یافت نشد" in store["message"]


_QUOTED = "به قول مولانا، «هر چه بود از من بگیر هر چه نبود رها کن» چنین است."


def test_unverified_attributed_quote_gets_a_warning(monkeypatch):
    _capture(monkeypatch, reply=_QUOTED)
    monkeypatch.setattr(chat, "_quote_in_poetry_db", lambda q: False)
    text = chat.ask("یک سخن از مولانا بگو")
    assert text.startswith(_QUOTED) and "⚠️" in text and "هر چه بود" in text


def test_verified_quote_gets_no_warning(monkeypatch):
    _capture(monkeypatch, reply=_QUOTED)
    monkeypatch.setattr(chat, "_quote_in_poetry_db", lambda q: True)
    assert "⚠️" not in chat.ask("یک سخن از مولانا بگو")


def test_unreadable_database_still_labels_the_quote(monkeypatch):
    _capture(monkeypatch, reply=_QUOTED)

    def boom(_q):
        raise RuntimeError("database missing")

    monkeypatch.setattr(chat, "_quote_in_poetry_db", boom)
    assert "⚠️" in chat.ask("یک سخن از مولانا بگو")


def test_very_short_quotes_are_not_judged():
    assert chat._quote_in_poetry_db("دو واژه") is True


def test_english_notice_reaches_english_users():
    assert t("note_unverified_work", "en", titles="X").startswith("⚠️ I could not verify X")


def test_main_chat_works_when_chat_ask_has_no_lang_parameter(monkeypatch):
    from fastapi.testclient import TestClient

    monkeypatch.setattr(main, "chat_ask", lambda query, agent="hakim", return_metadata=False, **kw: ("پاسخ", False))
    r = TestClient(main.app).post("/chat", data={"query": "سلام", "agent": "hakim"})
    assert r.status_code == 200
    assert r.json()["disclosure"] == main.KNOWLEDGE_DISCLOSURE


_REPLY_CUE = "مولانا، با نگاهی به عمق وجود انسان، چنین می‌گوید: «آمد شهر صیام سنجق سلطان رسید دست بدار از طعام مایده جان رسید» و همین."


def test_quote_after_a_poet_name_is_checked_even_without_by_the_words_of(monkeypatch):
    _capture(monkeypatch, reply=_REPLY_CUE)
    monkeypatch.setattr(chat, "_quote_in_poetry_db", lambda q: False)
    text = chat.ask("یک سخن معروف درباره صبر بگو")
    assert "⚠️" in text and "آمد شهر صیام" in text


def test_quote_with_no_poet_name_is_left_alone(monkeypatch):
    _capture(monkeypatch, reply="خداوند می‌فرماید: «ان الله مع الصابرین و بشر الصابرین» پس صبر کن.")
    monkeypatch.setattr(chat, "_quote_in_poetry_db", lambda q: False)
    assert "⚠️" not in chat.ask("درباره صبر بگو")


def test_quote_that_the_user_typed_is_not_flagged(monkeypatch):
    quote = "هر چه بود از من بگیر هر چه نبود رها کن"
    _capture(monkeypatch, reply="مولانا می‌گوید: «%s» و این را به او نسبت داده‌اند." % quote)
    monkeypatch.setattr(chat, "_quote_in_poetry_db", lambda q: False)
    assert "⚠️" not in chat.ask("آیا «%s» از مولانا است؟" % quote)


def test_cued_quote_found_in_the_database_is_not_flagged(monkeypatch):
    _capture(monkeypatch, reply=_REPLY_CUE)
    monkeypatch.setattr(chat, "_quote_in_poetry_db", lambda q: True)
    assert "⚠️" not in chat.ask("یک سخن معروف درباره صبر بگو")
