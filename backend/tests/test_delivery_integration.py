"""Запись и чтение котировок в настоящей таблице delivery_quotes."""
from decimal import Decimal

import pytest
from sqlalchemy import text

from app.db import engine
from app.delivery.base import DeliveryQuote
from app.delivery.store import QuoteStore

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def clean_quotes():
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM delivery_quotes WHERE region_key LIKE 'test-%'"))
    yield
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM delivery_quotes WHERE region_key LIKE 'test-%'"))


def test_latest_returns_most_recent_quote():
    store = QuoteStore()
    store.save("test-spb", "medium", DeliveryQuote(Decimal("400.00"), 1))
    store.save("test-spb", "medium", DeliveryQuote(Decimal("470.00"), 2))

    latest = store.latest("test-spb", "medium")
    assert latest.cost == Decimal("470.00") and latest.eta_days == 2
    assert latest.approximate is True


def test_latest_is_none_for_unknown_region():
    assert QuoteStore().latest("test-nowhere", "light") is None
