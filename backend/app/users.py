"""Работа с таблицей users."""
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from .db import engine


class EmailAlreadyExists(Exception):
    pass


def normalize_email(email: str) -> str:
    return email.strip().lower()


def create_user(email: str, password_hash: str, name: str) -> dict:
    try:
        with engine.begin() as conn:
            row = conn.execute(
                text(
                    "INSERT INTO users (email, password_hash, name) "
                    "VALUES (:email, :password_hash, :name) "
                    "RETURNING id, email, name"
                ),
                {"email": normalize_email(email), "password_hash": password_hash, "name": name},
            ).mappings().one()
    except IntegrityError as exc:
        raise EmailAlreadyExists from exc
    return dict(row)


def get_by_email(email: str) -> dict | None:
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT id, email, name, password_hash FROM users WHERE email = :email"),
            {"email": normalize_email(email)},
        ).mappings().first()
    return dict(row) if row else None


def get_by_id(user_id: UUID) -> dict | None:
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT id, email, name FROM users WHERE id = :id"), {"id": user_id}
        ).mappings().first()
    return dict(row) if row else None
