"""Routes for pay scales."""

from fastapi import APIRouter, Query

from tare.common.deps import TheOperator, TheStore
from tare.modules.scales.schemas import (
    ArrearsOut, ListScalePoints, PublishScalePoint, ScalePointOut,
)
from tare.modules.scales.service import ScalesService

router = APIRouter(prefix="/scales", tags=["scales"])


@router.get("")
def list_scale_points(
    operator: TheOperator, store: TheStore,
    scale_code: str | None = Query(default=None),
    in_force_on: str | None = Query(default=None),
    limit: int | None = Query(default=None),
    offset: int | None = Query(default=None),
) -> dict:
    answer = ScalesService(store).list(operator, ListScalePoints(
        scale_code=scale_code, in_force_on=in_force_on, limit=limit, offset=offset))
    return {"data": [ScalePointOut.of(row) for row in answer["data"]],
            "total": answer["total"]}


@router.get("/{scale_code}/point/{point}")
def point_value(
    scale_code: str, point: int, on: str, operator: TheOperator, store: TheStore,
) -> dict:
    service = ScalesService(store)
    return {"scale_code": scale_code, "point": point, "on": on,
            "annual_salary": service.value(scale_code, point, on),
            "next_point": service.next_point(scale_code, point, on)}


@router.get("/{scale_code}/arrears/{point}")
def point_arrears(
    scale_code: str, point: int, was_on: str, now_on: str, days: int,
    operator: TheOperator, store: TheStore,
) -> ArrearsOut:
    return ArrearsOut(**ScalesService(store).arrears(
        scale_code, point, was_on, now_on, days))


@router.post("", status_code=201)
def publish_scale_point(
    dto: PublishScalePoint, operator: TheOperator, store: TheStore,
) -> ScalePointOut:
    return ScalePointOut.of(ScalesService(store).publish(operator, dto))
