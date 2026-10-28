"""Геокодирование (адрес <-> координаты) через OpenStreetMap Nominatim, ключ не нужен.

Правила использования Nominatim: осмысленный User-Agent, не чаще 1 запроса в секунду
и никакого автодополнения «на каждую букву» (поиск только по явному действию пользователя).
Подсказки адресов при наборе даёт Photon (тоже на данных OSM, для автодополнения он и сделан),
а Nominatim используется только для разового поиска. Поэтому запросы выстроены в очередь с паузой, а результаты кэшируются в памяти.
Для коммерческой нагрузки нужен свой геокодер или платный сервис."""
import logging
import threading
import time
from functools import lru_cache
from collections import OrderedDict
from dataclasses import dataclass
from typing import Callable, Optional

import httpx

from .base import BadAddressError, ProviderError

logger = logging.getLogger("app.delivery.geocoder")

USER_AGENT = "flower-delivery-coursework/1.0 (student project)"
MIN_INTERVAL_SECONDS = 1.0


@dataclass(frozen=True)
class Place:
    lon: float
    lat: float
    label: str = ""
    country_code: Optional[str] = None  # «ru», «by» ... в нижнем регистре, если известен


class NominatimGeocoder:
    def __init__(
        self,
        base_url: str = "https://nominatim.openstreetmap.org",
        timeout_seconds: float = 3.0,
        client: Optional[httpx.Client] = None,
        cache_size: int = 500,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout_seconds
        self._client = client or httpx.Client()
        self._cache: "OrderedDict[tuple, object]" = OrderedDict()
        self._cache_size = cache_size
        self._clock, self._sleep = clock, sleep
        self._lock = threading.Lock()
        self._last_request = -MIN_INTERVAL_SECONDS

    # ---- служебное ----
    def _get(self, path: str, params: dict):
        with self._lock:  # не чаще 1 запроса в секунду
            wait = MIN_INTERVAL_SECONDS - (self._clock() - self._last_request)
            if wait > 0:
                self._sleep(wait)
            self._last_request = self._clock()
            try:
                response = self._client.get(
                    f"{self._base_url}{path}",
                    params={**params, "format": "jsonv2", "addressdetails": 1, "accept-language": "ru"},
                    headers={"User-Agent": USER_AGENT},
                    timeout=self._timeout,
                )
                response.raise_for_status()
                return response.json()
            except (httpx.HTTPError, ValueError) as exc:
                logger.warning("geocoder request failed: %s", exc)
                raise ProviderError(f"geocoder unavailable: {exc}") from exc

    def _remember(self, key: tuple, value):
        self._cache[key] = value
        if len(self._cache) > self._cache_size:
            self._cache.popitem(last=False)
        return value

    @staticmethod
    def _to_place(item: dict) -> Place:
        try:
            address = item.get("address") or {}
            return Place(
                lon=float(item["lon"]),
                lat=float(item["lat"]),
                label=str(item.get("display_name", "")),
                country_code=(address.get("country_code") or "").lower() or None,
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ProviderError(f"unexpected geocoder response: {item!r}") from exc

    # ---- публичные методы ----
    def search(self, query: str, limit: int = 5) -> list[Place]:
        """Поиск адреса. Пустой список, если ничего не найдено."""
        key = ("search", " ".join(query.lower().split()), limit)
        if key in self._cache:
            return self._cache[key]  # type: ignore[return-value]
        items = self._get("/search", {"q": query, "limit": limit})
        return self._remember(key, [self._to_place(i) for i in items])

    def reverse(self, lat: float, lon: float) -> Place:
        """Адрес по точке на карте. BadAddressError, если там ничего нет (например, море)."""
        key = ("reverse", round(lat, 4), round(lon, 4))
        if key in self._cache:
            return self._cache[key]  # type: ignore[return-value]
        item = self._get("/reverse", {"lat": lat, "lon": lon, "zoom": 18})
        if not isinstance(item, dict) or "error" in item:
            raise BadAddressError(f"no address at {lat}, {lon}")
        return self._remember(key, self._to_place(item))

    def locate(self, address: str) -> Place:
        places = self.search(address, limit=1)
        if not places:
            raise BadAddressError(f"address not found: {address}")
        return places[0]

    def geocode(self, address: str) -> tuple[float, float]:
        """Совместимость со старым кодом: (долгота, широта)."""
        place = self.locate(address)
        return place.lon, place.lat


@lru_cache
def get_geocoder() -> NominatimGeocoder:
    """Один геокодер на всё приложение: общий кэш и общий лимит 1 запрос в секунду."""
    from ..config import settings

    return NominatimGeocoder(timeout_seconds=max(settings.delivery_timeout_seconds, 5.0))


class PhotonSuggester:
    """Подсказки адресов по мере набора (Photon, данные OpenStreetMap, ключ не нужен).
    Показывает только места внутри зоны доставки, чтобы нельзя было выбрать адрес,
    куда магазин не возит."""

    def __init__(
        self,
        center: tuple[float, float],
        radius_km: float,
        base_url: str = "https://photon.komoot.io",
        timeout_seconds: float = 3.0,
        client: Optional[httpx.Client] = None,
        cache_size: int = 500,
    ) -> None:
        from .area import ServiceArea

        self._center = center
        self._area = ServiceArea(center[0], center[1], radius_km)
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout_seconds
        self._client = client or httpx.Client()
        self._cache: "OrderedDict[tuple, list[Place]]" = OrderedDict()
        self._cache_size = cache_size

    @staticmethod
    def _label(props: dict) -> str:
        street = props.get("street") or ""
        house = props.get("housenumber") or ""
        head = " ".join(x for x in (street, house) if x) or props.get("name") or ""
        city = props.get("city") or props.get("town") or props.get("village") or props.get("county") or ""
        parts = [head]
        if city and city != head:
            parts.append(city)
        state = props.get("state") or ""
        if state and state != city:
            parts.append(state)
        return ", ".join(p for p in parts if p)

    def search(self, query: str, limit: int = 5) -> list[Place]:
        key = (" ".join(query.lower().split()), limit)
        if key in self._cache:
            return self._cache[key]
        # Широта и долгота центра смещают выдачу к магазину; лишние места отсекаем сами
        # (с запасом запрашиваем больше, чем нужно).
        params = {"q": query, "limit": min(limit * 3, 20), "lon": self._center[0], "lat": self._center[1]}
        try:
            response = self._client.get(
                f"{self._base_url}/api/", params=params, headers={"User-Agent": USER_AGENT}, timeout=self._timeout
            )
            response.raise_for_status()
            features = response.json().get("features", [])
        except (httpx.HTTPError, ValueError, AttributeError) as exc:
            logger.warning("suggest request failed: %s", exc)
            raise ProviderError(f"suggest unavailable: {exc}") from exc

        places: list[Place] = []
        for feature in features:
            try:
                lon, lat = (float(v) for v in feature["geometry"]["coordinates"][:2])
                props = feature.get("properties") or {}
            except (KeyError, TypeError, ValueError):
                continue  # странный объект пропускаем, остальные подсказки показываем
            code = (props.get("countrycode") or "").lower() or None
            label = self._label(props)
            if not label or (code and code != "ru") or not self._area.contains(lon, lat):
                continue
            if any(p.label == label for p in places):
                continue
            places.append(Place(lon=lon, lat=lat, label=label, country_code=code))
            if len(places) >= limit:
                break
        self._cache[key] = places
        if len(self._cache) > self._cache_size:
            self._cache.popitem(last=False)
        return places


@lru_cache
def get_suggester() -> PhotonSuggester:
    from ..config import settings

    return PhotonSuggester(
        (settings.shop_lon, settings.shop_lat), settings.delivery_radius_km,
        base_url=settings.photon_base_url, timeout_seconds=max(settings.delivery_timeout_seconds, 4.0),
    )
