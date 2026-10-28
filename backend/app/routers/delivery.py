from fastapi import APIRouter, Depends, HTTPException, Query, status

from ..delivery.service import DeliveryService, get_delivery_service
from ..schemas import DeliveryOptionOut, DeliveryOptionsOut, DeliveryQuoteOut, ErrorResponse, WeightCategory

router = APIRouter(tags=["Доставка"])


def _to_out(option) -> DeliveryOptionOut:
    return DeliveryOptionOut(
        id=option.id, service=option.service, cost=option.cost, eta_days=option.eta_days,
        eta_hours=option.eta_hours, approximate=option.approximate,
    )


@router.get("/delivery/options", response_model=DeliveryOptionsOut,
            summary="Варианты доставки от доступных служб")
def delivery_options(
    address: str = Query(min_length=3, examples=["Санкт-Петербург, Невский пр., 1"]),
    weight_category: WeightCategory = "medium",
    lat: float | None = Query(default=None, ge=-90, le=90, description="Точка на карте"),
    lon: float | None = Query(default=None, ge=-180, le=180),
    service: DeliveryService = Depends(get_delivery_service),
):
    result = service.get_options(address, weight_category, lat, lon)
    return DeliveryOptionsOut(
        available=result.available, reason=result.reason,
        options=[_to_out(o) for o in result.options], source=result.source,
    )


@router.get("/delivery/quote", response_model=DeliveryQuoteOut, responses={409: {"model": ErrorResponse}},
            summary="Самый дешёвый вариант доставки (упрощённый ответ)")
def delivery_quote(
    address: str = Query(min_length=3, examples=["Санкт-Петербург, Невский пр., 1"]),
    weight_category: WeightCategory = "medium",
    service: DeliveryService = Depends(get_delivery_service),
):
    result = service.get_options(address, weight_category)
    if not result.available:
        raise HTTPException(status.HTTP_409_CONFLICT, result.reason)
    cheapest = result.options[0]
    return DeliveryQuoteOut(
        cost=cheapest.cost, eta_days=cheapest.eta_days,
        approximate=cheapest.approximate or result.source == "fallback", source=result.source,
    )
