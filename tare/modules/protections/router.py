"""Routes for protected earnings."""

from fastapi import APIRouter, Query

from tare.common.deps import TheOperator, TheStore
from tare.modules.protections.schemas import (
    EndProtection, ListProtections, ProtectionOut, ReachOut, SetProtection,
)
from tare.modules.protections.service import ProtectionsService

router = APIRouter(prefix="/protections", tags=["protections"])


@router.get("")
def list_protections(
    operator: TheOperator, store: TheStore,
    employee_id: str | None = Query(default=None),
    standing_on: str | None = Query(default=None),
    limit: int | None = Query(default=None),
    offset: int | None = Query(default=None),
) -> dict:
    answer = ProtectionsService(store).list(operator, ListProtections(
        employee_id=employee_id, standing_on=standing_on, limit=limit, offset=offset))
    return {"data": [ProtectionOut.of(row) for row in answer["data"]],
            "total": answer["total"]}


@router.get("/reach/{employee_id}")
def reach(
    employee_id: str, on: str, pay: int, asked: int,
    operator: TheOperator, store: TheStore,
) -> ReachOut:
    return ReachOut(**ProtectionsService(store).reach(
        operator, employee_id, on, pay, asked))


@router.get("/{protection_id}")
def get_protection(
    protection_id: str, operator: TheOperator, store: TheStore,
) -> ProtectionOut:
    return ProtectionOut.of(ProtectionsService(store).get(operator, protection_id))


@router.post("", status_code=201)
def set_protection(
    dto: SetProtection, operator: TheOperator, store: TheStore,
) -> ProtectionOut:
    return ProtectionOut.of(ProtectionsService(store).set(operator, dto))


@router.post("/{protection_id}/end")
def end_protection(
    protection_id: str, dto: EndProtection, operator: TheOperator, store: TheStore,
) -> ProtectionOut:
    return ProtectionOut.of(ProtectionsService(store).end(operator, protection_id, dto))
