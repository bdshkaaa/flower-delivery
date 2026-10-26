"""Тесты контракта API: статусы, форма ответов, фильтры и сортировка (заглушки)."""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
AUTH = {"Authorization": "Bearer stub-token"}
FIRST_PRODUCT = "11111111-1111-1111-1111-000000000001"  # 2500.00


def test_login_returns_token_and_user():
    r = client.post("/login", json={"email": "a@b.ru", "password": "secret123"})
    assert r.status_code == 200
    body = r.json()
    assert body["token_type"] == "bearer" and body["access_token"]
    assert body["user"]["email"] == "a@b.ru"


def test_login_with_wrong_password_is_401():
    r = client.post("/login", json={"email": "a@b.ru", "password": "wrong"})
    assert r.status_code == 401
    assert "detail" in r.json()


def test_register_returns_201():
    r = client.post("/register", json={"email": "n@b.ru", "password": "secret123", "name": "Нина"})
    assert r.status_code == 201
    assert r.json()["user"]["name"] == "Нина"


def test_logout_requires_token():
    assert client.post("/logout").status_code == 401
    assert client.post("/logout", headers=AUTH).status_code == 204


def test_goods_list_default_sorted_by_popularity():
    body = client.get("/goods").json()
    popularity = [p["popularity"] for p in body["items"]]
    assert body["total"] == len(body["items"]) > 0
    assert popularity == sorted(popularity, reverse=True)


def test_goods_filter_by_category_and_price_with_sort():
    r = client.get("/goods", params={"category": "birthday", "price_max": 2500, "sort": "price_asc"})
    items = r.json()["items"]
    assert [p["category"] for p in items] == ["birthday", "birthday"]
    assert [p["price"] for p in items] == [1800.0, 2500.0]


def test_goods_empty_result_is_empty_list_not_error():
    r = client.get("/goods", params={"category": "nonexistent"})
    assert r.status_code == 200
    assert r.json() == {"items": [], "total": 0}


def test_good_by_id_and_not_found():
    assert client.get(f"/goods/{FIRST_PRODUCT}").json()["name"] == "Нежность"
    missing = client.get("/goods/11111111-1111-1111-1111-999999999999")
    assert missing.status_code == 404


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


def test_create_order_calculates_total_with_delivery():
    r = client.post("/orders", headers=AUTH, json={
        "items": [{"product_id": FIRST_PRODUCT, "quantity": 2}],
        "delivery_type": "delivery", "address": "Москва, Тверская 1",
    })
    assert r.status_code == 201
    order = r.json()
    assert order["delivery_cost"] == 450.0
    assert order["total_price"] == 2 * 2500.0 + 450.0


def test_pickup_order_has_no_delivery_cost():
    r = client.post("/orders", headers=AUTH, json={
        "items": [{"product_id": FIRST_PRODUCT, "quantity": 1}], "delivery_type": "pickup",
    })
    assert r.status_code == 201
    assert r.json()["total_price"] == 2500.0


def test_delivery_order_without_address_is_422():
    r = client.post("/orders", headers=AUTH, json={
        "items": [{"product_id": FIRST_PRODUCT, "quantity": 1}], "delivery_type": "delivery",
    })
    assert r.status_code == 422


def test_order_with_unknown_product_is_404():
    r = client.post("/orders", headers=AUTH, json={
        "items": [{"product_id": "11111111-1111-1111-1111-999999999999", "quantity": 1}],
        "delivery_type": "pickup",
    })
    assert r.status_code == 404


def test_order_history_newest_first():
    for qty in (1, 3):
        client.post("/orders", headers=AUTH, json={
            "items": [{"product_id": FIRST_PRODUCT, "quantity": qty}], "delivery_type": "pickup"})
    orders = client.get("/orders", headers=AUTH).json()
    created = [o["created_at"] for o in orders]
    assert len(orders) >= 2 and created == sorted(created, reverse=True)


def test_swagger_is_available():
    assert client.get("/docs").status_code == 200
    assert "/delivery/quote" in client.get("/openapi.json").json()["paths"]
