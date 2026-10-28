"""Unit-тесты отказоустойчивости доставки: Circuit Breaker, TTL-кэш, несколько служб,
недоступность доставки, запасной тариф. БД не нужна."""
from decimal import Decimal

import pytest

from app.delivery.base import BadAddressError, DeliveryOption, NotServiceable, ProviderError
from app.delivery.breaker import CLOSED, HALF_OPEN, OPEN, CircuitBreaker
from app.delivery.cache import TTLCache
from app.delivery.service import (
    ADDRESS_NOT_FOUND,
    FALLBACK_ETA_DAYS,
    FALLBACK_TARIFF,
    DeliveryService,
    region_key,
)
from tests.fakes import ScriptedProvider, option


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


class MemoryStore:
    """Подмена таблицы delivery_quotes."""

    def __init__(self, latest=None):
        self.saved = []
        self._latest = latest or []

    def save(self, region, weight, options):
        self.saved.append((region, weight, options))

    def latest(self, region, weight):
        return self._latest


def make_service(*providers, store=None, ttl=60, threshold=3):
    clock = FakeClock()
    service = DeliveryService(
        list(providers), TTLCache(ttl, clock), store,
        breaker_threshold=threshold, breaker_reset_seconds=30, breaker_clock=clock,
    )
    return service, clock


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


# ---- Ключ региона ----
def test_region_key_is_first_part_of_address():
    assert region_key("Москва, Тверская 1") == "москва"
    assert region_key("  ") == "unknown"


def test_region_key_for_map_point_is_one_km_cell():
    assert region_key("любой адрес", 59.9386, 30.3141) == "59.94,30.31"


# ---- Несколько служб ----
def test_options_of_all_providers_are_merged_and_sorted_by_cost():
    a = ScriptedProvider("a", [option("a:std", "900.00", 3), option("a:fast", "1500.00", 1)])
    b = ScriptedProvider("b", [option("b:std", "600.00", 2)])
    service, _ = make_service(a, b)

    result = service.get_options("Москва, 1", "medium")

    assert result.available and result.source == "api"
    assert [o.id for o in result.options] == ["b:std", "a:std", "a:fast"]


def test_one_failing_provider_does_not_hide_others():
    good = ScriptedProvider("good")
    bad = ScriptedProvider("bad", ProviderError("down"))
    service, _ = make_service(bad, good)

    result = service.get_options("Москва, 1", "light")

    assert result.available and [o.id for o in result.options] == ["good:std"]


def test_live_options_are_cached_and_saved():
    store = MemoryStore()
    provider = ScriptedProvider("a")
    service, _ = make_service(provider, store=store)

    first = service.get_options("Москва, Тверская 1", "medium")
    second = service.get_options("Москва, Арбат 5", "medium")  # тот же регион и вес

    assert first.source == "api" and second.source == "cache"
    assert provider.calls == 1 and len(store.saved) == 1


def test_cache_expires_and_providers_are_called_again():
    provider = ScriptedProvider("a")
    service, clock = make_service(provider, ttl=60)
    service.get_options("Москва, 1", "light")
    clock.now = 61
    service.get_options("Москва, 1", "light")
    assert provider.calls == 2


# ---- Сбои и запасные варианты ----
def test_all_providers_down_uses_last_known_options_from_db():
    old = DeliveryOption("a:std", "Служба", Decimal("480.00"), 2, approximate=True)
    service, _ = make_service(ScriptedProvider("a", ProviderError("x")), store=MemoryStore([old]))

    result = service.get_options("Москва, 1", "medium")

    assert result.source == "cache" and result.options[0].cost == Decimal("480.00")
    assert result.options[0].approximate


def test_all_providers_down_without_history_uses_fallback_tariff():
    service, _ = make_service(ScriptedProvider("a", ProviderError("x")), store=MemoryStore())

    result = service.get_options("Москва, 1", "heavy")

    assert result.available and result.source == "fallback"
    only = result.options[0]
    assert only.approximate and only.cost == FALLBACK_TARIFF["heavy"] and only.eta_days == FALLBACK_ETA_DAYS


def test_open_breaker_stops_calling_failing_provider_only():
    bad = ScriptedProvider("bad", ProviderError("down"))
    good = ScriptedProvider("good")
    service, clock = make_service(bad, good, threshold=3)

    for i in range(5):
        service.get_options(f"Город{i}, 1", "light")

    assert bad.calls == 3  # после 3 сбоев эту службу больше не дёргаем
    assert good.calls == 5  # исправная служба работает как обычно

    clock.now = 31  # пауза прошла: пробный запрос к восстановившейся службе
    bad.result = [option("bad:std")]
    result = service.get_options("Город9, 1", "light")
    assert bad.calls == 4 and "bad:std" in [o.id for o in result.options]


# ---- Доставка недоступна ----
def test_all_providers_refuse_means_delivery_unavailable_with_reason():
    refusal = NotServiceable("Доставка в эту страну недоступна")
    service, _ = make_service(ScriptedProvider("a", refusal), ScriptedProvider("b", refusal))

    result = service.get_options("Paris", "medium")

    assert result.available is False and result.options == []
    assert result.reason == "Доставка в эту страну недоступна"


def test_refusal_is_not_a_failure_for_circuit_breaker():
    provider = ScriptedProvider("a", NotServiceable("нет"))
    service, _ = make_service(provider, threshold=2)

    for i in range(5):
        service.get_options(f"Город{i}", "light")

    assert provider.calls == 5  # breaker не открылся


def test_one_provider_refuses_other_delivers():
    service, _ = make_service(
        ScriptedProvider("a", NotServiceable("нет")), ScriptedProvider("b", [option("b:std")]))

    assert service.get_options("Минск", "light").available


def test_foreign_country_during_outage_is_unavailable_not_fallback():
    service, _ = make_service(ScriptedProvider("a", ProviderError("down")), store=MemoryStore())

    result = service.get_options("Париж, Франция", "light")

    assert result.available is False and result.source != "fallback"


def test_address_not_found_asks_to_clarify():
    service, _ = make_service(ScriptedProvider("a", BadAddressError("no")))

    result = service.get_options("Нигдеград", "light")

    assert result.available is False and result.reason == ADDRESS_NOT_FOUND


def test_address_not_found_does_not_open_breaker():
    provider = ScriptedProvider("a", BadAddressError("no"))
    service, _ = make_service(provider, threshold=2)

    for i in range(5):
        service.get_options(f"Нигде{i}", "light")

    assert provider.calls == 5
