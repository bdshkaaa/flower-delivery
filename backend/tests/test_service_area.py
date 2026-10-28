"""Зона доставки: только Санкт-Петербург и ближайшая Ленинградская область."""
import httpx
import pytest

from app.delivery.area import ServiceArea
from app.delivery.base import BadAddressError, DeliveryOption, NotServiceable, ProviderError
from app.delivery.cache import TTLCache
from app.delivery.geocoder import PhotonSuggester, Place
from app.delivery.mock import MockDeliveryProvider
from app.delivery.service import DeliveryService

SHOP = (30.4150, 59.9590)  # Полюстровский проспект, 14А


def area(geocoder=None, radius=100.0):
    return ServiceArea(SHOP[0], SHOP[1], radius, geocoder)


class FakeLocator:
    def __init__(self, place=None, error=None):
        self.place, self.error, self.calls = place, error, 0

    def locate(self, address):
        self.calls += 1
        if self.error:
            raise self.error
        return self.place


@pytest.mark.parametrize("address", [
    "Санкт-Петербург, Невский проспект 1", "Гатчина, Ленина 1", "Всеволожск, Центральная 3", "Колпино, Тверская 5",
])
def test_cities_of_the_region_are_inside_the_zone(address):
    area().check(address)  # не бросает исключение


@pytest.mark.parametrize("address", ["Москва, Тверская 1", "Нижний Новгород, Покровка 1", "Псков, Ленина 1"])
def test_other_regions_are_refused_with_a_clear_reason(address):
    with pytest.raises(NotServiceable) as refused:
        area().check(address)
    assert "Санкт-Петербургу" in refused.value.reason and "100" in refused.value.reason


def test_selected_point_is_checked_without_geocoder():
    area().check("Любая улица, 1", lat=59.93, lon=30.32)
    with pytest.raises(NotServiceable):
        area().check("Любая улица, 1", lat=55.75, lon=37.62)


def test_unknown_town_is_located_by_geocoder():
    near = FakeLocator(Place(lon=30.0, lat=59.7, label="Гатчинский район"))
    far = FakeLocator(Place(lon=49.1, lat=55.8, label="Казань"))
    area(near).check("деревня Горки, 3")
    with pytest.raises(NotServiceable):
        area(far).check("деревня Горки, 3")


def test_when_place_cannot_be_found_the_decision_is_left_to_services():
    area(FakeLocator(error=ProviderError("down"))).check("деревня Горки, 3")
    area(FakeLocator(error=BadAddressError("no"))).check("деревня Горки, 3")
    area(None).check("деревня Горки, 3")


def test_foreign_address_is_left_to_country_check():
    locator = FakeLocator(Place(lon=2.35, lat=48.85, label="Париж"))
    area(locator).check("Париж, Франция")
    assert locator.calls == 0


def test_service_refuses_before_asking_any_provider():
    provider = MockDeliveryProvider()
    calls = []
    original = provider.get_options
    provider.get_options = lambda d, w: calls.append(d) or original(d, w)
    service = DeliveryService([provider], TTLCache(60), area=area())

    moscow = service.get_options("Москва, Тверская 1", "medium")
    gatchina = service.get_options("Гатчина, Ленина 1", "medium")

    assert moscow.available is False and "Ленинградской области" in moscow.reason and calls == [calls[0]]
    assert gatchina.available is True
    assert len(calls) == 1  # в Москву ни одна служба не опрашивалась


# ---- Подсказки адресов ----
def feature(lon, lat, **props):
    return {"type": "Feature", "geometry": {"type": "Point", "coordinates": [lon, lat]}, "properties": props}


def suggester(payload, status=200):
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(status, json=payload)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    return PhotonSuggester(SHOP, 100.0, client=client), seen


def test_suggestions_are_labelled_and_limited_to_the_zone():
    s, seen = suggester({"features": [
        feature(30.41, 59.96, street="Полюстровский проспект", housenumber="14А", city="Санкт-Петербург",
                state="Санкт-Петербург", countrycode="RU"),
        feature(37.6, 55.7, street="Тверская", housenumber="1", city="Москва", countrycode="RU"),
        feature(24.9, 60.1, street="Mannerheimintie", city="Helsinki", countrycode="FI"),
        {"geometry": None},
    ]})

    places = s.search("Полюстровский 14")

    assert [p.label for p in places] == ["Полюстровский проспект 14А, Санкт-Петербург"]
    assert places[0].lat == 59.96 and places[0].country_code == "ru"
    assert seen[0].url.params["q"] == "Полюстровский 14" and seen[0].url.params["lat"] == str(SHOP[1])


def test_suggestions_are_cached_and_deduplicated():
    s, seen = suggester({"features": [
        feature(30.3, 59.9, street="Невский проспект", housenumber="1", city="Санкт-Петербург", countrycode="RU"),
        feature(30.3, 59.9, street="Невский проспект", housenumber="1", city="Санкт-Петербург", countrycode="RU"),
    ]})

    assert len(s.search("Невский 1")) == 1
    s.search("невский   1")
    assert len(seen) == 1


def test_suggestions_outage_raises_provider_error():
    s, _ = suggester({}, status=503)
    with pytest.raises(ProviderError):
        s.search("Невский")


# ---- DaData ----
from app.delivery.geocoder import DadataSuggester  # noqa: E402


def dadata(payload, status=200):
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(status, json=payload)

    s = DadataSuggester("tok", SHOP, 100.0, client=httpx.Client(transport=httpx.MockTransport(handler)))
    return s, seen


def item(value, lat, lon, house="14"):
    return {"value": value, "data": {"geo_lat": lat, "geo_lon": lon, "house": house}}


def test_dadata_returns_real_addresses_with_house_numbers_inside_the_zone():
    s, seen = dadata({"suggestions": [
        item("г Санкт-Петербург, Полюстровский пр-кт, д 14 литера А", "59.9590", "30.4150"),
        item("г Москва, Тверская ул, д 1", "55.76", "37.61"),
        item("г Санкт-Петербург, Полюстровский пр-кт", "59.96", "30.41", house=None),
        {"value": "без координат", "data": {"geo_lat": None, "geo_lon": None}},
    ]})

    places = s.search("Полюстровский 14")

    assert [p.label for p in places] == [
        "г Санкт-Петербург, Полюстровский пр-кт, д 14 литера А", "г Санкт-Петербург, Полюстровский пр-кт"]
    assert [p.precise for p in places] == [True, False]
    request = seen[0]
    assert request.headers["Authorization"] == "Token tok" and request.method == "POST"
    body = __import__("json").loads(request.content)
    assert body["query"] == "Полюстровский 14" and {"kladr_id": "7800000000000"} in body["locations"]


def test_dadata_errors_and_missing_token():
    s, _ = dadata({}, status=403)
    with pytest.raises(ProviderError):
        s.search("Невский")
    with pytest.raises(ValueError):
        DadataSuggester("", SHOP, 100.0)


def test_dadata_is_used_only_when_token_is_set(monkeypatch):
    from app import config
    from app.delivery import geocoder

    geocoder.get_suggester.cache_clear()
    base = config.settings
    from dataclasses import replace

    monkeypatch.setattr(config, "settings", replace(base, dadata_token="tok"))
    assert isinstance(geocoder.get_suggester(), DadataSuggester)
    geocoder.get_suggester.cache_clear()
    monkeypatch.setattr(config, "settings", replace(base, dadata_token=""))
    assert isinstance(geocoder.get_suggester(), PhotonSuggester)
    geocoder.get_suggester.cache_clear()
