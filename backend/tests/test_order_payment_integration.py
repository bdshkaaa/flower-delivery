"""Оплата и статус заказа на настоящей БД: от создания заказа до «в пути»."""
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db import engine
from app.delivery.cache import TTLCache
from app.delivery.mock import MockDeliveryProvider
from app.delivery.service import DeliveryService, get_delivery_service
from app.main import app

pytestmark = pytest.mark.integration

client = TestClient(app)

DETAILS = {"recipient_name": "Анна", "recipient_phone": "+7 900 123-45-67", "apartment": "12"}
CARD = {"method": "card", "card_number": "4242 4242 4242 4242", "expiry": "12/40", "cvc": "123"}


@pytest.fixture(autouse=True)
def provider():
    service = DeliveryService([MockDeliveryProvider()], TTLCache(60))
    app.dependency_overrides[get_delivery_service] = lambda: service
    yield
    app.dependency_overrides.pop(get_delivery_service, None)


def new_headers():
    email = f"buyer-{uuid4().hex[:10]}@example.com"
    token = client.post("/register", json={"email": email, "password": "secret123", "name": "Покупатель"}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def headers():
    return new_headers()


@pytest.fixture()
def product():
    return client.get("/goods", params={"sort": "price_asc"}).json()["items"][0]


def create_order(headers, product, delivery_type="delivery"):
    body = {"items": [{"product_id": product["id"], "quantity": 1}], "delivery_type": delivery_type}
    if delivery_type == "delivery":
        body |= {"address": "Санкт-Петербург, Невский проспект 1", **DETAILS}
    response = client.post("/orders", headers=headers, json=body)
    assert response.status_code == 201
    return response.json()


def test_new_order_waits_for_payment_and_has_number_and_eta(headers, product):
    order = create_order(headers, product)

    assert order["status"] == "created"
    assert order["number"] >= 1001
    assert order["eta_minutes"] and order["eta_minutes"] > 0
    assert order["paid_at"] is None and order["seconds_left"] is None


def test_paid_order_starts_assembling_with_a_countdown(headers, product):
    order = create_order(headers, product)

    paid = client.post(f"/orders/{order['id']}/pay", headers=headers, json=CARD)

    assert paid.status_code == 200
    body = paid.json()
    assert body["status"] == "assembling"
    assert body["payment_method"] == "card" and body["paid_at"]
    assert 0 < body["seconds_left"] <= body["eta_minutes"] * 60
    assert "4242" not in paid.text  # номер карты нигде не возвращается


def test_status_page_returns_the_same_order(headers, product):
    order = create_order(headers, product)
    client.post(f"/orders/{order['id']}/pay", headers=headers, json={"method": "sbp"})

    fetched = client.get(f"/orders/{order['id']}", headers=headers)

    assert fetched.status_code == 200
    assert fetched.json()["id"] == order["id"] and fetched.json()["payment_method"] == "sbp"


def test_order_moves_to_shipping_as_time_passes(headers, product):
    order = create_order(headers, product)
    client.post(f"/orders/{order['id']}/pay", headers=headers, json=CARD)
    # «Прокручиваем время»: оплата была три часа назад, а срок доставки у заглушки — сутки
    with engine.begin() as conn:
        conn.execute(
            text("UPDATE orders SET paid_at = :t WHERE id = :id"),
            {"t": datetime.now(timezone.utc) - timedelta(hours=3), "id": order["id"]},
        )

    assert client.get(f"/orders/{order['id']}", headers=headers).json()["status"] == "shipping"

    with engine.begin() as conn:
        conn.execute(
            text("UPDATE orders SET paid_at = :t WHERE id = :id"),
            {"t": datetime.now(timezone.utc) - timedelta(days=2), "id": order["id"]},
        )
    final = client.get(f"/orders/{order['id']}", headers=headers).json()
    assert final["status"] == "delivered" and final["seconds_left"] == 0


def test_pickup_order_becomes_ready_for_pickup(headers, product):
    order = create_order(headers, product, "pickup")
    assert order["eta_minutes"] == 45
    client.post(f"/orders/{order['id']}/pay", headers=headers, json=CARD)
    with engine.begin() as conn:
        conn.execute(
            text("UPDATE orders SET paid_at = :t WHERE id = :id"),
            {"t": datetime.now(timezone.utc) - timedelta(hours=2), "id": order["id"]},
        )

    assert client.get(f"/orders/{order['id']}", headers=headers).json()["status"] == "ready"


def test_declined_card_keeps_the_order_unpaid_and_can_be_retried(headers, product):
    order = create_order(headers, product)

    declined = client.post(f"/orders/{order['id']}/pay", headers=headers,
                           json=CARD | {"card_number": "4000 0000 0000 0002"})
    assert declined.status_code == 402
    assert client.get(f"/orders/{order['id']}", headers=headers).json()["status"] == "created"

    retried = client.post(f"/orders/{order['id']}/pay", headers=headers, json=CARD)
    assert retried.status_code == 200 and retried.json()["status"] == "assembling"


def test_invalid_card_data_is_rejected_with_422(headers, product):
    order = create_order(headers, product)

    response = client.post(f"/orders/{order['id']}/pay", headers=headers, json=CARD | {"cvc": "1"})

    assert response.status_code == 422
    assert client.get(f"/orders/{order['id']}", headers=headers).json()["status"] == "created"


def test_order_cannot_be_paid_twice(headers, product):
    order = create_order(headers, product)
    assert client.post(f"/orders/{order['id']}/pay", headers=headers, json=CARD).status_code == 200

    second = client.post(f"/orders/{order['id']}/pay", headers=headers, json=CARD)

    assert second.status_code == 409


def test_someone_elses_order_is_not_visible_or_payable(headers, product):
    order = create_order(headers, product)
    stranger = new_headers()

    assert client.get(f"/orders/{order['id']}", headers=stranger).status_code == 404
    assert client.post(f"/orders/{order['id']}/pay", headers=stranger, json=CARD).status_code == 404
    assert client.get(f"/orders/{order['id']}", headers=headers).json()["status"] == "created"


def test_unknown_order_and_missing_token(headers):
    assert client.get(f"/orders/{uuid4()}", headers=headers).status_code == 404
    assert client.get(f"/orders/{uuid4()}").status_code == 401
    assert client.post(f"/orders/{uuid4()}/pay", json=CARD).status_code == 401
