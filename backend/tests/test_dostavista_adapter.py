import httpx
import pytest

from app.delivery.base import Destination, NotServiceable, ProviderError
from app.delivery.dostavista import DostavistaProvider

DEST = Destination(region_key="санкт-петербург", address="Санкт-Петербург, Невский проспект 1", lon=30.32, lat=59.93)
OK = {"is_successful": True, "order": {"payment_amount": "389.00", "delivery_fee_amount": "389.00"}}


def provider(handler, token="secret-token"):
    return DostavistaProvider(
        token, "https://dv.example/api/business/1.6", "Санкт-Петербург, Полюстровский проспект, 14А", 3.0,
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )


def test_price_is_taken_from_response_and_request_is_built_as_expected():
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(200, json=OK)

    options = provider(handler).get_options(DEST, "medium")

    assert len(options) == 1 and options[0].id == "dostavista:courier" and options[0].cost == 389
    assert options[0].service.startswith("Достависта")
    request = seen[0]
    assert request.url.path.endswith("/calculate-order") and request.headers["X-DV-Auth-Token"] == "secret-token"
    body = __import__("json").loads(request.content)
    assert body["points"][0]["address"].startswith("Санкт-Петербург, Полюстровский")
    assert body["points"][1] == {"address": DEST.address, "latitude": 59.93, "longitude": 30.32}


def test_unsuccessful_answer_means_not_serviceable():
    with pytest.raises(NotServiceable):
        provider(lambda r: httpx.Response(200, json={"is_successful": False, "errors": ["bad address"]})).get_options(DEST, "light")


def test_foreign_country_is_refused_without_request():
    def handler(request):
        raise AssertionError("no request expected")

    with pytest.raises(NotServiceable):
        provider(handler).get_options(Destination(region_key="x", address="Париж, Франция"), "light")


@pytest.mark.parametrize("status", [401, 403, 429, 500, 503])
def test_http_errors_become_provider_error(status):
    with pytest.raises(ProviderError):
        provider(lambda r: httpx.Response(status)).get_options(DEST, "light")


@pytest.mark.parametrize("payload", [[], {"is_successful": True}, {"is_successful": True, "order": {"payment_amount": "0"}}])
def test_unexpected_payload_is_provider_error(payload):
    with pytest.raises(ProviderError):
        provider(lambda r: httpx.Response(200, json=payload)).get_options(DEST, "light")


def test_missing_token_is_rejected():
    with pytest.raises(ValueError):
        DostavistaProvider("", "https://x", "addr", 3.0)
