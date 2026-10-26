"""products: popularity and description

Колонка popularity нужна для сортировки каталога «по популярности»
(user story «Выбор букета», README этап 2). Пока это простое число,
которое позже можно обновлять по количеству заказов.

Revision ID: 0002
Revises: 0001
"""
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE products ADD COLUMN description TEXT")
    op.execute("ALTER TABLE products ADD COLUMN popularity INT NOT NULL DEFAULT 0")
    # Сортировка по популярности внутри повода
    op.execute("CREATE INDEX idx_products_popularity ON products (popularity DESC)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_products_popularity")
    op.execute("ALTER TABLE products DROP COLUMN IF EXISTS popularity")
    op.execute("ALTER TABLE products DROP COLUMN IF EXISTS description")
