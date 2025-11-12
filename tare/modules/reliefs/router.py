"""Routes for reliefs."""

from fastapi import APIRouter, Query

from tare.common.deps import TheOperator, TheStore
from tare.modules.reliefs.schemas import (
    ListReliefs, PublishRelief, ReliefAppliedOut, ReliefOut,
)
from tare.modules.reliefs.service import ReliefsService

router = APIRouter(prefix="/reliefs", tags=["reliefs"])


@router.get("")
def list_reliefs(
    operator: TheOperator, store: TheStore,
    code: str | None = Query(default=None),
    in_force_on: str | None = Query(default=None),
    limit: int | None = Query(default=None),
    offset: int | None = Query(default=None),
) -> dict:
    answer = ReliefsService(store).list(operator, ListReliefs(
        code=code, in_force_on=in_force_on, limit=limit, offset=offset))
    return {"data": [ReliefOut.of(row) for row in answer["data"]],
            "total": answer["total"]}


@router.get("/{code}/applied")
def relief_applied(
    code: str, on: str, pay: int, operator: TheOperator, store: TheStore,
) -> ReliefAppliedOut:
    return ReliefAppliedOut(**ReliefsService(store).applied(code, on, pay))


@router.get("/row/{relief_id}")
def get_relief(relief_id: str, operator: TheOperator, store: TheStore) -> ReliefOut:
    return ReliefOut.of(ReliefsService(store).get(operator, relief_id))


@router.post("", status_code=201)
def publish_relief(dto: PublishRelief, operator: TheOperator, store: TheStore) -> ReliefOut:
    return ReliefOut.of(ReliefsService(store).publish(operator, dto))
