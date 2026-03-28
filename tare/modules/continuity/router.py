"""Routes for runs of service."""

from fastapi import APIRouter, Query

from tare.common.deps import TheOperator, TheStore
from tare.modules.continuity.schemas import (
    ContinuityOut, EndService, ListService, RecordService, ServiceOut,
)
from tare.modules.continuity.service import ContinuityService

router = APIRouter(prefix="/continuity", tags=["continuity"])


@router.get("")
def list_service(
    operator: TheOperator, store: TheStore,
    employee_id: str | None = Query(default=None),
    limit: int | None = Query(default=None),
    offset: int | None = Query(default=None),
) -> dict:
    answer = ContinuityService(store).list(operator, ListService(
        employee_id=employee_id, limit=limit, offset=offset))
    return {"data": [ServiceOut.of(row) for row in answer["data"]],
            "total": answer["total"]}


@router.get("/of/{employee_id}")
def continuity_of(
    employee_id: str, upto: str, operator: TheOperator, store: TheStore,
) -> ContinuityOut:
    return ContinuityOut(**ContinuityService(store).of(operator, employee_id, upto))


@router.get("/{record_id}")
def get_record(record_id: str, operator: TheOperator, store: TheStore) -> ServiceOut:
    return ServiceOut.of(ContinuityService(store).get(operator, record_id))


@router.post("", status_code=201)
def record_service(
    dto: RecordService, operator: TheOperator, store: TheStore,
) -> ServiceOut:
    return ServiceOut.of(ContinuityService(store).record(operator, dto))


@router.post("/{record_id}/end")
def end_service(
    record_id: str, dto: EndService, operator: TheOperator, store: TheStore,
) -> ServiceOut:
    return ServiceOut.of(ContinuityService(store).end(operator, record_id, dto))
