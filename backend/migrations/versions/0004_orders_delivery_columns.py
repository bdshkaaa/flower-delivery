"""Заказы: стоимость доставки и признак «предварительная» хранятся в самом заказе

Revision ID: 0004
Revises: 0003
"""
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE orders ADD COLUMN delivery_cost NUMERIC(10, 2) NOT NULL DEFAULT 0")
    op.execute("ALTER TABLE orders ADD COLUMN delivery_approximate BOOLEAN NOT NULL DEFAULT FALSE")


def downgrade() -> None:
    op.execute("ALTER TABLE orders DROP COLUMN delivery_approximate")
    op.execute("ALTER TABLE orders DROP COLUMN delivery_cost")
