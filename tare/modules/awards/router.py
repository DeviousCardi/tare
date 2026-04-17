"""Routes for awards."""

from fastapi import APIRouter, Query

from tare.common.deps import TheOperator, TheStore
from tare.modules.awards.schemas import AwardOut, ListAwards, MakeAward, ReviewCostOut
from tare.modules.awards.service import AwardsService

router = APIRouter(prefix="/awards", tags=["awards"])


@router.get("")
def list_awards(
    operator: TheOperator, store: TheStore,
    review_id: str | None = Query(default=None),
    employee_id: str | None = Query(default=None),
    limit: int | None = Query(default=None),
    offset: int | None = Query(default=None),
) -> dict:
    answer = AwardsService(store).list(operator, ListAwards(
        review_id=review_id, employee_id=employee_id, limit=limit, offset=offset))
    return {"data": [AwardOut.of(row) for row in answer["data"]],
            "total": answer["total"]}


@router.get("/cost/{review_id}")
def review_cost(review_id: str, operator: TheOperator, store: TheStore) -> ReviewCostOut:
    return ReviewCostOut(**AwardsService(store).cost(operator, review_id))


@router.get("/{award_id}")
def get_award(award_id: str, operator: TheOperator, store: TheStore) -> AwardOut:
    return AwardOut.of(AwardsService(store).get(operator, award_id))


@router.post("", status_code=201)
def make_award(dto: MakeAward, operator: TheOperator, store: TheStore) -> AwardOut:
    return AwardOut.of(AwardsService(store).make(operator, dto))
