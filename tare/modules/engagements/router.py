"""Routes for engagements."""

from fastapi import APIRouter, Query

from tare.common.deps import TheOperator, TheStore
from tare.modules.engagements.schemas import (
    EndEngagement, EngagementOut, ListEngagements, OpenEngagement,
)
from tare.modules.engagements.service import EngagementsService

router = APIRouter(prefix="/engagements", tags=["engagements"])


@router.get("")
def list_engagements(
    operator: TheOperator, store: TheStore,
    employer_id: str | None = Query(default=None),
    running_on: str | None = Query(default=None),
    limit: int | None = Query(default=None),
    offset: int | None = Query(default=None),
) -> dict:
    answer = EngagementsService(store).list(operator, ListEngagements(
        employer_id=employer_id, running_on=running_on, limit=limit, offset=offset))
    return {"data": [EngagementOut.of(row) for row in answer["data"]],
            "total": answer["total"]}


@router.get("/{engagement_id}")
def get_engagement(
    engagement_id: str, operator: TheOperator, store: TheStore,
) -> EngagementOut:
    return EngagementOut.of(EngagementsService(store).get(operator, engagement_id))


@router.get("/{engagement_id}/inside")
def engagement_inside(
    engagement_id: str, operator: TheOperator, store: TheStore,
) -> dict:
    return {"engagement_id": engagement_id,
            "inside": EngagementsService(store).inside(operator, engagement_id)}


@router.post("", status_code=201)
def open_engagement(
    dto: OpenEngagement, operator: TheOperator, store: TheStore,
) -> EngagementOut:
    return EngagementOut.of(EngagementsService(store).open(operator, dto))


@router.post("/{engagement_id}/end")
def end_engagement(
    engagement_id: str, dto: EndEngagement, operator: TheOperator, store: TheStore,
) -> EngagementOut:
    return EngagementOut.of(EngagementsService(store).end(operator, engagement_id, dto))
