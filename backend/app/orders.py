"""Запросы к таблицам orders и order_items."""
from decimal import Decimal
from uuid import UUID

from sqlalchemy import text

from .db import engine

ORDER_COLUMNS = (
    "id, status, created_at, delivery_type, address, "
    "delivery_cost, delivery_approximate, total_price"
)


def create_order(
    user_id: UUID,
    delivery_type: str,
    address: str | None,
    items: list[dict],
    delivery_cost: Decimal,
    delivery_approximate: bool,
) -> UUID:
    """Создаёт заказ и его состав одной транзакцией: либо всё, либо ничего.
    items: [{product_id, quantity, unit_price}]"""
    goods_total = sum((i["unit_price"] * i["quantity"] for i in items), Decimal("0"))
    with engine.begin() as conn:
        order_id = conn.execute(
            text(
                "INSERT INTO orders (user_id, delivery_type, address, total_price, "
                "delivery_cost, delivery_approximate) "
                "VALUES (:u, :t, :a, :total, :dc, :da) RETURNING id"
            ),
            {"u": user_id, "t": delivery_type, "a": address, "total": goods_total + delivery_cost,
             "dc": delivery_cost, "da": delivery_approximate},
        ).scalar_one()
        for item in items:
            conn.execute(
                text(
                    "INSERT INTO order_items (order_id, product_id, quantity, unit_price) "
                    "VALUES (:o, :p, :q, :price)"
                ),
                {"o": order_id, "p": item["product_id"], "q": item["quantity"], "price": item["unit_price"]},
            )
    return order_id


def _attach_items(conn, orders: list[dict]) -> list[dict]:
    if not orders:
        return orders
    rows = conn.execute(
        text(
            "SELECT oi.order_id, oi.product_id, p.name, oi.quantity, oi.unit_price "
            "FROM order_items oi JOIN products p ON p.id = oi.product_id "
            "WHERE oi.order_id = ANY(:ids) ORDER BY p.name"
        ),
        {"ids": [o["id"] for o in orders]},
    ).mappings().all()
    for order in orders:
        order["items"] = [
            {k: r[k] for k in ("product_id", "name", "quantity", "unit_price")}
            for r in rows if r["order_id"] == order["id"]
        ]
    return orders


def get_order(user_id: UUID, order_id: UUID) -> dict | None:
    with engine.connect() as conn:
        row = conn.execute(
            text(f"SELECT {ORDER_COLUMNS} FROM orders WHERE id = :id AND user_id = :u"),
            {"id": order_id, "u": user_id},
        ).mappings().first()
        return _attach_items(conn, [dict(row)])[0] if row else None


def list_orders(user_id: UUID) -> list[dict]:
    """История заказов пользователя, от новых к старым (индекс idx_orders_user_created)."""
    with engine.connect() as conn:
        rows = conn.execute(
            text(f"SELECT {ORDER_COLUMNS} FROM orders WHERE user_id = :u ORDER BY created_at DESC"),
            {"u": user_id},
        ).mappings().all()
        return _attach_items(conn, [dict(r) for r in rows])
