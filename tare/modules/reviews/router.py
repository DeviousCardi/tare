"""Routes for reviews."""

from fastapi import APIRouter, Query

from tare.common.deps import TheOperator, TheStore
from tare.modules.employees.schemas import EmployeeOut
from tare.modules.reviews.schemas import CloseReview, ListReviews, OpenReview, ReviewOut
from tare.modules.reviews.service import ReviewsService

router = APIRouter(prefix="/reviews", tags=["reviews"])


@router.get("")
def list_reviews(
    operator: TheOperator, store: TheStore,
    employer_id: str | None = Query(default=None),
    open_only: bool = Query(default=False),
    limit: int | None = Query(default=None),
    offset: int | None = Query(default=None),
) -> dict:
    answer = ReviewsService(store).list(operator, ListReviews(
        employer_id=employer_id, open_only=open_only, limit=limit, offset=offset))
    return {"data": [ReviewOut.of(row) for row in answer["data"]],
            "total": answer["total"]}


@router.get("/{review_id}")
def get_review(review_id: str, operator: TheOperator, store: TheStore) -> ReviewOut:
    return ReviewOut.of(ReviewsService(store).get(operator, review_id))


@router.get("/{review_id}/population")
def review_population(review_id: str, operator: TheOperator, store: TheStore) -> dict:
    rows = ReviewsService(store).population(operator, review_id)
    return {"review_id": review_id,
            "data": [EmployeeOut.of(row) for row in rows], "total": len(rows)}


@router.post("", status_code=201)
def open_review(dto: OpenReview, operator: TheOperator, store: TheStore) -> ReviewOut:
    return ReviewOut.of(ReviewsService(store).open(operator, dto))


@router.post("/{review_id}/close")
def close_review(
    review_id: str, dto: CloseReview, operator: TheOperator, store: TheStore,
) -> ReviewOut:
    return ReviewOut.of(ReviewsService(store).close(operator, review_id, dto))
