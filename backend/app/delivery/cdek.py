"""Адаптер СДЭК (API v2, расчёт по всем доступным тарифам).

ВАЖНО: на реальных учётных данных адаптер не запускался, только на тестах с подменённой
сетью. Формат запроса и ответа взят по памяти из открытой документации API v2 СДЭК
(авторизация `POST /v2/oauth/token`, расчёт `POST /v2/calculator/tarifflist`), поэтому
после получения доступа первым делом запустите ручную проверку (python -m app.delivery.check)
и сверьте разбор ответа с актуальной документацией. Код устроен так, что от разбора ответа
зависит только `_parse_tariffs`.

Доступ: client_id и client_secret выдаются при регистрации интеграции на сайте СДЭК;
для проверки у СДЭК есть тестовая среда (https://api.edu.cdek.ru)."""
import logging
import time
from decimal import Decimal, InvalidOperation
from typing import Optional

import httpx

from .base import (
    WEIGHT_CATEGORIES,
    BadAddressError,
    DeliveryOption,
    Destination,
    NotServiceable,
    ProviderError,
)
from .countries import country_of

logger = logging.getLogger("app.delivery.cdek")

_WEIGHT_GRAMS = {"light": 1000, "medium": 2000, "heavy": 4000}
# delivery_mode по документации СДЭК: 1 — дверь-дверь, 3 — склад-дверь (курьер до получателя)
_TO_DOOR_MODES = {1, 3}
MAX_OPTIONS = 2


class CdekProvider:
    id = "cdek"

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        base_url: str,
        from_code: int,
        timeout_seconds: float,
        client: Optional[httpx.Client] = None,
    ) -> None:
        if not client_id or not client_secret:
            raise ValueError("CDEK_CLIENT_ID / CDEK_CLIENT_SECRET are not set")
        self._client_id, self._client_secret = client_id, client_secret
        self._base_url = base_url.rstrip("/")
        self._from_code = from_code
        self._timeout = timeout_seconds
        self._client = client or httpx.Client()
        self._token: Optional[str] = None
        self._token_expires = 0.0

    def _auth_headers(self) -> dict:
        if self._token is None or time.monotonic() >= self._token_expires:
            try:
                response = self._client.post(
                    f"{self._base_url}/v2/oauth/token",
                    data={"grant_type": "client_credentials", "client_id": self._client_id,
                          "client_secret": self._client_secret},
                    timeout=self._timeout,
                )
                response.raise_for_status()
                payload = response.json()
                self._token = payload["access_token"]
                # обновляем токен с запасом в минуту
                self._token_expires = time.monotonic() + max(0, int(payload.get("expires_in", 3600)) - 60)
            except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
                logger.warning("cdek authorization failed: %s", exc)
                raise ProviderError(f"cdek authorization failed: {exc}") from exc
        return {"Authorization": f"Bearer {self._token}"}

    def get_options(self, destination: Destination, weight_category: str) -> list[DeliveryOption]:
        if weight_category not in WEIGHT_CATEGORIES:
            raise ValueError(f"unknown weight category: {weight_category}")
        if country_of(destination.address) == "OTHER":
            raise NotServiceable("СДЭК: доставка в эту страну через наш магазин недоступна")

        to_location = (
            {"latitude": destination.lat, "longitude": destination.lon, "address": destination.address}
            if destination.lat is not None and destination.lon is not None
            else {"address": destination.address}
        )
        body = {
            "type": 1,
            "from_location": {"code": self._from_code},
            "to_location": to_location,
            "packages": [{"weight": _WEIGHT_GRAMS[weight_category], "length": 40, "width": 30, "height": 40}],
        }
        try:
            response = self._client.post(
                f"{self._base_url}/v2/calculator/tarifflist",
                json=body, headers=self._auth_headers(), timeout=self._timeout,
            )
        except httpx.HTTPError as exc:
            logger.warning("cdek request failed: %s", exc)
            raise ProviderError(str(exc)) from exc

        if response.status_code in (401, 403):
            self._token = None  # следующая попытка получит новый токен
        if response.status_code >= 500 or response.status_code in (401, 403, 429):
            raise ProviderError(f"cdek returned HTTP {response.status_code}")
        try:
            payload = response.json()
        except ValueError as exc:
            raise ProviderError("cdek returned invalid JSON") from exc
        return self._parse_tariffs(payload)

    @staticmethod
    def _parse_tariffs(payload: dict) -> list[DeliveryOption]:
        if not isinstance(payload, dict):
            raise ProviderError(f"unexpected response shape: {payload!r}")
        tariffs = payload.get("tariff_codes") or []
        options: list[DeliveryOption] = []
        for item in tariffs:
            try:
                if int(item.get("delivery_mode", 0)) not in _TO_DOOR_MODES:
                    continue
                cost = Decimal(str(item["delivery_sum"])).quantize(Decimal("0.01"))
                days = int(item.get("period_max") or item.get("period_min") or 1)
                options.append(DeliveryOption(
                    id=f"cdek:{int(item['tariff_code'])}",
                    service=f"СДЭК: {item.get('tariff_name', 'курьер')}",
                    cost=cost, eta_days=max(1, days),
                ))
            except (KeyError, TypeError, ValueError, InvalidOperation):
                logger.warning("skipping unexpected cdek tariff: %r", item)
        if options:
            return sorted(options, key=lambda o: (o.cost, o.eta_days))[:MAX_OPTIONS]
        if payload.get("errors") or not tariffs:
            # Служба ответила, но тарифов до двери для этого адреса нет
            raise NotServiceable("СДЭК не доставляет курьером по этому адресу")
        raise BadAddressError("cdek: no door-to-door tariffs")
