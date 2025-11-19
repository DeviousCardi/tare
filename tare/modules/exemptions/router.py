"""Routes for exemptions."""

from fastapi import APIRouter, Query

from tare.common.deps import TheOperator, TheStore
from tare.modules.exemptions.schemas import (
    EndExemption, ExemptionOut, GrantExemption, ListExemptions,
)
from tare.modules.exemptions.service import ExemptionsService

router = APIRouter(prefix="/exemptions", tags=["exemptions"])


@router.get("")
def list_exemptions(
    operator: TheOperator, store: TheStore,
    employee_id: str | None = Query(default=None),
    kind: str | None = Query(default=None),
    standing_on: str | None = Query(default=None),
    limit: int | None = Query(default=None),
    offset: int | None = Query(default=None),
) -> dict:
    answer = ExemptionsService(store).list(operator, ListExemptions(
        employee_id=employee_id, kind=kind, standing_on=standing_on,
        limit=limit, offset=offset))
    return {"data": [ExemptionOut.of(row) for row in answer["data"]],
            "total": answer["total"]}


@router.get("/standing/{employee_id}")
def standing(
    employee_id: str, on: str, operator: TheOperator, store: TheStore,
) -> dict:
    return {"employee_id": employee_id, "on": on,
            "kinds": ExemptionsService(store).standing(operator, employee_id, on)}


@router.get("/{exemption_id}")
def get_exemption(exemption_id: str, operator: TheOperator, store: TheStore) -> ExemptionOut:
    return ExemptionOut.of(ExemptionsService(store).get(operator, exemption_id))


@router.post("", status_code=201)
def grant_exemption(
    dto: GrantExemption, operator: TheOperator, store: TheStore,
) -> ExemptionOut:
    return ExemptionOut.of(ExemptionsService(store).grant(operator, dto))


@router.post("/{exemption_id}/end")
def end_exemption(
    exemption_id: str, dto: EndExemption, operator: TheOperator, store: TheStore,
) -> ExemptionOut:
    return ExemptionOut.of(ExemptionsService(store).end(operator, exemption_id, dto))
