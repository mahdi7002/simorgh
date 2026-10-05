import sqlite3

import pytest

from app.knowledge import poetry_lookup as pl

VERSES = [
    (1, 1, "الا یا ایها الساقی ادر کاسا و ناولها"),
    (2, 2, "بنی آدم اعضای یک پیکرند که در آفرینش ز یک گوهرند"),
    (3, 3, "توانا بود هر که دانا بود ز دانش دل پیر برنا بود"),
    (4, 1, "دوش دیدم که ملایک در میخانه زدند"),
    (5, 4, "دوش دیدم که ملایک در میخانه زدند"),  # same verse attributed to two poets -> ambiguous
]
POETS = {1: "حافظ", 2: "سعدی", 3: "فردوسی", 4: "مولوی"}


@pytest.fixture()
def verse_db(tmp_path, monkeypatch):
    path = tmp_path / "verses.db"
    conn = sqlite3.connect(path)
    conn.execute("create table poets(id integer primary key, name text)")
    conn.execute("create table verses(id integer primary key, poet_id int, poem_id int, bait_number int, text text)")
    conn.execute("create virtual table verses_fts using fts5(text)")
    for pid, name in POETS.items():
        conn.execute("insert into poets values (?,?)", (pid, name))
    for vid, pid, text in VERSES:
        conn.execute("insert into verses values (?,?,?,?,?)", (vid, pid, vid, 1, text))
        conn.execute("insert into verses_fts(rowid, text) values (?,?)", (vid, text))
    conn.commit()
    conn.close()
    pl.close()
    monkeypatch.setattr(pl, "DB", str(path))
    yield path
    pl.close()


def test_unique_phrase_gives_answer(verse_db):
    r = pl.lookup("بنی آدم اعضای یک پیکرند")
    assert r["status"] == "answer" and r["poet"] == "سعدی"


def test_same_verse_two_poets_is_ambiguous(verse_db):
    r = pl.lookup("دوش دیدم که ملایک در میخانه")
    assert r["status"] == "ambiguous" and set(r["candidates"]) == {"حافظ", "مولوی"}


def test_too_short_and_unknown(verse_db):
    assert pl.lookup("عشق")["status"] == "too_short"
    assert pl.lookup("زبرجد پلنگ ستاره غروب")["status"] == "none"


def test_chimera_is_not_accepted_as_answer(verse_db):
    chimera = "الا یا ایها گوهرند آفرینش ز یک"
    assert pl.lookup(chimera)["status"] != "answer"


def test_attribution_only_for_trigger_phrases(verse_db):
    assert pl.attribution("صبر چیست") is None
    out = pl.attribution("بنی آدم اعضای یک پیکرند از کیست")
    assert out and out.endswith("— سعدی")
    assert "مطمئن نیستم" in pl.attribution("دوش دیدم که ملایک در میخانه زدند از کیست")
    assert "پیدا نکردم" in pl.attribution("زبرجد پلنگ ستاره غروب از کیست")


def test_chat_uses_attribution_without_llm(verse_db, monkeypatch):
    from core import chat

    def no_llm(*a, **k):
        raise AssertionError("LLM must not be called for a verified verse attribution")

    monkeypatch.setattr(chat, "generate", no_llm)
    text, ai_generated = chat.ask("بنی آدم اعضای یک پیکرند از کیست", return_metadata=True)
    assert text.endswith("— سعدی") and ai_generated is False


def test_missing_or_lfs_pointer_db_fails_clearly_not_at_import(tmp_path, monkeypatch):
    pl.close()
    monkeypatch.setattr(pl, "DB", str(tmp_path / "nope.db"))
    with pytest.raises(FileNotFoundError):
        pl.get_db()
    pointer = tmp_path / "ptr.db"
    pointer.write_bytes(b"version https://git-lfs.github.com/spec/v1\noid sha256:abc\nsize 1\n")
    monkeypatch.setattr(pl, "DB", str(pointer))
    with pytest.raises(RuntimeError, match="git lfs pull"):
        pl.get_db()


def test_chat_survives_missing_verse_db(tmp_path, monkeypatch):
    from core import chat

    pl.close()
    monkeypatch.setattr(pl, "DB", str(tmp_path / "nope.db"))
    monkeypatch.setattr(chat, "generate", lambda *a, **k: "پاسخ مدل")
    assert chat.ask("این بیت از کیست؟", return_metadata=True) == ("پاسخ مدل", True)


def test_common_phrase_with_many_hits_is_not_certified_to_one_poet(verse_db):
    conn = sqlite3.connect(verse_db)
    for i in range(10):  # 10 verses by one poet sharing a stock phrase, plus one by another poet beyond the k=8 window
        vid = 100 + i
        text = f"خردمند و روشن دل و یادگیر شماره {i}"
        conn.execute("insert into verses values (?,?,?,?,?)", (vid, 3, vid, 1, text))
        conn.execute("insert into verses_fts(rowid, text) values (?,?)", (vid, text))
    conn.execute("insert into verses values (200,2,200,1,'قوی رای و روشن دل و سرفراز')")
    conn.execute("insert into verses_fts(rowid, text) values (200,'قوی رای و روشن دل و سرفراز')")
    conn.commit(); conn.close()
    pl.close()
    r = pl.lookup("و روشن دل و")
    assert r["status"] != "answer"
    assert "مطمئن نیستم" in pl.attribution("و روشن دل و از کیست")
