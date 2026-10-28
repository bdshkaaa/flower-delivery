from fastapi import APIRouter, Depends, HTTPException, Query, status

from ..delivery.base import ProviderError
from ..delivery.geocoder import PhotonSuggester, get_suggester
from ..schemas import ErrorResponse, GeoPlace

router = APIRouter(tags=["Адреса"], prefix="/geo",
                   responses={503: {"model": ErrorResponse}})

UNAVAILABLE = "Подсказки адресов временно недоступны. Введите адрес полностью."


def _place(p) -> GeoPlace:
    return GeoPlace(label=p.label, lat=p.lat, lon=p.lon, country_code=p.country_code)


@router.get("/search", response_model=list[GeoPlace], summary="Подсказки адресов по мере набора")
def search(
    q: str = Query(min_length=3, max_length=200, examples=["Невский 1"]),
    limit: int = Query(default=5, ge=1, le=8),
    suggester: PhotonSuggester = Depends(get_suggester),
):
    """Подсказки только внутри зоны доставки (Санкт-Петербург и ближайшая Ленинградская область)."""
    try:
        return [_place(p) for p in suggester.search(q, limit)]
    except ProviderError:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, UNAVAILABLE)
