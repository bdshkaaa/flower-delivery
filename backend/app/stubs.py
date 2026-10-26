"""Тестовые данные для заглушек API. Заменяются реальной БД в следующих задачах."""
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

from .schemas import OrderOut

STUB_TOKEN = "stub-token"

STUB_USER = {
    "id": UUID("00000000-0000-0000-0000-000000000001"),
    "email": "anna@example.com",
    "name": "Анна",
}

STUB_PRODUCTS = [
    {"id": UUID("11111111-1111-1111-1111-000000000001"), "name": "Нежность",
     "category": "birthday", "price": Decimal("2500.00"), "image_url": None, "popularity": 120},
    {"id": UUID("11111111-1111-1111-1111-000000000002"), "name": "Алая роза",
     "category": "anniversary", "price": Decimal("4200.00"), "image_url": None, "popularity": 200},
    {"id": UUID("11111111-1111-1111-1111-000000000003"), "name": "Белое облако",
     "category": "wedding", "price": Decimal("6800.00"), "image_url": None, "popularity": 75},
    {"id": UUID("11111111-1111-1111-1111-000000000004"), "name": "Полевой микс",
     "category": "birthday", "price": Decimal("1800.00"), "image_url": None, "popularity": 310},
    {"id": UUID("11111111-1111-1111-1111-000000000005"), "name": "Пионы",
     "category": "anniversary", "price": Decimal("5400.00"), "image_url": None, "popularity": 150},
]

DELIVERY_COST = Decimal("450.00")

# Заказы, созданные через заглушку (живут до перезапуска сервера)
STUB_ORDERS: list[OrderOut] = []


def new_order_id() -> UUID:
    return uuid4()


def now() -> datetime:
    return datetime.now(timezone.utc)
