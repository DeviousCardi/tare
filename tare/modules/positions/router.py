"""Routes for the posts people hold."""

from fastapi import APIRouter, Query

from tare.common.deps import TheOperator, TheStore
from tare.modules.positions.schemas import (
    AppointToPosition, EndPosition, ListPositions, PositionOut,
)
from tare.modules.positions.service import PositionsService

router = APIRouter(prefix="/positions", tags=["positions"])


@router.get("")
def list_positions(
    operator: TheOperator, store: TheStore,
    employee_id: str | None = Query(default=None),
    department_id: str | None = Query(default=None),
    cost_centre_id: str | None = Query(default=None),
    held_on: str | None = Query(default=None),
    limit: int | None = Query(default=None),
    offset: int | None = Query(default=None),
) -> dict:
    answer = PositionsService(store).list(operator, ListPositions(
        employee_id=employee_id, department_id=department_id,
        cost_centre_id=cost_centre_id, held_on=held_on, limit=limit, offset=offset))
    return {"data": [PositionOut.of(row) for row in answer["data"]],
            "total": answer["total"]}


@router.get("/headcount/{department_id}")
def department_headcount(
    department_id: str, on: str, operator: TheOperator, store: TheStore,
) -> dict:
    return {"department_id": department_id, "on": on,
            "headcount": PositionsService(store).headcount(operator, department_id, on)}


@router.get("/{position_id}")
def get_position(position_id: str, operator: TheOperator, store: TheStore) -> PositionOut:
    return PositionOut.of(PositionsService(store).get(operator, position_id))


@router.post("", status_code=201)
def appoint(dto: AppointToPosition, operator: TheOperator, store: TheStore) -> PositionOut:
    return PositionOut.of(PositionsService(store).appoint(operator, dto))


@router.post("/{position_id}/end")
def end_position(
    position_id: str, dto: EndPosition, operator: TheOperator, store: TheStore,
) -> PositionOut:
    return PositionOut.of(PositionsService(store).end(operator, position_id, dto))
