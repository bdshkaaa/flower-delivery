from ..config import Settings
from .base import DeliveryProvider
from .mock import MockDeliveryProvider
from .yandex import YandexDeliveryProvider


def get_provider(settings: Settings) -> DeliveryProvider:
    """Выбор провайдера по переменной окружения DELIVERY_PROVIDER."""
    if settings.delivery_provider == "yandex":
        return YandexDeliveryProvider(
            token=settings.yandex_delivery_token,
            base_url=settings.yandex_delivery_base_url,
            shop_lon=settings.shop_lon,
            shop_lat=settings.shop_lat,
            timeout_seconds=settings.delivery_timeout_seconds,
        )
    return MockDeliveryProvider()
