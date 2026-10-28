"""Заказы на настоящей БД: состав, сумма, доставка, изоляция пользователей."""
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.delivery.cache import TTLCache
from app.delivery.mock import MockDeliveryProvider
from app.delivery.service import DeliveryService, get_delivery_service
from app.main import app

pytestmark = pytest.mark.integration

client = TestClient(app)


@pytest.fixture(autouse=True)
def provider():
    """Свежий сервис доставки без БД-хранилища; провайдер можно «уронить» в тесте."""
    mock = MockDeliveryProvider()
    service = DeliveryService([mock], TTLCache(60))
    app.dependency_overrides[get_delivery_service] = lambda: service
    yield mock
    app.dependency_overrides.pop(get_delivery_service, None)


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
    assert order["delivery_approximate"] is False
    assert order["total_price"] == pytest.approx(2 * product["price"] + 450.0)
    assert order["items"][0]["name"] == product["name"]


def test_order_is_not_blocked_when_delivery_api_fails(headers, product, provider):
    provider.failing = True

    response = client.post("/orders", headers=headers, json={
        "items": [{"product_id": product["id"], "quantity": 2}],
        "delivery_type": "delivery", "address": "Казань, Баумана 1",
    })

    assert response.status_code == 201
    order = response.json()
    assert order["delivery_approximate"] is True
    assert order["delivery_cost"] == 500.0  # запасной тариф для medium
    assert order["total_price"] == pytest.approx(2 * product["price"] + 500.0)


def test_order_is_saved_and_returned_in_history_with_items(headers, product):
    created = client.post("/orders", headers=headers, json={
        "items": [{"product_id": product["id"], "quantity": 3}], "delivery_type": "pickup",
    }).json()

    history = client.get("/orders", headers=headers).json()

    assert [o["id"] for o in history] == [created["id"]]
    assert history[0]["items"][0]["quantity"] == 3
    assert history[0]["items"][0]["name"] == product["name"]


def test_user_sees_only_own_orders(headers, product):
    client.post("/orders", headers=headers, json={
        "items": [{"product_id": product["id"], "quantity": 1}], "delivery_type": "pickup"})
    other = client.post("/register", json={
        "email": f"other-{uuid4().hex[:10]}@example.com", "password": "secret123", "name": "Другой"}
    ).json()["access_token"]

    assert client.get("/orders", headers={"Authorization": f"Bearer {other}"}).json() == []


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


# ---- Выбор варианта доставки и недоступная доставка ----
from tests.fakes import ScriptedProvider, option  # noqa: E402


def _use_providers(*providers):
    service = DeliveryService(list(providers), TTLCache(60))
    app.dependency_overrides[get_delivery_service] = lambda: service


def _order(headers, product, **extra):
    body = {"items": [{"product_id": product["id"], "quantity": 1}],
            "delivery_type": "delivery", "address": "Москва, Тверская 1", **extra}
    return client.post("/orders", headers=headers, json=body)


def test_chosen_delivery_option_is_used_and_service_is_saved(headers, product):
    _use_providers(ScriptedProvider("a", [option("a:std", "500.00", 3, "Дешёвая служба"),
                                          option("a:fast", "1200.00", 1, "Быстрая служба")]))

    response = _order(headers, product, delivery_option_id="a:fast")

    assert response.status_code == 201
    order = response.json()
    assert order["delivery_cost"] == 1200.0 and order["delivery_service"] == "Быстрая служба"
    assert order["total_price"] == pytest.approx(product["price"] + 1200.0)
    assert client.get("/orders", headers=headers).json()[0]["delivery_service"] == "Быстрая служба"


def test_without_option_the_cheapest_is_taken(headers, product):
    _use_providers(ScriptedProvider("a", [option("a:fast", "1200.00", 1), option("a:std", "500.00", 3)]))

    assert _order(headers, product).json()["delivery_cost"] == 500.0


def test_unknown_option_is_409(headers, product):
    _use_providers(ScriptedProvider("a"))

    response = _order(headers, product, delivery_option_id="gone:std")

    assert response.status_code == 409


def test_order_to_unavailable_address_is_rejected_but_pickup_still_works(headers, product):
    _use_providers(MockDeliveryProvider())

    rejected = _order(headers, product, address="nowhere, 1")
    pickup = client.post("/orders", headers=headers, json={
        "items": [{"product_id": product["id"], "quantity": 1}], "delivery_type": "pickup"})

    assert rejected.status_code == 422 and "недоступна" in rejected.json()["detail"]
    assert pickup.status_code == 201
    # отклонённый заказ не сохранился
    assert [o["delivery_type"] for o in client.get("/orders", headers=headers).json()] == ["pickup"]
