"""Routes for deduction instructions."""

from fastapi import APIRouter, Query

from tare.common.deps import TheOperator, TheStore
from tare.modules.deductions.schemas import (
    DeductionOut, InstructDeduction, ListDeductions, RunOut, StopDeduction,
)
from tare.modules.deductions.service import DeductionsService

router = APIRouter(prefix="/deductions", tags=["deductions"])


@router.get("")
def list_deductions(
    operator: TheOperator, store: TheStore,
    employee_id: str | None = Query(default=None),
    element_id: str | None = Query(default=None),
    due_in_period: int | None = Query(default=None),
    year_starts_on: str | None = Query(default=None),
    limit: int | None = Query(default=None),
    offset: int | None = Query(default=None),
) -> dict:
    answer = DeductionsService(store).list(operator, ListDeductions(
        employee_id=employee_id, element_id=element_id, due_in_period=due_in_period,
        year_starts_on=year_starts_on, limit=limit, offset=offset))
    return {"data": [DeductionOut.of(row) for row in answer["data"]],
            "total": answer["total"]}


@router.get("/run/{employee_id}")
def run_deductions(
    employee_id: str, period: int, year_starts_on: str, pay: int,
    operator: TheOperator, store: TheStore,
) -> RunOut:
    return RunOut(**DeductionsService(store).run(
        operator, employee_id, period, year_starts_on, pay))


@router.get("/{instruction_id}")
def get_deduction(
    instruction_id: str, operator: TheOperator, store: TheStore,
) -> DeductionOut:
    return DeductionOut.of(DeductionsService(store).get(operator, instruction_id))


@router.post("", status_code=201)
def instruct_deduction(
    dto: InstructDeduction, operator: TheOperator, store: TheStore,
) -> DeductionOut:
    return DeductionOut.of(DeductionsService(store).instruct(operator, dto))


@router.post("/{instruction_id}/stop")
def stop_deduction(
    instruction_id: str, dto: StopDeduction, operator: TheOperator, store: TheStore,
) -> DeductionOut:
    return DeductionOut.of(DeductionsService(store).stop(operator, instruction_id, dto))
