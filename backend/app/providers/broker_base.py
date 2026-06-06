from abc import ABC, abstractmethod


class BrokerAdapter(ABC):
    @abstractmethod
    async def connect(self):
        """Connect to the broker in the configured account mode."""
        raise NotImplementedError

    @abstractmethod
    async def get_account_summary(self):
        """Return read-only broker account information."""
        raise NotImplementedError

    @abstractmethod
    async def is_symbol_tradable(self, ticker):
        """Return whether ticker is tradable at the broker."""
        raise NotImplementedError
