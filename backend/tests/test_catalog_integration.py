"""Каталог на настоящей БД с начальным ассортиментом из миграции 0003."""
import pytest
from fastapi.testclient import TestClient

from app.main import app

pytestmark = pytest.mark.integration

client = TestClient(app)


def _goods(**params):
    response = client.get("/goods", params=params)
    assert response.status_code == 200
    return response.json()


def test_catalog_is_not_empty_and_has_expected_fields():
    body = _goods()

    assert body["total"] == len(body["items"]) >= 10
    product = body["items"][0]
    for field in ("id", "name", "category", "price", "image_url", "description", "popularity"):
        assert field in product


def test_default_sort_is_by_popularity():
    popularity = [p["popularity"] for p in _goods()["items"]]

    assert popularity == sorted(popularity, reverse=True)


def test_sort_by_price_both_directions():
    asc = [p["price"] for p in _goods(sort="price_asc")["items"]]
    desc = [p["price"] for p in _goods(sort="price_desc")["items"]]

    assert asc == sorted(asc)
    assert desc == sorted(desc, reverse=True)


def test_filter_by_category():
    items = _goods(category="wedding")["items"]

    assert items and {p["category"] for p in items} == {"wedding"}


def test_filter_by_price_range():
    items = _goods(price_min=2000, price_max=3000)["items"]

    assert items and all(2000 <= p["price"] <= 3000 for p in items)


def test_filters_and_sort_work_together():
    items = _goods(category="birthday", price_max=2500, sort="price_desc")["items"]
    prices = [p["price"] for p in items]

    assert items
    assert {p["category"] for p in items} == {"birthday"}
    assert all(price <= 2500 for price in prices)
    assert prices == sorted(prices, reverse=True)


def test_no_matches_returns_empty_list():
    assert _goods(category="birthday", price_min=100000) == {"items": [], "total": 0}


def test_unknown_category_returns_empty_list():
    assert _goods(category="nonexistent")["total"] == 0


def test_product_card_by_id_and_unknown_id():
    first = _goods()["items"][0]

    card = client.get(f"/goods/{first['id']}")
    missing = client.get("/goods/00000000-0000-4000-8000-999999999999")

    assert card.status_code == 200 and card.json()["name"] == first["name"]
    assert missing.status_code == 404


def test_sql_injection_in_category_is_harmless():
    assert _goods(category="x' OR '1'='1")["total"] == 0
