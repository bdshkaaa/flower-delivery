"""Симулятор оплаты. Настоящих списаний нет и платёжного шлюза нет.

Номер карты проверяется как у настоящего эквайринга (длина, контрольная сумма Луна, срок действия),
но нигде не сохраняется и не пишется в логи: в базу попадает только способ оплаты.

Тестовые карты для проверки:
  4242 4242 4242 4242: платёж проходит
  4000 0000 0000 0002: банк отклоняет платёж (недостаточно средств)
Оплата через СБП всегда проходит."""
from datetime import datetime, timezone

DECLINED_TEST_CARD = "4000000000000002"


class PaymentError(Exception):
    """Платёж не прошёл. status_code: 422 — данные карты неверны, 402 — банк отказал."""

    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.message = message


def luhn_valid(digits: str) -> bool:
    total = 0
    for i, ch in enumerate(reversed(digits)):
        n = int(ch)
        if i % 2 == 1:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return total % 10 == 0


def _check_expiry(expiry: str, now: datetime) -> None:
    parts = expiry.replace(" ", "").split("/")
    if len(parts) != 2 or not all(p.isdigit() for p in parts) or len(parts[0]) != 2 or len(parts[1]) not in (2, 4):
        raise PaymentError(422, "Срок действия укажите в формате ММ/ГГ")
    month, year = int(parts[0]), int(parts[1])
    if year < 100:
        year += 2000
    if not 1 <= month <= 12:
        raise PaymentError(422, "Срок действия укажите в формате ММ/ГГ")
    if (year, month) < (now.year, now.month):
        raise PaymentError(422, "Срок действия карты истёк")


def process(
    method: str,
    card_number: str | None = None,
    expiry: str | None = None,
    cvc: str | None = None,
    now: datetime | None = None,
) -> None:
    """Проводит «платёж»: возвращает None при успехе или бросает PaymentError."""
    if method == "sbp":
        return
    now = now or datetime.now(timezone.utc)

    digits = "".join(ch for ch in (card_number or "") if ch.isdigit())
    if not 13 <= len(digits) <= 19 or not luhn_valid(digits):
        raise PaymentError(422, "Проверьте номер карты")
    _check_expiry(expiry or "", now)
    if not (cvc or "").isdigit() or len(cvc) != 3:
        raise PaymentError(422, "CVC — это три цифры на обратной стороне карты")
    if digits == DECLINED_TEST_CARD:
        raise PaymentError(402, "Банк отклонил платёж: недостаточно средств. Попробуйте другую карту.")
