"""Routes for remittances."""

from fastapi import APIRouter, Query

from tare.common.deps import TheOperator, TheStore
from tare.modules.remittances.schemas import (
    ListRemittances, RaiseRemittance, RemittanceOut, SendRemittance,
)
from tare.modules.remittances.service import RemittancesService

router = APIRouter(prefix="/remittances", tags=["remittances"])


@router.get("")
def list_remittances(
    operator: TheOperator, store: TheStore,
    run_id: str | None = Query(default=None),
    provider_id: str | None = Query(default=None),
    waiting_only: bool = Query(default=False),
    limit: int | None = Query(default=None),
    offset: int | None = Query(default=None),
) -> dict:
    answer = RemittancesService(store).list(operator, ListRemittances(
        run_id=run_id, provider_id=provider_id, waiting_only=waiting_only,
        limit=limit, offset=offset))
    return {"data": [RemittanceOut.of(row) for row in answer["data"]],
            "total": answer["total"]}


@router.get("/overdue")
def overdue(on: str, operator: TheOperator, store: TheStore) -> dict:
    rows = RemittancesService(store).overdue(operator, on)
    return {"on": on, "data": [RemittanceOut.of(row) for row in rows],
            "total": len(rows)}


@router.get("/owed/{provider_id}")
def owed(provider_id: str, operator: TheOperator, store: TheStore) -> dict:
    return {"provider_id": provider_id,
            "owed": RemittancesService(store).owed(operator, provider_id)}


@router.get("/{remittance_id}")
def get_remittance(
    remittance_id: str, operator: TheOperator, store: TheStore,
) -> RemittanceOut:
    return RemittanceOut.of(RemittancesService(store).get(operator, remittance_id))


@router.post("", status_code=201)
def raise_remittance(
    dto: RaiseRemittance, operator: TheOperator, store: TheStore,
) -> RemittanceOut:
    return RemittanceOut.of(RemittancesService(store).raise_it(operator, dto))


@router.post("/{remittance_id}/send")
def send_remittance(
    remittance_id: str, dto: SendRemittance, operator: TheOperator, store: TheStore,
) -> RemittanceOut:
    return RemittanceOut.of(RemittancesService(store).send(operator, remittance_id, dto))
