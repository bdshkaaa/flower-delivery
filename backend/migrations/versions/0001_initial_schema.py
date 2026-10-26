"""initial schema

Схема из ER-диаграммы README (этап 3): users, products, delivery_quotes,
orders, order_items и индексы под расчётную нагрузку.

Revision ID: 0001
Revises:
"""
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

# Каждая команда выполняется отдельным op.execute
UPGRADE_STATEMENTS = [
    'CREATE EXTENSION IF NOT EXISTS "pgcrypto"',
    """
    CREATE TABLE users (
        id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        email          VARCHAR(255) NOT NULL UNIQUE,
        password_hash  VARCHAR(255) NOT NULL,
        name           VARCHAR(255) NOT NULL,
        phone          VARCHAR(32),
        created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """,
    """
    CREATE TABLE products (
        id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        name        VARCHAR(255) NOT NULL,
        category    VARCHAR(100) NOT NULL,
        price       NUMERIC(10, 2) NOT NULL,
        image_url   TEXT,
        created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """,
    # GET /goods с фильтром по категории и цене
    "CREATE INDEX idx_products_category_price ON products (category, price)",
    """
    CREATE TABLE delivery_quotes (
        id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        region_key        VARCHAR(100) NOT NULL,
        weight_category   VARCHAR(50) NOT NULL,
        cost              NUMERIC(10, 2) NOT NULL,
        eta_days          INT NOT NULL,
        fetched_at        TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """,
    # Быстрый поиск последней котировки для региона (fallback при недоступности API)
    """
    CREATE INDEX idx_delivery_quotes_lookup
        ON delivery_quotes (region_key, weight_category, fetched_at DESC)
    """,
    """
    CREATE TABLE orders (
        id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id             UUID NOT NULL REFERENCES users(id),
        delivery_quote_id   UUID REFERENCES delivery_quotes(id),
        status              VARCHAR(50) NOT NULL DEFAULT 'created',
        delivery_type       VARCHAR(20) NOT NULL,
        address             TEXT,
        total_price         NUMERIC(10, 2) NOT NULL,
        created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """,
    # GET /orders: история заказов пользователя от новых к старым
    "CREATE INDEX idx_orders_user_created ON orders (user_id, created_at DESC)",
    """
    CREATE TABLE order_items (
        id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        order_id     UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
        product_id   UUID NOT NULL REFERENCES products(id),
        quantity     INT NOT NULL CHECK (quantity > 0),
        unit_price   NUMERIC(10, 2) NOT NULL
    )
    """,
    # JOIN при сборке состава заказа
    "CREATE INDEX idx_order_items_order ON order_items (order_id)",
]


def upgrade() -> None:
    for statement in UPGRADE_STATEMENTS:
        op.execute(statement)


def downgrade() -> None:
    for table in ("order_items", "orders", "delivery_quotes", "products", "users"):
        op.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
