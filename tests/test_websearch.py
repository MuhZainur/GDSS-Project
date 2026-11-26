"""Web search for the chat: the ddgs library is used and failures never break a chat turn (no network here)."""
import ddgs

from llm.websearch import search_web


class _FakeDDGS:
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def text(self, query, max_results):
        return [{"title": "H100", "href": "https://example.com/h100", "body": "x" * 900}]


def test_search_uses_ddgs_and_maps_the_fields(monkeypatch):
    monkeypatch.setenv("WEB_SEARCH_PROVIDER", "ddgs")
    monkeypatch.setattr(ddgs, "DDGS", _FakeDDGS)
    assert search_web("H100") == [{"title": "H100", "url": "https://example.com/h100", "snippet": "x" * 500}]


def test_search_failure_returns_an_empty_list(monkeypatch):
    class Broken(_FakeDDGS):
        def text(self, query, max_results):
            raise RuntimeError("rate limited")

    monkeypatch.setenv("WEB_SEARCH_PROVIDER", "ddgs")
    monkeypatch.setattr(ddgs, "DDGS", Broken)
    assert search_web("H100") == []
