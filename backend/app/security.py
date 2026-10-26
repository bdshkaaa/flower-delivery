"""Хеширование паролей (bcrypt) и токены доступа (JWT)."""
import base64
import hashlib
from datetime import datetime, timedelta, timezone
from uuid import UUID

import bcrypt
import jwt

from .config import settings

ALGORITHM = "HS256"


def _prepare(password: str) -> bytes:
    # bcrypt принимает не больше 72 байт; SHA-256 + base64 даёт ровно 44 байта
    # для пароля любой длины и с любыми символами (в том числе кириллицей)
    return base64.b64encode(hashlib.sha256(password.encode("utf-8")).digest())


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_prepare(password), bcrypt.gensalt()).decode("ascii")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(_prepare(password), password_hash.encode("ascii"))


def create_access_token(user_id: UUID, expires_minutes: int | None = None) -> str:
    minutes = settings.jwt_expire_minutes if expires_minutes is None else expires_minutes
    payload = {
        "sub": str(user_id),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


def decode_access_token(token: str) -> UUID:
    """Возвращает id пользователя или бросает jwt.InvalidTokenError (в т.ч. при истёкшем сроке)."""
    payload = jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
    return UUID(payload["sub"])
