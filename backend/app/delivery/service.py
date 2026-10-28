"""Расчёт доставки у нескольких служб с отказоустойчивостью.

Для каждой службы по очереди: свежий кэш (TTL) -> запрос через её Circuit Breaker.
Варианты всех служб собираются в один список (дешёвые первыми).
Если ни одна служба не ответила:
  * все службы сообщили, что по адресу не доставляют, — «доставка недоступна» (с причиной);
  * адрес не найден — просим уточнить адрес;
  * иначе (сбой служб) — последние известные тарифы из БД, а затем запасной тариф.
Оформление заказа сбой служб не блокирует, но к странам и местам, куда не доставляет
никто, запасной тариф не применяется."""
import logging
from dataclasses import dataclass, field
from decimal import Decimal
from functools import lru_cache
from typing import Optional

from ..config import settings
from .base import (
    BadAddressError,
    DeliveryOption,
    Destination,
    NotServiceable,
    OptionsProvider,
    ProviderError,
)
from .area import ServiceArea
from .breaker import CircuitBreaker
from .cache import TTLCache
from .countries import country_of
from .factory import build_providers
from .geocoder import get_geocoder
from .store import QuoteStore

logger = logging.getLogger("app.delivery.service")

FALLBACK_TARIFF = {
    "light": Decimal("350.00"),
    "medium": Decimal("500.00"),
    "heavy": Decimal("700.00"),
}
FALLBACK_ETA_DAYS = 3
ADDRESS_NOT_FOUND = "Не удалось найти адрес. Уточните город, улицу и дом."
NOBODY_DELIVERS = "По этому адресу доставка недоступна: подходящих служб доставки нет."


@dataclass
class OptionsResult:
    available: bool
    options: list[DeliveryOption] = field(default_factory=list)
    reason: Optional[str] = None
    source: str = "api"  # api | cache | fallback


def region_key(address: str, lat: Optional[float] = None, lon: Optional[float] = None) -> str:
    """Ключ региона для кэша: точка на карте (клетка около 1 км) или первая часть адреса
    («Москва, Тверская 1» -> «москва»)."""
    if lat is not None and lon is not None:
        return f"{lat:.2f},{lon:.2f}"
    return address.split(",")[0].strip().lower() or "unknown"


class DeliveryService:
    def __init__(
        self,
        providers: list[OptionsProvider],
        cache: TTLCache,
        store: Optional[QuoteStore] = None,
        breaker_threshold: int = 3,
        breaker_reset_seconds: float = 30.0,
        breaker_clock=None,
        area: Optional[ServiceArea] = None,
    ) -> None:
        self.area = area
        self.providers = providers
        self.cache = cache
        self.store = store
        kwargs = {"clock": breaker_clock} if breaker_clock else {}
        # у каждой службы свой Circuit Breaker: сбой одной не отключает остальные
        self.breakers = {
            p.id: CircuitBreaker(breaker_threshold, breaker_reset_seconds, **kwargs) for p in providers
        }

    def get_options(
        self, address: str, weight_category: str, lat: Optional[float] = None, lon: Optional[float] = None
    ) -> OptionsResult:
        if self.area is not None:
            try:
                self.area.check(address, lat, lon)
            except NotServiceable as exc:
                return OptionsResult(False, reason=exc.reason)
        region = region_key(address, lat, lon)
        destination = Destination(region_key=region, address=address, lon=lon, lat=lat)

        collected: list[DeliveryOption] = []
        fresh = False
        refusals: list[str] = []
        not_found = False
        outage = False

        for provider in self.providers:
            key = (provider.id, region, weight_category)
            cached = self.cache.get(key)
            if cached is not None:
                collected += cached
                continue
            breaker = self.breakers[provider.id]
            if not breaker.allow_request():
                logger.info("delivery provider %s skipped: circuit breaker is open", provider.id)
                outage = True
                continue
            try:
                options = provider.get_options(destination, weight_category)
            except NotServiceable as exc:
                breaker.record_success()  # служба ответила, это не сбой
                refusals.append(exc.reason)
            except BadAddressError as exc:
                logger.info("delivery address not found by %s: %s", provider.id, exc)
                not_found = True
            except ProviderError as exc:
                breaker.record_failure()
                outage = True
                logger.warning("delivery provider %s failed: %s", provider.id, exc)
            else:
                breaker.record_success()
                self.cache.set(key, options)
                if self.store:
                    self.store.save(region, weight_category, options)
                collected += options
                fresh = True

        if collected:
            collected.sort(key=lambda o: (o.cost, o.eta_days))
            return OptionsResult(True, collected, source="api" if fresh else "cache")

        if not outage:
            if not_found and not refusals:
                return OptionsResult(False, reason=ADDRESS_NOT_FOUND)
            return OptionsResult(False, reason=refusals[0] if refusals else NOBODY_DELIVERS)

        # Службы недоступны: последние известные тарифы, затем запасной тариф
        if country_of(address) == "OTHER":
            return OptionsResult(False, reason=refusals[0] if refusals else NOBODY_DELIVERS)
        if self.store:
            old = self.store.latest(region, weight_category)
            if old:
                return OptionsResult(True, sorted(old, key=lambda o: (o.cost, o.eta_days)), source="cache")
        fallback = DeliveryOption(
            "fallback:standard", "Доставка (предварительная стоимость)",
            FALLBACK_TARIFF[weight_category], FALLBACK_ETA_DAYS, approximate=True,
        )
        return OptionsResult(True, [fallback], source="fallback")


@lru_cache
def get_delivery_service() -> DeliveryService:
    return DeliveryService(
        providers=build_providers(settings, get_geocoder()),
        cache=TTLCache(settings.delivery_cache_ttl_seconds),
        store=QuoteStore(),
        breaker_threshold=settings.delivery_breaker_threshold,
        breaker_reset_seconds=settings.delivery_breaker_reset_seconds,
        area=ServiceArea(settings.shop_lon, settings.shop_lat, settings.delivery_radius_km, get_geocoder()),
    )
