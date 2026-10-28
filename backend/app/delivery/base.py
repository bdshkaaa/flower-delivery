from dataclasses import dataclass
from decimal import Decimal
from typing import Optional, Protocol

# Допустимые весовые категории букета (используются как часть ключа кэша котировок)
WEIGHT_CATEGORIES = ("light", "medium", "heavy")


class ProviderError(Exception):
    """Внешний сервис доставки недоступен или вернул неожиданный ответ.

    Именно это исключение считает Circuit Breaker (ещё не реализован —
    первая задача для backend после скелета)."""


class NotServiceable(Exception):
    """Служба работает, но по этому адресу доставить не может (другая страна, вне зоны).
    Это не сбой: Circuit Breaker её не считает, а пользователь видит «доставка недоступна»."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class BadAddressError(ProviderError):
    """Адрес не найден. Это ошибка ввода покупателя, а не сбой сервиса,
    поэтому Circuit Breaker её не считает."""


@dataclass(frozen=True)
class Destination:
    """Куда везём. region_key — ключ региона для кэша котировок (например, «spb»),
    lon/lat нужны только провайдерам, которые считают по координатам."""

    region_key: str
    address: str = ""
    lon: Optional[float] = None
    lat: Optional[float] = None


@dataclass(frozen=True)
class DeliveryQuote:
    cost: Decimal
    eta_days: int
    # True, если это не живой ответ API, а кэш или фиксированный тариф
    approximate: bool = False


@dataclass(frozen=True)
class DeliveryOption:
    """Один вариант доставки, который видит покупатель."""

    id: str  # «служба:тариф», например «courier:express»; по нему заказ находит выбранный вариант
    service: str  # название для интерфейса
    cost: Decimal
    eta_days: int
    eta_hours: Optional[int] = None  # для доставки в день заказа («за 3 часа»)
    approximate: bool = False


class OptionsProvider(Protocol):
    """Служба доставки: по адресу возвращает один или несколько вариантов."""

    id: str

    def get_options(self, destination: "Destination", weight_category: str) -> list[DeliveryOption]:
        """Бросает ProviderError (сбой), BadAddressError (адрес не найден) или NotServiceable."""
        ...


class DeliveryProvider(Protocol):
    def get_quote(self, destination: Destination, weight_category: str) -> DeliveryQuote:
        """Вернуть стоимость и срок доставки или бросить ProviderError."""
        ...
