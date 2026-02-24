"""Routes for allowances."""

from fastapi import APIRouter, Query

from tare.common.deps import TheOperator, TheStore
from tare.modules.allowances.schemas import (
    AllowanceOut, AwardAllowance, EndAllowance, ListAllowances, StandingOut,
)
from tare.modules.allowances.service import AllowancesService

router = APIRouter(prefix="/allowances", tags=["allowances"])


@router.get("")
def list_allowances(
    operator: TheOperator, store: TheStore,
    employee_id: str | None = Query(default=None),
    element_id: str | None = Query(default=None),
    standing_on: str | None = Query(default=None),
    limit: int | None = Query(default=None),
    offset: int | None = Query(default=None),
) -> dict:
    answer = AllowancesService(store).list(operator, ListAllowances(
        employee_id=employee_id, element_id=element_id, standing_on=standing_on,
        limit=limit, offset=offset))
    return {"data": [AllowanceOut.of(row) for row in answer["data"]],
            "total": answer["total"]}


@router.get("/standing/{employee_id}")
def standing(
    employee_id: str, on: str, operator: TheOperator, store: TheStore,
) -> StandingOut:
    answer = AllowancesService(store).standing(operator, employee_id, on)
    return StandingOut(
        employee_id=answer["employee_id"], on=answer["on"],
        allowances=[AllowanceOut.of(row) for row in answer["allowances"]],
        comes_to=answer["comes_to"], by_element=answer["by_element"])


@router.get("/{allowance_id}")
def get_allowance(allowance_id: str, operator: TheOperator, store: TheStore) -> AllowanceOut:
    return AllowanceOut.of(AllowancesService(store).get(operator, allowance_id))


@router.post("", status_code=201)
def award_allowance(
    dto: AwardAllowance, operator: TheOperator, store: TheStore,
) -> AllowanceOut:
    return AllowanceOut.of(AllowancesService(store).award(operator, dto))


@router.post("/{allowance_id}/end")
def end_allowance(
    allowance_id: str, dto: EndAllowance, operator: TheOperator, store: TheStore,
) -> AllowanceOut:
    return AllowanceOut.of(AllowancesService(store).end(operator, allowance_id, dto))
