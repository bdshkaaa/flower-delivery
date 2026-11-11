"""Симулятор оплаты: проверка карты без БД и без сети."""
from datetime import datetime, timezone

import pytest

from app.payments import DECLINED_TEST_CARD, PaymentError, luhn_valid, process

NOW = datetime(2026, 11, 11, tzinfo=timezone.utc)


def pay(card="4242 4242 4242 4242", expiry="12/30", cvc="123"):
    return process("card", card, expiry, cvc, now=NOW)


def test_luhn_checksum():
    assert luhn_valid("4242424242424242")
    assert luhn_valid(DECLINED_TEST_CARD)
    assert not luhn_valid("4242424242424241")


def test_valid_card_and_sbp_succeed():
    assert pay() is None
    assert process("sbp") is None  # СБП данных карты не требует


def test_card_number_with_typo_is_rejected_as_invalid_data():
    with pytest.raises(PaymentError) as err:
        pay(card="4242 4242 4242 4241")
    assert err.value.status_code == 422


def test_short_or_empty_card_number_is_rejected():
    for card in ("", "4242", "abcd"):
        with pytest.raises(PaymentError) as err:
            pay(card=card)
        assert err.value.status_code == 422


def test_expired_card_is_rejected_but_current_month_is_fine():
    with pytest.raises(PaymentError) as err:
        pay(expiry="10/26")
    assert "истёк" in err.value.message
    assert pay(expiry="11/26") is None  # срок действует до конца месяца
    assert pay(expiry="11/2026") is None


@pytest.mark.parametrize("expiry", ["", "1226", "13/30", "00/30", "ab/cd", "12/3"])
def test_malformed_expiry_is_rejected(expiry):
    with pytest.raises(PaymentError) as err:
        pay(expiry=expiry)
    assert err.value.status_code == 422


@pytest.mark.parametrize("cvc", ["", "12", "1234", "abc"])
def test_cvc_must_be_three_digits(cvc):
    with pytest.raises(PaymentError) as err:
        pay(cvc=cvc)
    assert err.value.status_code == 422


def test_declined_test_card_is_refused_by_the_bank_not_by_validation():
    with pytest.raises(PaymentError) as err:
        pay(card=DECLINED_TEST_CARD)
    assert err.value.status_code == 402
    assert "недостаточно средств" in err.value.message
