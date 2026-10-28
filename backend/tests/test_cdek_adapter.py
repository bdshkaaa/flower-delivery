"""Адаптер СДЭК на подменённой сети: учётных данных в CI нет."""
import json
from decimal import Decimal

import httpx
import pytest

from app.delivery.base import Destination, NotServiceable, ProviderError
from app.delivery.cdek import CdekProvider

DEST = Destination(region_key="казань", address="Казань, Баумана 1")

TARIFFS = {
    "tariff_codes": [
        {"tariff_code": 137, "tariff_name": "Посылка склад-дверь", "delivery_mode": 3,
         "delivery_sum": 640, "period_min": 2, "period_max": 3},
        {"tariff_code": 136, "tariff_name": "Посылка склад-склад", "delivery_mode": 4,
         "delivery_sum": 350, "period_min": 2, "period_max": 3},
        {"tariff_code": 139, "tariff_name": "Посылка дверь-дверь", "delivery_mode": 1,
         "delivery_sum": 720.5, "period_min": 1, "period_max": 2},
        {"tariff_code": 5, "tariff_name": "Экономичная дверь-дверь", "delivery_mode": 3,
         "delivery_sum": 900, "period_min": 5, "period_max": 7},
    ]
}


def provider(handler):
    return CdekProvider("id", "secret", "https://cdek.test", 137, 1,
                        client=httpx.Client(transport=httpx.MockTransport(handler)))


def handler_with(tariffs, calls=None):
    def handler(request):
        if calls is not None:
            calls.append(request.url.path)
        if request.url.path == "/v2/oauth/token":
            return httpx.Response(200, json={"access_token": "tok", "expires_in": 3600})
        return httpx.Response(200, json=tariffs)
    return handler


def test_door_tariffs_are_returned_cheapest_first_max_two():
    options = provider(handler_with(TARIFFS)).get_options(DEST, "medium")

    assert [o.id for o in options] == ["cdek:137", "cdek:139"]  # склад-склад отброшен, экономичный лишний
    assert options[0].cost == Decimal("640.00") and options[0].eta_days == 3
    assert options[0].service.startswith("СДЭК")


def test_request_is_built_as_expected_and_token_is_reused():
    calls, bodies = [], []

    def handler(request):
        calls.append(request.url.path)
        if request.url.path == "/v2/oauth/token":
            return httpx.Response(200, json={"access_token": "tok", "expires_in": 3600})
        bodies.append((request.headers["authorization"], json.loads(request.content)))
        return httpx.Response(200, json=TARIFFS)

    cdek = provider(handler)
    cdek.get_options(DEST, "heavy")
    cdek.get_options(DEST, "heavy")

    assert calls.count("/v2/oauth/token") == 1  # токен получен один раз
    auth, body = bodies[0]
    assert auth == "Bearer tok"
    assert body["from_location"] == {"code": 137} and body["packages"][0]["weight"] == 4000


def test_no_door_tariffs_means_not_serviceable():
    with pytest.raises(NotServiceable):
        provider(handler_with({"tariff_codes": [], "errors": [{"code": "x"}]})).get_options(DEST, "light")


def test_foreign_country_is_not_serviceable_without_request():
    calls = []
    with pytest.raises(NotServiceable):
        provider(handler_with(TARIFFS, calls)).get_options(Destination("x", "Париж, Франция"), "light")
    assert calls == []


@pytest.mark.parametrize("status", [401, 429, 500])
def test_http_errors_become_provider_error(status):
    def handler(request):
        if request.url.path == "/v2/oauth/token":
            return httpx.Response(200, json={"access_token": "tok", "expires_in": 3600})
        return httpx.Response(status)

    with pytest.raises(ProviderError):
        provider(handler).get_options(DEST, "light")


def test_failed_authorization_is_provider_error():
    with pytest.raises(ProviderError):
        provider(lambda r: httpx.Response(401, json={})).get_options(DEST, "light")


def test_missing_credentials_are_rejected():
    with pytest.raises(ValueError):
        CdekProvider("", "", "https://x", 137, 1)
