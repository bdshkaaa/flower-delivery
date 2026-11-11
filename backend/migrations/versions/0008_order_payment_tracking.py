"""Оплата и отслеживание заказа: номер, время оплаты, способ оплаты, срок доставки в минутах

Revision ID: 0008
Revises: 0007
"""
from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Короткий номер заказа для покупателя («Заказ №1001»); у старых заказов номера проставятся сами
    op.execute("ALTER TABLE orders ADD COLUMN number BIGINT GENERATED ALWAYS AS IDENTITY (START WITH 1001)")
    op.execute("CREATE UNIQUE INDEX idx_orders_number ON orders (number)")
    op.execute("ALTER TABLE orders ADD COLUMN paid_at TIMESTAMPTZ")
    op.execute("ALTER TABLE orders ADD COLUMN payment_method VARCHAR(20)")
    # Срок доставки (или готовности к выдаче) в минутах: от него считается таймер на странице заказа
    op.execute("ALTER TABLE orders ADD COLUMN eta_minutes INT")


def downgrade() -> None:
    op.execute("ALTER TABLE orders DROP COLUMN eta_minutes")
    op.execute("ALTER TABLE orders DROP COLUMN payment_method")
    op.execute("ALTER TABLE orders DROP COLUMN paid_at")
    op.execute("DROP INDEX idx_orders_number")
    op.execute("ALTER TABLE orders DROP COLUMN number")
