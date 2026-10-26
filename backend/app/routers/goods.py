from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from .. import catalog
from ..schemas import ErrorResponse, Product, ProductList, SortOrder

router = APIRouter(tags=["Каталог"])


@router.get("/goods", response_model=ProductList, summary="Список букетов")
def list_goods(
    category: str | None = Query(default=None, description="Повод: birthday, anniversary, wedding, thanks, love"),
    price_min: Decimal | None = Query(default=None, ge=0),
    price_max: Decimal | None = Query(default=None, ge=0),
    sort: SortOrder = Query(default="popularity"),
):
    rows = catalog.list_products(category, price_min, price_max, sort)
    return ProductList(items=[Product(**row) for row in rows], total=len(rows))


@router.get("/goods/{product_id}", response_model=Product,
            responses={404: {"model": ErrorResponse}}, summary="Карточка букета")
def get_good(product_id: UUID):
    row = catalog.get_product(product_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Товар не найден")
    return Product(**row)
