import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    database_url: str
    log_level: str
    # Провайдер расчёта доставки: "mock" (по умолчанию) или "yandex"
    delivery_provider: str
    # Жёсткий таймаут на запрос к внешнему API доставки, секунды (см. README, «Отказоустойчивость»)
    delivery_timeout_seconds: float
    yandex_delivery_token: str
    yandex_delivery_base_url: str
    # Координаты точки отправления (магазина), долгота и широта
    shop_lon: float
    shop_lat: float


def load_settings() -> Settings:
    return Settings(
        database_url=os.environ.get(
            "DATABASE_URL",
            "postgresql+psycopg://flower:flower@localhost:5432/flower_delivery",
        ),
        log_level=os.environ.get("LOG_LEVEL", "INFO"),
        delivery_provider=os.environ.get("DELIVERY_PROVIDER", "mock"),
        delivery_timeout_seconds=float(os.environ.get("DELIVERY_TIMEOUT_SECONDS", "3")),
        yandex_delivery_token=os.environ.get("YANDEX_DELIVERY_TOKEN", ""),
        yandex_delivery_base_url=os.environ.get(
            "YANDEX_DELIVERY_BASE_URL", "https://b2b.taxi.yandex.net"
        ),
        shop_lon=float(os.environ.get("SHOP_LON", "30.3141")),
        shop_lat=float(os.environ.get("SHOP_LAT", "59.9386")),
    )


settings = load_settings()
