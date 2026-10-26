"""Регистрация, вход и выход на настоящей БД (запускаются в docker-compose)."""
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app

pytestmark = pytest.mark.integration

client = TestClient(app)


def _new_email() -> str:
    return f"user-{uuid4().hex[:12]}@example.com"


def _register(email: str, password: str = "secret123", name: str = "Анна"):
    return client.post("/register", json={"email": email, "password": password, "name": name})


def test_register_creates_user_and_returns_token():
    email = _new_email()

    response = _register(email)

    assert response.status_code == 201
    body = response.json()
    assert body["access_token"] and body["token_type"] == "bearer"
    assert body["user"]["email"] == email
    assert body["user"]["name"] == "Анна"


def test_register_same_email_twice_is_409_case_insensitive():
    email = _new_email()
    assert _register(email).status_code == 201

    response = _register(email.upper())

    assert response.status_code == 409


def test_register_validates_input():
    assert _register("not-an-email").status_code == 422
    assert _register(_new_email(), password="123").status_code == 422


def test_login_with_correct_password():
    email = _new_email()
    _register(email, password="secret123")

    response = client.post("/login", json={"email": email, "password": "secret123"})

    assert response.status_code == 200
    assert response.json()["user"]["email"] == email


def test_login_wrong_password_and_unknown_user_give_same_error():
    email = _new_email()
    _register(email, password="secret123")

    wrong = client.post("/login", json={"email": email, "password": "wrong-password"})
    unknown = client.post("/login", json={"email": _new_email(), "password": "secret123"})

    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()


def test_password_is_stored_hashed():
    from sqlalchemy import text

    from app.db import engine

    email = _new_email()
    _register(email, password="secret123")

    with engine.connect() as conn:
        stored = conn.execute(
            text("SELECT password_hash FROM users WHERE email = :e"), {"e": email}
        ).scalar_one()

    assert stored != "secret123" and stored.startswith("$2")


def test_token_gives_access_to_orders_and_logout_works():
    token = _register(_new_email()).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    assert client.get("/orders", headers=headers).status_code == 200
    assert client.post("/logout", headers=headers).status_code == 204


def test_orders_reject_missing_and_garbage_token():
    assert client.get("/orders").status_code == 401
    assert client.get("/orders", headers={"Authorization": "Bearer garbage"}).status_code == 401
