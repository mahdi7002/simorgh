"""Small helper for user-visible strings that live in locales/<lang>.json."""
import json
import re
from functools import lru_cache
from pathlib import Path

_LOCALES = Path(__file__).resolve().parents[1] / "locales"
_PERSIAN = re.compile(r"[\u0600-\u06FF]")
_LATIN = re.compile(r"[A-Za-z]")


def detect_lang(text: str) -> str:
    """'en' only for text with Latin letters and no Persian or Arabic letters; everything else is 'fa'."""
    s = text or ""
    if _LATIN.search(s) and not _PERSIAN.search(s):
        return "en"
    return "fa"


@lru_cache(maxsize=16)
def _load(lang: str) -> dict:
    # The file comes from a directory listing, never from the argument itself.
    path = {p.stem: p for p in _LOCALES.glob("*.json")}.get(lang)
    if path is None:
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def t(key: str, lang: str = "fa", **kwargs) -> str:
    text = _load(lang).get(key) or _load("fa").get(key) or key
    return text.format(**kwargs) if kwargs else text
