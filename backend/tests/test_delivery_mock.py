from decimal import Decimal

import pytest

from app.delivery.base import Destination, ProviderError
from app.delivery.mock import MockDeliveryProvider

SPB = Destination(region_key="spb", address="Невский пр., 1")


def test_quote_depends_on_weight_category():
    provider = MockDeliveryProvider()

    light = provider.get_quote(SPB, "light")
    heavy = provider.get_quote(SPB, "heavy")

    assert light.cost == Decimal("300.00")
    assert heavy.cost > light.cost
    assert light.approximate is False


def test_failing_provider_raises_provider_error():
    provider = MockDeliveryProvider(failing=True)

    with pytest.raises(ProviderError):
        provider.get_quote(SPB, "light")


def test_unknown_weight_category_is_rejected():
    provider = MockDeliveryProvider()

    with pytest.raises(ValueError):
        provider.get_quote(SPB, "gigantic")
