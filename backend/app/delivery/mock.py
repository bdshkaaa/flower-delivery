from decimal import Decimal

from .base import (
    WEIGHT_CATEGORIES,
    DeliveryQuote,
    Destination,
    ProviderError,
)

_BASE_COST = {
    "light": Decimal("300.00"),
    "medium": Decimal("450.00"),
    "heavy": Decimal("650.00"),
}


class MockDeliveryProvider:
    """Заглушка внешнего API: не ходит в сеть, ответ предсказуем.

    Нужна CI и тестам: во-первых, реальный сервис нестабилен и имеет лимиты,
    во-вторых, заглушку можно «уронить» (failing=True) и проверить поведение
    при недоступности API — кэш, Circuit Breaker, fallback."""

    def __init__(self, failing: bool = False) -> None:
        self.failing = failing
        self.calls = 0

    def get_quote(self, destination: Destination, weight_category: str) -> DeliveryQuote:
        self.calls += 1
        if self.failing:
            raise ProviderError("mock provider is failing")
        if weight_category not in WEIGHT_CATEGORIES:
            raise ValueError(f"unknown weight category: {weight_category}")
        return DeliveryQuote(cost=_BASE_COST[weight_category], eta_days=1)
