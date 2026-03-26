"""Routes for benefit classes."""

from fastapi import APIRouter, Query

from tare.common.deps import TheOperator, TheStore
from tare.modules.valuations.schemas import (
    ClassOut, DefineClass, ListClasses, RevalueClass, WorthOut,
)
from tare.modules.valuations.service import ValuationsService

router = APIRouter(prefix="/valuations", tags=["valuations"])


@router.get("")
def list_classes(
    operator: TheOperator, store: TheStore,
    employer_id: str | None = Query(default=None),
    limit: int | None = Query(default=None),
    offset: int | None = Query(default=None),
) -> dict:
    answer = ValuationsService(store).list(operator, ListClasses(
        employer_id=employer_id, limit=limit, offset=offset))
    return {"data": [ClassOut.of(row) for row in answer["data"]],
            "total": answer["total"]}


@router.get("/{class_id}")
def get_class(class_id: str, operator: TheOperator, store: TheStore) -> ClassOut:
    return ClassOut.of(ValuationsService(store).get(operator, class_id))


@router.get("/{class_id}/worth")
def class_worth(
    class_id: str, days: int, operator: TheOperator, store: TheStore,
) -> WorthOut:
    return WorthOut(**ValuationsService(store).worth(operator, class_id, days))


@router.post("", status_code=201)
def define_class(dto: DefineClass, operator: TheOperator, store: TheStore) -> ClassOut:
    return ClassOut.of(ValuationsService(store).define(operator, dto))


@router.post("/{class_id}/revalue")
def revalue_class(
    class_id: str, dto: RevalueClass, operator: TheOperator, store: TheStore,
) -> ClassOut:
    return ClassOut.of(ValuationsService(store).revalue(operator, class_id, dto))
