import logging
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from .. import catalog, orders
from ..delivery.service import DeliveryService, get_delivery_service
from ..schemas import ErrorResponse, OrderCreate, OrderOut
from .auth import require_user

logger = logging.getLogger("app.orders")

router = APIRouter(tags=["Заказы"], dependencies=[Depends(require_user)],
                   responses={401: {"model": ErrorResponse}})


def weight_category_for(total_quantity: int) -> str:
    """Весовая категория заказа для расчёта доставки: 1 букет — light, 2–3 — medium, 4+ — heavy."""
    if total_quantity <= 1:
        return "light"
    return "medium" if total_quantity <= 3 else "heavy"


@router.post("/orders", response_model=OrderOut, status_code=status.HTTP_201_CREATED,
             responses={404: {"model": ErrorResponse}}, summary="Создать заказ")
def create_order(
    body: OrderCreate,
    user_id: UUID = Depends(require_user),
    delivery: DeliveryService = Depends(get_delivery_service),
):
    items = []
    for item in body.items:
        product = catalog.get_product(item.product_id)
        if product is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"Товар {item.product_id} не найден")
        items.append({"product_id": product["id"], "quantity": item.quantity,
                      "unit_price": product["price"]})

    delivery_cost, approximate, service_name = Decimal("0"), False, None
    if body.delivery_type == "delivery":
        result = delivery.get_options(
            body.address, weight_category_for(sum(i["quantity"] for i in items)), body.lat, body.lon)
        if not result.available:
            raise HTTPException(422, result.reason)
        chosen = result.options[0]  # самый дешёвый, если вариант не указан
        if body.delivery_option_id:
            chosen = next((o for o in result.options if o.id == body.delivery_option_id), None)
            if chosen is None:
                raise HTTPException(
                    status.HTTP_409_CONFLICT,
                    "Выбранный вариант доставки больше недоступен. Обновите расчёт и выберите заново.")
        # Цену берём только у сервера: стоимость от клиента не принимается
        delivery_cost, service_name = chosen.cost, chosen.service
        approximate = chosen.approximate or result.source == "fallback"
        if approximate:
            logger.warning("order created with approximate delivery cost (source=%s)", result.source)

    order_id = orders.create_order(user_id, body.delivery_type, body.address, items,
                                   delivery_cost, approximate, service_name)
    return orders.get_order(user_id, order_id)


@router.get("/orders", response_model=list[OrderOut], summary="История заказов")
def list_orders(user_id: UUID = Depends(require_user)):
    return orders.list_orders(user_id)
