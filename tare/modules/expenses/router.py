"""Routes for expense claims."""

from fastapi import APIRouter, Query

from tare.common.deps import TheOperator, TheStore
from tare.modules.expenses.schemas import (
    ClaimOut, DecideClaim, ListClaims, MakeClaim, OwedOut,
)
from tare.modules.expenses.service import ExpensesService

router = APIRouter(prefix="/expenses", tags=["expenses"])


@router.get("")
def list_claims(
    operator: TheOperator, store: TheStore,
    employee_id: str | None = Query(default=None),
    status: str | None = Query(default=None),
    start: str | None = Query(default=None),
    end: str | None = Query(default=None),
    limit: int | None = Query(default=None),
    offset: int | None = Query(default=None),
) -> dict:
    answer = ExpensesService(store).list(operator, ListClaims(
        employee_id=employee_id, status=status, start=start, end=end,
        limit=limit, offset=offset))
    return {"data": [ClaimOut.of(row) for row in answer["data"]],
            "total": answer["total"]}


@router.get("/owed/{employee_id}")
def owed(employee_id: str, operator: TheOperator, store: TheStore) -> OwedOut:
    return OwedOut(**ExpensesService(store).owed(operator, employee_id))


@router.get("/{claim_id}")
def get_claim(claim_id: str, operator: TheOperator, store: TheStore) -> ClaimOut:
    return ClaimOut.of(ExpensesService(store).get(operator, claim_id))


@router.post("", status_code=201)
def make_claim(dto: MakeClaim, operator: TheOperator, store: TheStore) -> ClaimOut:
    return ClaimOut.of(ExpensesService(store).make(operator, dto))


@router.post("/{claim_id}/decide")
def decide_claim(
    claim_id: str, dto: DecideClaim, operator: TheOperator, store: TheStore,
) -> ClaimOut:
    return ClaimOut.of(ExpensesService(store).decide(operator, claim_id, dto))
