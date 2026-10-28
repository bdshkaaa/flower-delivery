import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    database_url: str
    log_level: str
    # Службы доставки через запятую: courier, yandex, cdek, mock (см. delivery/factory.py)
    delivery_providers: str
    # Жёсткий таймаут на запрос к внешнему API доставки, секунды (см. README, «Отказоустойчивость»)
    delivery_timeout_seconds: float
    # Кэш котировок (TTL) и Circuit Breaker
    delivery_cache_ttl_seconds: float
    delivery_breaker_threshold: int
    delivery_breaker_reset_seconds: float
    yandex_delivery_token: str
    cdek_client_id: str
    cdek_client_secret: str
    cdek_base_url: str
    # Код города отправления в справочнике СДЭК (137 — Санкт-Петербург)
    cdek_from_code: int
    yandex_delivery_base_url: str
    # Координаты точки отправления (магазина), долгота и широта
    shop_lon: float
    shop_lat: float
    # Радиус зоны доставки по дорогам от магазина, км (СПб и ближайшая Ленинградская область)
    delivery_radius_km: float
    # Подсказки адресов (Photon, на базе OpenStreetMap)
    photon_base_url: str
    # Секрет для подписи JWT. В продакшене обязательно задать свой через переменную окружения
    jwt_secret: str
    # Срок жизни токена доступа, минуты
    jwt_expire_minutes: int


def load_settings() -> Settings:
    return Settings(
        database_url=os.environ.get(
            "DATABASE_URL",
            "postgresql+psycopg://flower:flower@localhost:5432/flower_delivery",
        ),
        log_level=os.environ.get("LOG_LEVEL", "INFO"),
        delivery_providers=os.environ.get("DELIVERY_PROVIDERS", "courier"),
        delivery_timeout_seconds=float(os.environ.get("DELIVERY_TIMEOUT_SECONDS", "3")),
        delivery_cache_ttl_seconds=float(os.environ.get("DELIVERY_CACHE_TTL_SECONDS", "300")),
        delivery_breaker_threshold=int(os.environ.get("DELIVERY_BREAKER_THRESHOLD", "3")),
        delivery_breaker_reset_seconds=float(os.environ.get("DELIVERY_BREAKER_RESET_SECONDS", "30")),
        cdek_client_id=os.environ.get("CDEK_CLIENT_ID", ""),
        cdek_client_secret=os.environ.get("CDEK_CLIENT_SECRET", ""),
        cdek_base_url=os.environ.get("CDEK_BASE_URL", "https://api.cdek.ru"),
        cdek_from_code=int(os.environ.get("CDEK_FROM_CODE", "137")),
        yandex_delivery_token=os.environ.get("YANDEX_DELIVERY_TOKEN", ""),
        yandex_delivery_base_url=os.environ.get(
            "YANDEX_DELIVERY_BASE_URL", "https://b2b.taxi.yandex.net"
        ),
        # Магазин: Санкт-Петербург, Полюстровский проспект, 14А (координаты приблизительные)
        shop_lon=float(os.environ.get("SHOP_LON", "30.4150")),
        shop_lat=float(os.environ.get("SHOP_LAT", "59.9590")),
        delivery_radius_km=float(os.environ.get("DELIVERY_RADIUS_KM", "100")),
        photon_base_url=os.environ.get("PHOTON_BASE_URL", "https://photon.komoot.io"),
        jwt_secret=os.environ.get("JWT_SECRET", "dev-only-secret-change-me-in-production-0123456789"),
        jwt_expire_minutes=int(os.environ.get("JWT_EXPIRE_MINUTES", "1440")),
    )


settings = load_settings()
