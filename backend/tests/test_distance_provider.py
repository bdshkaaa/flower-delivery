"""Расчёт доставки по расстоянию: цена и срок зависят от города (БД и сеть не нужны)."""
from decimal import Decimal

import pytest

from app.delivery.base import BadAddressError, Destination, ProviderError
from app.delivery.cities import find_city
from app.delivery.distance import DistanceDeliveryProvider, haversine_km, tariff

SHOP = (30.3141, 59.9386)  # Санкт-Петербург


class FakeGeocoder:
    def __init__(self, point=None, error=None):
        self.point, self.error, self.calls = point, error, 0

    def geocode(self, address):
        self.calls += 1
        if self.error:
            raise self.error
        return self.point


def quote(address, weight="medium", geocoder=None):
    provider = DistanceDeliveryProvider(*SHOP, geocoder=geocoder)
    return provider.get_quote(Destination(region_key="x", address=address), weight)


def test_distance_spb_moscow_is_about_630_km():
    assert haversine_km(30.32, 59.94, 37.62, 55.75) == pytest.approx(634, abs=10)


def test_home_city_costs_base_tariff_in_one_day():
    result = quote("Санкт-Петербург, Невский проспект 1", "light")

    assert result.cost == Decimal("300.00") and result.eta_days == 1


def test_cost_grows_with_distance():
    spb = quote("Санкт-Петербург, Невский 1")
    vyborg = quote("Выборг, Ленина 5")
    moscow = quote("Москва, Тверская 1")
    kazan = quote("Казань, Баумана 1")

    assert spb.cost < vyborg.cost < moscow.cost < kazan.cost
    assert spb.eta_days <= vyborg.eta_days < moscow.eta_days <= kazan.eta_days


def test_moscow_light_bouquet_known_value():
    result = quote("Москва, Тверская 1", "light")

    assert result.cost == Decimal("3010.00")  # 300 + 900 + 2.5 * (824 - 100), округление до 10 ₽
    assert result.eta_days == 3


def test_cost_grows_with_weight():
    costs = [quote("Москва, Арбат 1", w).cost for w in ("light", "medium", "heavy")]

    assert costs == sorted(costs) and len(set(costs)) == 3


@pytest.mark.parametrize("address", ["г. Казань, ул. Баумана 1", "ул. Баумана 1, КАЗАНЬ", "казань"])
def test_city_is_found_in_any_address_format(address):
    assert find_city(address) == find_city("Казань, Баумана 1") is not None


def test_yo_letter_does_not_matter():
    assert find_city("Королёв, Ленина 1") == find_city("Королев, Ленина 1") is not None


def test_unknown_city_uses_external_geocoder():
    geocoder = FakeGeocoder(point=(37.62, 55.75))  # геокодер «нашёл» Москву

    result = quote("посёлок Лесной, 1", geocoder=geocoder)

    assert geocoder.calls == 1
    assert result.cost == quote("Москва, 1").cost


def test_known_city_does_not_call_geocoder():
    geocoder = FakeGeocoder(point=(0, 0))

    quote("Москва, Тверская 1", geocoder=geocoder)

    assert geocoder.calls == 0


def test_unknown_city_without_geocoder_is_provider_error():
    with pytest.raises(ProviderError):
        quote("Нигдеград, 1")


def test_geocoder_errors_are_passed_through():
    with pytest.raises(BadAddressError):
        quote("Нигдеград, 1", geocoder=FakeGeocoder(error=BadAddressError("no")))


@pytest.mark.parametrize("km, expected", [(10, 300), (25, 300), (50, 600), (100, 1200), (200, 1450)])
def test_tariff_zones_light(km, expected):
    cost, _ = tariff(km, "light")

    assert cost == expected


# ---- Варианты курьера магазина ----
from app.delivery.base import NotServiceable  # noqa: E402


def options(address, weight="medium", geocoder=None):
    provider = DistanceDeliveryProvider(*SHOP, geocoder=geocoder)
    return provider.get_options(Destination(region_key="x", address=address), weight)


def test_two_courier_tariffs_standard_and_express():
    standard, express = options("Москва, Тверская 1")

    assert standard.id == "courier:standard" and express.id == "courier:express"
    assert express.cost > standard.cost and express.eta_days < standard.eta_days


def test_local_express_is_within_hours():
    _, express = options("Санкт-Петербург, Невский 1")

    assert express.eta_days == 1 and express.eta_hours == 3


def test_map_point_is_used_without_geocoding():
    geocoder = FakeGeocoder(point=(0, 0))
    provider = DistanceDeliveryProvider(*SHOP, geocoder=geocoder)

    got = provider.get_options(Destination("x", "Улица, Россия", lon=37.62, lat=55.75), "light")

    assert geocoder.calls == 0 and got[0].cost == quote("Москва, 1", "light").cost


@pytest.mark.parametrize("address", ["Минск, Беларусь", "Paris, France", "Берлин, Германия"])
def test_other_countries_are_not_serviceable(address):
    with pytest.raises(NotServiceable):
        options(address)


def test_geocoder_that_reports_foreign_country_is_not_serviceable():
    from app.delivery.geocoder import Place

    class Geo:
        def locate(self, address):
            return Place(lon=2.35, lat=48.85, country_code="fr")

    with pytest.raises(NotServiceable):
        options("Париж", geocoder=Geo())
