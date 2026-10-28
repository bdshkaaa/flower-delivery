"""Схемы запросов и ответов API. Это и есть контракт: по ним FastAPI строит Swagger (/docs)."""
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, Field, PlainSerializer, field_validator, model_validator

# Деньги в БД хранятся как NUMERIC(10, 2), а в JSON отдаются обычным числом
Money = Annotated[
    Decimal, PlainSerializer(float, return_type=float, when_used="json")
]

SortOrder = Literal["popularity", "price_asc", "price_desc"]
WeightCategory = Literal["light", "medium", "heavy"]
DeliveryType = Literal["delivery", "pickup"]


class ErrorResponse(BaseModel):
    detail: str


# ---------- Авторизация ----------
EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


class RegisterRequest(BaseModel):
    email: str = Field(pattern=EMAIL_PATTERN, max_length=255, examples=["anna@example.com"])
    password: str = Field(min_length=6, max_length=128, examples=["secret123"])
    name: str = Field(min_length=1, max_length=255, examples=["Анна"])


class LoginRequest(BaseModel):
    email: str = Field(max_length=255, examples=["anna@example.com"])
    password: str = Field(max_length=128, examples=["secret123"])


class UserOut(BaseModel):
    id: UUID
    email: str
    name: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    user: UserOut


# ---------- Каталог ----------
class Product(BaseModel):
    id: UUID
    name: str
    category: str = Field(description="Повод: birthday, wedding, anniversary, ...")
    price: Money
    image_url: str | None = None
    description: str | None = None
    popularity: int = Field(description="Сколько раз букет заказывали (для сортировки)")


class ProductList(BaseModel):
    items: list[Product]
    total: int


# ---------- Доставка ----------
class DeliveryQuoteOut(BaseModel):
    cost: Money
    eta_days: int
    approximate: bool = Field(
        description="true — стоимость предварительная («будет уточнена»): "
        "внешний API недоступен, взят кэш или запасной тариф"
    )
    source: Literal["api", "cache", "fallback"]


class DeliveryOptionOut(BaseModel):
    id: str = Field(description="Идентификатор варианта «служба:тариф»; передаётся в POST /orders")
    service: str
    cost: Money
    eta_days: int
    eta_hours: int | None = Field(default=None, description="Срок в часах для доставки в день заказа")
    approximate: bool = False


class DeliveryOptionsOut(BaseModel):
    available: bool = Field(description="false — по адресу не доставляет ни одна служба")
    reason: str | None = Field(default=None, description="Причина, если доставка недоступна")
    options: list[DeliveryOptionOut]
    source: Literal["api", "cache", "fallback"]


class GeoPlace(BaseModel):
    label: str
    lat: float
    lon: float
    country_code: str | None = None
    precise: bool = Field(default=True, description="False: в адресе ещё нет номера дома")


# ---------- Заказы ----------
class OrderItemIn(BaseModel):
    product_id: UUID
    quantity: int = Field(gt=0, examples=[1])


class OrderCreate(BaseModel):
    items: list[OrderItemIn] = Field(min_length=1)
    delivery_type: DeliveryType
    address: str | None = Field(default=None, examples=["Санкт-Петербург, Невский пр., 1"])
    lat: float | None = Field(default=None, ge=-90, le=90, description="Точка на карте, если адрес выбран на карте")
    lon: float | None = Field(default=None, ge=-180, le=180)
    delivery_option_id: str | None = Field(
        default=None, description="Вариант доставки из GET /delivery/options; без него берётся самый дешёвый"
    )

    # Получатель и детали адреса, как в обычных приложениях доставки
    recipient_name: str | None = Field(default=None, max_length=100, examples=["Анна"])
    recipient_phone: str | None = Field(default=None, max_length=30, examples=["+7 900 123-45-67"])
    private_house: bool = Field(default=False, description="Частный дом: квартиру указывать не нужно")
    apartment: str | None = Field(default=None, max_length=20, examples=["12"])
    entrance: str | None = Field(default=None, max_length=10, examples=["2"])
    floor: str | None = Field(default=None, max_length=10, examples=["5"])
    intercom: str | None = Field(default=None, max_length=20, examples=["12К"])
    courier_comment: str | None = Field(default=None, max_length=300)

    @field_validator("recipient_name", "apartment", "entrance", "floor", "intercom", "courier_comment")
    @classmethod
    def strip_text(cls, value):
        value = (value or "").strip()
        return value or None

    @field_validator("recipient_phone")
    @classmethod
    def normalize_phone(cls, value):
        if not (value or "").strip():
            return None
        digits = "".join(ch for ch in value if ch.isdigit())
        if len(digits) == 11 and digits[0] in "78":
            digits = digits[1:]
        if len(digits) != 10:
            raise ValueError("Укажите телефон в формате +7 900 123-45-67")
        return f"+7{digits}"

    @model_validator(mode="after")
    def delivery_requires_details(self):
        if self.delivery_type == "delivery":
            if not (self.address or "").strip():
                raise ValueError("Для доставки нужен адрес")
            if not self.recipient_name or len(self.recipient_name) < 2:
                raise ValueError("Укажите имя получателя")
            if not self.recipient_phone:
                raise ValueError("Укажите телефон получателя")
            if not self.private_house and not self.apartment:
                raise ValueError("Укажите квартиру или отметьте «Частный дом»")
        return self


class OrderItemOut(BaseModel):
    product_id: UUID
    name: str
    quantity: int
    unit_price: Money


class OrderOut(BaseModel):
    id: UUID
    status: str
    created_at: datetime
    delivery_type: DeliveryType
    address: str | None
    recipient_name: str | None = None
    recipient_phone: str | None = None
    private_house: bool = False
    apartment: str | None = None
    entrance: str | None = None
    floor: str | None = None
    intercom: str | None = None
    courier_comment: str | None = None
    items: list[OrderItemOut]
    delivery_cost: Money
    delivery_service: str | None = None
    delivery_approximate: bool
    total_price: Money = Field(description="Букеты + доставка")
