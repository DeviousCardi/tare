"""Routes for pay elements."""

from fastapi import APIRouter, Query
from pydantic import BaseModel

from tare.common.deps import TheOperator, TheStore
from tare.modules.elements.rules import Entry
from tare.modules.elements.schemas import (
    ChangeElement, DefineElement, ElementOut, EntryIn, ListElements, TotalsOut,
)
from tare.modules.elements.service import ElementsService

router = APIRouter(prefix="/elements", tags=["elements"])


class TotalsIn(BaseModel):
    employer_id: str
    entries: list[EntryIn]


@router.get("")
def list_elements(
    operator: TheOperator, store: TheStore,
    employer_id: str | None = Query(default=None),
    kind: str | None = Query(default=None),
    limit: int | None = Query(default=None),
    offset: int | None = Query(default=None),
) -> dict:
    answer = ElementsService(store).list(operator, ListElements(
        employer_id=employer_id, kind=kind, limit=limit, offset=offset))
    return {"data": [ElementOut.of(row) for row in answer["data"]],
            "total": answer["total"]}


@router.get("/{element_id}")
def get_element(element_id: str, operator: TheOperator, store: TheStore) -> ElementOut:
    return ElementOut.of(ElementsService(store).get(operator, element_id))


@router.post("", status_code=201)
def define_element(dto: DefineElement, operator: TheOperator, store: TheStore) -> ElementOut:
    return ElementOut.of(ElementsService(store).define(operator, dto))


@router.post("/{element_id}/change")
def change_element(
    element_id: str, dto: ChangeElement, operator: TheOperator, store: TheStore,
) -> ElementOut:
    return ElementOut.of(ElementsService(store).change(operator, element_id, dto))


@router.post("/totals")
def element_totals(dto: TotalsIn, operator: TheOperator, store: TheStore) -> TotalsOut:
    entries = [Entry(element_id=row.element_id, amount=row.amount) for row in dto.entries]
    return TotalsOut(**ElementsService(store).totals(operator, dto.employer_id, entries))
