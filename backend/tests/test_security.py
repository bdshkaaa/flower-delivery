"""Unit-тесты хеширования паролей и JWT (без БД)."""
from uuid import uuid4

import jwt
import pytest

from app.config import settings
from app.security import (
    ALGORITHM,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_password_hash_is_not_plaintext_and_verifies():
    hashed = hash_password("secret123")

    assert "secret123" not in hashed
    assert verify_password("secret123", hashed)
    assert not verify_password("secret124", hashed)


def test_same_password_gives_different_hashes():
    assert hash_password("secret123") != hash_password("secret123")


def test_very_long_cyrillic_password_is_supported():
    password = "пароль" * 40  # много больше лимита bcrypt в 72 байта
    hashed = hash_password(password)

    assert verify_password(password, hashed)
    assert not verify_password(password + "!", hashed)


def test_token_roundtrip_returns_user_id():
    user_id = uuid4()

    assert decode_access_token(create_access_token(user_id)) == user_id


def test_expired_token_is_rejected():
    token = create_access_token(uuid4(), expires_minutes=-1)

    with pytest.raises(jwt.ExpiredSignatureError):
        decode_access_token(token)


def test_token_signed_with_other_secret_is_rejected():
    forged = jwt.encode({"sub": str(uuid4())}, "another-secret-" * 3, algorithm=ALGORITHM)

    with pytest.raises(jwt.InvalidTokenError):
        decode_access_token(forged)


def test_default_secret_is_long_enough_for_hs256():
    assert len(settings.jwt_secret) >= 32
