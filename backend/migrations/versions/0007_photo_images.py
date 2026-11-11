"""Каталог переходит на фотографии букетов (.jpg вместо нарисованных .svg)

Файлы лежат во frontend/public/bouquets под теми же именами. Если фотографии для букета ещё нет,
фронтенд показывает прежнюю картинку (.svg), а затем заглушку.

Revision ID: 0007
Revises: 0006
"""
from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("UPDATE products SET image_url = replace(image_url, '.svg', '.jpg') WHERE image_url LIKE '/bouquets/%.svg'")


def downgrade() -> None:
    op.execute("UPDATE products SET image_url = replace(image_url, '.jpg', '.svg') WHERE image_url LIKE '/bouquets/%.jpg'")
