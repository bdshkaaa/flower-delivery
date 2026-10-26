"""Расчёт доставки с отказоустойчивостью. Порядок:
1) свежий кэш (TTL) -> 2) внешний API через Circuit Breaker ->
3) последняя котировка из БД -> 4) запасной тариф.
Оформление заказа доставка не блокирует: сервис никогда не бросает исключений."""
import logging
from decimal import Decimal
from functools import lru_cache
from typing import Optional

from ..config import settings
from .base import DeliveryProvider, DeliveryQuote, Destination, ProviderError
from .breaker import CircuitBreaker
from .cache import TTLCache
from .factory import get_provider
from .store import QuoteStore

logger = logging.getLogger("app.delivery.service")

FALLBACK_TARIFF = {
    "light": Decimal("350.00"),
    "medium": Decimal("500.00"),
    "heavy": Decimal("700.00"),
}
FALLBACK_ETA_DAYS = 3


def region_key_from_address(address: str) -> str:
    """Регион для ключа кэша: первая часть адреса до запятой («Москва, Тверская 1» -> «москва»)."""
    return address.split(",")[0].strip().lower() or "unknown"


class DeliveryService:
    def __init__(
        self,
        provider: DeliveryProvider,
        breaker: CircuitBreaker,
        cache: TTLCache,
        store: Optional[QuoteStore] = None,
    ) -> None:
        self.provider = provider
        self.breaker = breaker
        self.cache = cache
        self.store = store

    def get_quote(self, address: str, weight_category: str) -> tuple[DeliveryQuote, str]:
        """Возвращает (котировка, источник): api / cache / fallback."""
        region = region_key_from_address(address)
        key = (region, weight_category)

        cached = self.cache.get(key)
        if cached is not None:
            return cached, "cache"

        if self.breaker.allow_request():
            try:
                quote = self.provider.get_quote(Destination(region_key=region, address=address), weight_category)
            except ProviderError as exc:
                self.breaker.record_failure()
                logger.warning("delivery api failed: %s", exc)
            else:
                self.breaker.record_success()
                self.cache.set(key, quote)
                if self.store:
                    self.store.save(region, weight_category, quote)
                return quote, "api"
        else:
            logger.info("delivery api skipped: circuit breaker is open")

        if self.store:
            old = self.store.latest(region, weight_category)
            if old is not None:
                return old, "cache"

        return (
            DeliveryQuote(cost=FALLBACK_TARIFF[weight_category], eta_days=FALLBACK_ETA_DAYS, approximate=True),
            "fallback",
        )


@lru_cache
def get_delivery_service() -> DeliveryService:
    return DeliveryService(
        provider=get_provider(settings),
        breaker=CircuitBreaker(settings.delivery_breaker_threshold, settings.delivery_breaker_reset_seconds),
        cache=TTLCache(settings.delivery_cache_ttl_seconds),
        store=QuoteStore(),
    )
