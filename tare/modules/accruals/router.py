"""Routes for accruals."""

from fastapi import APIRouter, Query

from tare.common.deps import TheOperator, TheStore
from tare.modules.accruals.schemas import (
    AccrualOut, EarnedOut, ListAccruals, RecordAccrual,
)
from tare.modules.accruals.service import AccrualsService

router = APIRouter(prefix="/accruals", tags=["accruals"])


@router.get("")
def list_accruals(
    operator: TheOperator, store: TheStore,
    employee_id: str | None = Query(default=None),
    year_starts_on: str | None = Query(default=None),
    limit: int | None = Query(default=None),
    offset: int | None = Query(default=None),
) -> dict:
    answer = AccrualsService(store).list(operator, ListAccruals(
        employee_id=employee_id, year_starts_on=year_starts_on,
        limit=limit, offset=offset))
    return {"data": [AccrualOut.of(row) for row in answer["data"]],
            "total": answer["total"]}


@router.get("/earned/{employee_id}")
def earned(
    employee_id: str, year_starts_on: str, operator: TheOperator, store: TheStore,
) -> EarnedOut:
    return EarnedOut(**AccrualsService(store).earned(
        operator, employee_id, year_starts_on))


@router.get("/{accrual_id}")
def get_accrual(accrual_id: str, operator: TheOperator, store: TheStore) -> AccrualOut:
    return AccrualOut.of(AccrualsService(store).get(operator, accrual_id))


@router.post("", status_code=201)
def record_accrual(
    dto: RecordAccrual, operator: TheOperator, store: TheStore,
) -> AccrualOut:
    return AccrualOut.of(AccrualsService(store).record(operator, dto))
