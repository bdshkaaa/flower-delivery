"""Адаптер Яндекс Доставки.

ВАЖНО: этот файл НЕ проверен на реальном токене.
Проверено по документации: базовый адрес https://b2b.taxi.yandex.net и авторизация
заголовком `Authorization: Bearer <токен>`. Токен выдаётся в личном кабинете
Яндекс Доставки (вкладка «Интеграции») по учётным данным от менеджера Яндекс Доставки.

Путь метода и формат тела запроса взяты из обсуждения на форуме (метод check-price),
а структура ответа в источниках не приводилась. Поэтому разбор ответа ниже написан
осторожно, и первым делом после получения токена нужно сверить его с актуальной
документацией и поправить `_parse_response`. Остальной код от этого не зависит."""

import logging
from decimal import Decimal, InvalidOperation

import httpx

from .base import (
    WEIGHT_CATEGORIES,
    DeliveryQuote,
    Destination,
    ProviderError,
)

logger = logging.getLogger("app.delivery.yandex")

# Примерный вес букета по категории, кг
_WEIGHT_KG = {"light": 1.0, "medium": 2.0, "heavy": 4.0}


class YandexDeliveryProvider:
    def __init__(
        self,
        token: str,
        base_url: str,
        shop_lon: float,
        shop_lat: float,
        timeout_seconds: float,
    ) -> None:
        if not token:
            raise ValueError("YANDEX_DELIVERY_TOKEN is not set")
        self._token = token
        self._base_url = base_url.rstrip("/")
        self._shop = (shop_lon, shop_lat)
        self._timeout = timeout_seconds

    def get_quote(self, destination: Destination, weight_category: str) -> DeliveryQuote:
        if weight_category not in WEIGHT_CATEGORIES:
            raise ValueError(f"unknown weight category: {weight_category}")
        if destination.lon is None or destination.lat is None:
            # Геокодирование адреса в координаты — отдельная задача (Issue)
            raise ProviderError("destination coordinates are required")

        body = {
            "items": [
                {
                    "quantity": 1,
                    "size": {"length": 0.4, "width": 0.3, "height": 0.4},
                    "weight": _WEIGHT_KG[weight_category],
                }
            ],
            "route_points": [
                {"coordinates": list(self._shop)},
                {"coordinates": [destination.lon, destination.lat]},
            ],
        }
        url = f"{self._base_url}/b2b/cargo/integration/v1/check-price"
        headers = {"Authorization": f"Bearer {self._token}", "Accept-Language": "ru"}

        try:
            response = httpx.post(
                url, json=body, headers=headers, timeout=self._timeout
            )
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning("yandex delivery request failed: %s", exc)
            raise ProviderError(str(exc)) from exc

        return self._parse_response(payload)

    @staticmethod
    def _parse_response(payload: dict) -> DeliveryQuote:
        # TODO: сверить с актуальной документацией, когда будет токен
        try:
            cost = Decimal(str(payload["price"]))
        except (KeyError, InvalidOperation) as exc:
            raise ProviderError(f"unexpected response shape: {payload!r}") from exc
        return DeliveryQuote(cost=cost, eta_days=1)
