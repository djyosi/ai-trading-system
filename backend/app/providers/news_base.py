from abc import ABC, abstractmethod


class NewsProvider(ABC):
    @abstractmethod
    async def get_news(self, ticker, start, end):
        """Return normalized news records for ticker between start and end."""
        raise NotImplementedError
