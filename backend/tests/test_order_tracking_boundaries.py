from datetime import datetime, timedelta, timezone

import pytest

from app.order_tracking import derive


PAID_AT = datetime(2026, 11, 11, 12, 0, tzinfo=timezone.utc)


@pytest.mark.parametrize(
    "elapsed_seconds, expected_status, expected_seconds_left",
    [
        (899, "assembling", 2701),
        (900, "shipping", 2700),
        (3599, "shipping", 1),
        (3600, "delivered", 0),
    ],
)
def test_delivery_status_at_exact_stage_boundaries(
    elapsed_seconds, expected_status, expected_seconds_left
):
    now = PAID_AT + timedelta(seconds=elapsed_seconds)

    tracking = derive("paid", PAID_AT, 60, "delivery", now)

    assert tracking.status == expected_status
    assert tracking.seconds_left == expected_seconds_left
    assert tracking.expected_at == PAID_AT + timedelta(hours=1)


def test_fractional_second_remaining_rounds_up_until_pickup_is_ready():
    now = PAID_AT + timedelta(minutes=45, milliseconds=-100)

    tracking = derive("paid", PAID_AT, 45, "pickup", now)

    assert tracking.status == "assembling"
    assert tracking.seconds_left == 1
