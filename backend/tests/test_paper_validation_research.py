import pytest

from app.backtesting.paper_validation_research import _fetch_news_catalysts


class FlakyNewsProvider:
    async def get_news(self, ticker, start, end):
        if ticker == "BAD":
            raise TimeoutError("provider timeout")
        return [{"ticker": ticker, "headline": "ok"}]


@pytest.mark.asyncio
async def test_fetch_news_catalysts_is_best_effort_on_provider_timeout():
    result = await _fetch_news_catalysts(
        ["GOOD", "BAD", "NEXT"],
        "2026-01-01",
        "2026-01-31",
        FlakyNewsProvider(),
    )

    assert result["GOOD"] == [{"ticker": "GOOD", "headline": "ok"}]
    assert result["BAD"] == []
    assert result["NEXT"] == [{"ticker": "NEXT", "headline": "ok"}]
