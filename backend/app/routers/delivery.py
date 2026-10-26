from fastapi import APIRouter, Depends, Query

from ..delivery.service import DeliveryService, get_delivery_service
from ..schemas import DeliveryQuoteOut, WeightCategory

router = APIRouter(tags=["Доставка"])


@router.get("/delivery/quote", response_model=DeliveryQuoteOut,
            summary="Стоимость и срок доставки по адресу")
def delivery_quote(
    address: str = Query(min_length=3, examples=["Санкт-Петербург, Невский пр., 1"]),
    weight_category: WeightCategory = "medium",
    service: DeliveryService = Depends(get_delivery_service),
):
    quote, source = service.get_quote(address, weight_category)
    return DeliveryQuoteOut(
        cost=quote.cost,
        eta_days=quote.eta_days,
        approximate=quote.approximate or source == "fallback",
        source=source,
    )
