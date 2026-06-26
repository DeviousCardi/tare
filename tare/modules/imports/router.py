"""Routes for import batches."""

from fastapi import APIRouter, Query

from tare.common.deps import TheOperator, TheStore
from tare.modules.imports.schemas import (
    BatchOut, BatchStateOut, DecideBatch, ListBatches, ReceiveBatch,
)
from tare.modules.imports.service import ImportsService

router = APIRouter(prefix="/imports", tags=["imports"])


@router.get("")
def list_batches(
    operator: TheOperator, store: TheStore,
    employer_id: str | None = Query(default=None),
    kind: str | None = Query(default=None),
    open_only: bool = Query(default=False),
    start: str | None = Query(default=None),
    end: str | None = Query(default=None),
    limit: int | None = Query(default=None),
    offset: int | None = Query(default=None),
) -> dict:
    answer = ImportsService(store).list(operator, ListBatches(
        employer_id=employer_id, kind=kind, open_only=open_only, start=start,
        end=end, limit=limit, offset=offset))
    return {"data": [BatchOut.of(row) for row in answer["data"]],
            "total": answer["total"]}


@router.get("/{batch_id}")
def get_batch(batch_id: str, operator: TheOperator, store: TheStore) -> BatchOut:
    return BatchOut.of(ImportsService(store).get(operator, batch_id))


@router.get("/{batch_id}/state")
def batch_state(
    batch_id: str, operator: TheOperator, store: TheStore,
) -> BatchStateOut:
    return BatchStateOut(**ImportsService(store).state(operator, batch_id))


@router.post("", status_code=201)
def receive_batch(dto: ReceiveBatch, operator: TheOperator, store: TheStore) -> BatchOut:
    return BatchOut.of(ImportsService(store).receive(operator, dto))


@router.post("/{batch_id}/decide")
def decide_batch(
    batch_id: str, dto: DecideBatch, operator: TheOperator, store: TheStore,
) -> BatchOut:
    return BatchOut.of(ImportsService(store).decide(operator, batch_id, dto))
