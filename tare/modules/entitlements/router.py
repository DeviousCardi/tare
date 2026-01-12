"""Routes for entitlements."""

from fastapi import APIRouter, Query

from tare.common.deps import TheOperator, TheStore
from tare.modules.entitlements.schemas import (
    BalanceOut, ChangeEntitlement, EntitlementOut, GrantEntitlement, ListEntitlements,
)
from tare.modules.entitlements.service import EntitlementsService

router = APIRouter(prefix="/entitlements", tags=["entitlements"])


@router.get("")
def list_entitlements(
    operator: TheOperator, store: TheStore,
    employee_id: str | None = Query(default=None),
    year_starts_on: str | None = Query(default=None),
    limit: int | None = Query(default=None),
    offset: int | None = Query(default=None),
) -> dict:
    answer = EntitlementsService(store).list(operator, ListEntitlements(
        employee_id=employee_id, year_starts_on=year_starts_on,
        limit=limit, offset=offset))
    return {"data": [EntitlementOut.of(row) for row in answer["data"]],
            "total": answer["total"]}


@router.get("/balance/{employee_id}")
def entitlement_balance(
    employee_id: str, on: str, operator: TheOperator, store: TheStore,
) -> BalanceOut:
    return BalanceOut(**EntitlementsService(store).balance(operator, employee_id, on))


@router.get("/{entitlement_id}")
def get_entitlement(
    entitlement_id: str, operator: TheOperator, store: TheStore,
) -> EntitlementOut:
    return EntitlementOut.of(EntitlementsService(store).get(operator, entitlement_id))


@router.post("", status_code=201)
def grant_entitlement(
    dto: GrantEntitlement, operator: TheOperator, store: TheStore,
) -> EntitlementOut:
    return EntitlementOut.of(EntitlementsService(store).grant(operator, dto))


@router.post("/{entitlement_id}/change")
def change_entitlement(
    entitlement_id: str, dto: ChangeEntitlement, operator: TheOperator, store: TheStore,
) -> EntitlementOut:
    return EntitlementOut.of(EntitlementsService(store).change(
        operator, entitlement_id, dto))
