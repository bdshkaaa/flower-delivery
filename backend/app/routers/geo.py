from fastapi import APIRouter, Depends, HTTPException, Query, status

from ..delivery.base import BadAddressError, ProviderError
from ..delivery.geocoder import NominatimGeocoder, get_geocoder
from ..schemas import ErrorResponse, GeoPlace

router = APIRouter(tags=["Карта и адреса"], prefix="/geo",
                   responses={503: {"model": ErrorResponse}})

UNAVAILABLE = "Сервис карт временно недоступен. Введите адрес вручную."


def _place(p) -> GeoPlace:
    return GeoPlace(label=p.label, lat=p.lat, lon=p.lon, country_code=p.country_code)


@router.get("/search", response_model=list[GeoPlace], summary="Поиск адреса по тексту")
def search(
    q: str = Query(min_length=3, max_length=200, examples=["Казань, Баумана 1"]),
    limit: int = Query(default=5, ge=1, le=8),
    geocoder: NominatimGeocoder = Depends(get_geocoder),
):
    """Вызывается по явному действию пользователя (кнопка «Найти»), не при каждой букве."""
    try:
        return [_place(p) for p in geocoder.search(q, limit)]
    except ProviderError:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, UNAVAILABLE)


@router.get("/reverse", response_model=GeoPlace, responses={404: {"model": ErrorResponse}},
            summary="Адрес по точке на карте")
def reverse(
    lat: float = Query(ge=-90, le=90),
    lon: float = Query(ge=-180, le=180),
    geocoder: NominatimGeocoder = Depends(get_geocoder),
):
    try:
        return _place(geocoder.reverse(lat, lon))
    except BadAddressError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "В этой точке нет адреса. Выберите место на суше.")
    except ProviderError:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, UNAVAILABLE)
