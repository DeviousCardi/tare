"""Routes for carried balances."""

from fastapi import APIRouter, Query

from tare.common.deps import TheOperator, TheStore
from tare.modules.balances.schemas import (
    BalanceOut, ClearBalance, HoldOver, ListBalances,
)
from tare.modules.balances.service import BalancesService

router = APIRouter(prefix="/balances", tags=["balances"])


@router.get("")
def list_balances(
    operator: TheOperator, store: TheStore,
    employee_id: str | None = Query(default=None),
    element_id: str | None = Query(default=None),
    open_only: bool = Query(default=False),
    limit: int | None = Query(default=None),
    offset: int | None = Query(default=None),
) -> dict:
    answer = BalancesService(store).list(operator, ListBalances(
        employee_id=employee_id, element_id=element_id, open_only=open_only,
        limit=limit, offset=offset))
    return {"data": [BalanceOut.of(row) for row in answer["data"]],
            "total": answer["total"]}


@router.get("/open/{employee_id}")
def open_balances(employee_id: str, operator: TheOperator, store: TheStore) -> dict:
    rows = BalancesService(store).open_for(operator, employee_id)
    return {"employee_id": employee_id,
            "data": [BalanceOut.of(row) for row in rows], "total": len(rows)}


@router.get("/outstanding/{employee_id}")
def outstanding(
    employee_id: str, element_id: str, operator: TheOperator, store: TheStore,
) -> dict:
    return {"employee_id": employee_id, "element_id": element_id,
            "outstanding": BalancesService(store).outstanding(
                operator, employee_id, element_id)}


@router.get("/{balance_id}")
def get_balance(balance_id: str, operator: TheOperator, store: TheStore) -> BalanceOut:
    return BalanceOut.of(BalancesService(store).get(operator, balance_id))


@router.post("", status_code=201)
def hold_over(dto: HoldOver, operator: TheOperator, store: TheStore) -> BalanceOut:
    return BalanceOut.of(BalancesService(store).hold_over(operator, dto))


@router.post("/{balance_id}/clear")
def clear_balance(
    balance_id: str, dto: ClearBalance, operator: TheOperator, store: TheStore,
) -> BalanceOut:
    return BalanceOut.of(BalancesService(store).clear(operator, balance_id, dto))
