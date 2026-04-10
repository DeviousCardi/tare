"""Routes for loan plans."""

from fastapi import APIRouter, Query

from tare.common.deps import TheOperator, TheStore
from tare.modules.loanplans.schemas import (
    CollectOnPlan, DueOut, ListPlans, PlanOut, SettlePlan, StartPlan,
)
from tare.modules.loanplans.service import LoanPlansService

router = APIRouter(prefix="/loan-plans", tags=["loan plans"])


@router.get("")
def list_plans(
    operator: TheOperator, store: TheStore,
    employee_id: str | None = Query(default=None),
    live_only: bool = Query(default=False),
    limit: int | None = Query(default=None),
    offset: int | None = Query(default=None),
) -> dict:
    answer = LoanPlansService(store).list(operator, ListPlans(
        employee_id=employee_id, live_only=live_only, limit=limit, offset=offset))
    return {"data": [PlanOut.of(row) for row in answer["data"]],
            "total": answer["total"]}


@router.get("/live/{employee_id}")
def live_plans(employee_id: str, operator: TheOperator, store: TheStore) -> dict:
    rows = LoanPlansService(store).live_for(operator, employee_id)
    return {"employee_id": employee_id,
            "data": [PlanOut.of(row) for row in rows], "total": len(rows)}


@router.get("/{plan_id}")
def get_plan(plan_id: str, operator: TheOperator, store: TheStore) -> PlanOut:
    return PlanOut.of(LoanPlansService(store).get(operator, plan_id))


@router.get("/{plan_id}/due")
def plan_due(plan_id: str, pay: int, operator: TheOperator, store: TheStore) -> DueOut:
    return DueOut(**LoanPlansService(store).due(operator, plan_id, pay))


@router.post("", status_code=201)
def start_plan(dto: StartPlan, operator: TheOperator, store: TheStore) -> PlanOut:
    return PlanOut.of(LoanPlansService(store).start(operator, dto))


@router.post("/{plan_id}/collect")
def collect_on_plan(
    plan_id: str, dto: CollectOnPlan, operator: TheOperator, store: TheStore,
) -> PlanOut:
    return PlanOut.of(LoanPlansService(store).collect(operator, plan_id, dto))


@router.post("/{plan_id}/settle")
def settle_plan(
    plan_id: str, dto: SettlePlan, operator: TheOperator, store: TheStore,
) -> PlanOut:
    return PlanOut.of(LoanPlansService(store).settle(operator, plan_id, dto))
