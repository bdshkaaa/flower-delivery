"""Тесты контракта API, которым не нужна БД: доставка (заглушка), защита заказов, Swagger."""
import pytest
from fastapi.testclient import TestClient

from app.delivery.cache import TTLCache
from app.delivery.mock import MockDeliveryProvider
from app.delivery.service import DeliveryService, get_delivery_service

from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def fresh_delivery_service():
    """Свежий сервис доставки без БД на каждый тест: общий Circuit Breaker не влияет на соседей."""
    service = DeliveryService([MockDeliveryProvider()], TTLCache(60))
    app.dependency_overrides[get_delivery_service] = lambda: service
    yield
    app.dependency_overrides.pop(get_delivery_service, None)


def test_delivery_quote_exact_and_fallback():
    exact = client.get("/delivery/quote", params={"address": "Москва, Тверская 1"}).json()
    assert exact["approximate"] is False and exact["source"] == "api"

    approx = client.get("/delivery/quote", params={"address": "fallback test"}).json()
    assert approx["approximate"] is True and approx["source"] == "fallback"


def test_delivery_quote_requires_address():
    assert client.get("/delivery/quote").status_code == 422


def test_orders_require_auth():
    assert client.get("/orders").status_code == 401
    assert client.post("/orders", json={}).status_code == 401


def test_goods_validates_query_parameters():
    assert client.get("/goods", params={"sort": "by_color"}).status_code == 422
    assert client.get("/goods", params={"price_min": -5}).status_code == 422


def test_swagger_is_available():
    assert client.get("/docs").status_code == 200
    paths = client.get("/openapi.json").json()["paths"]
    for path in ("/login", "/register", "/goods", "/delivery/quote", "/orders"):
        assert path in paths
