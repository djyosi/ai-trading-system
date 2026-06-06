import pytest

from app.core.config import Settings
from app.providers.ibkr_paper import IBKRPaperBroker, LiveTradingSafetyError


@pytest.mark.asyncio
async def test_ibkr_paper_adapter_defaults_to_disabled():
    adapter = IBKRPaperBroker(Settings(enable_ibkr=False))

    assert await adapter.connect() is False
    assert await adapter.get_account_summary() == {"connected": False, "mode": "paper"}


@pytest.mark.asyncio
async def test_ibkr_paper_adapter_refuses_live_mode():
    adapter = IBKRPaperBroker(Settings(enable_ibkr=True, ibkr_account_mode="live"))

    with pytest.raises(LiveTradingSafetyError, match="live trading is not supported"):
        await adapter.connect()


@pytest.mark.asyncio
async def test_ibkr_paper_adapter_can_use_injected_client_for_read_only_connection():
    class FakeClient:
        def __init__(self):
            self.connected_with = None

        async def connect(self, host, port, client_id):
            self.connected_with = {"host": host, "port": port, "client_id": client_id}
            return True

        async def get_account_summary(self):
            return {"NetLiquidation": "100000", "BuyingPower": "50000"}

        async def is_symbol_tradable(self, ticker):
            return ticker == "AAPL"

    client = FakeClient()
    settings = Settings(enable_ibkr=True, ibkr_account_mode="paper")
    adapter = IBKRPaperBroker(settings, client=client)

    assert await adapter.connect() is True
    assert client.connected_with == {"host": "127.0.0.1", "port": 7497, "client_id": 7}
    assert await adapter.get_account_summary() == {"NetLiquidation": "100000", "BuyingPower": "50000"}
    assert await adapter.is_symbol_tradable("AAPL") is True
    assert await adapter.is_symbol_tradable("OTCXYZ") is False


def test_ibkr_paper_adapter_has_no_order_placement_method_in_mvp():
    adapter = IBKRPaperBroker(Settings())

    assert not hasattr(adapter, "place_order")
