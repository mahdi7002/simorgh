import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load(lang):
    return json.loads((ROOT / "locales" / f"{lang}.json").read_text(encoding="utf-8"))


def test_locale_keys_are_identical():
    assert set(_load("fa")) == set(_load("en"))


def test_locale_values_are_non_empty_strings():
    for lang in ("fa", "en"):
        for key, value in _load(lang).items():
            assert isinstance(value, str) and value.strip(), (lang, key)


def test_every_key_used_by_the_pages_exists():
    keys = set(_load("fa"))
    for page in ("learn.html", "index.html"):
        html = (ROOT / "app" / page).read_text(encoding="utf-8")
        used = set(re.findall(r'data-(?:i|q|ph)="([a-z0-9_]+)"', html))
        used |= set(re.findall(r"\bt\('([a-z0-9_]+)'\)", html))
        assert used and used <= keys, (page, sorted(used - keys))


def test_no_local_absolute_paths():
    for rel in ("app/learn.html", "locales/fa.json", "locales/en.json"):
        assert "/home/" not in (ROOT / rel).read_text(encoding="utf-8"), rel


def test_learn_page_and_locales_are_served():
    from fastapi.testclient import TestClient
    import main

    client = TestClient(main.app)
    assert client.get("/learn").status_code == 200
    fa = client.get("/locales/fa.json")
    assert fa.status_code == 200 and fa.json()["app_name"]
    assert client.get("/locales/xx.json").status_code == 404
    assert client.get("/locales/..%2Fmain.json").status_code in (404, 422)


def test_main_page_is_served_and_carries_the_language_switch():
    from fastapi.testclient import TestClient
    import main

    html = TestClient(main.app).get("/").text
    assert 'data-l="fa"' in html and 'data-l="en"' in html
    assert "/locales/" in html


def test_appimage_script_bundles_locales():
    script = (ROOT / "packaging" / "build-appimage.sh").read_text(encoding="utf-8")
    assert "dashboard models locales" in script
