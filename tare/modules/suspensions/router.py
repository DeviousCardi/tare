"""Routes for suspensions."""

from fastapi import APIRouter, Query

from tare.common.deps import TheOperator, TheStore
from tare.modules.suspensions.schemas import (
    ListSuspensions, LiftSuspension, SuspendDeduction, SuspensionOut,
)
from tare.modules.suspensions.service import SuspensionsService

router = APIRouter(prefix="/suspensions", tags=["suspensions"])


@router.get("")
def list_suspensions(
    operator: TheOperator, store: TheStore,
    employee_id: str | None = Query(default=None),
    element_id: str | None = Query(default=None),
    open_only: bool = Query(default=False),
    limit: int | None = Query(default=None),
    offset: int | None = Query(default=None),
) -> dict:
    answer = SuspensionsService(store).list(operator, ListSuspensions(
        employee_id=employee_id, element_id=element_id, open_only=open_only,
        limit=limit, offset=offset))
    return {"data": [SuspensionOut.of(row) for row in answer["data"]],
            "total": answer["total"]}


@router.get("/held-off/{employee_id}")
def held_off(
    employee_id: str, period: int, year_starts_on: str,
    operator: TheOperator, store: TheStore,
) -> dict:
    return {"employee_id": employee_id, "period": period,
            "elements": SuspensionsService(store).held_off(
                operator, employee_id, period, year_starts_on)}


@router.get("/{suspension_id}")
def get_suspension(
    suspension_id: str, operator: TheOperator, store: TheStore,
) -> SuspensionOut:
    return SuspensionOut.of(SuspensionsService(store).get(operator, suspension_id))


@router.post("", status_code=201)
def suspend_deduction(
    dto: SuspendDeduction, operator: TheOperator, store: TheStore,
) -> SuspensionOut:
    return SuspensionOut.of(SuspensionsService(store).suspend(operator, dto))


@router.post("/{suspension_id}/lift")
def lift_suspension(
    suspension_id: str, dto: LiftSuspension, operator: TheOperator, store: TheStore,
) -> SuspensionOut:
    return SuspensionOut.of(SuspensionsService(store).lift(operator, suspension_id, dto))
