"""Получатель и детали адреса в заказе: квартира, подъезд, этаж, домофон, комментарий курьеру

Revision ID: 0006
Revises: 0005
"""
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None

COLUMNS = [
    ("recipient_name", "VARCHAR(100)"),
    ("recipient_phone", "VARCHAR(20)"),
    ("private_house", "BOOLEAN NOT NULL DEFAULT FALSE"),
    ("apartment", "VARCHAR(20)"),
    ("entrance", "VARCHAR(10)"),
    ("floor", "VARCHAR(10)"),
    ("intercom", "VARCHAR(20)"),
    ("courier_comment", "VARCHAR(300)"),
]


def upgrade() -> None:
    for name, ddl in COLUMNS:
        op.execute(f"ALTER TABLE orders ADD COLUMN {name} {ddl}")


def downgrade() -> None:
    for name, _ in reversed(COLUMNS):
        op.execute(f"ALTER TABLE orders DROP COLUMN {name}")
