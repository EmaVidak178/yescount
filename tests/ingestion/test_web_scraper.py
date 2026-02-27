from __future__ import annotations

from src.ingestion.web_scraper import scrape_site


class _DummyResponse:
    def __init__(self, text: str):
        self.text = text

    def raise_for_status(self) -> None:
        return None


def test_scrape_site_extracts_date_from_card_text(monkeypatch):
    html = """
    <html>
      <body>
        <article>
          Big Night Out - March 15, 2026 at 7pm in NYC
        </article>
      </body>
    </html>
    """

    def _fake_get(url: str, timeout: int):
        assert url == "https://example.com"
        assert timeout == 30
        return _DummyResponse(html)

    monkeypatch.setattr("src.ingestion.web_scraper.requests.get", _fake_get)
    rows = scrape_site("https://example.com", source_name="example")
    assert len(rows) == 1
    assert rows[0]["date_start"] is not None
    assert str(rows[0]["date_start"]).startswith("2026-03-15")
