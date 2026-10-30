
from fastapi import (
    APIRouter,
    HTTPException,
    Query,
)

from . import service

from .schema import (
    MfKpiResponse,
    MfRecommendationsResponse,
)


router = APIRouter(
    prefix="/mf",
    tags=["MF 추천"],
)


@router.get(
    "/kpi",
    response_model=MfKpiResponse,
)
def get_kpi():
    try:
        return service.get_kpi()

    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        ) from exc


@router.get(
    "/recommendations",
    response_model=MfRecommendationsResponse,
)
def get_recommendations(
    user_id: int = Query(..., ge=1),
):
    try:
        return service.get_recommendations(
            user_id
        )

    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        ) from exc

    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc
