"""Хранилище котировок в таблице delivery_quotes (запасной кэш при недоступном API)."""
import logging
from decimal import Decimal
from typing import Optional

from sqlalchemy import text

from ..db import engine
from .base import DeliveryQuote

logger = logging.getLogger("app.delivery.store")


class QuoteStore:
    """Любая ошибка БД логируется и не ломает расчёт доставки."""

    def save(self, region_key: str, weight_category: str, quote: DeliveryQuote) -> None:
        try:
            with engine.begin() as conn:
                conn.execute(
                    text(
                        "INSERT INTO delivery_quotes (region_key, weight_category, cost, eta_days) "
                        "VALUES (:r, :w, :c, :e)"
                    ),
                    {"r": region_key, "w": weight_category, "c": quote.cost, "e": quote.eta_days},
                )
        except Exception as exc:  # noqa: BLE001
            logger.warning("cannot save delivery quote: %s", exc)

    def latest(self, region_key: str, weight_category: str) -> Optional[DeliveryQuote]:
        try:
            with engine.connect() as conn:
                row = conn.execute(
                    text(
                        "SELECT cost, eta_days FROM delivery_quotes "
                        "WHERE region_key = :r AND weight_category = :w "
                        "ORDER BY fetched_at DESC LIMIT 1"
                    ),
                    {"r": region_key, "w": weight_category},
                ).first()
        except Exception as exc:  # noqa: BLE001
            logger.warning("cannot read delivery quote: %s", exc)
            return None
        if row is None:
            return None
        return DeliveryQuote(cost=Decimal(row.cost), eta_days=row.eta_days, approximate=True)
