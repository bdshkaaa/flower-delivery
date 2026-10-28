"""Расчёт доставки по расстоянию от магазина до адреса (собственная тарифная модель).

Это НЕ API перевозчика, а понятный расчётный тариф: цена зависит от веса букета и
расстояния. Работает без токенов, поэтому подходит как режим по умолчанию.
Яндекс Доставка подключается отдельно (DELIVERY_PROVIDER=yandex).

Тариф (₽):
  в пределах 25 км по дорогам      — базовая цена по весу (light 300, medium 400, heavy 550)
  от 25 до 100 км                  — база + 12 ₽ за каждый километр свыше 25
  дальше 100 км (межгород, экспресс) — база + 900 + 2,5 ₽ за каждый километр свыше 100
Расстояние по дорогам = расстояние по прямой × 1,3. Итог округляется до 10 ₽.
Срок: до 100 км — 1 день, дальше — 1 день + 1 день на каждые 700 км (не больше 14)."""
import logging
import math
from decimal import Decimal
from typing import Optional, Protocol

from .base import (
    WEIGHT_CATEGORIES,
    DeliveryOption,
    DeliveryQuote,
    Destination,
    NotServiceable,
    ProviderError,
)
from .cities import find_city
from .countries import country_of

logger = logging.getLogger("app.delivery.distance")

BASE_COST = {"light": 300, "medium": 400, "heavy": 550}
ROAD_FACTOR = 1.3
CITY_RADIUS_KM = 25
REGION_RADIUS_KM = 100
REGION_RATE = 12
REGION_PART = (REGION_RADIUS_KM - CITY_RADIUS_KM) * REGION_RATE  # 900
LONG_RATE = 2.5
EARTH_RADIUS_KM = 6371.0


class Geocoder(Protocol):
    def geocode(self, address: str) -> tuple[float, float]: ...


def haversine_km(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


def tariff(road_km: float, weight_category: str) -> tuple[int, int]:
    """Возвращает (стоимость в рублях, срок в днях) по расстоянию по дорогам."""
    cost = float(BASE_COST[weight_category])
    if road_km > REGION_RADIUS_KM:
        cost += REGION_PART + LONG_RATE * (road_km - REGION_RADIUS_KM)
        days = min(14, 1 + math.ceil(road_km / 700))
    elif road_km > CITY_RADIUS_KM:
        cost += REGION_RATE * (road_km - CITY_RADIUS_KM)
        days = 1
    else:
        days = 1
    return int(round(cost / 10.0)) * 10, days


EXPRESS_FACTOR = 1.5
NOT_RU = "Доставка в эту страну недоступна: курьерская служба магазина работает только по России."


class DistanceDeliveryProvider:
    """Курьерская служба магазина. Сначала ищет город в локальной таблице, незнакомый адрес
    отдаёт внешнему геокодеру. Предлагает два тарифа: стандарт и экспресс."""

    id = "courier"

    def __init__(self, shop_lon: float, shop_lat: float, geocoder: Optional[Geocoder] = None) -> None:
        self._shop = (shop_lon, shop_lat)
        self._geocoder = geocoder

    def _locate(self, address: str) -> tuple[float, float]:
        point = find_city(address)
        if point is not None:
            return point
        if self._geocoder is None:
            raise ProviderError(f"unknown city: {address}")
        return self._geocoder.geocode(address)

    def _road_km(self, destination: Destination) -> float:
        if country_of(destination.address) == "OTHER":
            raise NotServiceable(NOT_RU)
        if destination.lon is not None and destination.lat is not None:
            lon, lat = destination.lon, destination.lat
        else:
            point = find_city(destination.address)
            if point is not None:
                lon, lat = point
            elif self._geocoder is None:
                raise ProviderError(f"unknown city: {destination.address}")
            else:
                locate = getattr(self._geocoder, "locate", None)
                if locate is not None:  # полноценный геокодер знает страну
                    place = locate(destination.address)
                    if place.country_code and place.country_code != "ru":
                        raise NotServiceable(NOT_RU)
                    lon, lat = place.lon, place.lat
                else:
                    lon, lat = self._geocoder.geocode(destination.address)
        return haversine_km(self._shop[0], self._shop[1], lon, lat) * ROAD_FACTOR

    def get_options(self, destination: Destination, weight_category: str) -> list[DeliveryOption]:
        if weight_category not in WEIGHT_CATEGORIES:
            raise ValueError(f"unknown weight category: {weight_category}")
        road_km = self._road_km(destination)
        cost, days = tariff(road_km, weight_category)
        express_cost = int(round(cost * EXPRESS_FACTOR / 10.0)) * 10
        options = [
            DeliveryOption("courier:standard", "Курьер магазина: стандарт", Decimal(cost).quantize(Decimal("0.01")), days)
        ]
        if days == 1:
            # по городу и области курьер успевает в тот же день
            options.append(DeliveryOption(
                "courier:express", "Курьер магазина: экспресс (за 3 часа)",
                Decimal(express_cost).quantize(Decimal("0.01")), 1, eta_hours=3))
        else:
            options.append(DeliveryOption(
                "courier:express", "Курьер магазина: экспресс",
                Decimal(express_cost).quantize(Decimal("0.01")), max(1, days - 1)))
        return options

    def get_quote(self, destination: Destination, weight_category: str) -> DeliveryQuote:
        if weight_category not in WEIGHT_CATEGORIES:
            raise ValueError(f"unknown weight category: {weight_category}")
        lon, lat = (
            (destination.lon, destination.lat)
            if destination.lon is not None and destination.lat is not None
            else self._locate(destination.address)
        )
        road_km = haversine_km(self._shop[0], self._shop[1], lon, lat) * ROAD_FACTOR
        cost, days = tariff(road_km, weight_category)
        logger.info("distance quote: %.0f km by road -> %s RUB, %s d", road_km, cost, days)
        return DeliveryQuote(cost=Decimal(cost).quantize(Decimal("0.01")), eta_days=days)
