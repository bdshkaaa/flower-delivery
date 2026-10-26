"""Адаптер Яндекс Доставки (метод предварительной оценки без создания заявки).

Сверено с документацией (раздел «Предварительная оценка без создания заявки»):
POST {base_url}/b2b/cargo/integration/v2/check-price, заголовок `Authorization: Bearer <токен>`.
Ответ: `price` (строка, например "12.50"), `currency_rules.code` («RUB»), `eta` (минуты),
`distance_meters`. Ошибки: 400 (`bad_request`/`address_not_found`), 409 (нет подходящих
курьеров), 429 (слишком много запросов).

ВАЖНО: на реальном токене адаптер ещё не запускался — только на тестах с подменой сети.
Токен выдаётся в личном кабинете Яндекс Доставки (вкладка «Интеграции»). После получения
токена нужен один ручной запрос (см. README, этап «Проверка адаптера»)."""

import logging
import math
from decimal import Decimal, InvalidOperation
from typing import Optional

import httpx

from .base import (
    WEIGHT_CATEGORIES,
    BadAddressError,
    DeliveryQuote,
    Destination,
    ProviderError,
)
from .geocoder import NominatimGeocoder

logger = logging.getLogger("app.delivery.yandex")

# Примерный вес букета по категории, кг
_WEIGHT_KG = {"light": 1.0, "medium": 2.0, "heavy": 4.0}
_MINUTES_IN_DAY = 24 * 60


class YandexDeliveryProvider:
    def __init__(
        self,
        token: str,
        base_url: str,
        shop_lon: float,
        shop_lat: float,
        timeout_seconds: float,
        geocoder: Optional[NominatimGeocoder] = None,
        client: Optional[httpx.Client] = None,
    ) -> None:
        if not token:
            raise ValueError("YANDEX_DELIVERY_TOKEN is not set")
        self._token = token
        self._base_url = base_url.rstrip("/")
        self._shop = (shop_lon, shop_lat)
        self._timeout = timeout_seconds
        self._geocoder = geocoder or NominatimGeocoder(timeout_seconds=timeout_seconds)
        self._client = client or httpx.Client()

    def get_quote(self, destination: Destination, weight_category: str) -> DeliveryQuote:
        if weight_category not in WEIGHT_CATEGORIES:
            raise ValueError(f"unknown weight category: {weight_category}")

        lon, lat = destination.lon, destination.lat
        if lon is None or lat is None:
            lon, lat = self._geocoder.geocode(destination.address)

        body = {
            "items": [
                {
                    "quantity": 1,
                    "size": {"length": 0.4, "width": 0.3, "height": 0.4},
                    "weight": _WEIGHT_KG[weight_category],
                    "pickup_point": 1,
                    "dropoff_point": 2,
                }
            ],
            "route_points": [
                {"id": 1, "coordinates": list(self._shop)},
                {"id": 2, "coordinates": [lon, lat], "fullname": destination.address},
            ],
            "requirements": {"taxi_class": "courier"},
        }
        headers = {"Authorization": f"Bearer {self._token}", "Accept-Language": "ru"}

        try:
            response = self._client.post(
                f"{self._base_url}/b2b/cargo/integration/v2/check-price",
                json=body, headers=headers, timeout=self._timeout,
            )
        except httpx.HTTPError as exc:
            logger.warning("yandex delivery request failed: %s", exc)
            raise ProviderError(str(exc)) from exc

        if response.status_code == 400 and "address_not_found" in response.text:
            raise BadAddressError("yandex: address_not_found")
        if response.status_code != 200:
            logger.warning("yandex delivery returned %s: %s", response.status_code, response.text[:200])
            raise ProviderError(f"yandex returned HTTP {response.status_code}")
        try:
            payload = response.json()
        except ValueError as exc:
            raise ProviderError("yandex returned invalid JSON") from exc

        return self._parse_response(payload)

    @staticmethod
    def _parse_response(payload: dict) -> DeliveryQuote:
        try:
            cost = Decimal(str(payload["price"])).quantize(Decimal("0.01"))
            currency = payload["currency_rules"]["code"]
            eta_minutes = payload.get("eta")
        except (KeyError, TypeError, InvalidOperation) as exc:
            raise ProviderError(f"unexpected response shape: {payload!r}") from exc
        if currency != "RUB":
            raise ProviderError(f"unexpected currency: {currency}")
        if cost <= 0:
            raise ProviderError(f"non-positive price: {cost}")

        # eta у Яндекса в минутах, а нам нужны дни: округляем вверх, минимум 1
        eta_days = max(1, math.ceil(eta_minutes / _MINUTES_IN_DAY)) if isinstance(eta_minutes, (int, float)) else 1
        return DeliveryQuote(cost=cost, eta_days=eta_days)
