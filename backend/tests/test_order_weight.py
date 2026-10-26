"""Unit-тест правила весовой категории заказа (БД не нужна)."""
import pytest

from app.routers.orders import weight_category_for


@pytest.mark.parametrize("quantity, expected", [(1, "light"), (2, "medium"), (3, "medium"), (4, "heavy"), (10, "heavy")])
def test_weight_category_by_total_quantity(quantity, expected):
    assert weight_category_for(quantity) == expected
