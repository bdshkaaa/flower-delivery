"""Unit-тесты отказоустойчивости доставки: Circuit Breaker, TTL-кэш, запасной тариф. БД не нужна."""
from decimal import Decimal

from app.delivery.base import DeliveryQuote
from app.delivery.breaker import CLOSED, HALF_OPEN, OPEN, CircuitBreaker
from app.delivery.cache import TTLCache
from app.delivery.mock import MockDeliveryProvider
from app.delivery.service import (
    FALLBACK_ETA_DAYS,
    FALLBACK_TARIFF,
    DeliveryService,
    region_key_from_address,
)


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


class MemoryStore:
    """Подмена таблицы delivery_quotes."""

    def __init__(self, latest=None):
        self.saved = []
        self._latest = latest

    def save(self, region, weight, quote):
        self.saved.append((region, weight, quote))

    def latest(self, region, weight):
        return self._latest


def make_service(provider=None, store=None, clock=None, threshold=3, ttl=60):
    clock = clock or FakeClock()
    return (
        DeliveryService(
            provider or MockDeliveryProvider(),
            CircuitBreaker(threshold, 30, clock),
            TTLCache(ttl, clock),
            store,
        ),
        clock,
    )


# ---- Circuit Breaker ----
def test_breaker_opens_after_threshold_failures():
    breaker = CircuitBreaker(failure_threshold=3, reset_seconds=30, clock=FakeClock())
    for _ in range(2):
        breaker.record_failure()
    assert breaker.state == CLOSED
    breaker.record_failure()
    assert breaker.state == OPEN
    assert breaker.allow_request() is False


def test_breaker_half_open_after_pause_then_closes_on_success():
    clock = FakeClock()
    breaker = CircuitBreaker(failure_threshold=1, reset_seconds=30, clock=clock)
    breaker.record_failure()
    clock.now = 31
    assert breaker.state == HALF_OPEN
    breaker.record_success()
    assert breaker.state == CLOSED


def test_breaker_reopens_if_probe_fails():
    clock = FakeClock()
    breaker = CircuitBreaker(failure_threshold=3, reset_seconds=30, clock=clock)
    for _ in range(3):
        breaker.record_failure()
    clock.now = 31
    assert breaker.state == HALF_OPEN
    breaker.record_failure()
    assert breaker.state == OPEN


# ---- TTL-кэш ----
def test_cache_expires_after_ttl():
    clock = FakeClock()
    cache = TTLCache(10, clock)
    cache.set(("spb", "light"), "x")
    clock.now = 9
    assert cache.get(("spb", "light")) == "x"
    clock.now = 10
    assert cache.get(("spb", "light")) is None


# ---- Сервис ----
def test_region_key_is_first_part_of_address():
    assert region_key_from_address("Москва, Тверская 1") == "москва"
    assert region_key_from_address("  ") == "unknown"


def test_live_quote_is_cached_and_saved():
    store = MemoryStore()
    provider = MockDeliveryProvider()
    service, _ = make_service(provider, store)

    quote, source = service.get_quote("Москва, Тверская 1", "medium")
    assert source == "api" and quote.cost == Decimal("450.00") and not quote.approximate
    assert len(store.saved) == 1

    _, source = service.get_quote("Москва, Арбат 5", "medium")  # тот же регион и вес
    assert source == "cache"
    assert provider.calls == 1


def test_cache_expires_and_provider_is_called_again():
    provider = MockDeliveryProvider()
    service, clock = make_service(provider, ttl=60)
    service.get_quote("Москва, 1", "light")
    clock.now = 61
    _, source = service.get_quote("Москва, 1", "light")
    assert source == "api" and provider.calls == 2


def test_failing_api_uses_last_db_quote():
    old = DeliveryQuote(cost=Decimal("480.00"), eta_days=2, approximate=True)
    service, _ = make_service(MockDeliveryProvider(failing=True), MemoryStore(latest=old))

    quote, source = service.get_quote("Москва, 1", "medium")
    assert source == "cache" and quote.cost == Decimal("480.00") and quote.approximate


def test_failing_api_without_history_uses_fallback_tariff():
    service, _ = make_service(MockDeliveryProvider(failing=True), MemoryStore())

    quote, source = service.get_quote("Москва, 1", "heavy")
    assert source == "fallback" and quote.approximate
    assert quote.cost == FALLBACK_TARIFF["heavy"] and quote.eta_days == FALLBACK_ETA_DAYS


def test_open_breaker_stops_calling_api():
    provider = MockDeliveryProvider(failing=True)
    service, clock = make_service(provider, threshold=3)
    for i in range(5):
        service.get_quote(f"Город{i}, 1", "light")
    assert provider.calls == 3  # после 3 сбоев API больше не дёргаем

    clock.now = 31  # пауза прошла — пробный запрос
    provider.failing = False
    _, source = service.get_quote("Город9, 1", "light")
    assert source == "api" and provider.calls == 4
