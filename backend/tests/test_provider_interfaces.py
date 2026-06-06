import pytest

from app.providers.broker_base import BrokerAdapter
from app.providers.market_data_base import MarketDataProvider
from app.providers.news_base import NewsProvider


def test_market_data_provider_cannot_be_instantiated_directly():
    with pytest.raises(TypeError):
        MarketDataProvider()


def test_news_provider_cannot_be_instantiated_directly():
    with pytest.raises(TypeError):
        NewsProvider()


def test_broker_adapter_cannot_be_instantiated_directly():
    with pytest.raises(TypeError):
        BrokerAdapter()


def test_minimal_market_data_provider_implements_required_contract():
    class FakeMarketDataProvider(MarketDataProvider):
        async def get_symbols(self):
            return []

        async def get_daily_candles(self, ticker, start, end):
            return []

        async def get_intraday_candles(self, ticker, start, end, timeframe="1m"):
            return []

        async def get_snapshot(self, ticker):
            return None

    provider = FakeMarketDataProvider()
    assert isinstance(provider, MarketDataProvider)


def test_minimal_news_provider_implements_required_contract():
    class FakeNewsProvider(NewsProvider):
        async def get_news(self, ticker, start, end):
            return []

    provider = FakeNewsProvider()
    assert isinstance(provider, NewsProvider)


def test_minimal_broker_adapter_implements_required_contract():
    class FakeBrokerAdapter(BrokerAdapter):
        async def connect(self):
            return True

        async def get_account_summary(self):
            return {}

        async def is_symbol_tradable(self, ticker):
            return True

    adapter = FakeBrokerAdapter()
    assert isinstance(adapter, BrokerAdapter)
