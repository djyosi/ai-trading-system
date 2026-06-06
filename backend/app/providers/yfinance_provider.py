from app.providers.market_data_base import MarketDataProvider


class YFinanceProvider(MarketDataProvider):
    """Low-cost historical fallback provider.

    yfinance data is useful for prototyping and historical development, but it is
    delayed/not guaranteed and should not be treated as production-grade live
    day-trading data.
    """

    provider_name = "yfinance"

    def __init__(self, ticker_factory=None):
        self._ticker_factory = ticker_factory

    def _ticker(self, ticker):
        if self._ticker_factory is not None:
            return self._ticker_factory(ticker)
        import yfinance as yf

        return yf.Ticker(ticker)

    async def get_symbols(self):
        return []

    async def get_daily_candles(self, ticker, start, end):
        return self._history_to_candles(ticker, start, end, interval="1d", timeframe="1d")

    async def get_intraday_candles(self, ticker, start, end, timeframe="1m"):
        return self._history_to_candles(ticker, start, end, interval=timeframe, timeframe=timeframe)

    async def get_snapshot(self, ticker):
        return None

    def _history_to_candles(self, ticker, start, end, interval, timeframe):
        history = self._ticker(ticker).history(
            start=start,
            end=end,
            interval=interval,
            auto_adjust=False,
            prepost=True,
        )
        if history is None or history.empty:
            return []

        candles = []
        for timestamp, row in history.iterrows():
            raw = {
                "Open": self._float_or_none(row.get("Open")),
                "High": self._float_or_none(row.get("High")),
                "Low": self._float_or_none(row.get("Low")),
                "Close": self._float_or_none(row.get("Close")),
                "Volume": self._int_or_none(row.get("Volume")),
            }
            candles.append(
                {
                    "ticker": ticker,
                    "provider": self.provider_name,
                    "timeframe": timeframe,
                    "timestamp": timestamp.isoformat(),
                    "open": raw["Open"],
                    "high": raw["High"],
                    "low": raw["Low"],
                    "close": raw["Close"],
                    "volume": raw["Volume"],
                    "vwap": None,
                    "transactions": None,
                    "raw": raw,
                }
            )
        return candles

    def _float_or_none(self, value):
        if value is None:
            return None
        return float(value)

    def _int_or_none(self, value):
        if value is None:
            return None
        return int(value)
