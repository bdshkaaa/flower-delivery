"""Хранилище вариантов доставки в таблице delivery_quotes (запасной кэш при сбое служб)."""
import logging
from decimal import Decimal

from sqlalchemy import text

from ..db import engine
from .base import DeliveryOption

logger = logging.getLogger("app.delivery.store")


class QuoteStore:
    """Любая ошибка БД логируется и не ломает расчёт доставки."""

    def save(self, region_key: str, weight_category: str, options: list[DeliveryOption]) -> None:
        try:
            with engine.begin() as conn:
                for option in options:
                    conn.execute(
                        text(
                            "INSERT INTO delivery_quotes "
                            "(region_key, weight_category, cost, eta_days, option_id, service) "
                            "VALUES (:r, :w, :c, :e, :o, :s)"
                        ),
                        {"r": region_key, "w": weight_category, "c": option.cost, "e": option.eta_days,
                         "o": option.id, "s": option.service},
                    )
        except Exception as exc:  # noqa: BLE001
            logger.warning("cannot save delivery quotes: %s", exc)

    def latest(self, region_key: str, weight_category: str) -> list[DeliveryOption]:
        """Последний известный вариант каждой службы для региона и веса; помечены как предварительные."""
        try:
            with engine.connect() as conn:
                rows = conn.execute(
                    text(
                        "SELECT DISTINCT ON (option_id) option_id, service, cost, eta_days "
                        "FROM delivery_quotes "
                        "WHERE region_key = :r AND weight_category = :w AND option_id IS NOT NULL "
                        "ORDER BY option_id, fetched_at DESC"
                    ),
                    {"r": region_key, "w": weight_category},
                ).all()
        except Exception as exc:  # noqa: BLE001
            logger.warning("cannot read delivery quotes: %s", exc)
            return []
        return [
            DeliveryOption(r.option_id, r.service or r.option_id, Decimal(r.cost), r.eta_days, approximate=True)
            for r in rows
        ]
