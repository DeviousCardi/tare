"""Routes for determinations."""

from fastapi import APIRouter, Query

from tare.common.deps import TheOperator, TheStore
from tare.modules.determinations.schemas import (
    DecideEngagement, DeterminationOut, ListDeterminations,
)
from tare.modules.determinations.service import DeterminationsService

router = APIRouter(prefix="/determinations", tags=["determinations"])


@router.get("")
def list_determinations(
    operator: TheOperator, store: TheStore,
    engagement_id: str | None = Query(default=None),
    employer_id: str | None = Query(default=None),
    inside_only: bool = Query(default=False),
    limit: int | None = Query(default=None),
    offset: int | None = Query(default=None),
) -> dict:
    answer = DeterminationsService(store).list(operator, ListDeterminations(
        engagement_id=engagement_id, employer_id=employer_id,
        inside_only=inside_only, limit=limit, offset=offset))
    return {"data": [DeterminationOut.of(row) for row in answer["data"]],
            "total": answer["total"]}


@router.get("/owed/{employer_id}")
def owed(employer_id: str, operator: TheOperator, store: TheStore) -> dict:
    return {"employer_id": employer_id,
            "deemed": DeterminationsService(store).owed(operator, employer_id)}


@router.get("/{determination_id}")
def get_determination(
    determination_id: str, operator: TheOperator, store: TheStore,
) -> DeterminationOut:
    return DeterminationOut.of(
        DeterminationsService(store).get(operator, determination_id))


@router.post("", status_code=201)
def decide_engagement(
    dto: DecideEngagement, operator: TheOperator, store: TheStore,
) -> DeterminationOut:
    return DeterminationOut.of(DeterminationsService(store).decide(operator, dto))
