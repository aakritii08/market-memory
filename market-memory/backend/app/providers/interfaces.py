from abc import ABC, abstractmethod
from datetime import datetime

class MarketDataProvider(ABC):
    @abstractmethod
    def quote(self, symbol: str) -> dict: ...
class NewsProvider(ABC):
    @abstractmethod
    def events(self, symbol: str, since: datetime | None = None) -> list[dict]: ...
class CompanyDataProvider(ABC):
    @abstractmethod
    def company(self, symbol: str) -> dict: ...
