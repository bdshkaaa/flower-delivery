from uuid import UUID

import jwt
from fastapi import APIRouter, Header, HTTPException, Response, status

from .. import users
from ..schemas import ErrorResponse, LoginRequest, RegisterRequest, TokenResponse, UserOut
from ..security import create_access_token, decode_access_token, hash_password, verify_password

router = APIRouter(tags=["Авторизация"])

# Хеш для сравнения, когда пользователя с таким email нет: время ответа
# не должно выдавать, зарегистрирован ли адрес
_DUMMY_HASH = hash_password("dummy-password")


def require_user(authorization: str | None = Header(default=None)) -> UUID:
    """Проверяет заголовок Authorization: Bearer <JWT> и возвращает id пользователя."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Требуется вход в аккаунт")
    try:
        return decode_access_token(authorization.removeprefix("Bearer "))
    except (jwt.InvalidTokenError, ValueError, KeyError):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Токен недействителен или истёк")


def _token_response(user: dict) -> TokenResponse:
    return TokenResponse(
        access_token=create_access_token(user["id"]),
        user=UserOut(id=user["id"], email=user["email"], name=user["name"]),
    )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED,
             responses={409: {"model": ErrorResponse}}, summary="Регистрация")
def register(body: RegisterRequest):
    try:
        user = users.create_user(body.email, hash_password(body.password), body.name.strip())
    except users.EmailAlreadyExists:
        raise HTTPException(status.HTTP_409_CONFLICT, "Пользователь с таким email уже существует")
    return _token_response(user)


@router.post("/login", response_model=TokenResponse,
             responses={401: {"model": ErrorResponse}}, summary="Вход")
def login(body: LoginRequest):
    user = users.get_by_email(body.email)
    password_hash = user["password_hash"] if user else _DUMMY_HASH
    if not verify_password(body.password, password_hash) or user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Неверный email или пароль")
    return _token_response(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT,
             responses={401: {"model": ErrorResponse}}, summary="Выход")
def logout(authorization: str | None = Header(default=None)):
    # JWT не хранится на сервере: «выход» = клиент удаляет токен.
    # Эндпоинт проверяет токен и подтверждает выход.
    require_user(authorization)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
