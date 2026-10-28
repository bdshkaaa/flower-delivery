"""Адаптер Достависты (курьерская доставка в день заказа, API «Бизнес» v1.6, метод расчёта).

ВАЖНО: на реальном токене адаптер не запускался, только на тестах с подменённой сетью.
Формат запроса и ответа (`POST /calculate-order`, заголовок `X-DV-Auth-Token`,
в ответе `order.payment_amount`) взят по памяти из открытой документации, поэтому после
получения токена запустите ручную проверку (python -m app.delivery.check) и сверьте разбор
ответа с актуальной документацией. От разбора ответа зависит только `_parse_response`.

Доступ: токен выдаётся в личном кабинете Достависты (раздел API). Для проверки у них есть
тестовая среда (https://robotapitest.dostavista.ru/api/business/1.6)."""
import logging
from decimal import Decimal, InvalidOperation
from typing import Optional

import httpx

from .base import WEIGHT_CATEGORIES, DeliveryOption, Destination, NotServiceable, ProviderError
from .countries import country_of

logger = logging.getLogger("app.delivery.dostavista")

_WEIGHT_KG = {"light": 1, "medium": 3, "heavy": 6}


class DostavistaProvider:
    id = "dostavista"

    def __init__(
        self,
        token: str,
        base_url: str,
        shop_address: str,
        timeout_seconds: float,
        client: Optional[httpx.Client] = None,
    ) -> None:
        if not token:
            raise ValueError("DOSTAVISTA_TOKEN is not set")
        self._token = token
        self._base_url = base_url.rstrip("/")
        self._shop_address = shop_address
        self._timeout = timeout_seconds
        self._client = client or httpx.Client()

    def get_options(self, destination: Destination, weight_category: str) -> list[DeliveryOption]:
        if weight_category not in WEIGHT_CATEGORIES:
            raise ValueError(f"unknown weight category: {weight_category}")
        if country_of(destination.address) == "OTHER":
            raise NotServiceable("Достависта: доставка в эту страну через наш магазин недоступна")

        to_point = {"address": destination.address}
        if destination.lat is not None and destination.lon is not None:
            to_point.update(latitude=destination.lat, longitude=destination.lon)
        body = {
            "matter": "Цветы",
            "total_weight_kg": _WEIGHT_KG[weight_category],
            "points": [{"address": self._shop_address}, to_point],
        }
        try:
            response = self._client.post(
                f"{self._base_url}/calculate-order",
                json=body, headers={"X-DV-Auth-Token": self._token}, timeout=self._timeout,
            )
        except httpx.HTTPError as exc:
            logger.warning("dostavista request failed: %s", exc)
            raise ProviderError(str(exc)) from exc

        if response.status_code >= 500 or response.status_code in (401, 403, 429):
            raise ProviderError(f"dostavista returned HTTP {response.status_code}")
        try:
            payload = response.json()
        except ValueError as exc:
            raise ProviderError("dostavista returned invalid JSON") from exc
        return self._parse_response(payload)

    @staticmethod
    def _parse_response(payload: dict) -> list[DeliveryOption]:
        if not isinstance(payload, dict):
            raise ProviderError(f"unexpected response shape: {payload!r}")
        if not payload.get("is_successful"):
            # Служба ответила, но по этому адресу не доставляет (адрес не найден, вне зоны)
            raise NotServiceable("Достависта не доставляет по этому адресу")
        try:
            order = payload["order"]
            cost = Decimal(str(order.get("payment_amount", order.get("delivery_fee_amount")))).quantize(Decimal("0.01"))
        except (KeyError, TypeError, AttributeError, InvalidOperation) as exc:
            raise ProviderError(f"unexpected response: {payload!r}") from exc
        if cost <= 0:
            raise ProviderError("dostavista returned non-positive price")
        return [DeliveryOption("dostavista:courier", "Достависта: курьер", cost, 1)]
