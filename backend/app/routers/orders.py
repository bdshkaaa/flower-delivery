from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status

from ..schemas import ErrorResponse, OrderCreate, OrderItemOut, OrderOut
from ..stubs import DELIVERY_COST, STUB_ORDERS, STUB_PRODUCTS, new_order_id, now
from .auth import require_token

router = APIRouter(tags=["Заказы"], dependencies=[Depends(require_token)],
                   responses={401: {"model": ErrorResponse}})


@router.post("/orders", response_model=OrderOut, status_code=status.HTTP_201_CREATED,
             responses={404: {"model": ErrorResponse}}, summary="Создать заказ")
def create_order(body: OrderCreate):
    products = {p["id"]: p for p in STUB_PRODUCTS}
    items: list[OrderItemOut] = []
    for item in body.items:
        product = products.get(item.product_id)
        if product is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"Товар {item.product_id} не найден")
        items.append(OrderItemOut(product_id=product["id"], name=product["name"],
                                  quantity=item.quantity, unit_price=product["price"]))

    delivery_cost = DELIVERY_COST if body.delivery_type == "delivery" else Decimal("0")
    total = sum((i.unit_price * i.quantity for i in items), Decimal("0")) + delivery_cost

    order = OrderOut(
        id=new_order_id(), status="created", created_at=now(),
        delivery_type=body.delivery_type, address=body.address, items=items,
        delivery_cost=delivery_cost, delivery_approximate=False, total_price=total,
    )
    STUB_ORDERS.append(order)
    return order


@router.get("/orders", response_model=list[OrderOut], summary="История заказов")
def list_orders():
    # От новых к старым
    return sorted(STUB_ORDERS, key=lambda o: o.created_at, reverse=True)
