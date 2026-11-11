"""Этапы заказа после оплаты: чистая логика без БД."""
from datetime import datetime, timedelta, timezone

import pytest

from app.order_tracking import PICKUP_ETA_MINUTES, derive, eta_minutes_for

PAID = datetime(2026, 11, 11, 12, 0, tzinfo=timezone.utc)


def at(minutes: float) -> datetime:
    return PAID + timedelta(minutes=minutes)


def test_unpaid_order_has_no_timer():
    tracking = derive("created", None, 180, "delivery", at(5))
    assert tracking.status == "created" and tracking.seconds_left is None and tracking.expected_at is None


def test_cancelled_order_stays_cancelled():
    assert derive("cancelled", PAID, 180, "delivery", at(5)).status == "cancelled"


def test_delivery_goes_through_assembling_shipping_delivered():
    # доставка за 3 часа: сборка занимает 25% срока, но не больше 30 минут
    assert derive("paid", PAID, 180, "delivery", at(1)).status == "assembling"
    assert derive("paid", PAID, 180, "delivery", at(29)).status == "assembling"
    assert derive("paid", PAID, 180, "delivery", at(31)).status == "shipping"
    assert derive("paid", PAID, 180, "delivery", at(179)).status == "shipping"
    assert derive("paid", PAID, 180, "delivery", at(180)).status == "delivered"


def test_assembly_is_a_quarter_of_a_short_delivery():
    # доставка за час: сборка 15 минут
    assert derive("paid", PAID, 60, "delivery", at(14)).status == "assembling"
    assert derive("paid", PAID, 60, "delivery", at(16)).status == "shipping"


def test_seconds_left_counts_down_to_zero():
    tracking = derive("paid", PAID, 180, "delivery", at(60))
    assert tracking.seconds_left == 120 * 60
    assert tracking.expected_at == at(60) + timedelta(seconds=120 * 60)
    assert derive("paid", PAID, 180, "delivery", at(500)).seconds_left == 0


def test_multi_day_delivery_still_starts_with_short_assembly():
    day = 24 * 60
    assert derive("paid", PAID, day, "delivery", at(10)).status == "assembling"
    assert derive("paid", PAID, day, "delivery", at(40)).status == "shipping"
    assert derive("paid", PAID, day, "delivery", at(day - 1)).status == "shipping"


def test_pickup_is_assembled_then_ready():
    assert derive("paid", PAID, PICKUP_ETA_MINUTES, "pickup", at(1)).status == "assembling"
    assert derive("paid", PAID, PICKUP_ETA_MINUTES, "pickup", at(PICKUP_ETA_MINUTES - 1)).status == "assembling"
    assert derive("paid", PAID, PICKUP_ETA_MINUTES, "pickup", at(PICKUP_ETA_MINUTES)).status == "ready"


def test_time_scale_speeds_up_stages_but_timer_stays_in_real_seconds():
    # масштаб 60: одна реальная минута идёт как час. Через 1 реальную минуту прошёл час из трёх
    tracking = derive("paid", PAID, 180, "delivery", at(1), time_scale=60)
    assert tracking.status == "shipping"
    assert tracking.seconds_left == 2 * 60  # осталось два «часа» = две реальные минуты
    assert derive("paid", PAID, 180, "delivery", at(3), time_scale=60).status == "delivered"


def test_paid_in_the_future_does_not_break_the_timer():
    # рассинхрон часов: время оплаты чуть позже «сейчас», этап не уходит в минус
    tracking = derive("paid", at(2), 180, "delivery", PAID)
    assert tracking.status == "assembling" and tracking.seconds_left == 180 * 60


@pytest.mark.parametrize(
    "delivery_type, days, hours, expected",
    [
        ("pickup", None, None, PICKUP_ETA_MINUTES),
        ("delivery", 1, 3, 180),  # «за 3 часа» важнее, чем 1 день
        ("delivery", 2, None, 2 * 24 * 60),
        ("delivery", 0, None, 24 * 60),  # срок не бывает нулевым
        ("delivery", None, None, 24 * 60),
    ],
)
def test_eta_minutes_for(delivery_type, days, hours, expected):
    assert eta_minutes_for(delivery_type, days, hours) == expected
