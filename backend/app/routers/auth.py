from fastapi import APIRouter, Header, HTTPException, Response, status

from ..schemas import ErrorResponse, LoginRequest, RegisterRequest, TokenResponse, UserOut
from ..stubs import STUB_TOKEN, STUB_USER

router = APIRouter(tags=["Авторизация"])


def require_token(authorization: str | None = Header(default=None)) -> str:
    """Заглушка проверки токена: нужен заголовок Authorization: Bearer <токен>."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Требуется вход в аккаунт")
    return authorization.removeprefix("Bearer ")


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED,
             summary="Регистрация")
def register(body: RegisterRequest):
    user = {**STUB_USER, "email": body.email, "name": body.name}
    return TokenResponse(access_token=STUB_TOKEN, user=UserOut(**user))


@router.post("/login", response_model=TokenResponse,
             responses={401: {"model": ErrorResponse}}, summary="Вход")
def login(body: LoginRequest):
    # Заглушка: пароль «wrong» считается неверным, чтобы фронтенд мог показать ошибку
    if body.password == "wrong":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Неверный email или пароль")
    user = {**STUB_USER, "email": body.email}
    return TokenResponse(access_token=STUB_TOKEN, user=UserOut(**user))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT,
             responses={401: {"model": ErrorResponse}}, summary="Выход")
def logout(authorization: str | None = Header(default=None)):
    require_token(authorization)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
