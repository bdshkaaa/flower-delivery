"""Варианты доставки: служба и тариф в котировках и в заказе

Revision ID: 0005
Revises: 0004
"""
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE delivery_quotes ADD COLUMN option_id VARCHAR(100)")
    op.execute("ALTER TABLE delivery_quotes ADD COLUMN service VARCHAR(150)")
    op.execute(
        "CREATE INDEX idx_delivery_quotes_option "
        "ON delivery_quotes (region_key, weight_category, option_id, fetched_at DESC)"
    )
    op.execute("ALTER TABLE orders ADD COLUMN delivery_service VARCHAR(150)")


def downgrade() -> None:
    op.execute("ALTER TABLE orders DROP COLUMN delivery_service")
    op.execute("DROP INDEX idx_delivery_quotes_option")
    op.execute("ALTER TABLE delivery_quotes DROP COLUMN service")
    op.execute("ALTER TABLE delivery_quotes DROP COLUMN option_id")
