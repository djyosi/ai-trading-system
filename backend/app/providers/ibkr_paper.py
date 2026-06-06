from app.core.config import settings as default_settings
from app.providers.broker_base import BrokerAdapter


class LiveTradingSafetyError(RuntimeError):
    """Raised when MVP code is asked to use live brokerage mode."""


class IBKRPaperBroker(BrokerAdapter):
    """Read-only IBKR paper adapter skeleton.

    MVP v1 intentionally has no order placement capability. Execution will be
    added only after recommendations, backtests, walk-forward tests, and paper
    safety controls are implemented.
    """

    def __init__(self, settings=None, client=None):
        self.settings = settings or default_settings
        self.client = client
        self.connected = False

    async def connect(self):
        self._ensure_safe_mode()
        if not self.settings.enable_ibkr:
            self.connected = False
            return False
        if self.client is None:
            self.connected = False
            return False
        self.connected = await self.client.connect(
            self.settings.ibkr_host,
            self.settings.ibkr_port,
            self.settings.ibkr_client_id,
        )
        return self.connected

    async def get_account_summary(self):
        self._ensure_safe_mode()
        if not self.connected or self.client is None:
            return {"connected": False, "mode": "paper"}
        return await self.client.get_account_summary()

    async def is_symbol_tradable(self, ticker):
        self._ensure_safe_mode()
        if not self.connected or self.client is None:
            return False
        return await self.client.is_symbol_tradable(ticker)

    def _ensure_safe_mode(self):
        if self.settings.ibkr_account_mode != "paper":
            raise LiveTradingSafetyError("IBKR live trading is not supported in MVP v1")
