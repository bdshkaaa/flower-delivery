from fastapi import APIRouter, Query

from ..schemas import DeliveryQuoteOut, WeightCategory
from ..stubs import DELIVERY_COST

router = APIRouter(tags=["Доставка"])


@router.get("/delivery/quote", response_model=DeliveryQuoteOut,
            summary="Стоимость и срок доставки по адресу")
def delivery_quote(
    address: str = Query(min_length=3, examples=["Санкт-Петербург, Невский пр., 1"]),
    weight_category: WeightCategory = "medium",
):
    # Заглушка. Чтобы фронтенд мог проверить сценарий «API недоступен»,
    # адрес со словом "fallback" возвращает приблизительную стоимость.
    if "fallback" in address.lower():
        return DeliveryQuoteOut(cost=DELIVERY_COST, eta_days=2, approximate=True, source="fallback")
    return DeliveryQuoteOut(cost=DELIVERY_COST, eta_days=1, approximate=False, source="api")
