"""Адаптер Яндекс Доставки и геокодер на подменённой сети (httpx.MockTransport).
Реальный API не вызывается: токена в CI нет."""
import json
from decimal import Decimal

import httpx
import pytest

from app.delivery.base import BadAddressError, Destination, ProviderError
from app.delivery.breaker import CircuitBreaker
from app.delivery.cache import TTLCache
from app.delivery.geocoder import NominatimGeocoder
from app.delivery.service import DeliveryService
from app.delivery.yandex import YandexDeliveryProvider

DEST = Destination(region_key="москва", address="Москва, Тверская 1")


class FakeGeocoder:
    def __init__(self, error=None):
        self.error, self.calls = error, 0

    def geocode(self, address):
        self.calls += 1
        if self.error:
            raise self.error
        return 37.6, 55.75


def provider(handler, geocoder=None):
    return YandexDeliveryProvider(
        token="secret-token", base_url="https://api.test", shop_lon=30.3, shop_lat=59.9,
        timeout_seconds=1, geocoder=geocoder or FakeGeocoder(),
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )


def ok(request):
    return httpx.Response(200, json={"price": "412.5000", "currency_rules": {"code": "RUB"}, "eta": 90})


def test_successful_quote_is_parsed():
    quote = provider(ok).get_quote(DEST, "medium")

    assert quote.cost == Decimal("412.50")
    assert quote.eta_days == 1
    assert quote.approximate is False


def test_request_is_built_as_documented():
    seen = {}

    def handler(request):
        seen["url"], seen["auth"] = str(request.url), request.headers["authorization"]
        seen["body"] = json.loads(request.content)
        return ok(request)

    provider(handler).get_quote(DEST, "heavy")

    assert seen["url"] == "https://api.test/b2b/cargo/integration/v2/check-price"
    assert seen["auth"] == "Bearer secret-token"
    assert seen["body"]["items"][0]["weight"] == 4.0
    assert seen["body"]["route_points"][0]["coordinates"] == [30.3, 59.9]  # магазин: долгота, широта
    assert seen["body"]["route_points"][1]["coordinates"] == [37.6, 55.75]


def test_long_eta_is_rounded_up_to_days():
    def handler(request):
        return httpx.Response(200, json={"price": "900", "currency_rules": {"code": "RUB"}, "eta": 1500})

    assert provider(handler).get_quote(DEST, "light").eta_days == 2


@pytest.mark.parametrize("status", [409, 429, 500, 503])
def test_http_errors_become_provider_error(status):
    with pytest.raises(ProviderError):
        provider(lambda r: httpx.Response(status, json={"code": "x"})).get_quote(DEST, "light")


def test_address_not_found_is_bad_address_error():
    response = httpx.Response(400, json={"code": "address_not_found", "message": "no"})

    with pytest.raises(BadAddressError):
        provider(lambda r: response).get_quote(DEST, "light")


def test_timeout_and_network_error_become_provider_error():
    def handler(request):
        raise httpx.ConnectTimeout("timeout")

    with pytest.raises(ProviderError):
        provider(handler).get_quote(DEST, "light")


@pytest.mark.parametrize("payload", [
    {"price": "100"},                                              # нет валюты
    {"price": "abc", "currency_rules": {"code": "RUB"}},           # цена не число
    {"price": "100", "currency_rules": {"code": "USD"}},           # не рубли
    {"price": "0", "currency_rules": {"code": "RUB"}},             # нулевая цена
])
def test_unexpected_payload_is_rejected(payload):
    with pytest.raises(ProviderError):
        provider(lambda r: httpx.Response(200, json=payload)).get_quote(DEST, "light")


def test_geocoder_failure_is_provider_error_and_skips_api():
    called = []
    prov = provider(lambda r: called.append(1) or ok(r), FakeGeocoder(ProviderError("down")))

    with pytest.raises(ProviderError):
        prov.get_quote(DEST, "light")
    assert called == []


def test_missing_token_is_rejected():
    with pytest.raises(ValueError):
        YandexDeliveryProvider("", "https://x", 0, 0, 1)


def test_bad_address_does_not_open_circuit_breaker():
    prov = provider(lambda r: httpx.Response(400, json={"code": "address_not_found"}))
    breaker = CircuitBreaker(failure_threshold=2)
    service = DeliveryService(prov, breaker, TTLCache(60))

    for i in range(5):
        _, source = service.get_quote(f"Нигде{i}, 1", "light")
        assert source == "fallback"

    assert breaker.allow_request() is True


# ---- Геокодер ----
def geocoder(handler):
    return NominatimGeocoder("https://geo.test", client=httpx.Client(transport=httpx.MockTransport(handler)))


def test_geocoder_returns_lon_lat_and_caches():
    calls = []

    def handler(request):
        calls.append(request.url.params["q"])
        return httpx.Response(200, json=[{"lat": "55.76", "lon": "37.61"}])

    geo = geocoder(handler)

    assert geo.geocode("Москва, Тверская 1") == (37.61, 55.76)
    assert geo.geocode("  москва,  тверская 1 ") == (37.61, 55.76)  # тот же адрес: из кэша
    assert len(calls) == 1


def test_geocoder_empty_result_is_bad_address():
    with pytest.raises(BadAddressError):
        geocoder(lambda r: httpx.Response(200, json=[])).geocode("Асдфгх")


def test_geocoder_server_error_is_provider_error():
    with pytest.raises(ProviderError):
        geocoder(lambda r: httpx.Response(503)).geocode("Москва")
