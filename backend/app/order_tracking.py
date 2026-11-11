"""Статус заказа после оплаты.

Настоящей службы доставки у нас нет, поэтому ход заказа имитируется по времени: в базе хранятся
только факты (оплачен, когда, за сколько минут обещана доставка), а текущий этап считается при
каждом запросе. Фоновых задач и планировщика не нужно, всё работает и при нескольких инстансах backend.

Этапы оплаченного заказа:
  доставка:   assembling (собирают) -> shipping (курьер в пути) -> delivered (доставлен)
  самовывоз:  assembling (собирают) -> ready (готов к выдаче)

Модуль не зависит от БД и FastAPI, поэтому покрыт обычными unit-тестами.
"""
import math
from dataclasses import dataclass
from datetime import datetime, timedelta

PICKUP_ETA_MINUTES = 45  # за столько минут собираем заказ для самовывоза
MAX_ASSEMBLY_SECONDS = 30 * 60  # сборка не дольше получаса, даже если доставка идёт несколько дней
ASSEMBLY_SHARE = 0.25  # доля срока, которую занимает сборка

FINAL_STATUSES = ("delivered", "ready", "cancelled")


@dataclass(frozen=True)
class Tracking:
    status: str
    seconds_left: int | None  # реальных секунд до готовности/доставки; None, пока заказ не оплачен
    expected_at: datetime | None


def eta_minutes_for(delivery_type: str, eta_days: int | None = None, eta_hours: int | None = None) -> int:
    """Срок в минутах: самовывоз — фиксированный, доставка — из выбранного варианта (часы или дни)."""
    if delivery_type == "pickup":
        return PICKUP_ETA_MINUTES
    if eta_hours:
        return eta_hours * 60
    return max(1, eta_days or 1) * 24 * 60


def assembly_seconds(total_seconds: float) -> float:
    return min(total_seconds * ASSEMBLY_SHARE, MAX_ASSEMBLY_SECONDS)


def derive(
    status: str,
    paid_at: datetime | None,
    eta_minutes: int | None,
    delivery_type: str,
    now: datetime,
    time_scale: float = 1.0,
) -> Tracking:
    """Текущий этап заказа.

    time_scale ускоряет время для демонстрации: при 60 одна реальная минута идёт как час.
    seconds_left всегда в реальных секундах, чтобы таймер на странице шёл в обычном темпе."""
    if status != "paid" or paid_at is None or not eta_minutes:
        return Tracking(status, None, None)

    scale = time_scale if time_scale > 0 else 1.0
    total = eta_minutes * 60
    elapsed = max(0.0, (now - paid_at).total_seconds()) * scale

    if elapsed >= total:
        return Tracking("ready" if delivery_type == "pickup" else "delivered", 0, now)

    if delivery_type == "pickup" or elapsed < assembly_seconds(total):
        stage = "assembling"
    else:
        stage = "shipping"
    seconds_left = math.ceil((total - elapsed) / scale)
    return Tracking(stage, seconds_left, now + timedelta(seconds=seconds_left))
