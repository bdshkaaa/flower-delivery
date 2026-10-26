"""seed products

Начальный ассортимент (12 букетов), чтобы каталог не был пустым.
Картинки лежат во frontend/public/bouquets и отдаются тем же сайтом.

Revision ID: 0003
Revises: 0002
"""
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

# (номер, название, повод, цена, популярность, описание)
PRODUCTS = [
    (1, "Нежность", "birthday", 2500, 120,
     "Розовые розы и эустома в крафтовой упаковке. Мягкий букет для близкого человека."),
    (2, "Алая роза", "anniversary", 4200, 200,
     "Одиннадцать красных роз с зеленью. Классика для важной даты."),
    (3, "Белое облако", "wedding", 6800, 75,
     "Белые розы, гортензия и гипсофила: воздушный букет для свадебной церемонии."),
    (4, "Полевой микс", "birthday", 1800, 310,
     "Яркая смесь сезонных цветов: ромашки, васильки и астры. Самый популярный выбор."),
    (5, "Пионы", "anniversary", 5400, 150,
     "Девять пышных розовых пионов. Сезонный букет, его аромат запоминается надолго."),
    (6, "Солнечный день", "birthday", 2200, 260,
     "Подсолнухи и хлопок. Поднимает настроение даже в пасмурную погоду."),
    (7, "Лавандовое поле", "thanks", 1900, 90,
     "Лаванда и эвкалипт: спокойный аромат и тёплое «спасибо»."),
    (8, "Весенние тюльпаны", "thanks", 2100, 180,
     "Пятнадцать разноцветных тюльпанов, завязанных лентой."),
    (9, "Королевский", "wedding", 9500, 40,
     "Крупные белые и кремовые розы, орхидеи и зелень. Для особенного торжества."),
    (10, "Розовый рассвет", "love", 3600, 140,
     "Розовые розы и пионовидные кустовые розы. Нежное признание."),
    (11, "Букет невесты", "wedding", 7200, 65,
     "Каскадный букет из белых роз, фрезий и мелких веточек зелени."),
    (12, "Страсть", "love", 11900, 55,
     "Пятьдесят одна алая роза. Слова будут лишними."),
]


def _uuid(number: int) -> str:
    return f"00000000-0000-4000-8000-{number:012d}"


def _quote(value: str) -> str:
    return value.replace("'", "''")


SLUGS = {
    1: "nezhnost", 2: "alaya-roza", 3: "beloe-oblako", 4: "polevoj-miks",
    5: "piony", 6: "solnechnyj-den", 7: "lavandovoe-pole", 8: "vesennie-tyulpany",
    9: "korolevskij", 10: "rozovyj-rassvet", 11: "buket-nevesty", 12: "strast",
}


def upgrade() -> None:
    for number, name, category, price, popularity, description in PRODUCTS:
        op.execute(
            "INSERT INTO products (id, name, category, price, image_url, description, popularity) "
            f"VALUES ('{_uuid(number)}', '{_quote(name)}', '{category}', {price}, "
            f"'/bouquets/{SLUGS[number]}.svg', '{_quote(description)}', {popularity}) "
            "ON CONFLICT (id) DO NOTHING"
        )


def downgrade() -> None:
    for number, *_ in PRODUCTS:
        op.execute(f"DELETE FROM products WHERE id = '{_uuid(number)}'")
