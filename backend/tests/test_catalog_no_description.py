"""Каталог на настоящей БД: у букетов нет описаний, остаются название, повод, цена и фото."""
import pytest
from fastapi.testclient import TestClient

from app.main import app

pytestmark = pytest.mark.integration

client = TestClient(app)


def test_catalog_has_twelve_bouquets_without_descriptions():
    body = client.get("/goods").json()

    assert body["total"] == 12
    assert all(item["description"] is None for item in body["items"])


def test_every_bouquet_keeps_name_category_price_and_photo():
    items = client.get("/goods").json()["items"]

    for item in items:
        assert item["name"] and item["category"] and item["price"] > 0
        assert item["image_url"].startswith("/bouquets/") and item["image_url"].endswith(".jpg")
