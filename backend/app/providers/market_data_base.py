from abc import ABC, abstractmethod


class MarketDataProvider(ABC):
    @abstractmethod
    async def get_symbols(self):
        """Return normalized symbol/reference records."""
        raise NotImplementedError

    @abstractmethod
    async def get_daily_candles(self, ticker, start, end):
        """Return normalized daily candles for ticker between start and end."""
        raise NotImplementedError

    @abstractmethod
    async def get_intraday_candles(self, ticker, start, end, timeframe="1m"):
        """Return normalized intraday candles for ticker between start and end."""
        raise NotImplementedError

    @abstractmethod
    async def get_snapshot(self, ticker):
        """Return the latest normalized snapshot for ticker, if available."""
        raise NotImplementedError
