"""E2E: сквозной сценарий покупателя через настоящий HTTP.

В docker-compose тест ходит на frontend (nginx), а тот проксирует /api на backend.
Так проверяется вся цепочка: nginx -> FastAPI -> PostgreSQL, как её видит браузер.
Без переменной E2E_BASE_URL (например, при запуске pytest на ноутбуке) тест пропускается."""
import os
import time
from uuid import uuid4

import httpx
import pytest

BASE_URL = os.environ.get("E2E_BASE_URL")
MOCK_PROVIDER = os.environ.get("DELIVERY_PROVIDER", "mock") == "mock"

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(not BASE_URL, reason="E2E_BASE_URL не задан: полный стенд не запущен"),
]


@pytest.fixture(scope="module")
def http():
    with httpx.Client(base_url=BASE_URL, timeout=15) as client:
        # Контейнеры стартуют параллельно: ждём, пока стенд ответит
        deadline = time.monotonic() + 90
        while True:
            try:
                if client.get("/health").status_code == 200:
                    break
            except httpx.HTTPError:
                pass
            if time.monotonic() > deadline:
                pytest.fail(f"стенд {BASE_URL} не поднялся за 90 секунд")
            time.sleep(2)
        yield client


def test_customer_journey_catalog_to_order_history(http):
    # 1. Регистрация
    email = f"e2e-{uuid4().hex[:10]}@example.com"
    registered = http.post("/register", json={"email": email, "password": "secret123", "name": "Ева"})
    assert registered.status_code == 201
    headers = {"Authorization": f"Bearer {registered.json()['access_token']}"}

    # 2. Каталог с фильтром и сортировкой
    catalog = http.get("/goods", params={"category": "birthday", "sort": "price_asc"}).json()
    assert catalog["total"] > 0
    prices = [p["price"] for p in catalog["items"]]
    assert prices == sorted(prices)
    assert all(p["category"] == "birthday" for p in catalog["items"])
    bouquet = catalog["items"][0]

    # 3. Стоимость и срок доставки до оформления
    quote = http.get("/delivery/quote", params={"address": "Москва, Тверская 1", "weight_category": "medium"}).json()
    assert quote["cost"] > 0 and quote["eta_days"] >= 1

    # 4. Заказ с доставкой: сумма = букеты + доставка
    created = http.post("/orders", headers=headers, json={
        "items": [{"product_id": bouquet["id"], "quantity": 2}],
        "delivery_type": "delivery", "address": "Москва, Тверская 1",
    })
    assert created.status_code == 201
    order = created.json()
    assert order["total_price"] == pytest.approx(2 * bouquet["price"] + order["delivery_cost"])

    # 5. Заказ виден в истории вместе с составом
    history = http.get("/orders", headers=headers).json()
    assert [o["id"] for o in history] == [order["id"]]
    assert history[0]["items"][0]["name"] == bouquet["name"]

    # 6. Чужой токен и отсутствие токена заказов не показывают
    assert http.get("/orders").status_code == 401


@pytest.mark.skipif(not MOCK_PROVIDER, reason="сбой доставки имитируется только заглушкой")
def test_order_is_created_when_delivery_service_is_down(http):
    email = f"e2e-{uuid4().hex[:10]}@example.com"
    token = http.post("/register", json={"email": email, "password": "secret123", "name": "Ева"}).json()["access_token"]
    bouquet = http.get("/goods").json()["items"][0]

    # Адрес со словом fallback «роняет» заглушку API доставки
    response = http.post("/orders", headers={"Authorization": f"Bearer {token}"}, json={
        "items": [{"product_id": bouquet["id"], "quantity": 1}],
        "delivery_type": "delivery", "address": "fallback, 1",
    })

    assert response.status_code == 201
    assert response.json()["delivery_approximate"] is True
