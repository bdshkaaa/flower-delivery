"""Заказы (пока заглушка хранения) на реальных товарах из каталога."""
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app

pytestmark = pytest.mark.integration

client = TestClient(app)


@pytest.fixture()
def headers():
    email = f"buyer-{uuid4().hex[:10]}@example.com"
    token = client.post(
        "/register", json={"email": email, "password": "secret123", "name": "Покупатель"}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def product():
    return client.get("/goods", params={"sort": "price_asc"}).json()["items"][0]


def test_create_order_calculates_total_with_delivery(headers, product):
    response = client.post("/orders", headers=headers, json={
        "items": [{"product_id": product["id"], "quantity": 2}],
        "delivery_type": "delivery", "address": "Москва, Тверская 1",
    })

    assert response.status_code == 201
    order = response.json()
    assert order["delivery_cost"] == 450.0
    assert order["total_price"] == pytest.approx(2 * product["price"] + 450.0)
    assert order["items"][0]["name"] == product["name"]


def test_pickup_order_has_no_delivery_cost(headers, product):
    response = client.post("/orders", headers=headers, json={
        "items": [{"product_id": product["id"], "quantity": 1}], "delivery_type": "pickup",
    })

    assert response.status_code == 201
    assert response.json()["total_price"] == pytest.approx(product["price"])


def test_delivery_order_without_address_is_422(headers, product):
    response = client.post("/orders", headers=headers, json={
        "items": [{"product_id": product["id"], "quantity": 1}], "delivery_type": "delivery",
    })

    assert response.status_code == 422


def test_order_with_unknown_product_is_404(headers):
    response = client.post("/orders", headers=headers, json={
        "items": [{"product_id": "00000000-0000-4000-8000-999999999999", "quantity": 1}],
        "delivery_type": "pickup",
    })

    assert response.status_code == 404


def test_order_history_newest_first(headers, product):
    for quantity in (1, 3):
        client.post("/orders", headers=headers, json={
            "items": [{"product_id": product["id"], "quantity": quantity}],
            "delivery_type": "pickup",
        })

    created = [o["created_at"] for o in client.get("/orders", headers=headers).json()]

    assert len(created) >= 2 and created == sorted(created, reverse=True)
