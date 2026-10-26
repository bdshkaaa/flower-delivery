import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db import engine
from app.main import app

pytestmark = pytest.mark.integration

EXPECTED_TABLES = {"users", "products", "delivery_quotes", "orders", "order_items"}


def test_migrations_created_all_tables():
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'public'"
            )
        )
        tables = {row[0] for row in rows}

    assert EXPECTED_TABLES <= tables


def test_health_db_endpoint_reaches_database():
    response = TestClient(app).get("/health/db")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
