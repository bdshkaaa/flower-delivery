from dataclasses import dataclass
from decimal import Decimal
from typing import Optional, Protocol

# Допустимые весовые категории букета (используются как часть ключа кэша котировок)
WEIGHT_CATEGORIES = ("light", "medium", "heavy")


class ProviderError(Exception):
    """Внешний сервис доставки недоступен или вернул неожиданный ответ.

    Именно это исключение считает Circuit Breaker (ещё не реализован —
    первая задача для backend после скелета)."""


@dataclass(frozen=True)
class Destination:
    """Куда везём. region_key — ключ региона для кэша котировок (например, «spb»),
    lon/lat нужны только провайдерам, которые считают по координатам."""

    region_key: str
    address: str = ""
    lon: Optional[float] = None
    lat: Optional[float] = None


@dataclass(frozen=True)
class DeliveryQuote:
    cost: Decimal
    eta_days: int
    # True, если это не живой ответ API, а кэш или фиксированный тариф
    approximate: bool = False


class DeliveryProvider(Protocol):
    def get_quote(self, destination: Destination, weight_category: str) -> DeliveryQuote:
        """Вернуть стоимость и срок доставки или бросить ProviderError."""
        ...
