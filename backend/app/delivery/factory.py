import logging

from ..config import Settings
from .base import OptionsProvider
from .cdek import CdekProvider
from .distance import DistanceDeliveryProvider
from .dostavista import DostavistaProvider
from .geocoder import NominatimGeocoder
from .mock import MockDeliveryProvider
from .yandex import YandexDeliveryProvider

logger = logging.getLogger("app.delivery.factory")


def build_providers(settings: Settings, geocoder: NominatimGeocoder | None = None) -> list[OptionsProvider]:
    """Службы доставки из переменной DELIVERY_PROVIDERS (через запятую):
    courier — курьер магазина (свой тариф по расстоянию, работает без ключей),
    yandex — Яндекс Доставка (нужен YANDEX_DELIVERY_TOKEN),
    dostavista — Достависта (нужен DOSTAVISTA_TOKEN),
    cdek — СДЭК (нужны CDEK_CLIENT_ID и CDEK_CLIENT_SECRET),
    mock — заглушка для тестов.
    Служба без ключей пропускается с предупреждением в логе."""
    geocoder = geocoder or NominatimGeocoder(timeout_seconds=settings.delivery_timeout_seconds)
    providers: list[OptionsProvider] = []
    for name in (n.strip().lower() for n in settings.delivery_providers.split(",")):
        if not name:
            continue
        try:
            if name == "courier":
                providers.append(DistanceDeliveryProvider(settings.shop_lon, settings.shop_lat, geocoder))
            elif name == "mock":
                providers.append(MockDeliveryProvider())
            elif name == "yandex":
                providers.append(YandexDeliveryProvider(
                    token=settings.yandex_delivery_token, base_url=settings.yandex_delivery_base_url,
                    shop_lon=settings.shop_lon, shop_lat=settings.shop_lat,
                    timeout_seconds=settings.delivery_timeout_seconds, geocoder=geocoder))
            elif name == "dostavista":
                providers.append(DostavistaProvider(
                    token=settings.dostavista_token, base_url=settings.dostavista_base_url,
                    shop_address=settings.shop_address, timeout_seconds=settings.delivery_timeout_seconds))
            elif name == "cdek":
                providers.append(CdekProvider(
                    client_id=settings.cdek_client_id, client_secret=settings.cdek_client_secret,
                    base_url=settings.cdek_base_url, from_code=settings.cdek_from_code,
                    timeout_seconds=settings.delivery_timeout_seconds))
            else:
                logger.warning("unknown delivery provider %r skipped", name)
        except ValueError as exc:
            logger.warning("delivery provider %r is disabled: %s", name, exc)
    if not providers:
        logger.warning("no delivery providers configured, using courier")
        providers.append(DistanceDeliveryProvider(settings.shop_lon, settings.shop_lat, geocoder))
    return providers
