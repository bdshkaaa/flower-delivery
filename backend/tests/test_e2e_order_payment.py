"""E2E: оформление -> оплата -> статус заказа через настоящий HTTP (frontend nginx -> backend -> PostgreSQL).
Без переменной E2E_BASE_URL (например, при запуске pytest на ноутбуке) тест пропускается."""
import os
import time
from uuid import uuid4

import httpx
import pytest

BASE_URL = os.environ.get("E2E_BASE_URL")
DETAILS = {"recipient_name": "Анна", "recipient_phone": "+7 900 123-45-67", "apartment": "12"}

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(not BASE_URL, reason="E2E_BASE_URL не задан: полный стенд не запущен"),
]


@pytest.fixture(scope="module")
def http():
    with httpx.Client(base_url=BASE_URL, timeout=15) as client:
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


def test_customer_places_pays_and_tracks_order(http):
    registered = http.post("/register", json={"email": f"e2e-{uuid4().hex[:10]}@example.com",
                                              "password": "secret123", "name": "Ева"})
    headers = {"Authorization": f"Bearer {registered.json()['access_token']}"}
    bouquet = http.get("/goods").json()["items"][0]

    # 1. Заказ оформлен, но не оплачен: таймера ещё нет
    order = http.post("/orders", headers=headers, json={
        "items": [{"product_id": bouquet["id"], "quantity": 1}], "delivery_type": "pickup"}).json()
    assert order["status"] == "created" and order["number"] and order["seconds_left"] is None

    # 2. Банк отклонил карту: заказ остался неоплаченным
    declined = http.post(f"/orders/{order['id']}/pay", headers=headers, json={
        "method": "card", "card_number": "4000 0000 0000 0002", "expiry": "12/40", "cvc": "123"})
    assert declined.status_code == 402
    assert http.get(f"/orders/{order['id']}", headers=headers).json()["status"] == "created"

    # 3. Оплата успешной картой: заказ собирается, идёт таймер
    paid = http.post(f"/orders/{order['id']}/pay", headers=headers, json={
        "method": "card", "card_number": "4242 4242 4242 4242", "expiry": "12/40", "cvc": "123"})
    assert paid.status_code == 200
    assert paid.json()["status"] == "assembling" and paid.json()["seconds_left"] > 0

    # 4. Повторная оплата невозможна, статус виден на странице заказа и в истории
    assert http.post(f"/orders/{order['id']}/pay", headers=headers, json={"method": "sbp"}).status_code == 409
    status = http.get(f"/orders/{order['id']}", headers=headers).json()
    assert status["payment_method"] == "card" and status["id"] == order["id"]
    assert [o["id"] for o in http.get("/orders", headers=headers).json()] == [order["id"]]
