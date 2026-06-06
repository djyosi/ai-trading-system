from datetime import datetime

import httpx

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
