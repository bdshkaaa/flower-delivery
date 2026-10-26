from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from ..schemas import ErrorResponse, Product, ProductList, SortOrder
from ..stubs import STUB_PRODUCTS

router = APIRouter(tags=["Каталог"])


@router.get("/goods", response_model=ProductList, summary="Список букетов")
def list_goods(
    category: str | None = Query(default=None, description="Повод (birthday, wedding, ...)"),
    price_min: Decimal | None = Query(default=None, ge=0),
    price_max: Decimal | None = Query(default=None, ge=0),
    sort: SortOrder = Query(default="popularity"),
):
    items = list(STUB_PRODUCTS)
    if category:
        items = [p for p in items if p["category"] == category]
    if price_min is not None:
        items = [p for p in items if p["price"] >= price_min]
    if price_max is not None:
        items = [p for p in items if p["price"] <= price_max]

    if sort == "price_asc":
        items.sort(key=lambda p: p["price"])
    elif sort == "price_desc":
        items.sort(key=lambda p: p["price"], reverse=True)
    else:
        items.sort(key=lambda p: p["popularity"], reverse=True)

    return ProductList(items=[Product(**p) for p in items], total=len(items))


@router.get("/goods/{product_id}", response_model=Product,
            responses={404: {"model": ErrorResponse}}, summary="Карточка букета")
def get_good(product_id: UUID):
    for p in STUB_PRODUCTS:
        if p["id"] == product_id:
            return Product(**p)
    raise HTTPException(status.HTTP_404_NOT_FOUND, "Товар не найден")
