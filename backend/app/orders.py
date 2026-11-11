"""Запросы к таблицам orders и order_items."""
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import text

from . import order_tracking
from .config import settings
from .db import engine

ORDER_COLUMNS = (
    "id, number, status, created_at, delivery_type, address, "
    "delivery_cost, delivery_service, delivery_approximate, total_price, "
    "recipient_name, recipient_phone, private_house, apartment, entrance, floor, intercom, courier_comment, "
    "paid_at, payment_method, eta_minutes"
)

DETAIL_FIELDS = (
    "recipient_name", "recipient_phone", "private_house", "apartment", "entrance", "floor", "intercom",
    "courier_comment",
)


def create_order(
    user_id: UUID,
    delivery_type: str,
    address: str | None,
    items: list[dict],
    delivery_cost: Decimal,
    delivery_approximate: bool,
    delivery_service: str | None = None,
    details: dict | None = None,
    eta_minutes: int | None = None,
) -> UUID:
    """Создаёт заказ и его состав одной транзакцией: либо всё, либо ничего.
    items: [{product_id, quantity, unit_price}]"""
    details = {k: (details or {}).get(k) for k in DETAIL_FIELDS}
    details["private_house"] = bool(details["private_house"])
    goods_total = sum((i["unit_price"] * i["quantity"] for i in items), Decimal("0"))
    with engine.begin() as conn:
        order_id = conn.execute(
            text(
                "INSERT INTO orders (user_id, delivery_type, address, total_price, "
                "delivery_cost, delivery_approximate, delivery_service, "
                "recipient_name, recipient_phone, private_house, apartment, entrance, floor, intercom, "
                "courier_comment, eta_minutes) "
                "VALUES (:u, :t, :a, :total, :dc, :da, :ds, "
                ":recipient_name, :recipient_phone, :private_house, :apartment, :entrance, :floor, :intercom, "
                ":courier_comment, :eta) RETURNING id"
            ),
            {"u": user_id, "t": delivery_type, "a": address, "total": goods_total + delivery_cost,
             "dc": delivery_cost, "da": delivery_approximate, "ds": delivery_service, "eta": eta_minutes,
             **details},
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


def _with_tracking(order: dict) -> dict:
    """Подставляет текущий этап заказа (собирается, в пути, доставлен) вместо сохранённого статуса «paid»."""
    tracking = order_tracking.derive(
        order["status"], order["paid_at"], order["eta_minutes"], order["delivery_type"],
        datetime.now(timezone.utc), settings.order_time_scale,
    )
    order["status"] = tracking.status
    order["seconds_left"] = tracking.seconds_left
    order["expected_at"] = tracking.expected_at
    return order


def get_order(user_id: UUID, order_id: UUID) -> dict | None:
    with engine.connect() as conn:
        row = conn.execute(
            text(f"SELECT {ORDER_COLUMNS} FROM orders WHERE id = :id AND user_id = :u"),
            {"id": order_id, "u": user_id},
        ).mappings().first()
        return _with_tracking(_attach_items(conn, [dict(row)])[0]) if row else None


def list_orders(user_id: UUID) -> list[dict]:
    """История заказов пользователя, от новых к старым (индекс idx_orders_user_created)."""
    with engine.connect() as conn:
        rows = conn.execute(
            text(f"SELECT {ORDER_COLUMNS} FROM orders WHERE user_id = :u ORDER BY created_at DESC"),
            {"u": user_id},
        ).mappings().all()
        return [_with_tracking(o) for o in _attach_items(conn, [dict(r) for r in rows])]


def mark_paid(user_id: UUID, order_id: UUID, method: str) -> str:
    """Помечает заказ оплаченным. Условие status = 'created' делает оплату идемпотентной:
    при двойном нажатии кнопки (или гонке двух запросов) второй запрос ничего не изменит.

    Возвращает 'paid', 'not_payable' (заказ уже оплачен или отменён) или 'not_found'."""
    with engine.begin() as conn:
        updated = conn.execute(
            text(
                "UPDATE orders SET status = 'paid', paid_at = now(), payment_method = :m "
                "WHERE id = :id AND user_id = :u AND status = 'created' RETURNING id"
            ),
            {"id": order_id, "u": user_id, "m": method},
        ).first()
        if updated:
            return "paid"
        exists = conn.execute(
            text("SELECT 1 FROM orders WHERE id = :id AND user_id = :u"), {"id": order_id, "u": user_id}
        ).first()
    return "not_payable" if exists else "not_found"
