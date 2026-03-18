"""Routes for mandates."""

from fastapi import APIRouter, Query

from tare.common.deps import TheOperator, TheStore
from tare.modules.mandates.schemas import (
    EndMandate, ListMandates, MandateOut, SetMandate,
)
from tare.modules.mandates.service import MandatesService

router = APIRouter(prefix="/mandates", tags=["mandates"])


@router.get("")
def list_mandates(
    operator: TheOperator, store: TheStore,
    employee_id: str | None = Query(default=None),
    standing_on: str | None = Query(default=None),
    limit: int | None = Query(default=None),
    offset: int | None = Query(default=None),
) -> dict:
    answer = MandatesService(store).list(operator, ListMandates(
        employee_id=employee_id, standing_on=standing_on, limit=limit, offset=offset))
    return {"data": [MandateOut.of(row) for row in answer["data"]],
            "total": answer["total"]}


@router.get("/standing/{employee_id}")
def standing_mandate(
    employee_id: str, on: str, operator: TheOperator, store: TheStore,
) -> MandateOut:
    return MandateOut.of(MandatesService(store).standing(operator, employee_id, on))


@router.get("/{mandate_id}")
def get_mandate(mandate_id: str, operator: TheOperator, store: TheStore) -> MandateOut:
    return MandateOut.of(MandatesService(store).get(operator, mandate_id))


@router.post("", status_code=201)
def set_mandate(dto: SetMandate, operator: TheOperator, store: TheStore) -> MandateOut:
    return MandateOut.of(MandatesService(store).set(operator, dto))


@router.post("/{mandate_id}/end")
def end_mandate(
    mandate_id: str, dto: EndMandate, operator: TheOperator, store: TheStore,
) -> MandateOut:
    return MandateOut.of(MandatesService(store).end(operator, mandate_id, dto))
