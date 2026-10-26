"""Заглушки, которые пока не заменены реальной БД: стоимость доставки и список заказов."""
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

from .schemas import OrderOut

DELIVERY_COST = Decimal("450.00")

# Заказы, созданные через заглушку (живут до перезапуска сервера)
STUB_ORDERS: list[OrderOut] = []


def new_order_id() -> UUID:
    return uuid4()


def now() -> datetime:
    return datetime.now(timezone.utc)
