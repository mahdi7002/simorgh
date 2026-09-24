from __future__ import annotations

import pytest

from core.mother.research import _safe_url, browser_search_urls


def test_research_rejects_local_targets():
    with pytest.raises(ValueError):
        _safe_url("http://127.0.0.1:8000/health")
    with pytest.raises(ValueError):
        _safe_url("http://localhost/test")


def test_research_rejects_non_http():
    with pytest.raises(ValueError):
        _safe_url("file:///etc/passwd")


def test_browser_search_urls_are_explicit():
    urls = browser_search_urls("SIMORGH Mother")
    assert urls["duckduckgo"].startswith("https://duckduckgo.com/?q=")
    assert urls["bing"].startswith("https://www.bing.com/search?q=")
    assert urls["google"].startswith("https://www.google.com/search?q=")
