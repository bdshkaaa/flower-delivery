"""Запросы к таблице products (каталог)."""
from decimal import Decimal
from uuid import UUID

from sqlalchemy import text

from .db import engine

COLUMNS = "id, name, category, price, image_url, description, popularity"

# Порядок сортировки берётся только из этого словаря: значение из запроса
# никогда не подставляется в SQL напрямую
ORDER_BY = {
    "popularity": "popularity DESC, name ASC",
    "price_asc": "price ASC, name ASC",
    "price_desc": "price DESC, name ASC",
}


def list_products(
    category: str | None = None,
    price_min: Decimal | None = None,
    price_max: Decimal | None = None,
    sort: str = "popularity",
) -> list[dict]:
    conditions: list[str] = []
    params: dict = {}
    if category:
        conditions.append("category = :category")
        params["category"] = category
    if price_min is not None:
        conditions.append("price >= :price_min")
        params["price_min"] = price_min
    if price_max is not None:
        conditions.append("price <= :price_max")
        params["price_max"] = price_max

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    sql = f"SELECT {COLUMNS} FROM products {where} ORDER BY {ORDER_BY[sort]}"
    with engine.connect() as conn:
        return [dict(row) for row in conn.execute(text(sql), params).mappings()]


def get_product(product_id: UUID) -> dict | None:
    with engine.connect() as conn:
        row = conn.execute(
            text(f"SELECT {COLUMNS} FROM products WHERE id = :id"), {"id": product_id}
        ).mappings().first()
    return dict(row) if row else None
