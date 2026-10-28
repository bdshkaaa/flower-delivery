"""Служба доставки с заранее заданным ответом для тестов сервиса."""
from decimal import Decimal

from app.delivery.base import DeliveryOption


def option(option_id="p:std", cost="400.00", days=1, service="Служба"):
    return DeliveryOption(option_id, service, Decimal(cost), days)


class ScriptedProvider:
    def __init__(self, provider_id, result=None):
        self.id = provider_id
        self.result = result if result is not None else [option(f"{provider_id}:std")]
        self.calls = 0

    def get_options(self, destination, weight_category):
        self.calls += 1
        if isinstance(self.result, Exception):
            raise self.result
        return self.result
