"""API вариантов доставки и карты (без БД): /delivery/options, /delivery/quote, /geo/*."""
import pytest
from fastapi.testclient import TestClient

from app.delivery.base import ProviderError
from app.delivery.cache import TTLCache
from app.delivery.geocoder import Place, get_suggester
from app.delivery.mock import MockDeliveryProvider
from app.delivery.service import DeliveryService, get_delivery_service
from app.main import app
from tests.fakes import ScriptedProvider, option

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_overrides():
    yield
    app.dependency_overrides.clear()


def use_providers(*providers):
    service = DeliveryService(list(providers), TTLCache(60))
    app.dependency_overrides[get_delivery_service] = lambda: service


def test_options_endpoint_lists_several_options():
    use_providers(ScriptedProvider("a", [option("a:std", "700.00", 2, "Служба А")]),
                  ScriptedProvider("b", [option("b:std", "500.00", 3, "Служба Б")]))

    body = client.get("/delivery/options", params={"address": "Москва, Тверская 1"}).json()

    assert body["available"] is True and body["reason"] is None
    assert [o["service"] for o in body["options"]] == ["Служба Б", "Служба А"]  # дешёвые первыми
    assert body["options"][0]["id"] == "b:std" and body["source"] == "api"


def test_options_endpoint_reports_unavailable_delivery_with_reason():
    use_providers(MockDeliveryProvider())

    body = client.get("/delivery/options", params={"address": "nowhere, 1"}).json()

    assert body["available"] is False and body["options"] == []
    assert body["reason"] == "Доставка по этому адресу недоступна"


def test_options_endpoint_falls_back_when_services_are_down():
    use_providers(ScriptedProvider("a", ProviderError("down")))

    body = client.get("/delivery/options", params={"address": "Москва, 1"}).json()

    assert body["available"] is True and body["source"] == "fallback"
    assert body["options"][0]["approximate"] is True


def test_options_endpoint_accepts_map_point_and_validates_it():
    use_providers(MockDeliveryProvider())

    ok = client.get("/delivery/options", params={"address": "Улица, Россия", "lat": 55.7, "lon": 37.6})
    bad = client.get("/delivery/options", params={"address": "Улица", "lat": 200, "lon": 37.6})

    assert ok.status_code == 200 and bad.status_code == 422


def test_quote_endpoint_returns_cheapest_or_409_when_unavailable():
    use_providers(MockDeliveryProvider())

    assert client.get("/delivery/quote", params={"address": "Москва, 1"}).status_code == 200
    unavailable = client.get("/delivery/quote", params={"address": "nowhere, 1"})
    assert unavailable.status_code == 409


# ---- Подсказки адресов ----
class FakeSuggester:
    def __init__(self, places=None, error=None):
        self.places, self.error = places or [], error

    def search(self, q, limit=5):
        if self.error:
            raise self.error
        return self.places


def use_suggester(suggester):
    app.dependency_overrides[get_suggester] = lambda: suggester


def test_geo_search_returns_places():
    use_suggester(FakeSuggester([Place(lon=30.39, lat=59.96, label="Полюстровский проспект 14А, Санкт-Петербург", country_code="ru")]))

    body = client.get("/geo/search", params={"q": "Полюстровский 14"}).json()

    assert body == [{"label": "Полюстровский проспект 14А, Санкт-Петербург", "lat": 59.96, "lon": 30.39, "country_code": "ru", "precise": True}]


def test_geo_search_validates_query_length():
    use_suggester(FakeSuggester())
    assert client.get("/geo/search", params={"q": "ab"}).status_code == 422


def test_geo_search_outage_is_503_and_map_endpoint_is_gone():
    use_suggester(FakeSuggester(error=ProviderError("down")))
    assert client.get("/geo/search", params={"q": "Невский"}).status_code == 503
    assert client.get("/geo/reverse", params={"lat": 1, "lon": 1}).status_code == 404
