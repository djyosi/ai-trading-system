from datetime import datetime, timezone

import httpx

from app.catalysts.classifier import classify_catalyst
from app.core.config import settings as default_settings
from app.providers.market_data_base import MarketDataProvider


class ProviderConfigurationError(RuntimeError):
    """Raised when a provider cannot run because required configuration is missing."""


class MassiveProvider(MarketDataProvider):
    provider_name = "massive"

    def __init__(self, settings=None, client=None):
        self.settings = settings or default_settings
        self.client = client or httpx.AsyncClient(base_url=self.settings.massive_base_url, timeout=30)

    def _require_api_key(self):
        if not self.settings.massive_api_key:
            raise ProviderConfigurationError("MASSIVE_API_KEY is required for MassiveProvider")
        return self.settings.massive_api_key

    async def aclose(self):
        await self.client.aclose()

    async def get_symbols(self):
        api_key = self._require_api_key()
        response = await self.client.get("/v3/reference/tickers", params={"apiKey": api_key})
        response.raise_for_status()
        payload = response.json()
        return payload.get("results", [])

    async def get_daily_candles(self, ticker, start, end):
        return await self._get_aggregate_candles(ticker, start, end, multiplier=1, timespan="day", timeframe="1d")

    async def get_intraday_candles(self, ticker, start, end, timeframe="1m"):
        multiplier, timespan = self._parse_timeframe(timeframe)
        return await self._get_aggregate_candles(
            ticker,
            start,
            end,
            multiplier=multiplier,
            timespan=timespan,
            timeframe=timeframe,
        )

    async def get_snapshot(self, ticker):
        api_key = self._require_api_key()
        response = await self.client.get(f"/v2/snapshot/locale/us/markets/stocks/tickers/{ticker}", params={"apiKey": api_key})
        response.raise_for_status()
        payload = response.json()
        snapshot = payload.get("ticker") or payload
        return self._normalize_snapshot(snapshot)

    async def get_news(self, ticker, start, end):
        api_key = self._require_api_key()
        response = await self.client.get(
            "/v2/reference/news",
            params={
                "ticker": ticker,
                "published_utc.gte": self._format_date(start),
                "published_utc.lte": self._format_date(end),
                "order": "desc",
                "limit": 100,
                "apiKey": api_key,
            },
        )
        response.raise_for_status()
        payload = response.json()
        return [self._normalize_news(ticker, row) for row in payload.get("results", [])]

    async def _get_aggregate_candles(self, ticker, start, end, multiplier, timespan, timeframe):
        api_key = self._require_api_key()
        start_value = self._format_date(start)
        end_value = self._format_date(end)
        path = f"/v2/aggs/ticker/{ticker}/range/{multiplier}/{timespan}/{start_value}/{end_value}"
        response = await self.client.get(
            path,
            params={"adjusted": "true", "sort": "asc", "limit": 50000, "apiKey": api_key},
        )
        response.raise_for_status()
        payload = response.json()
        return [self._normalize_candle(ticker, timeframe, row) for row in payload.get("results", [])]

    def _normalize_candle(self, ticker, timeframe, row):
        return {
            "ticker": ticker,
            "provider": self.provider_name,
            "timeframe": timeframe,
            "timestamp_ms": row.get("t"),
            "open": row.get("o"),
            "high": row.get("h"),
            "low": row.get("l"),
            "close": row.get("c"),
            "volume": row.get("v"),
            "vwap": row.get("vw"),
            "transactions": row.get("n"),
            "raw": row,
        }

    def _normalize_snapshot(self, snapshot):
        day = snapshot.get("day") or {}
        previous_day = snapshot.get("prevDay") or {}
        last_quote = snapshot.get("lastQuote") or {}
        return {
            "ticker": snapshot.get("ticker"),
            "provider": self.provider_name,
            "price": day.get("c"),
            "volume": day.get("v"),
            "previous_close": previous_day.get("c"),
            "bid": last_quote.get("p"),
            "ask": last_quote.get("P"),
            "raw": snapshot,
        }

    def _normalize_news(self, ticker, row):
        headline = row.get("title") or ""
        catalyst_type = self._infer_news_catalyst_type(headline, row.get("description"))
        published_utc = row.get("published_utc")
        return {
            "provider": self.provider_name,
            "ticker": ticker,
            "external_id": row.get("id"),
            "headline": headline,
            "summary": row.get("description"),
            "published_utc": published_utc,
            "timestamp_ms": self._timestamp_ms_from_utc(published_utc),
            "source": (row.get("publisher") or {}).get("name"),
            "url": row.get("article_url"),
            "catalyst_type": catalyst_type,
            "raw": row,
        }

    def _infer_news_catalyst_type(self, headline, description=None):
        text = f"{headline or ''} {description or ''}".lower()
        if "earnings beat" in text or "beats earnings" in text or "beats estimates" in text:
            return "earnings_beat"
        if "earnings miss" in text or "misses earnings" in text or "misses estimates" in text or "missed expectations" in text:
            return "earnings_miss"
        if "raises guidance" in text or "guidance raise" in text:
            return "guidance_raise"
        if "cuts guidance" in text or "guidance cut" in text:
            return "guidance_cut"
        if "credit rating" in text or "rating agency" in text or ("moody" in text and "rating" in text):
            return "credit_rating"
        if "upgrade" in text:
            return "analyst_upgrade"
        if "downgrade" in text:
            return "analyst_downgrade"
        if "fda approval" in text or "approved by fda" in text or "fda clearance" in text:
            return "fda_approval"
        if "contract" in text and ("win" in text or "award" in text):
            return "contract_win"
        if "partnership" in text or "strategic alliance" in text or "collaborat" in text:
            return "partnership"
        if "buyback" in text or "repurchase" in text:
            return "buyback"
        if "dividend" in text and ("increase" in text or "raise" in text or "special" in text or "declare" in text):
            return "dividend"
        if "launch" in text or "unveils" in text or "introduces" in text:
            return "product_launch"
        if "acquire" in text or "acquisition" in text or "merger" in text or "buyout" in text:
            return "m_and_a"
        if "clinical trial" in text or "phase 1" in text or "phase 2" in text or "phase 3" in text:
            return "fda_clinical"
        if "initiat" in text and ("coverage" in text or "rating" in text):
            return "analyst_initiation"
        if "credit rating" in text or "rating agency" in text or ("moody" in text and "rating" in text):
            return "credit_rating"
        if "investigation" in text or "lawsuit" in text or "sues " in text or "sec probe" in text:
            return "investigation"
        return classify_catalyst({})["catalyst_type"]

    def _parse_timeframe(self, timeframe):
        if timeframe.endswith("m"):
            return int(timeframe[:-1]), "minute"
        if timeframe.endswith("h"):
            return int(timeframe[:-1]), "hour"
        if timeframe.endswith("d"):
            return int(timeframe[:-1]), "day"
        raise ValueError("Unsupported timeframe: {0}".format(timeframe))

    def _format_date(self, value):
        if isinstance(value, datetime):
            return value.date().isoformat()
        return str(value)

    def _timestamp_ms_from_utc(self, value):
        if not value:
            return None
        normalized = value.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return int(parsed.timestamp() * 1000)
