"""Геокодирование адреса в координаты (OpenStreetMap Nominatim, ключ не нужен).

Правила использования Nominatim: осмысленный User-Agent и не чаще 1 запроса в секунду,
поэтому результаты кэшируются в памяти. Для коммерческой нагрузки нужен свой геокодер
или платный сервис; для учебного проекта этого достаточно."""
import logging
from collections import OrderedDict
from typing import Optional

import httpx

from .base import BadAddressError, ProviderError

logger = logging.getLogger("app.delivery.geocoder")

USER_AGENT = "flower-delivery-coursework/1.0 (student project)"


class NominatimGeocoder:
    def __init__(
        self,
        base_url: str = "https://nominatim.openstreetmap.org",
        timeout_seconds: float = 3.0,
        client: Optional[httpx.Client] = None,
        cache_size: int = 500,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout_seconds
        self._client = client or httpx.Client()
        self._cache: "OrderedDict[str, tuple[float, float]]" = OrderedDict()
        self._cache_size = cache_size

    def geocode(self, address: str) -> tuple[float, float]:
        """Возвращает (долгота, широта). Бросает BadAddressError, если адрес не найден,
        и ProviderError, если сервис недоступен."""
        key = " ".join(address.lower().split())
        if key in self._cache:
            self._cache.move_to_end(key)
            return self._cache[key]

        try:
            response = self._client.get(
                f"{self._base_url}/search",
                params={"q": address, "format": "json", "limit": 1, "countrycodes": "ru"},
                headers={"User-Agent": USER_AGENT, "Accept-Language": "ru"},
                timeout=self._timeout,
            )
            response.raise_for_status()
            results = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning("geocoder request failed: %s", exc)
            raise ProviderError(f"geocoder unavailable: {exc}") from exc

        if not results:
            raise BadAddressError(f"address not found: {address}")
        try:
            point = (float(results[0]["lon"]), float(results[0]["lat"]))
        except (KeyError, TypeError, ValueError) as exc:
            raise ProviderError(f"unexpected geocoder response: {results!r}") from exc

        self._cache[key] = point
        if len(self._cache) > self._cache_size:
            self._cache.popitem(last=False)
        return point
