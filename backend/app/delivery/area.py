"""Зона доставки: магазин возит цветы только по своему региону (Санкт-Петербург и
ближайшая Ленинградская область). Зона задаётся радиусом от магазина по дорогам
(DELIVERY_RADIUS_KM, по умолчанию 100 км), поэтому одинаково работает для любого адреса.
Проверка стоит перед всеми службами: ни курьер магазина, ни Яндекс, ни СДЭК не получат
запрос на адрес за пределами региона."""
import logging
from typing import Optional

from .base import NotServiceable, ProviderError
from .cities import find_city
from .countries import country_of
from .distance import ROAD_FACTOR, haversine_km

logger = logging.getLogger("app.delivery.area")


class ServiceArea:
    def __init__(self, shop_lon: float, shop_lat: float, radius_km: float, geocoder=None) -> None:
        self._shop = (shop_lon, shop_lat)
        self.radius_km = radius_km
        self._geocoder = geocoder

    @property
    def reason(self) -> str:
        return (
            "Мы доставляем только по Санкт-Петербургу и ближайшей Ленинградской области "
            f"(до {self.radius_km:g} км от магазина)."
        )

    def road_km(self, lon: float, lat: float) -> float:
        return haversine_km(self._shop[0], self._shop[1], lon, lat) * ROAD_FACTOR

    def contains(self, lon: float, lat: float) -> bool:
        return self.road_km(lon, lat) <= self.radius_km

    def _locate(self, address: str) -> Optional[tuple[float, float]]:
        point = find_city(address)
        if point is not None:
            return point
        locate = getattr(self._geocoder, "locate", None)
        if locate is None:
            return None
        try:
            place = locate(address)
        except ProviderError as exc:  # геокодер недоступен или адрес не найден: решат службы доставки
            logger.info("service area: cannot locate %r: %s", address, exc)
            return None
        return place.lon, place.lat

    def check(self, address: str, lat: Optional[float] = None, lon: Optional[float] = None) -> None:
        """NotServiceable, если адрес вне зоны. Если место определить не удалось, не отказываем:
        дальше адрес проверят сами службы (и страна проверяется отдельно)."""
        if country_of(address) == "OTHER":
            return
        point = (lon, lat) if lat is not None and lon is not None else self._locate(address)
        if point is None:
            return
        km = self.road_km(*point)
        if km > self.radius_km:
            logger.info("delivery refused: %.0f km by road is outside the %g km zone", km, self.radius_km)
            raise NotServiceable(self.reason)
